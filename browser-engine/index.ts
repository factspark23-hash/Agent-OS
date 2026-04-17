/**
 * index.ts — Browser Engine Mini Service v2.1
 * Anti-detection browser engine powering social media automation.
 * Features: CDP Connection, Smart Browser Modes (Full/Light/Ghost),
 * Dual-Layer State Persistence, Handoff Controller, Auto Tab Management,
 * Rate Limiting, Request Validation, Graceful Shutdown.
 *
 * HTTP + WebSocket server on port 3003.
 */

import { createServer, IncomingMessage, ServerResponse } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { randomUUID } from "crypto";
import * as fs from "fs";
import * as path from "path";

import { generateFingerprint, BrowserFingerprint } from "./fingerprint";
import { getMasterStealthScript } from "./stealth";
import * as stateManager from "./state-manager";
import {
  connectToCDP,
  checkCDPPort,
  discoverCDPPort,
  getChromeVersion,
  getCDPTargets,
  getChromeLaunchInstruction,
  CDPConnectionResult,
} from "./cdp-connector";
import {
  launchSmartSession,
  closeSmartSession,
  decideMode,
  detectTaskCategory,
  SmartSession,
  BrowserMode,
  TaskCategory,
  ModeDecision,
} from "./browser-modes";
import { TabManager, TabManagerConfig, MemoryStats } from "./tab-manager";
import { getPlaywright } from "./browser-utils";
import * as instagramAdapter from "./platforms/instagram";
import * as twitterAdapter from "./platforms/twitter";
import * as linkedinAdapter from "./platforms/linkedin";
import * as facebookAdapter from "./platforms/facebook";

// ─── Types ───────────────────────────────────────────────────────────────────

interface LegacyBrowserSession {
  sessionId: string;
  platform: string;
  username: string;
  stateId: string;
  fingerprint: BrowserFingerprint;
  browser: any;
  context: any;
  page: any;
  cdpSession: any;
  cdpPort: number;
  createdAt: string;
  lastActivity: string;
  handover: {
    active: boolean;
    reason: string;
    startedAt: string | null;
    sseClients: Set<ServerResponse>;
    screenshotInterval: NodeJS.Timeout | null;
  };
}

// ─── Globals ─────────────────────────────────────────────────────────────────

const PORT = 3003;
const CDP_PORT_START = 9300;
let nextCdpPort = CDP_PORT_START;
const START_TIME = Date.now();

// Smart sessions (new mode-aware sessions)
const smartSessions = new Map<string, SmartSession>();

// Legacy sessions (backward compat)
const legacySessions = new Map<string, LegacyBrowserSession>();

// Tab manager
const tabManager = new TabManager(
  {
    maxMemoryMB: 1024,
    lightIdleTimeoutSec: 30,
    fullIdleTimeoutSec: 300,
    maxLightTabs: 5,
    maxFullSessions: 3,
    checkIntervalSec: 10,
    autoCloseIdle: true,
  },
  async (tabId, sessionId) => {
    // When tab manager closes a tab, also close the smart session
    const session = smartSessions.get(sessionId);
    if (session) {
      await closeSmartSession(session);
      smartSessions.delete(sessionId);
    }
  }
);

// ─── Rate Limiter ────────────────────────────────────────────────────────────

const rateLimiter = {
  requests: new Map<string, { count: number; resetTime: number }>(),
  maxRequests: 100,
  windowMs: 60000, // 1 minute

  check(ip: string): { allowed: boolean; remaining: number } {
    const now = Date.now();
    const entry = this.requests.get(ip);
    if (!entry || now > entry.resetTime) {
      this.requests.set(ip, { count: 1, resetTime: now + this.windowMs });
      return { allowed: true, remaining: this.maxRequests - 1 };
    }
    entry.count++;
    return {
      allowed: entry.count <= this.maxRequests,
      remaining: Math.max(0, this.maxRequests - entry.count),
    };
  },

  cleanup() {
    const now = Date.now();
    for (const [ip, entry] of this.requests) {
      if (now > entry.resetTime) this.requests.delete(ip);
    }
  },
};

// Cleanup rate limiter every 5 minutes
setInterval(() => rateLimiter.cleanup(), 300000);

// ─── Utility ─────────────────────────────────────────────────────────────────

function corsHeaders(res: ServerResponse) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
}

function sendJson(res: ServerResponse, status: number, data: any) {
  corsHeaders(res);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
    req.on("error", reject);
  });
}

/**
 * Parse request body as JSON with error handling.
 * Returns null and sends 400 if JSON is malformed.
 */
async function parseBody(req: IncomingMessage, res: ServerResponse): Promise<Record<string, any> | null> {
  try {
    const raw = await readBody(req);
    return JSON.parse(raw);
  } catch (err: any) {
    sendJson(res, 400, { error: "Invalid JSON in request body", details: err.message });
    return null;
  }
}

/**
 * Validate that required fields are present in the request body.
 * Returns true if all fields are present, false (and sends 400) if any are missing.
 */
function validateRequired(res: ServerResponse, body: Record<string, any>, fields: string[]): boolean {
  for (const field of fields) {
    if (body[field] === undefined || body[field] === null || body[field] === "") {
      sendJson(res, 400, { error: `Missing required field: ${field}` });
      return false;
    }
  }
  return true;
}

function getNextCdpPort(): number {
  const port = nextCdpPort;
  nextCdpPort++;
  return port;
}

function getClientIp(req: IncomingMessage): string {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string") return forwarded.split(",")[0].trim();
  if (Array.isArray(forwarded)) return forwarded[0].trim();
  return req.socket?.remoteAddress || "unknown";
}

// ─── Legacy Browser Launch (backward compat) ────────────────────────────────

async function ensureXvfb(): Promise<void> {
  try {
    const { execSync } = await import("child_process");
    execSync("pgrep -x Xvfb", { stdio: "ignore" });
  } catch {
    try {
      const { execSync } = await import("child_process");
      execSync("Xvfb :99 -screen 0 1920x1080x24 &", { stdio: "ignore" });
      process.env.DISPLAY = ":99";
      console.log("[BrowserEngine] Started Xvfb on :99");
      await new Promise((r) => setTimeout(r, 500));
    } catch (err) {
      console.log("[BrowserEngine] Could not start Xvfb, will try headless mode");
    }
  }
}

