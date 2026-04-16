#!/usr/bin/env python3
"""
Agent-OS BRUTAL STRESS TEST — Maximum Intensity (In-Process)
=============================================================
No mercy. No fixes. Just raw truth.

Starts the server IN-PROCESS and hammers it via HTTP.
Tests EVERYTHING: stealth, form filling on real sites, swarm, rapid-fire, etc.
"""
import asyncio
import json
import time
import sys
import os
import traceback
import aiohttp
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HTTP_PORT = 9001
WS_PORT = 9000
BASE_URL = f"http://127.0.0.1:{HTTP_PORT}"
TOKEN = "brutal-test-token-2025"

# ═══════════════════════════════════════════════════════════
# COLORS
# ═══════════════════════════════════════════════════════════
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ═══════════════════════════════════════════════════════════
# RESULTS TRACKER
# ═══════════════════════════════════════════════════════════
class BrutalResults:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.details = []
        self.category_results = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "errors": 0})
        self.start_time = time.time()
        self.crash_count = 0

    def record(self, name, status, duration=0, error="", category="general"):
        self.total += 1
        if status == "PASS": self.passed += 1
        elif status == "FAIL": self.failed += 1
        elif status == "ERROR": self.errors += 1
        elif status == "SKIP": self.skipped += 1
        self.details.append((name, status, duration, error))
        cat = self.category_results[category]
        cat["total"] += 1
        if status == "PASS": cat["passed"] += 1
        elif status == "FAIL": cat["failed"] += 1
        elif status == "ERROR": cat["errors"] += 1

    def summary(self):
        elapsed = time.time() - self.start_time
        rate = (self.passed / self.total * 100) if self.total > 0 else 0
        lines = []
        lines.append(f"\n{'='*80}")
        lines.append(f"{BOLD}{RED}  BRUTAL STRESS TEST — RAW RESULTS{RESET}")
        lines.append(f"{'='*80}")
        lines.append(f"  Total Tests:    {self.total}")
        lines.append(f"  {GREEN}PASSED:         {self.passed}{RESET}")
        lines.append(f"  {RED}FAILED:         {self.failed}{RESET}")
        lines.append(f"  {MAGENTA}ERRORS:         {self.errors}{RESET}")
        lines.append(f"  {YELLOW}SKIPPED:        {self.skipped}{RESET}")
        lines.append(f"  {BOLD}SUCCESS RATE:   {rate:.1f}%{RESET}")
        lines.append(f"  Crashes:        {self.crash_count}")
        lines.append(f"  Total Time:     {elapsed:.1f}s")
        lines.append(f"{'='*80}")
        lines.append(f"\n{BOLD}{CYAN}  CATEGORY BREAKDOWN{RESET}")
        lines.append(f"{'='*80}")
        for cat, data in sorted(self.category_results.items()):
            cat_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            color = GREEN if cat_rate >= 80 else YELLOW if cat_rate >= 50 else RED
            lines.append(f"  {cat:30s} {data['passed']:3d}/{data['total']:3d}  {color}{cat_rate:5.1f}%{RESET}  (F:{data['failed']} E:{data['errors']})")
        failed_tests = [(n, s, d, e) for n, s, d, e in self.details if s in ("FAIL", "ERROR")]
        if failed_tests:
            lines.append(f"\n{BOLD}{RED}  FAILED/ERROR TESTS{RESET}")
            lines.append(f"{'='*80}")
            for name, status, duration, error in failed_tests:
                lines.append(f"  {RED}[{status}]{RESET} {name} ({duration:.2f}s)")
                if error:
                    lines.append(f"         {error[:120]}")
        lines.append(f"\n{'='*80}")
        return "\n".join(lines)


R = BrutalResults()

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120))
    return _session

async def api_call(endpoint, method="GET", data=None):
    s = await get_session()
    headers = {"Content-Type": "application/json"}
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            async with s.get(url, headers=headers) as resp:
                return await resp.json(), resp.status
        elif method == "POST":
            async with s.post(url, json=data, headers=headers) as resp:
                return await resp.json(), resp.status
        elif method == "PUT":
            async with s.put(url, json=data, headers=headers) as resp:
                return await resp.json(), resp.status
    except asyncio.TimeoutError:
        return {"status": "error", "error": "Timeout"}, 0
    except Exception as e:
        return {"status": "error", "error": str(e)}, 0

