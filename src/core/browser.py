"""
Agent-OS Browser Engine
Core browser with anti-detection capabilities.
Uses Playwright with extensive anti-detection patches.
"""
import asyncio
import json
import base64
import random
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger("agent-os.browser")

# Anti-detection JavaScript injected into every page
ANTI_DETECTION_JS = """
// === AGENT-OS ANTI-DETECTION PATCH ===

// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 2. Spoof plugins (human browsers have plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
            {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
        ];
        plugins.length = 3;
        return plugins;
    }
});

// 3. Spoof languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

// 4. Override permissions query
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// 5. Spoof hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});

// 6. Spoof device memory
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

// 7. Spoof connection
Object.defineProperty(navigator, 'connection', {
    get: () => ({rtt: 50, downlink: 10, effectiveType: '4g', saveData: false})
});

// 8. WebGL vendor/renderer spoofing
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};

// 9. Chrome runtime (needed to look like real Chrome)
window.chrome = {
    runtime: {
        PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'},
        PlatformArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
        PlatformNaclArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
        RequestUpdateCheckStatus: {THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available'},
        OnInstalledReason: {INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update'},
        OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
    },
    loadTimes: () => ({requestTime: Date.now() / 1000, startLoadTime: Date.now() / 1000, commitLoadTime: Date.now() / 1000, finishDocumentLoadTime: Date.now() / 1000, finishLoadTime: Date.now() / 1000, firstPaintTime: Date.now() / 1000, firstPaintAfterLoadTime: 0, wasFetchedViaSpdy: false, wasNpnNegotiated: true, npnNegotiatedProtocol: 'h2', wasAlternateProtocolAvailable: false, connectionInfo: 'h2'}),
    csi: () => ({pageT: Date.now(), startE: Date.now(), onloadT: Date.now(), pageT: Date.now()})
};

// 10. Block Canvas fingerprinting (randomize slightly)
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png' && this.width === 16 && this.height === 16) {
        return toDataURL.apply(this, arguments);
    }
    const context = this.getContext('2d');
    if (context) {
        const shift = {r: Math.floor(Math.random() * 10) - 5, g: Math.floor(Math.random() * 10) - 5, b: Math.floor(Math.random() * 10) - 5};
        const width = this.width;
        const height = this.height;
        if (width && height) {
            const imageData = context.getImageData(0, 0, width, height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] += shift.r;
                imageData.data[i + 1] += shift.g;
                imageData.data[i + 2] += shift.b;
            }
            context.putImageData(imageData, 0, 0);
        }
    }
    return toDataURL.apply(this, arguments);
};

console.log('[Agent-OS] Anti-detection patches loaded');
"""

# Bot detection patterns to block
BOT_DETECTION_URLS = [
    "recaptcha", "captcha", "hcaptcha", "turnstile",
    "perimeterx", "datadome", "cloudflare-challenge",
    "check-bot", "verify-human", "bot-detection",
    "akamai-bot", "imperva", "f5-bot",
    "distil", "shape-security", "kasada",
]

# Fake human responses for blocked bot detection endpoints
FAKE_RESPONSES = {
    "recaptcha": {"success": True, "score": 0.95, "action": "login", "challenge_ts": "2026-01-01T00:00:00Z"},
    "captcha": {"status": "verified", "human": True, "score": 0.92},
    "perimeterx": {"status": 0, "uuid": "fake-uuid-123", "vid": "fake-vid", "risk_score": 5},
    "datadome": {"status": 200, "headers": {"x-datadome": "pass"}, "cookie": "human-verified"},
    "cloudflare": {"success": True, "cf_clearance": "fake-clearance-token"},
    "bot-detection": {"human": True, "verified": True, "timestamp": 1700000000},
}