async function launchBrowserInstance(
  platform: string,
  username: string,
  stateId: string
): Promise<LegacyBrowserSession> {
  const pw = await getPlaywright();
  const fingerprint = generateFingerprint();
  const cdpPort = getNextCdpPort();

  const launchArgs = [
    `--window-size=${fingerprint.screenWidth},${fingerprint.screenHeight}`,
    `--remote-debugging-port=${cdpPort}`,
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-site-isolation-trials",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
    "--disable-infobars",
    "--disable-breakpad",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-client-side-phishing-detection",
    "--disable-hang-monitor",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-ipc-flooding-protection",
    `--user-agent=${fingerprint.userAgent}`,
    "--lang=en-US",
  ];

  let browser: any;
  try {
    await ensureXvfb();
    if (process.env.DISPLAY) {
      browser = await pw.chromium.launch({
        headless: false,
        args: launchArgs,
        env: { ...process.env, DISPLAY: process.env.DISPLAY || ":99" },
      });
      console.log("[BrowserEngine] Launched in HEADED mode (virtual framebuffer)");
    } else {
      throw new Error("No DISPLAY, falling back to headless");
    }
  } catch {
    launchArgs.push("--headless=new");
    browser = await pw.chromium.launch({
      headless: true,
      args: launchArgs,
    });
    console.log("[BrowserEngine] Launched in HEADLESS mode");
  }

  const context = await browser.newContext({
    userAgent: fingerprint.userAgent,
    viewport: { width: fingerprint.availWidth, height: fingerprint.availHeight },
    screen: { width: fingerprint.screenWidth, height: fingerprint.screenHeight },
    colorScheme: "light",
    locale: "en-US",
    timezoneId: fingerprint.timezone,
    deviceScaleFactor: fingerprint.pixelRatio,
    hasTouch: fingerprint.maxTouchPoints > 0,
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: { "Accept-Language": fingerprint.languages.join(",") },
  });

  const page = await context.newPage();
  const cdpSession = await page.context().newCDPSession(page);

  // FIX #13: Removed duplicate webdriver override — stealth script already handles it
  const stealthScript = getMasterStealthScript(fingerprint);
  await cdpSession.send("Page.addScriptToEvaluateOnNewDocument", { source: stealthScript });

  // FIX #1: Log CDP grantPermissions failure instead of silently swallowing
  try {
    await cdpSession.send("Browser.grantPermissions", {
      origin: "",
      permissions: ["geolocation", "notifications", "midi", "clipboardReadWrite", "clipboardSanitizedWrite"],
    });
  } catch (err: any) {
    console.warn("[BrowserEngine] CDP grantPermissions failed:", err.message || err);
  }

  const sessionId = randomUUID();

  const session: LegacyBrowserSession = {
    sessionId, platform, username, stateId, fingerprint, browser, context, page,
    cdpSession, cdpPort,
    createdAt: new Date().toISOString(),
    lastActivity: new Date().toISOString(),
    handover: { active: false, reason: "", startedAt: null, sseClients: new Set(), screenshotInterval: null },
  };

  legacySessions.set(sessionId, session);
  console.log(`[BrowserEngine] Launched legacy session ${sessionId} for ${platform}/${username} (CDP port: ${cdpPort})`);
  return session;
}

// ─── Accessibility Tree Snapshot ─────────────────────────────────────────────

interface SnapshotNode {
  type: string; name: string; ref?: string; value?: string; children?: SnapshotNode[];
  text?: string; role?: string; checked?: string; disabled?: boolean; required?: boolean;
  level?: number; url?: string; placeholder?: string;
}

async function getAccessibilityTree(page: any): Promise<SnapshotNode[]> {
  // Try Playwright accessibility API first
  try {
    if (page.accessibility && typeof page.accessibility.snapshot === 'function') {
      const snapshot = await page.accessibility.snapshot();
      if (snapshot) {
        function flatten(node: any, depth: number = 0): SnapshotNode[] {
          const result: SnapshotNode[] = [];
          const entry: SnapshotNode = { type: node.role || "unknown", name: node.name || "" };
          if (node.value) entry.value = node.value;
          if (node.checked !== undefined) entry.checked = String(node.checked);
          if (node.disabled) entry.disabled = true;
          if (node.required) entry.required = true;
          if (node.level) entry.level = node.level;
          if (node.url) entry.url = node.url;
          if (node.placeholder) entry.placeholder = node.placeholder;

          const interactableRoles = ["button", "link", "textbox", "combobox", "searchbox", "checkbox", "radio", "switch", "menuitem", "tab", "treeitem", "option", "heading"];
          if (interactableRoles.includes(node.role)) {
            entry.ref = `ref-${Buffer.from(`${node.role}:${node.name}:${depth}`).toString("base64")}`;
          }

          if (node.children) {
            entry.children = [];
            for (const child of node.children) { entry.children.push(...flatten(child, depth + 1)); }
          }
          result.push(entry);
          return result;
        }
        return flatten(snapshot);
      }
    }
  } catch (err: any) {
    console.error("[BrowserEngine] Accessibility snapshot failed, using JS fallback:", err.message);
  }

  // Fallback: Use JavaScript to extract interactive elements from the DOM
  try {
    const elements = await page.evaluate(() => {
      const result: any[] = [];
      const selectors = 'input, button, a, select, textarea, [role="button"], [role="link"], [role="textbox"], [role="combobox"], [role="checkbox"], [role="radio"], h1, h2, h3, h4, h5, h6';
      const nodes = document.querySelectorAll(selectors);
      for (const el of nodes) {
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type') || '';
        const name = el.getAttribute('name') || el.textContent?.substring(0, 50) || '';
        const placeholder = el.getAttribute('placeholder') || '';
        const href = el.getAttribute('href') || '';
        const role = el.getAttribute('role') || '';
        const ariaLabel = el.getAttribute('aria-label') || '';

        let nodeType = tag;
        if (tag === 'input') nodeType = type === 'password' ? 'password' : type === 'checkbox' ? 'checkbox' : type === 'radio' ? 'radio' : 'textbox';
        else if (tag === 'button' || role === 'button') nodeType = 'button';
        else if (tag === 'a' || role === 'link') nodeType = 'link';
        else if (tag === 'select') nodeType = 'combobox';
        else if (tag === 'textarea') nodeType = 'textbox';
        else if (tag.startsWith('h')) nodeType = 'heading';

        result.push({
          type: nodeType,
          name: ariaLabel || name,
          value: (el as HTMLInputElement).value || '',
          placeholder,
          url: href,
          disabled: (el as HTMLInputElement).disabled || false,
          required: (el as HTMLInputElement).required || false,
        });
      }
      return result;
    });
    return elements;
  } catch (err: any) {
    console.error("[BrowserEngine] JS fallback extraction failed:", err.message);
    return [];
  }
}