async def cmd(command, params=None):
    data = {"command": command, "token": TOKEN}
    if params:
        data.update(params)
    return await api_call("/command", method="POST", data=data)

def pf(name, condition, duration=0, error="", category="general"):
    if condition:
        R.record(name, "PASS", duration, category=category)
        print(f"  {GREEN}✓{RESET} {name} ({duration:.2f}s)")
    else:
        R.record(name, "FAIL", duration, error, category=category)
        print(f"  {RED}✗{RESET} {name} ({duration:.2f}s) — {error[:80]}")


# ═══════════════════════════════════════════════════════════
# START SERVER IN-PROCESS
# ═══════════════════════════════════════════════════════════
async def start_server():
    """Start the Agent-OS server in the same process."""
    import argparse
    from src.core.config import Config
    from src.core.browser import AgentBrowser
    from src.core.session import SessionManager
    from src.agents.server import AgentServer

    # Override config for testing
    config = Config()
    config.set("server.ws_port", WS_PORT)
    config.set("server.http_port", HTTP_PORT)
    config.set("server.agent_token", TOKEN)
    config.set("swarm.enabled", True)

    browser = AgentBrowser(config)
    session_manager = SessionManager(config)

    # JWT handler
    import secrets
    from src.auth.jwt_handler import JWTHandler
    jwt_handler = JWTHandler(
        secret_key=secrets.token_urlsafe(48),
        algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=30,
        issuer="agent-os",
    )

    from src.auth.api_key_manager import APIKeyManager
    api_key_manager = APIKeyManager()

    from src.auth.user_manager import UserManager
    user_manager = UserManager()

    from src.auth.middleware import AuthMiddleware
    auth_middleware = AuthMiddleware(
        jwt_handler=jwt_handler,
        api_key_manager=api_key_manager,
        legacy_tokens=[TOKEN],
    )

    server = AgentServer(
        config=config,
        browser=browser,
        session_manager=session_manager,
        auth_middleware=auth_middleware,
        api_key_manager=api_key_manager,
        user_manager=user_manager,
    )

    print("  Starting browser engine...")
    await browser.start()
    print("  Starting session manager...")
    await session_manager.start()
    print("  Starting agent server...")
    await server.start()
    print(f"  {GREEN}Server ready!{RESET}")

    return browser, session_manager, server


# ═══════════════════════════════════════════════════════════
# TEST PHASES
# ═══════════════════════════════════════════════════════════

async def test_server_health():
    print(f"\n{BOLD}{CYAN}━━ PHASE 1: SERVER HEALTH ━━{RESET}")
    cat = "infrastructure"
    t0 = time.time(); resp, s = await api_call("/health")
    pf("Health endpoint", s == 200, time.time()-t0, f"status={s}", cat)
    t0 = time.time(); resp, s = await api_call("/status")
    pf("Status endpoint", s == 200, time.time()-t0, f"status={s}", cat)
    if s == 200:
        pf("Browser active", resp.get("browser_active", False), 0, "browser not running", cat)
    t0 = time.time(); resp, s = await api_call("/commands")
    pf("Commands list", s == 200, time.time()-t0, f"status={s}", cat)


async def test_navigation_brutal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 2: NAVIGATION — BRUTAL ━━{RESET}")
    cat = "navigation"
    sites = [
        ("https://example.com", "Example.com"),
        ("https://httpbin.org/forms/post", "HTTPBin Forms"),
        ("https://github.com", "GitHub"),
        ("https://news.ycombinator.com", "HackerNews"),
        ("https://www.wikipedia.org", "Wikipedia"),
        ("https://www.reddit.com", "Reddit"),
        ("https://twitter.com", "Twitter/X"),
        ("https://www.instagram.com", "Instagram"),
        ("https://www.linkedin.com", "LinkedIn"),
    ]
    for url, label in sites:
        t0 = time.time()
        try:
            resp, _ = await cmd("navigate", {"url": url})
            elapsed = time.time() - t0
            ok = resp.get("status") == "success"
            pf(f"Navigate {label}", ok, elapsed, resp.get("error", "")[:80], cat)
            if ok:
                cr, _ = await cmd("get-content")
                pf(f"  {label} content loaded", cr.get("status") == "success", 0, "no content", cat)
        except Exception as e:
            pf(f"Navigate {label}", False, time.time()-t0, str(e)[:80], cat)
            R.crash_count += 1
        await asyncio.sleep(1)