class AgentBrowser:
    """Core browser engine with anti-detection for AI agents."""

    def __init__(self, config):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._active_sessions: Dict[str, Dict] = {}
        self._blocked_requests: int = 0
        self._pages: Dict[str, Page] = {}

    async def start(self):
        """Launch the browser with anti-detection settings."""
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.get("browser.headless", True),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
                "--window-size=1920,1080",
            ]
        )

        self.context = await self.browser.new_context(
            user_agent=self.config.get("browser.user_agent"),
            viewport=self.config.get("browser.viewport", {"width": 1920, "height": 1080}),
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            color_scheme="light",
            device_scale_factor=1.0,
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
        )

        # Inject anti-detection script on every page
        await self.context.add_init_script(ANTI_DETECTION_JS)

        # Set up request interception for bot detection blocking
        await self.context.route("**/*", self._handle_request)

        self.page = await self.context.new_page()
        self._pages["main"] = self.page

        logger.info("Browser started with anti-detection patches")

    async def _handle_request(self, route, request):
        """Intercept and block bot detection requests."""
        url = request.url.lower()

        # Check if this is a bot detection request
        for pattern in BOT_DETECTION_URLS:
            if pattern in url:
                self._blocked_requests += 1
                fake_response = FAKE_RESPONSES.get(pattern, {"human": True})
                logger.debug(f"Blocked bot detection: {request.url}")
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(fake_response)
                )
                return

        # Check for bot detection JavaScript
        if request.resource_type == "script":
            for pattern in ["recaptcha", "captcha", "botdetect", "fingerprint"]:
                if pattern in url:
                    logger.debug(f"Blocked bot detection script: {request.url}")
                    await route.fulfill(status=200, body="")
                    return

        # Allow all other requests
        await route.continue_()

    async def navigate(self, url: str, page_id: str = "main") -> Dict[str, Any]:
        """Navigate to a URL with human-like timing."""
        page = self._pages.get(page_id, self.page)

        # Human-like delay before navigation (simulating "thinking")
        await asyncio.sleep(random.uniform(0.3, 1.2))

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for page to fully load (human-like)
            await asyncio.sleep(random.uniform(0.5, 1.5))

            return {
                "status": "success",
                "url": page.url,
                "title": await page.title(),
                "status_code": response.status if response else 200,
                "blocked_requests": self._blocked_requests
            }
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {"status": "error", "error": str(e)}

    async def get_content(self, page_id: str = "main") -> Dict[str, Any]:
        """Get current page content."""
        page = self._pages.get(page_id, self.page)
        return {
            "url": page.url,
            "title": await page.title(),
            "html": await page.content(),
            "text": await page.inner_text("body") if await page.query_selector("body") else ""
        }

    async def screenshot(self, page_id: str = "main") -> str:
        """Take a base64 screenshot."""
        page = self._pages.get(page_id, self.page)
        img_bytes = await page.screenshot(type="png")
        return base64.b64encode(img_bytes).decode()

    async def fill_form(self, fields: Dict[str, str], page_id: str = "main") -> Dict[str, Any]:
        """Fill form fields with human-like typing."""
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()
        filled = []

        for selector, value in fields.items():
            try:
                element = await page.query_selector(selector)
                if not element:
                    # Try common selectors
                    for alt in [f'input[name="{selector}"]', f'input[placeholder*="{selector}"]',
                                f'textarea[name="{selector}"]', f'#{selector}']:
                        element = await page.query_selector(alt)
                        if element:
                            break

                if element:
                    await element.click()
                    await asyncio.sleep(random.uniform(0.1, 0.3))

                    # Clear existing value
                    await element.fill("")

                    # Type with human-like delays
                    for char in value:
                        await element.type(char, delay=mimicry.typing_delay())
                    filled.append(selector)
                    await asyncio.sleep(random.uniform(0.05, 0.2))
                else:
                    logger.warning(f"Field not found: {selector}")
            except Exception as e:
                logger.error(f"Error filling {selector}: {e}")

        return {"status": "success", "filled": filled, "total": len(fields)}

    async def click(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Click an element with human-like mouse movement."""
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}

            box = await element.bounding_box()
            if box:
                # Move mouse in human-like path
                target_x = box["x"] + box["width"] / 2
                target_y = box["y"] + box["height"] / 2
                path = mimicry.mouse_path(target_x, target_y)

                for x, y in path:
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.005, 0.02))

            await asyncio.sleep(random.uniform(0.05, 0.15))
            await element.click()
            await asyncio.sleep(random.uniform(0.2, 0.5))

            return {"status": "success", "selector": selector}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def evaluate_js(self, script: str, page_id: str = "main") -> Any:
        """Execute JavaScript in the page context."""
        page = self._pages.get(page_id, self.page)
        return await page.evaluate(script)

    async def get_dom_snapshot(self, page_id: str = "main") -> str:
        """Get a structured DOM snapshot for agent analysis."""
        page = self._pages.get(page_id, self.page)
        snapshot = await page.evaluate("""() => {
            function getSnapshot(el, depth = 0) {
                if (depth > 5) return '';
                let result = '';
                const indent = '  '.repeat(depth);
                const tag = el.tagName?.toLowerCase() || '';
                if (!tag) return '';

                const attrs = [];
                if (el.id) attrs.push(`id="${el.id}"`);
                if (el.className && typeof el.className === 'string') attrs.push(`class="${el.className}"`);
                if (el.getAttribute('type')) attrs.push(`type="${el.getAttribute('type')}"`);
                if (el.getAttribute('name')) attrs.push(`name="${el.getAttribute('name')}"`);
                if (el.getAttribute('placeholder')) attrs.push(`placeholder="${el.getAttribute('placeholder')}"`);
                if (el.href) attrs.push(`href="${el.href}"`);

                const attrStr = attrs.length ? ' ' + attrs.join(' ') : '';
                const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                    ? el.childNodes[0].textContent.trim().substring(0, 100) : '';

                if (['script', 'style', 'noscript', 'svg'].includes(tag)) return '';

                const children = Array.from(el.children).map(c => getSnapshot(c, depth + 1)).filter(Boolean).join('');

                if (children) {
                    result = `${indent}<${tag}${attrStr}>${text ? ' ' + text : ''}\\n${children}${indent}</${tag}>\\n`;
                } else if (text) {
                    result = `${indent}<${tag}${attrStr}>${text}</${tag}>\\n`;
                } else {
                    result = `${indent}<${tag}${attrStr} />\\n`;
                }
                return result;
            }
            return getSnapshot(document.body);
        }""")
        return snapshot

    async def scroll(self, direction: str = "down", amount: int = 500, page_id: str = "main") -> Dict[str, Any]:
        """Scroll with human-like behavior."""
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

        y = amount if direction == "down" else -amount
        steps = random.randint(3, 8)

        for i in range(steps):
            step_y = y / steps + random.randint(-20, 20)
            await page.mouse.wheel(0, int(step_y))
            await asyncio.sleep(mimicry.scroll_delay())

        return {"status": "success", "direction": direction, "amount": amount}

    async def new_tab(self, tab_id: str) -> str:
        """Create a new tab."""
        page = await self.context.new_page()
        self._pages[tab_id] = page
        return tab_id

    async def close_tab(self, tab_id: str) -> bool:
        """Close a tab."""
        if tab_id in self._pages and tab_id != "main":
            await self._pages[tab_id].close()
            del self._pages[tab_id]
            return True
        return False

    async def stop(self):
        """Clean shutdown."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser stopped")