// ─── Element Interaction via Accessibility ───────────────────────────────────

// FIX #2: clickByRef — add debug logging, fix early return bug
async function clickByRef(page: any, ref: string): Promise<void> {
  const decoded = Buffer.from(ref.replace("ref-", ""), "base64").toString();
  const [role, ...nameParts] = decoded.split(":");
  const name = nameParts.join(":");

  // Strategy 1: Find by [role] attribute and matching text/aria-label/title
  try {
    const selector = `[role="${role}"]`;
    const elements = await page.$$(selector);
    for (const el of elements) {
      const text = await el.textContent().catch(() => "");
      const ariaLabel = await el.getAttribute("aria-label").catch(() => "");
      const title = await el.getAttribute("title").catch(() => "");
      if (text?.includes(name) || ariaLabel?.includes(name) || title?.includes(name)) {
        await el.click(); return;
      }
    }
  } catch (err: any) {
    console.debug(`[BrowserEngine] clickByRef: role-attribute strategy failed for ref=${ref}:`, err.message);
  }

  // Strategy 2: getByText
  try {
    await page.getByText(name, { exact: false }).first().click({ timeout: 3000 });
    return;
  } catch (err: any) {
    console.debug(`[BrowserEngine] clickByRef: getByText strategy failed for name="${name}":`, err.message);
  }

  // Strategy 3: getByLabel
  try {
    await page.getByLabel(name, { exact: false }).first().click({ timeout: 3000 });
    return;
  } catch (err: any) {
    console.debug(`[BrowserEngine] clickByRef: getByLabel strategy failed for name="${name}":`, err.message);
  }

  // Strategy 4: getByRole — only return on SUCCESS, don't early-return on unhandled roles
  try {
    if (role === "button") {
      await page.getByRole("button", { name, exact: false }).first().click({ timeout: 3000 });
      return;
    } else if (role === "link") {
      await page.getByRole("link", { name, exact: false }).first().click({ timeout: 3000 });
      return;
    } else if (role === "textbox") {
      await page.getByRole("textbox", { name, exact: false }).first().click({ timeout: 3000 });
      return;
    }
    // For unhandled roles, fall through to the error below
  } catch (err: any) {
    console.debug(`[BrowserEngine] clickByRef: getByRole strategy failed for role=${role}, name="${name}":`, err.message);
  }

  throw new Error(`Could not find element with ref: ${ref}`);
}

// FIX #3: fillByRef — add debug logging to empty catches
async function fillByRef(page: any, ref: string, value: string): Promise<void> {
  const decoded = Buffer.from(ref.replace("ref-", ""), "base64").toString();
  const [role, ...nameParts] = decoded.split(":");
  const name = nameParts.join(":");

  // Strategy 1: getByLabel
  try {
    await page.getByLabel(name, { exact: false }).first().fill(value, { timeout: 3000 });
    return;
  } catch (err: any) {
    console.debug(`[BrowserEngine] fillByRef: getByLabel strategy failed for name="${name}":`, err.message);
  }

  // Strategy 2: getByPlaceholder
  try {
    await page.getByPlaceholder(name, { exact: false }).first().fill(value, { timeout: 3000 });
    return;
  } catch (err: any) {
    console.debug(`[BrowserEngine] fillByRef: getByPlaceholder strategy failed for name="${name}":`, err.message);
  }

  // Strategy 3: getByRole("textbox")
  try {
    await page.getByRole("textbox", { name, exact: false }).first().fill(value, { timeout: 3000 });
    return;
  } catch (err: any) {
    console.debug(`[BrowserEngine] fillByRef: getByRole(textbox) strategy failed for name="${name}":`, err.message);
  }

  // Strategy 4: Manual DOM scan for matching inputs
  try {
    const inputs = await page.$$("input, textarea");
    for (const input of inputs) {
      const placeholder = await input.getAttribute("placeholder").catch(() => "");
      const ariaLabel = await input.getAttribute("aria-label").catch(() => "");
      const nameAttr = await input.getAttribute("name").catch(() => "");
      if (placeholder?.includes(name) || ariaLabel?.includes(name) || nameAttr?.includes(name)) {
        await input.fill(value); return;
      }
    }
  } catch (err: any) {
    console.debug(`[BrowserEngine] fillByRef: DOM scan strategy failed for name="${name}":`, err.message);
  }

  throw new Error(`Could not find input element with ref: ${ref}`);
}

// ─── Screenshot Helper ───────────────────────────────────────────────────────

async function takeScreenshot(session: SmartSession | LegacyBrowserSession): Promise<string> {
  const page = session.page;
  if (!page) throw new Error("No page available");
  const buffer = await page.screenshot({ type: "jpeg", quality: 75 });
  return buffer.toString("base64");
}

// ─── Handover Management ─────────────────────────────────────────────────────

// FIX #4: Log screenshot errors in startHandoverStreaming
function startHandoverStreaming(session: SmartSession | LegacyBrowserSession): void {
  if (session.handover.screenshotInterval) return;

  session.handover.screenshotInterval = setInterval(async () => {
    if (session.handover.sseClients.size === 0) return;
    try {
      const base64 = await takeScreenshot(session);
      const data = `data: ${JSON.stringify({ type: "screenshot", data: base64, timestamp: Date.now() })}\n\n`;
      const deadClients: ServerResponse[] = [];
      for (const client of session.handover.sseClients) {
        try { client.write(data); } catch { deadClients.push(client as ServerResponse); }
      }
      for (const client of deadClients) { session.handover.sseClients.delete(client); }
    } catch (err: any) {
      console.warn("[BrowserEngine] Handover screenshot capture failed:", err.message || err);
    }
  }, 500);
}

function stopHandoverStreaming(session: SmartSession | LegacyBrowserSession): void {
  if (session.handover.screenshotInterval) {
    clearInterval(session.handover.screenshotInterval);
    session.handover.screenshotInterval = null;
  }
  for (const client of session.handover.sseClients) { try { client.end(); } catch {} }
  session.handover.sseClients.clear();
}