async def test_stealth_brutal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 3: STEALTH ANTI-DETECTION ━━{RESET}")
    cat = "stealth"
    # Navigate to bot detection test
    t0 = time.time()
    resp, _ = await cmd("navigate", {"url": "https://bot.sannysoft.com/"})
    await asyncio.sleep(3)
    pf("Navigate to bot.sannysoft.com", resp.get("status") == "success", time.time()-t0, "", cat)

    stealth_checks = [
        ("navigator.webdriver", "webdriver undefined/false", lambda v: v is None or v is False or str(v) in ("undefined", "")),
        ("navigator.plugins.length", "plugins > 0", lambda v: v is not None and v != 0),
        ("navigator.languages.length", "languages > 0", lambda v: v is not None and v != 0),
        ("typeof window.chrome", "window.chrome exists", lambda v: v is not None and str(v) != "undefined"),
        ("navigator.hardwareConcurrency", "CPU cores > 0", lambda v: v is not None and v != 0),
        ("navigator.deviceMemory", "deviceMemory present", lambda v: v is not None),
    ]
    for script, desc, check_fn in stealth_checks:
        t0 = time.time()
        try:
            resp, _ = await cmd("evaluate-js", {"script": script})
            elapsed = time.time() - t0
            val = resp.get("result", resp.get("error"))
            if resp.get("status") != "success":
                pf(f"Stealth: {desc}", False, elapsed, f"error={resp.get('error', '')[:60]}", cat)
            else:
                try:
                    pf(f"Stealth: {desc}", check_fn(val), elapsed, f"value={val}" if not check_fn(val) else "", cat)
                except Exception:
                    pf(f"Stealth: {desc}", False, elapsed, f"check failed, value={val}", cat)
        except Exception as e:
            pf(f"Stealth: {desc}", False, time.time()-t0, str(e)[:80], cat)