// ─── Platform Adapter Router ─────────────────────────────────────────────────

async function getPlatformAdapter(platform: string) {
  switch (platform) {
    case "instagram": return instagramAdapter;
    case "twitter": case "x": return twitterAdapter;
    case "linkedin": return linkedinAdapter;
    case "facebook": return facebookAdapter;
    default: throw new Error(`Unknown platform: ${platform}`);
  }
}

// ─── Helper: Get page from any session type ──────────────────────────────────

function getSessionPage(sessionId: string): { page: any; cdpSession: any; platform: string; username: string; type: "smart" | "legacy" } | null {
  const smart = smartSessions.get(sessionId);
  if (smart) return { page: smart.page, cdpSession: smart.cdpSession, platform: smart.platform, username: smart.username, type: "smart" };
  const legacy = legacySessions.get(sessionId);
  if (legacy) return { page: legacy.page, cdpSession: legacy.cdpSession, platform: legacy.platform, username: legacy.username, type: "legacy" };
  return null;
}

function getSessionHandover(sessionId: string) {
  const smart = smartSessions.get(sessionId);
  if (smart) return smart.handover;
  const legacy = legacySessions.get(sessionId);
  if (legacy) return legacy.handover;
  return null;
}

function updateSessionActivity(sessionId: string): void {
  const smart = smartSessions.get(sessionId);
  if (smart) { smart.lastActivity = new Date().toISOString(); return; }
  const legacy = legacySessions.get(sessionId);
  if (legacy) { legacy.lastActivity = new Date().toISOString(); }
}

// ─── HTTP Request Handler ────────────────────────────────────────────────────

async function handleRequest(req: IncomingMessage, res: ServerResponse) {
  const url = new URL(req.url || "/", `http://localhost:${PORT}`);
  const pathname = url.pathname;
  const method = req.method || "GET";

  if (method === "OPTIONS") { corsHeaders(res); res.writeHead(204); res.end(); return; }

  // FIX #17: Rate limiting
  const clientIp = getClientIp(req);
  const rateCheck = rateLimiter.check(clientIp);
  if (!rateCheck.allowed) {
    sendJson(res, 429, { error: "Too many requests", retryAfter: 60 });
    return;
  }

  try {
    // ═══════════════════════════════════════════════════════════════════════
    // CDP ENDPOINTS (NEW)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/cdp/check" && method === "GET") {
      const port = parseInt(url.searchParams.get("port") || "9222");
      const available = await checkCDPPort("localhost", port);
      sendJson(res, 200, { available, port });
      return;
    }

    if (pathname === "/api/cdp/discover" && method === "GET") {
      const port = await discoverCDPPort();
      sendJson(res, 200, { found: port !== null, port });
      return;
    }

    if (pathname === "/api/cdp/version" && method === "GET") {
      const port = parseInt(url.searchParams.get("port") || "9222");
      const version = await getChromeVersion("localhost", port);
      sendJson(res, 200, { version, port });
      return;
    }

    if (pathname === "/api/cdp/targets" && method === "GET") {
      const port = parseInt(url.searchParams.get("port") || "9222");
      const targets = await getCDPTargets("localhost", port);
      sendJson(res, 200, { targets, count: targets.length });
      return;
    }

    if (pathname === "/api/cdp/connect" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { cdpPort, autoDiscover } = body;
      const result = await connectToCDP({
        cdpPort: cdpPort || 9222,
        autoDiscover: autoDiscover !== false,
      });
      sendJson(res, 200, result);
      return;
    }

    if (pathname === "/api/cdp/launch-instruction" && method === "GET") {
      const port = parseInt(url.searchParams.get("port") || "9222");
      const instruction = getChromeLaunchInstruction(port);
      sendJson(res, 200, instruction);
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SMART MODE ENDPOINTS (NEW)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/modes/decide" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { taskCategory, description, platform, url: taskUrl, forceMode } = body;

      let category: TaskCategory = taskCategory;
      if (!category && description) {
        category = detectTaskCategory(description);
      }
      if (!category) category = "custom";

      const decision = decideMode(category, platform, taskUrl, forceMode);
      sendJson(res, 200, { taskCategory: category, decision });
      return;
    }

    if (pathname === "/api/modes/detect-task" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { description } = body;
      const category = detectTaskCategory(description || "");
      const decision = decideMode(category);
      sendJson(res, 200, { category, decision });
      return;
    }

    if (pathname === "/api/smart/launch" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { taskCategory, platform, username, cdpPort, forceMode, url: taskUrl } = body;

      if (!platform || !username) {
        sendJson(res, 400, { error: "platform and username are required" });
        return;
      }

      // Check if we can launch
      const mode = forceMode || decideMode(taskCategory || "custom", platform, taskUrl).mode;
      const canLaunch = tabManager.canLaunch(mode);
      if (!canLaunch.allowed) {
        sendJson(res, 429, { error: canLaunch.reason });
        return;
      }

      const { session, decision } = await launchSmartSession(
        taskCategory || "custom",
        platform,
        username,
        { cdpPort, forceMode, url: taskUrl }
      );

      smartSessions.set(session.sessionId, session);

      // Register with tab manager
      tabManager.registerTab(
        session.sessionId,
        session.sessionId,
        session.mode,
        "",
        "",
        session.memoryEstimateMB
      );

      // Try to load saved state
      if (session.page && session.cdpSession) {
        await stateManager.loadState(session.cdpSession, session.page, platform, username);
      }

      sendJson(res, 200, {
        sessionId: session.sessionId,
        mode: session.mode,
        decision,
        cdpPort: session.cdpPort,
        memoryEstimateMB: session.memoryEstimateMB,
      });
      return;
    }

    if (pathname === "/api/smart/close" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId } = body;
      const session = smartSessions.get(sessionId);

      if (!session) {
        sendJson(res, 404, { error: "Smart session not found" });
        return;
      }

      // FIX #5: Save state before closing — track success, log errors
      let autoSaved = false;
      if (session.page && session.cdpSession) {
        try {
          await stateManager.saveState(session.cdpSession, session.page, session.platform, session.username);
          autoSaved = true;
        } catch (err: any) {
          console.warn("[BrowserEngine] Auto-save before smart session close failed:", err.message || err);
        }
      }

      stopHandoverStreaming(session);
      await closeSmartSession(session);
      smartSessions.delete(sessionId);
      tabManager.markTaskComplete(sessionId);

      sendJson(res, 200, { status: "closed", autoSaved });
      return;
    }

    if (pathname === "/api/smart/mode" && method === "GET") {
      const sessionId = url.searchParams.get("sessionId");
      const session = smartSessions.get(sessionId || "");

      if (!session) {
        sendJson(res, 404, { error: "Smart session not found" });
        return;
      }

      sendJson(res, 200, {
        sessionId: session.sessionId,
        mode: session.mode,
        platform: session.platform,
        taskCategory: session.taskCategory,
        memoryEstimateMB: session.memoryEstimateMB,
        createdAt: session.createdAt,
        lastActivity: session.lastActivity,
        taskComplete: session.taskComplete,
        handoverActive: session.handover.active,
      });
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TAB MANAGER ENDPOINTS (NEW)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/tabs/stats" && method === "GET") {
      const stats = tabManager.getMemoryStats();
      sendJson(res, 200, stats);
      return;
    }

    if (pathname === "/api/tabs/list" && method === "GET") {
      const tabs = tabManager.getAllTabs();
      sendJson(res, 200, { tabs });
      return;
    }

    if (pathname === "/api/tabs/can-launch" && method === "GET") {
      const mode = (url.searchParams.get("mode") || "light") as BrowserMode;
      const result = tabManager.canLaunch(mode);
      sendJson(res, 200, result);
      return;
    }

    if (pathname === "/api/tabs/force-cleanup" && method === "POST") {
      const closed = await tabManager.forceCleanup();
      sendJson(res, 200, { closed, stats: tabManager.getMemoryStats() });
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LEGACY Browser Endpoints (backward compat)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/browser/launch" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { platform, username, stateId } = body;

      if (!platform || !username) {
        sendJson(res, 400, { error: "platform and username are required" });
        return;
      }

      const session = await launchBrowserInstance(platform, username, stateId || randomUUID());
      await stateManager.loadState(session.cdpSession, session.page, platform, username);

      sendJson(res, 200, {
        sessionId: session.sessionId,
        cdpPort: session.cdpPort,
        fingerprint: {
          userAgent: session.fingerprint.userAgent,
          platform: session.fingerprint.platform,
          screenWidth: session.fingerprint.screenWidth,
          screenHeight: session.fingerprint.screenHeight,
        },
      });
      return;
    }

    // FIX #5 + #6: browser/close — log saveState errors, set autoSaved correctly, warn on close errors
    if (pathname === "/api/browser/close" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId } = body;

      // Try smart session first
      const smart = smartSessions.get(sessionId);
      if (smart) {
        stopHandoverStreaming(smart);
        let autoSaved = false;
        if (smart.page && smart.cdpSession) {
          try {
            await stateManager.saveState(smart.cdpSession, smart.page, smart.platform, smart.username);
            autoSaved = true;
          } catch (err: any) {
            console.warn("[BrowserEngine] Auto-save before smart close failed:", err.message || err);
          }
        }
        await closeSmartSession(smart);
        smartSessions.delete(sessionId);
        tabManager.markTaskComplete(sessionId);
        sendJson(res, 200, { status: "closed", autoSaved });
        return;
      }

      // Try legacy session
      const legacy = legacySessions.get(sessionId);
      if (legacy) {
        stopHandoverStreaming(legacy);
        let autoSaved = false;
        try {
          await stateManager.saveState(legacy.cdpSession, legacy.page, legacy.platform, legacy.username);
          autoSaved = true;
        } catch (err: any) {
          console.warn("[BrowserEngine] Auto-save before legacy close failed:", err.message || err);
        }
        try { await legacy.context.close(); } catch (err: any) { console.warn("[BrowserEngine] Failed to close context:", err.message || err); }
        try { await legacy.browser.close(); } catch (err: any) { console.warn("[BrowserEngine] Failed to close browser:", err.message || err); }
        legacySessions.delete(sessionId);
        sendJson(res, 200, { status: "closed", autoSaved });
        return;
      }

      sendJson(res, 404, { error: "Session not found" });
      return;
    }

    if (pathname === "/api/browser/navigate" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, url: navUrl, waitUntil, timeout: navTimeout } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }
      if (!info.page) { sendJson(res, 400, { error: "No browser page available for this session" }); return; }

      try {
        await info.page.goto(navUrl, { waitUntil: waitUntil || "domcontentloaded", timeout: navTimeout || 30000 });
        updateSessionActivity(sessionId);
        tabManager.updateActivity(sessionId, navUrl, await info.page.title().catch(() => ""));

        sendJson(res, 200, {
          url: info.page.url(),
          title: await info.page.title().catch(() => ""),
        });
      } catch (err: any) {
        sendJson(res, 500, { error: err.message, url: navUrl });
      }
      return;
    }

    if (pathname === "/api/browser/snapshot" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }
      if (!info.page) { sendJson(res, 400, { error: "No browser page available for this session" }); return; }

      try {
        const tree = await getAccessibilityTree(info.page);
        const pageUrl = info.page.url();
        const title = await info.page.title().catch(() => "");
        updateSessionActivity(sessionId);

        sendJson(res, 200, { tree, url: pageUrl, title });
      } catch (err: any) {
        sendJson(res, 500, { error: err.message, tree: [] });
      }
      return;
    }

    if (pathname === "/api/browser/click" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, ref } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      await clickByRef(info.page, ref);
      updateSessionActivity(sessionId);
      sendJson(res, 200, { status: "clicked" });
      return;
    }

    if (pathname === "/api/browser/fill" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, ref, value } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      await fillByRef(info.page, ref, value);
      updateSessionActivity(sessionId);
      sendJson(res, 200, { status: "filled" });
      return;
    }

    // FIX #7: setInputFiles fallback — return error to caller if both methods fail
    if (pathname === "/api/browser/upload-file" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, filePath, selector } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      if (!filePath) {
        sendJson(res, 400, { error: "Missing required field: filePath" });
        return;
      }

      const fileInputSelector = selector || 'input[type="file"]';
      const fileInput = await info.page.$(fileInputSelector);
      if (!fileInput) { sendJson(res, 404, { error: `File input not found: ${fileInputSelector}` }); return; }

      const resolvedPath = path.resolve(filePath);
      if (!fs.existsSync(resolvedPath)) { sendJson(res, 400, { error: `File not found: ${resolvedPath}` }); return; }

      try {
        await info.cdpSession.send("DOM.setFileInputFiles", {
          nodeId: await fileInput.evaluateHandle((el: any) => el).then(async (handle: any) => {
            const remoteObject = await info.cdpSession.send("DOM.describeNode", { objectId: handle._remoteObject?.objectId });
            return remoteObject.node?.nodeId;
          }),
          files: [resolvedPath],
        });
      } catch (cdpErr: any) {
        // CDP method failed, try Playwright fallback
        try {
          await fileInput.setInputFiles(resolvedPath);
        } catch (fallbackErr: any) {
          // Both methods failed — return error to caller
          sendJson(res, 500, {
            error: "File upload failed",
            cdpError: cdpErr.message || String(cdpErr),
            fallbackError: fallbackErr.message || String(fallbackErr),
          });
          return;
        }
      }

      updateSessionActivity(sessionId);
      sendJson(res, 200, { status: "uploaded", filePath: resolvedPath });
      return;
    }

    if (pathname === "/api/browser/evaluate" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, expression, script } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }
      if (!info.page) { sendJson(res, 400, { error: "No browser page available for this session" }); return; }

      const code = expression || script;
      if (!code) { sendJson(res, 400, { error: "Missing 'expression' or 'script' field" }); return; }

      try {
        const result = await info.page.evaluate(code);
        updateSessionActivity(sessionId);
        sendJson(res, 200, { result });
      } catch (err: any) {
        sendJson(res, 500, { error: err.message, result: null });
      }
      return;
    }

    if (pathname === "/api/browser/screenshot" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId } = body;

      // Try both session types
      const smart = smartSessions.get(sessionId);
      if (smart && smart.page) {
        const base64 = await takeScreenshot(smart);
        updateSessionActivity(sessionId);
        sendJson(res, 200, { screenshot: base64, type: "jpeg" });
        return;
      }

      const legacy = legacySessions.get(sessionId);
      if (legacy && legacy.page) {
        const base64 = await takeScreenshot(legacy);
        updateSessionActivity(sessionId);
        sendJson(res, 200, { screenshot: base64, type: "jpeg" });
        return;
      }

      sendJson(res, 404, { error: "Session not found" });
      return;
    }

    // FIX #8: wait fallback — return { status: "timeout" } instead of { status: "ready" }
    if (pathname === "/api/browser/wait" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, ref, timeout, text, urlPattern } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const waitTimeout = timeout || 10000;

      if (urlPattern) {
        try {
          await info.page.waitForURL(urlPattern, { timeout: waitTimeout });
          updateSessionActivity(sessionId);
          sendJson(res, 200, { status: "ready" });
        } catch (err: any) {
          updateSessionActivity(sessionId);
          sendJson(res, 200, { status: "timeout", error: err.message });
        }
      } else if (text) {
        try {
          await info.page.waitForSelector(`text=${text}`, { timeout: waitTimeout });
          updateSessionActivity(sessionId);
          sendJson(res, 200, { status: "ready" });
        } catch (err: any) {
          updateSessionActivity(sessionId);
          sendJson(res, 200, { status: "timeout", error: err.message });
        }
      } else if (ref) {
        const decoded = Buffer.from(ref.replace("ref-", ""), "base64").toString();
        const [role, ...nameParts] = decoded.split(":");
        const name = nameParts.join(":");
        let waited = false;
        try {
          await info.page.getByText(name, { exact: false }).first().waitFor({ timeout: waitTimeout });
          waited = true;
        } catch (err: any) {
          console.debug(`[BrowserEngine] wait: getByText waitFor failed for name="${name}":`, err.message);
          try {
            await info.page.getByRole(role as any, { name, exact: false }).first().waitFor({ timeout: 3000 });
            waited = true;
          } catch (innerErr: any) {
            console.debug(`[BrowserEngine] wait: getByRole waitFor fallback also failed for role=${role}:`, innerErr.message);
          }
        }
        updateSessionActivity(sessionId);
        sendJson(res, 200, { status: waited ? "ready" : "timeout" });
      } else {
        await new Promise((r) => setTimeout(r, Math.min(waitTimeout, 5000)));
        updateSessionActivity(sessionId);
        sendJson(res, 200, { status: "ready" });
      }
      return;
    }

    if (pathname === "/api/browser/press" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, key } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      await info.page.keyboard.press(key);
      updateSessionActivity(sessionId);
      sendJson(res, 200, { status: "pressed" });
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // State Endpoints (Enhanced)
    // ═══════════════════════════════════════════════════════════════════════

    // FIX #9: Use actual saveState return data properly
    if (pathname === "/api/state/save" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, username } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      // Get chrome profile dir for dual-layer check
      let chromeProfileDir: string | undefined;
      const smart = smartSessions.get(sessionId);
      if (smart && smart.mode === "full") {
        chromeProfileDir = path.join(process.env.HOME || "/tmp", ".agent-os", "chrome-profile", info.platform, info.username);
      }

      const saveResult = await stateManager.saveState(info.cdpSession, info.page, platform || info.platform, username || info.username, chromeProfileDir);
      sendJson(res, 200, {
        saved: true,
        cookieCount: saveResult.cookieCount ?? 0,
        isAuthenticated: saveResult.isAuthenticated ?? false,
        savedAt: saveResult.savedAt,
        hasLocalStorage: saveResult.hasLocalStorage ?? false,
        hasIndexedDB: saveResult.hasIndexedDB ?? false,
        status: "saved",
      });
      return;
    }

    if (pathname === "/api/state/load" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, username } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const loaded = await stateManager.loadState(info.cdpSession, info.page, platform || info.platform, username || info.username);
      sendJson(res, 200, { loaded });
      return;
    }

    if (pathname === "/api/state/list" && method === "GET") {
      const states = stateManager.listStates();
      sendJson(res, 200, { states });
      return;
    }

    if (pathname === "/api/state/delete" && method === "DELETE") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { platform, username } = body;
      const deleted = stateManager.deleteState(platform, username);
      sendJson(res, 200, { deleted });
      return;
    }

    if (pathname === "/api/state/has-auth" && method === "GET") {
      const platform = url.searchParams.get("platform");
      const username = url.searchParams.get("username");
      if (!platform || !username) { sendJson(res, 400, { error: "platform and username required" }); return; }
      const hasAuth = stateManager.hasAuthState(platform, username);
      const info = stateManager.getStateInfo(platform, username);
      sendJson(res, 200, { hasAuth, ...info });
      return;
    }

    if (pathname === "/api/state/info" && method === "GET") {
      const platform = url.searchParams.get("platform");
      const username = url.searchParams.get("username");
      if (!platform || !username) { sendJson(res, 400, { error: "platform and username required" }); return; }
      const info = stateManager.getStateInfo(platform, username);
      sendJson(res, 200, info);
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Handover Endpoints (Enhanced)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/handover/start" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, reason } = body;

      // Find session of either type
      let session: SmartSession | LegacyBrowserSession | undefined = smartSessions.get(sessionId);
      if (!session) session = legacySessions.get(sessionId);

      if (!session) { sendJson(res, 404, { error: "Session not found" }); return; }

      session.handover.active = true;
      session.handover.reason = reason || "other";
      session.handover.startedAt = new Date().toISOString();

      startHandoverStreaming(session);

      sendJson(res, 200, {
        handoverId: randomUUID(),
        streamUrl: `/api/handover/${sessionId}/stream`,
        reason: session.handover.reason,
        startedAt: session.handover.startedAt,
      });
      return;
    }

    // FIX #10: Send error event to client on initial SSE screenshot failure
    if (pathname.startsWith("/api/handover/") && pathname.endsWith("/stream") && method === "GET") {
      const sessionId = pathname.split("/")[3];
      const handover = getSessionHandover(sessionId);
      if (!handover) { sendJson(res, 404, { error: "Session not found" }); return; }

      corsHeaders(res);
      res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" });
      handover.sseClients.add(res);

      const info = getSessionPage(sessionId);
      if (info) {
        try {
          const buffer = await info.page.screenshot({ type: "jpeg", quality: 75 });
          res.write(`data: ${JSON.stringify({ type: "screenshot", data: buffer.toString("base64"), timestamp: Date.now() })}\n\n`);
        } catch (err: any) {
          // Send error event to client instead of silently swallowing
          res.write(`data: ${JSON.stringify({ type: "error", error: "Initial screenshot failed", details: err.message, timestamp: Date.now() })}\n\n`);
        }
      }

      req.on("close", () => { handover.sseClients.delete(res as any); });
      return;
    }

    if (pathname === "/api/handover/interact" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, action, x, y, text, deltaX, deltaY } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      switch (action) {
        case "click": await info.page.mouse.click(x || 0, y || 0); break;
        case "type":
          if (x !== undefined && y !== undefined) await info.page.mouse.click(x, y);
          if (text) await info.page.keyboard.type(text, { delay: 50 });
          break;
        case "scroll": await info.page.mouse.wheel(deltaX || 0, deltaY || 100); break;
        default: sendJson(res, 400, { error: `Unknown action: ${action}` }); return;
      }

      updateSessionActivity(sessionId);
      sendJson(res, 200, { status: "interacted", interacted: true, action });
      return;
    }

    if (pathname === "/api/handover/end" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId } = body;

      let session: SmartSession | LegacyBrowserSession | undefined = smartSessions.get(sessionId);
      if (!session) session = legacySessions.get(sessionId);
      if (!session) { sendJson(res, 404, { error: "Session not found" }); return; }

      stopHandoverStreaming(session);
      session.handover.active = false;
      session.handover.reason = "";
      session.handover.startedAt = null;

      // Auto-save state after handover — track success
      let stateSaved = false;
      try {
        await stateManager.saveState(session.cdpSession, session.page, session.platform, session.username);
        stateSaved = true;
      } catch (err: any) {
        console.error("[BrowserEngine] Auto-save after handover failed:", err.message || err);
      }

      sendJson(res, 200, { status: "ended", autoSaved: stateSaved, handoverActive: false, stateSaved });
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Social Media Endpoints
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/social/upload-media" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, filePath } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const adapter = await getPlatformAdapter(platform || info.platform);
      const result = await adapter.uploadMedia(info.page, info.cdpSession, filePath);
      updateSessionActivity(sessionId);
      sendJson(res, 200, result);
      return;
    }

    if (pathname === "/api/social/create-post" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, uploadId, caption, mediaType, hashtags, location } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const adapter = await getPlatformAdapter(platform || info.platform);
      const result = await adapter.createPost(info.page, info.cdpSession, caption, uploadId, mediaType, hashtags, location);
      updateSessionActivity(sessionId);
      sendJson(res, 200, result);
      return;
    }

    if (pathname === "/api/social/delete-post" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, postId } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const adapter = await getPlatformAdapter(platform || info.platform);
      const result = await adapter.deletePost(info.page, info.cdpSession, postId);
      updateSessionActivity(sessionId);
      sendJson(res, 200, result);
      return;
    }

    if (pathname === "/api/social/get-profile" && method === "POST") {
      const body = await parseBody(req, res);
      if (!body) return;
      const { sessionId, platform, username } = body;
      const info = getSessionPage(sessionId);
      if (!info) { sendJson(res, 404, { error: "Session not found" }); return; }

      const adapter = await getPlatformAdapter(platform || info.platform);
      const result = await adapter.getProfile(info.page, info.cdpSession, username);
      updateSessionActivity(sessionId);
      sendJson(res, 200, result);
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // Health / Status (FIX #18: Enhanced)
    // ═══════════════════════════════════════════════════════════════════════

    if (pathname === "/api/health") {
      const memStats = tabManager.getMemoryStats();
      const memUsage = process.memoryUsage();
      const uptimeSec = process.uptime();

      sendJson(res, 200, {
        status: "ok",
        service: "browser-engine",
        version: "2.1.0",
        uptime: uptimeSec,
        uptimeHuman: `${Math.floor(uptimeSec / 3600)}h ${Math.floor((uptimeSec % 3600) / 60)}m ${Math.floor(uptimeSec % 60)}s`,
        memory: {
          ...memStats,
          process: {
            rssMB: Math.round(memUsage.rss / 1024 / 1024),
            heapTotalMB: Math.round(memUsage.heapTotal / 1024 / 1024),
            heapUsedMB: Math.round(memUsage.heapUsed / 1024 / 1024),
            externalMB: Math.round(memUsage.external / 1024 / 1024),
          },
        },
        sessions: {
          smart: smartSessions.size,
          legacy: legacySessions.size,
          total: smartSessions.size + legacySessions.size,
        },
        playwright: "available",
        rateLimiter: {
          activeIps: rateLimiter.requests.size,
          maxRequestsPerMinute: rateLimiter.maxRequests,
        },
      });
      return;
    }

    if (pathname === "/api/sessions") {
      const smartList = Array.from(smartSessions.values()).map((s) => ({
        sessionId: s.sessionId,
        type: "smart",
        mode: s.mode,
        platform: s.platform,
        username: s.username,
        taskCategory: s.taskCategory,
        memoryEstimateMB: s.memoryEstimateMB,
        createdAt: s.createdAt,
        lastActivity: s.lastActivity,
        handover: { active: s.handover.active, reason: s.handover.reason },
        taskComplete: s.taskComplete,
      }));

      const legacyList = Array.from(legacySessions.values()).map((s) => ({
        sessionId: s.sessionId,
        type: "legacy",
        mode: "legacy",
        platform: s.platform,
        username: s.username,
        cdpPort: s.cdpPort,
        createdAt: s.createdAt,
        lastActivity: s.lastActivity,
        handover: { active: s.handover.active, reason: s.handover.reason },
      }));

      sendJson(res, 200, { sessions: [...smartList, ...legacyList] });
      return;
    }

    // 404
    sendJson(res, 404, { error: "Not found", path: pathname });
  } catch (err: any) {
    console.error(`[BrowserEngine] Error handling ${method} ${pathname}:`, err);
    sendJson(res, 500, {
      error: err.message || "Internal server error",
      stack: process.env.NODE_ENV === "development" ? err.stack : undefined,
    });
  }
}