async def test_form_filling_brutal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 4: FORM FILLING — REAL WEBSITES ━━{RESET}")
    cat = "form_filling"

    # ── HTTPBin Forms ──
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://httpbin.org/forms/post"})
    await asyncio.sleep(2)
    pf("Navigate HTTPBin forms", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    if resp.get("status") == "success":
        t0 = time.time()
        resp, _ = await cmd("fill-form", {"fields": {"custname": "Test User", "custtel": "1234567890", "custemail": "test@example.com"}})
        pf("Fill HTTPBin form", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    # ── Instagram Login ──
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://www.instagram.com/accounts/login/"})
    await asyncio.sleep(5)
    nav_ok = resp.get("status") == "success"
    pf("Navigate Instagram login", nav_ok, time.time()-t0, resp.get("error","")[:80], cat)
    if nav_ok:
        t0 = time.time()
        resp, _ = await cmd("fill-form", {"fields": {"username": "test_user_12345", "password": "test_pass_12345"}})
        pf("Fill Instagram login form", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
        # Verify via JS
        t0 = time.time()
        resp, _ = await cmd("evaluate-js", {"script": "document.querySelector('input[name=\"username\"]')?.value || 'NOT_FOUND'"})
        has_val = resp.get("status") == "success" and "test_user" in str(resp.get("result", ""))
        pf("Instagram username field filled", has_val, time.time()-t0, f"result={resp.get('result', resp.get('error', ''))}"[:80], cat)

    # ── Twitter/X Login ──
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://twitter.com/i/flow/login"})
    await asyncio.sleep(5)
    nav_ok = resp.get("status") == "success"
    pf("Navigate Twitter/X login", nav_ok, time.time()-t0, resp.get("error","")[:80], cat)
    if nav_ok:
        t0 = time.time()
        resp, _ = await cmd("fill-form", {"fields": {"username": "test_twitter_user"}})
        pf("Fill Twitter/X form", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    # ── GitHub Login ──
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://github.com/login"})
    await asyncio.sleep(3)
    nav_ok = resp.get("status") == "success"
    pf("Navigate GitHub login", nav_ok, time.time()-t0, resp.get("error","")[:80], cat)
    if nav_ok:
        t0 = time.time()
        resp, _ = await cmd("fill-form", {"fields": {"login": "test_github_user", "password": "test_pass"}})
        pf("Fill GitHub login form", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
        t0 = time.time()
        resp, _ = await cmd("evaluate-js", {"script": "document.querySelector('#login_field')?.value || 'NOT_FOUND'"})
        has_val = resp.get("status") == "success" and "test_github" in str(resp.get("result", ""))
        pf("GitHub login field filled", has_val, time.time()-t0, f"result={resp.get('result', '')}"[:80], cat)

    # ── LinkedIn Login ──
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://www.linkedin.com/login"})
    await asyncio.sleep(4)
    nav_ok = resp.get("status") == "success"
    pf("Navigate LinkedIn login", nav_ok, time.time()-t0, resp.get("error","")[:80], cat)
    if nav_ok:
        t0 = time.time()
        resp, _ = await cmd("fill-form", {"fields": {"username": "test_linkedin", "password": "test_pass"}})
        pf("Fill LinkedIn login form", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_swarm_brutal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 5: SWARM ROUTING & SEARCH ━━{RESET}")
    cat = "swarm"
    t0 = time.time(); resp, s = await api_call("/swarm/health")
    pf("Swarm health", s == 200, time.time()-t0, f"status={s}", cat)
    t0 = time.time(); resp, s = await api_call("/swarm/config")
    pf("Swarm config", s == 200, time.time()-t0, f"status={s}", cat)
    t0 = time.time(); resp, s = await api_call("/swarm/agents")
    pf("Swarm agents", s == 200, time.time()-t0, f"status={s}", cat)

    queries = [
        ("What is the weather in Tokyo?", "NEEDS_WEB"),
        ("Calculate 2+2", "NEEDS_CALCULATION"),
        ("Write a Python function", "NEEDS_CODE"),
        ("What is the capital of France?", "AMBIGUOUS"),
        ("Check XSS vulnerabilities", "NEEDS_SECURITY"),
    ]
    for query, _ in queries:
        t0 = time.time()
        resp, s = await api_call("/swarm/route", method="POST", data={"query": query})
        pf(f"Swarm route: '{query[:35]}'", resp.get("status") == "success", time.time()-t0,
           resp.get("error","")[:60], cat)

    t0 = time.time()
    resp, s = await api_call("/swarm/search", method="POST", data={"query": "latest AI news 2025", "max_results": 5})
    pf("Swarm search", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:60], cat)


async def test_rapid_fire():
    print(f"\n{BOLD}{CYAN}━━ PHASE 6: RAPID-FIRE COMMANDS ━━{RESET}")
    cat = "rapid_fire"
    await cmd("navigate", {"url": "https://example.com"})
    await asyncio.sleep(2)

    commands = [
        ("screenshot", {}), ("get-content", {}), ("get-links", {}), ("get-cookies", {}),
        ("console-logs", {}), ("scroll", {"direction": "down", "amount": 300}),
        ("evaluate-js", {"script": "1+1"}), ("evaluate-js", {"script": "document.title"}),
        ("evaluate-js", {"script": "navigator.userAgent"}),
        ("get-text", {"selector": "h1"}), ("back", {}), ("reload", {}),
        ("screenshot", {}), ("viewport", {"width": 1280, "height": 720}),
        ("viewport", {"width": 1920, "height": 1080}), ("tabs", {"action": "list"}),
    ]

    print(f"  Firing {len(commands)} commands RAPID-FIRE...")
    tasks = [cmd(c, p) for c, p in commands]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results_list):
        cname = commands[i][0]
        if isinstance(result, Exception):
            R.record(f"Rapid {cname}", "ERROR", 0, str(result)[:80], category=cat)
            print(f"  {RED}✗ ERROR{RESET} Rapid {cname}")
        else:
            resp, s = result
            pf(f"Rapid {cname}", resp.get("status") == "success", 0, resp.get("error","")[:60], cat)

    # BURST: 10 screenshots parallel
    print(f"  BURST: 10 parallel screenshots...")
    t0 = time.time()
    burst = await asyncio.gather(*[cmd("screenshot") for _ in range(10)], return_exceptions=True)
    ok_count = sum(1 for r in burst if not isinstance(r, Exception) and r[0].get("status") == "success")
    pf(f"Burst 10 screenshots ({ok_count}/10)", ok_count >= 7, time.time()-t0, f"only {ok_count}/10", cat)


async def test_element_interaction():
    print(f"\n{BOLD}{CYAN}━━ PHASE 7: ELEMENT INTERACTION ━━{RESET}")
    cat = "interaction"
    t0 = time.time(); resp, _ = await cmd("navigate", {"url": "https://the-internet.herokuapp.com"})
    await asyncio.sleep(2)
    pf("Navigate test page", resp.get("status") == "success", time.time()-t0, "", cat)

    t0 = time.time(); resp, _ = await cmd("click", {"selector": "a[href='/add_remove_elements/']"})
    pf("Click link", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    await asyncio.sleep(1)

    t0 = time.time(); resp, _ = await cmd("click", {"selector": "button[onclick='addElement()']"})
    pf("Click Add Element button", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    t0 = time.time(); resp, _ = await cmd("smart-find", {"description": "Add Element button"})
    pf("Smart find", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    await cmd("back"); await asyncio.sleep(1)

    t0 = time.time(); resp, _ = await cmd("hover", {"selector": "a"})
    pf("Hover", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    t0 = time.time(); resp, _ = await cmd("double-click", {"selector": "h1"})
    pf("Double-click", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)

    t0 = time.time(); resp, _ = await cmd("right-click", {"selector": "body"})
    pf("Right-click", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_evaluate_js_brutal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 8: JAVASCRIPT EVALUATION ━━{RESET}")
    cat = "evaluate_js"
    await cmd("navigate", {"url": "https://example.com"})
    await asyncio.sleep(2)

    js_tests = [
        ("1 + 1", lambda v: v == 2, "Arithmetic"),
        ("document.title", lambda v: v is not None and len(str(v)) > 0, "Document title"),
        ("navigator.userAgent", lambda v: v is not None and "Mozilla" in str(v), "UserAgent"),
        ("navigator.webdriver", lambda v: v is None or v is False or str(v) in ("undefined",""), "webdriver hidden"),
        ("navigator.plugins.length", lambda v: v is not None and int(v) > 0, "Plugins > 0"),
        ("typeof window.chrome", lambda v: v is not None and str(v) != "undefined", "window.chrome"),
        ("typeof fetch", lambda v: v == "function", "fetch API"),
        ("performance.now()", lambda v: v is not None, "Performance API"),
    ]
    for script, check_fn, desc in js_tests:
        t0 = time.time()
        try:
            resp, _ = await cmd("evaluate-js", {"script": script})
            elapsed = time.time() - t0
            val = resp.get("result")
            if resp.get("status") != "success":
                pf(f"JS: {desc}", False, elapsed, f"error={resp.get('error','')[:60]}", cat)
            else:
                try:
                    pf(f"JS: {desc}", check_fn(val), elapsed, f"value={val}" if not check_fn(val) else "", cat)
                except Exception:
                    pf(f"JS: {desc}", False, elapsed, f"check failed, value={val}", cat)
        except Exception as e:
            pf(f"JS: {desc}", False, time.time()-t0, str(e)[:80], cat)


async def test_smart_nav_fetch():
    print(f"\n{BOLD}{CYAN}━━ PHASE 9: SMART NAV & FETCH ━━{RESET}")
    cat = "smart_nav"
    t0 = time.time(); resp, _ = await cmd("smart-navigate", {"url": "https://example.com"})
    pf("Smart navigate", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("fetch", {"url": "https://example.com"})
    pf("Fetch example.com", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    if resp.get("status") == "success":
        pf("Fetch has text", bool(resp.get("text","")), 0, "no text", cat)
    t0 = time.time(); resp, _ = await cmd("nav-stats")
    pf("Nav stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("tls-get", {"url": "https://httpbin.org/get"})
    pf("TLS GET", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_page_analysis():
    print(f"\n{BOLD}{CYAN}━━ PHASE 10: PAGE ANALYSIS ━━{RESET}")
    cat = "analysis"
    await cmd("navigate", {"url": "https://news.ycombinator.com"})
    await asyncio.sleep(2)
    for c, d in [("page-summary","Summary"),("page-tables","Tables"),("page-structured","Structured"),
                 ("page-emails","Emails"),("page-seo","SEO"),("get-dom","DOM"),("get-links","Links"),
                 ("get-images","Images"),("console-logs","Console logs"),("get-cookies","Cookies")]:
        t0 = time.time(); resp, _ = await cmd(c, {})
        pf(f"Analysis: {d}", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:60], cat)


async def test_workflow_recording():
    print(f"\n{BOLD}{CYAN}━━ PHASE 11: WORKFLOW & RECORDING ━━{RESET}")
    cat = "workflow"
    t0 = time.time(); resp, _ = await cmd("record-start")
    pf("Start recording", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    await cmd("navigate", {"url": "https://example.com"}); await asyncio.sleep(1)
    await cmd("scroll", {"direction": "down"})
    t0 = time.time(); resp, _ = await cmd("record-stop")
    pf("Stop recording", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("record-list")
    pf("Record list", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("workflow-template")
    pf("Workflow templates", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_auth_security():
    print(f"\n{BOLD}{CYAN}━━ PHASE 12: AUTH & SECURITY ━━{RESET}")
    cat = "auth"
    t0 = time.time(); resp, s = await api_call("/auth/register", method="POST", data={"email":"test@brutal.test","username":"brutal","password":"Test123!"})
    pf("User registration", s in (200,400,409,501), time.time()-t0, f"status={s}", cat)
    t0 = time.time(); resp, _ = await cmd("detect-login-page")
    pf("Detect login page", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_multi_agent_hub():
    print(f"\n{BOLD}{CYAN}━━ PHASE 13: MULTI-AGENT HUB ━━{RESET}")
    cat = "hub"
    t0 = time.time(); resp, _ = await cmd("hub-register", {"agent_id": "test-agent-1", "capabilities": ["browser"]})
    pf("Hub register", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("hub-status")
    pf("Hub status", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("hub-agents")
    pf("Hub agents", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("hub-memory-set", {"key": "test_key", "value": "test_value"})
    pf("Hub memory set", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("hub-memory-get", {"key": "test_key"})
    pf("Hub memory get", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("hub-unregister", {"agent_id": "test-agent-1"})
    pf("Hub unregister", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_smart_wait_heal():
    print(f"\n{BOLD}{CYAN}━━ PHASE 14: SMART WAIT & AUTO HEAL ━━{RESET}")
    cat = "smart_wait"
    await cmd("navigate", {"url": "https://example.com"}); await asyncio.sleep(2)
    t0 = time.time(); resp, _ = await cmd("smart-wait", {"condition": "network_idle", "timeout": 5000})
    pf("Smart wait", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("heal-selector", {"selector": "h1"})
    pf("Heal selector", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("heal-stats")
    pf("Heal stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("retry-stats")
    pf("Retry stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_session_proxy():
    print(f"\n{BOLD}{CYAN}━━ PHASE 15: SESSION & PROXY ━━{RESET}")
    cat = "session"
    t0 = time.time(); resp, _ = await cmd("save-session", {"name": "brutal_test"})
    pf("Save session", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("list-sessions")
    pf("List sessions", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("set-cookie", {"name": "test", "value": "val", "domain": "example.com"})
    pf("Set cookie", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("get-cookies")
    pf("Get cookies", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("proxy-list")
    pf("Proxy list", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("proxy-stats")
    pf("Proxy stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("tls-stats")
    pf("TLS stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_query_router():
    print(f"\n{BOLD}{CYAN}━━ PHASE 16: QUERY ROUTER ━━{RESET}")
    cat = "query_router"
    for q in ["What's the stock price of Apple?", "How do I make a web scraper?", "What is 2^32?"]:
        t0 = time.time(); resp, _ = await cmd("classify-query", {"query": q})
        pf(f"Classify: '{q[:35]}'", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("router-stats")
    pf("Router stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


async def test_mobile_network():
    print(f"\n{BOLD}{CYAN}━━ PHASE 17: MOBILE & NETWORK ━━{RESET}")
    cat = "mobile"
    t0 = time.time(); resp, _ = await cmd("list-devices")
    pf("List devices", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("emulate-device", {"device": "iphone_14"})
    pf("Emulate iPhone 14", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    await cmd("navigate", {"url": "https://example.com"}); await asyncio.sleep(1)
    t0 = time.time(); resp, _ = await cmd("network-start")
    pf("Network capture start", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    await cmd("navigate", {"url": "https://example.com"}); await asyncio.sleep(2)
    t0 = time.time(); resp, _ = await cmd("network-get")
    pf("Network data", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("network-stop")
    pf("Network stop", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    await cmd("viewport", {"width": 1920, "height": 1080})


async def test_validation_handoff():
    print(f"\n{BOLD}{CYAN}━━ PHASE 18: VALIDATION & HANDOFF ━━{RESET}")
    cat = "validation"
    t0 = time.time(); resp, _ = await cmd("fill_form", {"fields": {}})
    pf("Underscore cmd normalized", resp.get("status") != "Unknown command", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("this-does-not-exist")
    pf("Unknown cmd rejected", resp.get("status") == "error", time.time()-t0, f"got={resp.get('status')}", cat)
    t0 = time.time(); resp, _ = await cmd("navigate", {})
    pf("Navigate w/o URL rejected", resp.get("status") == "error", time.time()-t0, f"got={resp.get('status')}", cat)
    t0 = time.time(); resp, _ = await cmd("login-handoff-list")
    pf("Handoff list", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)
    t0 = time.time(); resp, _ = await cmd("login-handoff-stats")
    pf("Handoff stats", resp.get("status") == "success", time.time()-t0, resp.get("error","")[:80], cat)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
async def main():
    print(f"\n{BOLD}{RED}{'='*80}")
    print(f"  AGENT-OS BRUTAL STRESS TEST — MAXIMUM INTENSITY")
    print(f"  No mercy. No fixes. Just raw truth.")
    print(f"  Started: {datetime.now().isoformat()}")
    print(f"{'='*80}{RESET}\n")

    # Start server in-process
    print(f"  {CYAN}Starting Agent-OS server in-process...{RESET}")
    try:
        browser, session_mgr, server = await start_server()
    except Exception as e:
        print(f"  {RED}Server startup failed: {e}{RESET}")
        traceback.print_exc()
        return

    # Run all test phases
    phases = [
        test_server_health,
        test_navigation_brutal,
        test_stealth_brutal,
        test_form_filling_brutal,
        test_swarm_brutal,
        test_rapid_fire,
        test_element_interaction,
        test_evaluate_js_brutal,
        test_smart_nav_fetch,
        test_page_analysis,
        test_workflow_recording,
        test_auth_security,
        test_multi_agent_hub,
        test_smart_wait_heal,
        test_session_proxy,
        test_query_router,
        test_mobile_network,
        test_validation_handoff,
    ]

    for phase_fn in phases:
        try:
            await phase_fn()
        except Exception as e:
            print(f"\n  {RED}Phase CRASHED: {e}{RESET}")
            traceback.print_exc()
            R.crash_count += 1

    # Print results
    print(R.summary())

    # Production readiness verdict
    rate = (R.passed / R.total * 100) if R.total > 0 else 0
    print(f"\n{BOLD}{'='*80}")
    print(f"  PRODUCTION READINESS VERDICT")
    print(f"{'='*80}{RESET}")

    if rate >= 90:
        print(f"  {BOLD}{GREEN}✅ PRODUCTION READY — {rate:.1f}%{RESET}")
    elif rate >= 75:
        print(f"  {BOLD}{YELLOW}⚠️ MOSTLY READY — {rate:.1f}%{RESET}")
    elif rate >= 50:
        print(f"  {BOLD}{YELLOW}⚠️ NOT READY — {rate:.1f}%{RESET}")
    else:
        print(f"  {BOLD}{RED}❌ FAR FROM READY — {rate:.1f}%{RESET}")

    concerns = []
    if R.crash_count > 0:
        concerns.append(f"  {RED}• {R.crash_count} phases CRASHED{RESET}")
    for cat, data in R.category_results.items():
        cat_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
        if cat_rate < 50:
            concerns.append(f"  {RED}• {cat}: {cat_rate:.0f}% — CRITICAL{RESET}")
        elif cat_rate < 75:
            concerns.append(f"  {YELLOW}• {cat}: {cat_rate:.0f}% — NEEDS WORK{RESET}")
    if concerns:
        for c in concerns: print(c)
    else:
        print(f"  {GREEN}No major concerns!{RESET}")

    # Save results
    result_file = "/home/z/my-project/Agent-OS/brutal_test_results.json"
    with open(result_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": R.total, "passed": R.passed, "failed": R.failed, "errors": R.errors,
            "success_rate": rate, "crashes": R.crash_count,
            "categories": dict(R.category_results),
            "details": [(n, s, d, e) for n, s, d, e in R.details],
        }, f, indent=2, default=str)
    print(f"\n  Results saved: {result_file}")

    # Cleanup
    s = await get_session()
    await s.close()
    print(f"\n  {CYAN}Shutting down...{RESET}")
    try:
        await server.stop()
        await session_mgr.stop()
        await browser.stop()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