// ─── Server Setup ────────────────────────────────────────────────────────────

const server = createServer(handleRequest);

const wss = new WebSocketServer({ server, path: "/ws" });

wss.on("connection", (ws: WebSocket) => {
  console.log("[BrowserEngine] WebSocket client connected");

  ws.on("message", async (data: Buffer) => {
    try {
      const msg = JSON.parse(data.toString());
      const { type, sessionId, payload } = msg;

      if (type === "subscribe" && sessionId) {
        const session = smartSessions.get(sessionId) || legacySessions.get(sessionId);
        if (session && session.handover.active) {
          const interval = setInterval(async () => {
            try {
              const base64 = await takeScreenshot(session);
              ws.send(JSON.stringify({ type: "screenshot", data: base64, timestamp: Date.now() }));
            } catch (err: any) {
              console.warn("[BrowserEngine] WS screenshot failed, stopping interval:", err.message);
              clearInterval(interval);
            }
          }, 500);
          ws.on("close", () => clearInterval(interval));
        }
      }

      if (type === "interact" && sessionId) {
        const info = getSessionPage(sessionId);
        if (!info) { ws.send(JSON.stringify({ type: "error", error: "Session not found" })); return; }

        const { action, x, y, text, deltaX, deltaY } = payload || {};
        switch (action) {
          case "click": await info.page.mouse.click(x || 0, y || 0); break;
          case "type":
            if (x !== undefined && y !== undefined) await info.page.mouse.click(x, y);
            if (text) await info.page.keyboard.type(text, { delay: 50 });
            break;
          case "scroll": await info.page.mouse.wheel(deltaX || 0, deltaY || 100); break;
        }
        ws.send(JSON.stringify({ type: "interacted", action }));
      }
    } catch (err: any) {
      ws.send(JSON.stringify({ type: "error", error: err.message }));
    }
  });

  ws.on("close", () => { console.log("[BrowserEngine] WebSocket client disconnected"); });
});

// ─── Graceful Shutdown (FIX #15: Enhanced with state saving) ─────────────────

let isShuttingDown = false;

async function shutdown() {
  if (isShuttingDown) return; // Prevent double-shutdown
  isShuttingDown = true;

  console.log("[BrowserEngine] Shutting down gracefully...");

  // Save all smart session states
  for (const [id, session] of smartSessions) {
    try {
      stopHandoverStreaming(session);
      if (session.page && session.cdpSession) {
        try {
          await stateManager.saveState(session.cdpSession, session.page, session.platform, session.username);
          console.log(`[BrowserEngine] Saved state for smart session ${id}`);
        } catch (err: any) {
          console.warn(`[BrowserEngine] Failed to save state for smart session ${id}:`, err.message || err);
        }
      }
      await closeSmartSession(session);
    } catch (err: any) {
      console.warn(`[BrowserEngine] Error closing smart session ${id}:`, err.message || err);
    }
  }
  smartSessions.clear();

  // Save all legacy session states and close browsers
  for (const [id, session] of legacySessions) {
    try {
      stopHandoverStreaming(session);
      try {
        await stateManager.saveState(session.cdpSession, session.page, session.platform, session.username);
        console.log(`[BrowserEngine] Saved state for legacy session ${id}`);
      } catch (err: any) {
        console.warn(`[BrowserEngine] Failed to save state for legacy session ${id}:`, err.message || err);
      }
      try { await session.context.close(); } catch (err: any) { console.warn(`[BrowserEngine] Error closing context for ${id}:`, err.message || err); }
      try { await session.browser.close(); } catch (err: any) { console.warn(`[BrowserEngine] Error closing browser for ${id}:`, err.message || err); }
    } catch (err: any) {
      console.warn(`[BrowserEngine] Error shutting down legacy session ${id}:`, err.message || err);
    }
  }
  legacySessions.clear();

  // Stop tab manager
  try {
    await tabManager.destroyAll();
  } catch (err: any) {
    console.warn("[BrowserEngine] Error destroying tab manager:", err.message || err);
  }

  wss.close();
  server.close();
  console.log("[BrowserEngine] Shutdown complete.");
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

// ─── Start Server ────────────────────────────────────────────────────────────

tabManager.start();

server.listen(PORT, () => {
  console.log(`[BrowserEngine] 🚀 Service v2.1 running on port ${PORT}`);
  console.log(`[BrowserEngine] Health check: http://localhost:${PORT}/api/health`);
  console.log(`[BrowserEngine] WebSocket endpoint: ws://localhost:${PORT}/ws`);
  console.log(`[BrowserEngine] Features: CDP, Smart Modes (Full/Light/Ghost), Dual-Layer State, Handoff, Tab Manager, Rate Limiting`);
  console.log(`[BrowserEngine] Browser states directory: /home/z/my-project/browser-states/`);
});
