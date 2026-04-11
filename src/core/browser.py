"""
Agent-OS Stealth Browser Engine
Advanced anti-detection with real Chrome, cookie persistence, proxy support.
"""
import asyncio
import json
import base64
import random
import time
import logging
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

from cryptography.fernet import Fernet
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from src.core.stealth import (
    ANTI_DETECTION_JS,
    handle_request_interception,
)
from src.core.tls_spoof import apply_tls_spoofing
from src.security.human_mimicry import HumanMimicry

logger = logging.getLogger("agent-os.browser")


class AgentBrowser:
    """Core browser engine with advanced anti-detection for AI agents."""

    # Mobile device presets
    DEVICE_PRESETS = {
        "iphone_se": {"width": 375, "height": 667, "device_scale_factor": 2, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
        "iphone_14": {"width": 390, "height": 844, "device_scale_factor": 3, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
        "iphone_14_pro_max": {"width": 430, "height": 932, "device_scale_factor": 3, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
        "ipad": {"width": 768, "height": 1024, "device_scale_factor": 2, "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
        "ipad_pro": {"width": 1024, "height": 1366, "device_scale_factor": 2, "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"},
        "galaxy_s23": {"width": 360, "height": 780, "device_scale_factor": 3, "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"},
        "galaxy_tab_s9": {"width": 800, "height": 1280, "device_scale_factor": 2, "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-X810) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
        "pixel_8": {"width": 412, "height": 915, "device_scale_factor": 2.625, "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"},
        "desktop_1080": {"width": 1920, "height": 1080, "device_scale_factor": 1, "user_agent": None},
        "desktop_1440": {"width": 2560, "height": 1440, "device_scale_factor": 1, "user_agent": None},
        "desktop_4k": {"width": 3840, "height": 2160, "device_scale_factor": 2, "user_agent": None},
    }

    def __init__(self, config):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._active_sessions: Dict[str, Dict] = {}
        self._blocked_requests: int = 0
        self._pages: Dict[str, Page] = {}
        self._console_logs: Dict[str, List[Dict]] = {}  # page_id → list of log entries
        self._cookie_dir = Path(os.path.expanduser("~/.agent-os/cookies"))
        self._download_dir = Path(os.path.expanduser("~/.agent-os/downloads"))
        self._proxy_config = None
        self._current_device = "desktop_1080"
        self._network_capture = None  # Set externally
        self._cookie_key = self._get_or_create_cookie_key()
        self._cookie_fernet = Fernet(self._cookie_key)
        self._crash_count = 0
        self._max_crash_retries = 3
        self._launch_args = None  # cached launch args
        self._recovery_lock = asyncio.Lock()
        # Proxy rotation
        self._proxy_pool: List[Dict[str, Any]] = []
        self._proxy_index: int = 0
        self._proxy_rotation_enabled: bool = False
        # Import at class level to avoid repeated imports
        self._mimicry = HumanMimicry()

    def _get_or_create_cookie_key(self) -> bytes:
        """Get or create encryption key for cookie storage."""
        key_path = Path(os.path.expanduser("~/.agent-os/.cookie_key"))
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    async def start(self):
        """Launch the browser with stealth settings."""
        self._cookie_dir.mkdir(parents=True, exist_ok=True)
        self._download_dir.mkdir(parents=True, exist_ok=True)

        await self._launch_browser()
        logger.info("Browser started with stealth patches v2.0")

    async def _launch_browser(self):
        """Internal: launch browser and set up context."""
        self.playwright = await async_playwright().start()

        # Use headed or headless based on config
        headless = self.config.get("browser.headless", True)

        # Build launch args (cached for recovery)
        if self._launch_args is None:
            self._launch_args = [
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
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-http2",
            ]

        # Build launch options
        launch_options = {
            "headless": headless,
            "args": self._launch_args,
        }

        # Proxy support
        proxy_url = self.config.get("browser.proxy")
        if proxy_url:
            proxy_config = self._parse_proxy_url(proxy_url)
            launch_options["proxy"] = proxy_config
            self._proxy_config = proxy_config
            logger.info(f"Proxy configured: {proxy_config.get('server', 'N/A')}")

        self.browser = await self.playwright.chromium.launch(**launch_options)

        # Create context with realistic settings
        storage_state = self._load_cookies("default")

        context_options = {
            "user_agent": self.config.get("browser.user_agent"),
            "viewport": self.config.get("browser.viewport", {"width": 1920, "height": 1080}),
            "locale": self.config.get("browser.locale", "en-US"),
            "timezone_id": self.config.get("browser.timezone_id", "America/New_York"),
            "permissions": ["geolocation", "notifications"],
            "color_scheme": "light",
            "device_scale_factor": 1.0,
            "has_touch": False,
            "is_mobile": False,
            "java_script_enabled": True,
            "ignore_https_errors": True,
        }

        if storage_state:
            context_options["storage_state"] = storage_state

        self.context = await self.browser.new_context(**context_options)

        # Inject stealth script on every page
        await self.context.add_init_script(ANTI_DETECTION_JS)

        # Set up request interception for bot detection blocking
        await self.context.route("**/*", self._handle_request)

        # Set up download handler
        self.context.on("download", self._handle_download)

        # Apply TLS fingerprint spoofing via CDP
        await apply_tls_spoofing(self.page)

        self.page = await self.context.new_page()
        self._pages["main"] = self.page
        self._attach_console_listener("main", self.page)

    async def recover(self):
        """Recover from browser crash by relaunching."""
        async with self._recovery_lock:
            self._crash_count += 1
            if self._crash_count > self._max_crash_retries:
                logger.error(f"Browser exceeded max crash retries ({self._max_crash_retries})")
                raise RuntimeError("Browser crashed too many times — manual restart required")

            logger.warning(f"Browser recovering from crash (attempt {self._crash_count}/{self._max_crash_retries})...")

            # Save cookies before closing
            try:
                await self._save_cookies("default")
            except Exception:
                pass

            # Close old browser
            try:
                if self.context:
                    await self.context.close()
            except Exception:
                pass
            try:
                if self.browser:
                    await self.browser.close()
            except Exception:
                pass
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception:
                pass

            # Clear state
            self.browser = None
            self.context = None
            self.page = None
            self._pages.clear()
            self._console_logs.clear()

            # Relaunch
            await self._launch_browser()
            self._crash_count = 0  # Reset on successful recovery
            logger.info("Browser recovered successfully")

    async def _safe_execute(self, coro, page_id: str = "main"):
        """Execute a browser operation with crash recovery."""
        try:
            return await coro
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in ["page crashed", "target closed", "context was destroyed",
                                                   "browser has been closed", "frame was detached",
                                                   "session deleted", "disconnected"]):
                logger.warning(f"Browser crash detected: {e}")
                await self.recover()
                raise RuntimeError(f"Browser crashed, recovered. Retry the operation. Original: {e}")
            raise

    def _attach_console_listener(self, page_id: str, page: Page):
        """Attach console and error listeners to a page."""
        self._console_logs[page_id] = []
        MAX_PER_PAGE = 150
        MAX_GLOBAL = 500

        def _enforce_global_cap():
            """Hard cap total console entries across all pages."""
            total = sum(len(v) for v in self._console_logs.values())
            if total > MAX_GLOBAL:
                # Trim oldest pages first
                sorted_pages = sorted(
                    self._console_logs.items(),
                    key=lambda kv: kv[1][0]["timestamp"] if kv[1] else float("inf")
                )
                for pid, logs in sorted_pages:
                    if total <= MAX_GLOBAL:
                        break
                    if pid == page_id:
                        # Trim this page's logs by half
                        half = len(logs) // 2
                        self._console_logs[pid] = logs[half:]
                        total -= half
                    else:
                        removed = len(logs)
                        self._console_logs[pid] = []
                        total -= removed

        def on_console(msg):
            entry = {
                "type": msg.type,               # log, warning, error, info, debug, etc.
                "text": msg.text,
                "location": {
                    "url": msg.location.get("url", ""),
                    "line": msg.location.get("lineNumber", 0),
                    "column": msg.location.get("columnNumber", 0),
                },
                "timestamp": time.time(),
            }
            logs = self._console_logs[page_id]
            logs.append(entry)
            # Per-page cap: drop oldest
            if len(logs) > MAX_PER_PAGE:
                self._console_logs[page_id] = logs[-MAX_PER_PAGE:]
            # Global cap
            _enforce_global_cap()

        def on_page_error(error):
            entry = {
                "type": "pageerror",
                "text": str(error),
                "location": {"url": "", "line": 0, "column": 0},
                "timestamp": time.time(),
            }
            logs = self._console_logs[page_id]
            logs.append(entry)
            if len(logs) > MAX_PER_PAGE:
                self._console_logs[page_id] = logs[-MAX_PER_PAGE:]
            _enforce_global_cap()

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

    def _load_cookies(self, profile: str) -> Optional[Dict]:
        """Load saved cookies for a profile (encrypted)."""
        cookie_file = self._cookie_dir / f"{profile}.enc"
        if cookie_file.exists():
            try:
                encrypted = cookie_file.read_bytes()
                decrypted = self._cookie_fernet.decrypt(encrypted)
                return json.loads(decrypted)
            except Exception as e:
                logger.warning(f"Failed to load encrypted cookies for {profile}: {e}")
        return None

    async def _save_cookies(self, profile: str = "default"):
        """Save current cookies for persistence (encrypted)."""
        if self.context:
            state = await self.context.storage_state()
            cookie_file = self._cookie_dir / f"{profile}.enc"
            encrypted = self._cookie_fernet.encrypt(json.dumps(state).encode())
            cookie_file.write_bytes(encrypted)
            cookie_file.chmod(0o600)
            logger.info(f"Cookies saved (encrypted) for profile: {profile}")

    async def _handle_download(self, download):
        """Handle file downloads."""
        download_path = self._download_dir / download.suggested_filename
        await download.save_as(download_path)
        logger.info(f"Downloaded: {download_path}")

    async def _handle_request(self, route, request):
        """Intercept and block bot detection requests."""
        should_block, fake_response = handle_request_interception(request.url, request.resource_type)
        if should_block:
            self._blocked_requests += 1
            if fake_response:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(fake_response)
                )
            else:
                await route.fulfill(status=200, body="")
            return
        await route.continue_()

    async def navigate(self, url: str, page_id: str = "main", wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        """Navigate to a URL with human-like timing and auto proxy rotation."""
        page = self._pages.get(page_id, self.page)

        # Auto-rotate proxy if pool is configured
        await self._maybe_rotate_proxy()

        # Human-like delay before navigation
        await asyncio.sleep(random.uniform(0.3, 1.2))

        try:
            response = await page.goto(url, wait_until=wait_until, timeout=30000)

            # Wait for page to fully load
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Save cookies after navigation
            await self._save_cookies("default")

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

    async def screenshot(self, page_id: str = "main", full_page: bool = False) -> str:
        """Take a base64 screenshot."""
        page = self._pages.get(page_id, self.page)
        img_bytes = await page.screenshot(type="png", full_page=full_page)
        return base64.b64encode(img_bytes).decode()

    async def fill_form(self, fields: Dict[str, str], page_id: str = "main") -> Dict[str, Any]:
        """Fill form fields with human-like typing."""
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry
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
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry

        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}

            box = await element.bounding_box()
            if box:
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

    async def type_text(self, text: str, page_id: str = "main") -> Dict[str, Any]:
        """Type text with human-like delays (into focused element)."""
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry

        for char in text:
            await page.keyboard.type(char, delay=mimicry.typing_delay())

        return {"status": "success", "typed": len(text)}

    async def press_key(self, key: str, page_id: str = "main") -> Dict[str, Any]:
        """Press a keyboard key (Enter, Tab, Escape, etc.)."""
        page = self._pages.get(page_id, self.page)
        await page.keyboard.press(key)
        return {"status": "success", "key": key}

    async def evaluate_js(self, script: str, page_id: str = "main") -> Any:
        """Execute JavaScript in the page context."""
        page = self._pages.get(page_id, self.page)
        return await page.evaluate(script)

    async def get_dom_snapshot(self, page_id: str = "main") -> str:
        """Get a structured DOM snapshot for agent analysis."""
        page = self._pages.get(page_id, self.page)
        snapshot = await page.evaluate("""() => {
            function getSnapshot(el, depth) {
                if (depth > 5) return '';
                let result = '';
                const indent = '  '.repeat(depth);
                const tag = el.tagName?.toLowerCase() || '';
                if (!tag) return '';

                const attrs = [];
                if (el.id) attrs.push('id="' + el.id + '"');
                if (el.className && typeof el.className === 'string') attrs.push('class="' + el.className + '"');
                if (el.getAttribute('type')) attrs.push('type="' + el.getAttribute('type') + '"');
                if (el.getAttribute('name')) attrs.push('name="' + el.getAttribute('name') + '"');
                if (el.getAttribute('placeholder')) attrs.push('placeholder="' + el.getAttribute('placeholder') + '"');
                if (el.href) attrs.push('href="' + el.href + '"');

                const attrStr = attrs.length ? ' ' + attrs.join(' ') : '';
                const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                    ? el.childNodes[0].textContent.trim().substring(0, 100) : '';

                if (['script', 'style', 'noscript', 'svg'].includes(tag)) return '';

                const children = Array.from(el.children).map(c => getSnapshot(c, depth + 1)).filter(Boolean).join('');

                if (children) {
                    result = indent + '<' + tag + attrStr + '>' + (text ? ' ' + text : '') + '\\n' + children + indent + '</' + tag + '>\\n';
                } else if (text) {
                    result = indent + '<' + tag + attrStr + '>' + text + '</' + tag + '>\\n';
                } else {
                    result = indent + '<' + tag + attrStr + ' />\\n';
                }
                return result;
            }
            return getSnapshot(document.body, 0);
        }""")
        return snapshot

    async def scroll(self, direction: str = "down", amount: int = 500, page_id: str = "main") -> Dict[str, Any]:
        """Scroll with human-like behavior."""
        page = self._pages.get(page_id, self.page)

        y = amount if direction == "down" else -amount
        steps = random.randint(3, 8)

        for i in range(steps):
            step_y = y / steps + random.randint(-20, 20)
            await page.mouse.wheel(0, int(step_y))
            await asyncio.sleep(random.uniform(0.05, 0.15))

        return {"status": "success", "direction": direction, "amount": amount}

    async def hover(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Hover over an element."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}
            await element.hover()
            return {"status": "success", "selector": selector}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def select_option(self, selector: str, value: str, page_id: str = "main") -> Dict[str, Any]:
        """Select an option in a dropdown."""
        page = self._pages.get(page_id, self.page)
        try:
            await page.select_option(selector, value)
            return {"status": "success", "selector": selector, "value": value}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def upload_file(self, selector: str, file_path: str, page_id: str = "main") -> Dict[str, Any]:
        """Upload a file to a file input."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"File input not found: {selector}"}
            await element.set_input_files(file_path)
            return {"status": "success", "selector": selector, "file": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def wait_for_element(self, selector: str, timeout: int = 10000, page_id: str = "main") -> Dict[str, Any]:
        """Wait for an element to appear."""
        page = self._pages.get(page_id, self.page)
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return {"status": "success", "selector": selector}
        except Exception:
            return {"status": "error", "error": f"Timeout waiting for: {selector}"}

    async def go_back(self, page_id: str = "main") -> Dict[str, Any]:
        """Go back in browser history."""
        page = self._pages.get(page_id, self.page)
        await page.go_back()
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"status": "success", "url": page.url, "title": await page.title()}

    async def go_forward(self, page_id: str = "main") -> Dict[str, Any]:
        """Go forward in browser history."""
        page = self._pages.get(page_id, self.page)
        await page.go_forward()
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"status": "success", "url": page.url, "title": await page.title()}

    async def right_click(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Right-click an element (opens context menu)."""
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry

        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}

            box = await element.bounding_box()
            if box:
                target_x = box["x"] + box["width"] / 2
                target_y = box["y"] + box["height"] / 2
                path = mimicry.mouse_path(target_x, target_y)
                for x, y in path:
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.005, 0.02))

            await asyncio.sleep(random.uniform(0.05, 0.15))
            await element.click(button="right")
            await asyncio.sleep(random.uniform(0.2, 0.5))

            return {"status": "success", "selector": selector, "action": "right_click"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def context_action(self, selector: str, action_text: str, page_id: str = "main") -> Dict[str, Any]:
        """Right-click and select a context menu option by text."""
        page = self._pages.get(page_id, self.page)

        # Right-click to open menu
        result = await self.right_click(selector, page_id)
        if result.get("status") != "success":
            return result

        await asyncio.sleep(random.uniform(0.3, 0.8))

        # Try to find and click the menu item
        menu_selectors = [
            f'text="{action_text}"',
            f'role=menuitem[name="{action_text}"]',
            f'[role="menuitem"]:has-text("{action_text}")',
            f'li:has-text("{action_text}")',
            f'div:has-text("{action_text}")',
        ]

        for sel in menu_selectors:
            try:
                item = await page.query_selector(sel)
                if item:
                    await item.click()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    return {"status": "success", "action": action_text, "selector": selector}
            except Exception:
                continue

        # If no menu item found, try keyboard shortcut based on common actions
        shortcuts = {
            "copy": "Control+c",
            "paste": "Control+v",
            "cut": "Control+x",
            "select all": "Control+a",
            "save": "Control+s",
            "inspect": "F12",
            "view source": "Control+u",
            "open in new tab": "Control+click",
            "reload": "F5",
        }

        shortcut = shortcuts.get(action_text.lower())
        if shortcut and "+" in shortcut:
            keys = shortcut.split("+")
            await page.keyboard.press("+".join(keys))
            return {"status": "success", "action": action_text, "method": "keyboard_shortcut"}

        return {"status": "error", "error": f"Context menu action '{action_text}' not found"}

    async def drag_and_drop(self, source_selector: str, target_selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Drag an element and drop it on another element."""
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry

        try:
            source = await page.query_selector(source_selector)
            target = await page.query_selector(target_selector)

            if not source:
                return {"status": "error", "error": f"Source element not found: {source_selector}"}
            if not target:
                return {"status": "error", "error": f"Target element not found: {target_selector}"}

            source_box = await source.bounding_box()
            target_box = await target.bounding_box()

            if not source_box or not target_box:
                return {"status": "error", "error": "Could not get element positions"}

            src_x = source_box["x"] + source_box["width"] / 2
            src_y = source_box["y"] + source_box["height"] / 2
            tgt_x = target_box["x"] + target_box["width"] / 2
            tgt_y = target_box["y"] + target_box["height"] / 2

            # Move to source with human-like path
            path_to_source = mimicry.mouse_path(src_x, src_y)
            for x, y in path_to_source:
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.005, 0.015))

            # Mouse down on source
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # Drag to target with human-like path
            path_to_target = mimicry.mouse_path(tgt_x, tgt_y)
            for x, y in path_to_target:
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.008, 0.02))

            await asyncio.sleep(random.uniform(0.05, 0.15))

            # Drop
            await page.mouse.up()
            await asyncio.sleep(random.uniform(0.2, 0.5))

            return {
                "status": "success",
                "source": source_selector,
                "target": target_selector,
                "from": (round(src_x, 1), round(src_y, 1)),
                "to": (round(tgt_x, 1), round(tgt_y, 1)),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def drag_by_offset(self, selector: str, x_offset: int, y_offset: int, page_id: str = "main") -> Dict[str, Any]:
        """Drag an element by a pixel offset."""
        page = self._pages.get(page_id, self.page)

        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}

            box = await element.bounding_box()
            if not box:
                return {"status": "error", "error": "Could not get element position"}

            src_x = box["x"] + box["width"] / 2
            src_y = box["y"] + box["height"] / 2

            await page.mouse.move(src_x, src_y)
            await page.mouse.down()

            # Move in steps for smooth drag
            steps = max(5, abs(x_offset) // 10 + abs(y_offset) // 10)
            for i in range(1, steps + 1):
                t = i / steps
                x = src_x + x_offset * t + random.gauss(0, 2)
                y = src_y + y_offset * t + random.gauss(0, 2)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.005, 0.015))

            await page.mouse.up()

            return {
                "status": "success",
                "selector": selector,
                "offset": (x_offset, y_offset),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def double_click(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Double-click an element (e.g., to edit a cell, open a file)."""
        page = self._pages.get(page_id, self.page)
        mimicry = self._mimicry

        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}

            box = await element.bounding_box()
            if box:
                target_x = box["x"] + box["width"] / 2
                target_y = box["y"] + box["height"] / 2
                path = mimicry.mouse_path(target_x, target_y)
                for x, y in path:
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.005, 0.02))

            await element.dblclick()
            await asyncio.sleep(random.uniform(0.2, 0.5))

            return {"status": "success", "selector": selector, "action": "double_click"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def clear_input(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Clear an input field."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}
            await element.click()
            await asyncio.sleep(0.1)
            await page.keyboard.press("Control+a")
            await asyncio.sleep(0.05)
            await page.keyboard.press("Backspace")
            return {"status": "success", "selector": selector, "action": "cleared"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def set_checkbox(self, selector: str, checked: bool, page_id: str = "main") -> Dict[str, Any]:
        """Set a checkbox to checked or unchecked."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}
            is_checked = await element.is_checked()
            if is_checked != checked:
                await element.click()
                await asyncio.sleep(random.uniform(0.1, 0.3))
            return {"status": "success", "selector": selector, "checked": checked}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_element_text(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Get text content of a specific element."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}
            text = await element.inner_text()
            return {"status": "success", "selector": selector, "text": text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_element_attribute(self, selector: str, attribute: str, page_id: str = "main") -> Dict[str, Any]:
        """Get an attribute value from an element."""
        page = self._pages.get(page_id, self.page)
        try:
            element = await page.query_selector(selector)
            if not element:
                return {"status": "error", "error": f"Element not found: {selector}"}
            value = await element.get_attribute(attribute)
            return {"status": "success", "selector": selector, "attribute": attribute, "value": value}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def set_viewport(self, width: int, height: int, page_id: str = "main") -> Dict[str, Any]:
        """Change the browser viewport size."""
        page = self._pages.get(page_id, self.page)
        try:
            await page.set_viewport_size({"width": width, "height": height})
            return {"status": "success", "viewport": {"width": width, "height": height}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def add_extension(self, extension_path: str) -> Dict[str, Any]:
        """Load a Chrome extension (CRX unpacked directory). Requires headed mode.

        Usage: First download/extract the extension, then point to its directory.
        Note: Extensions only work in headed mode (--headed flag).
        """
        # Playwright doesn't support dynamic extension loading after launch.
        # Extensions must be loaded at browser launch via --load-extension flag.
        # We store the path and advise restart.
        ext_dir = Path(extension_path)
        if not ext_dir.exists():
            return {"status": "error", "error": f"Extension path does not exist: {extension_path}"}

        manifest = ext_dir / "manifest.json"
        if not manifest.exists():
            return {"status": "error", "error": f"No manifest.json found in {extension_path}"}

        try:
            with open(manifest, "r") as f:
                ext_info = json.load(f)
            ext_name = ext_info.get("name", "Unknown")
            ext_version = ext_info.get("version", "Unknown")
        except Exception:
            ext_name = "Unknown"
            ext_version = "Unknown"

        return {
            "status": "info",
            "message": f"Extension '{ext_name}' v{ext_version} detected. Extensions require headed mode and browser restart.",
            "extension": ext_name,
            "version": ext_version,
            "path": str(ext_dir),
            "note": "To use extensions, restart Agent-OS with: python main.py --headed --extension-path " + str(ext_dir)
        }

    async def get_console_logs(self, page_id: str = "main", clear: bool = False) -> Dict[str, Any]:
        """Get browser console logs captured by Playwright listeners.

        Args:
            page_id: Which tab to read logs from.
            clear: If True, flush the log buffer after reading.
        """
        logs = self._console_logs.get(page_id, [])
        # Return last 100 entries, newest first
        result = logs[-100:]
        if clear:
            self._console_logs[page_id] = []
        return {
            "status": "success",
            "page_id": page_id,
            "logs": result,
            "count": len(result),
            "total_captured": len(logs),
        }

    async def intercept_network(self, url_pattern: str, page_id: str = "main") -> Dict[str, Any]:
        """Monitor network requests matching a URL pattern."""
        page = self._pages.get(page_id, self.page)
        requests = await page.evaluate("""(pattern) => {
            return (window.__agent_os_network || []).filter(r => r.url.includes(pattern));
        }""", url_pattern)
        return {"status": "success", "pattern": url_pattern, "requests": requests}

    async def get_cookies(self, page_id: str = "main") -> Dict[str, Any]:
        """Get all cookies for the current page."""
        page = self._pages.get(page_id, self.page)  # noqa: F841
        cookies = await self.context.cookies()
        return {"status": "success", "cookies": cookies, "count": len(cookies)}

    async def set_cookie(
        self,
        name: str,
        value: str,
        domain: str = None,
        path: str = "/",
        secure: bool = None,
        http_only: bool = False,
        same_site: str = None,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Set a cookie with full Playwright compatibility.

        Args:
            name: Cookie name.
            value: Cookie value.
            domain: Cookie domain. If not set, inferred from current page URL.
            path: Cookie path (default '/').
            secure: Require HTTPS. Auto-detected from current page if not set.
            http_only: Prevent JS access (default False).
            same_site: 'Strict', 'Lax', or 'None'. None = browser default.
            page_id: Tab to infer domain from if domain not provided.
        """
        page = self._pages.get(page_id, self.page)

        # Infer domain from current URL if not provided
        if not domain:
            try:
                parsed = page.url.split("/")
                if len(parsed) >= 3:
                    host = parsed[2]
                    # Strip port if present (e.g., "localhost:8080")
                    if ":" in host and not host.startswith("["):
                        host = host.split(":")[0]
                    # Strip brackets from IPv6
                    host = host.strip("[]")
                    if host and host != "about:blank":
                        domain = host
            except Exception:
                pass

        if not domain:
            return {
                "status": "error",
                "error": "Cannot infer cookie domain: current page has no valid URL. Provide 'domain' explicitly.",
            }

        # Auto-detect secure from URL scheme
        if secure is None:
            secure = page.url.startswith("https://")

        # Build cookie dict — Playwright requires name, value, domain, path
        cookie: Dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
        }

        if secure:
            cookie["secure"] = True
        if http_only:
            cookie["httpOnly"] = True
        if same_site and same_site.capitalize() in ("Strict", "Lax", "None"):
            cookie["sameSite"] = same_site.capitalize()

        try:
            await self.context.add_cookies([cookie])
            return {"status": "success", "cookie": cookie}
        except Exception as e:
            logger.error(f"set_cookie failed: {e}")
            return {"status": "error", "error": str(e)}

    async def reload(self, page_id: str = "main") -> Dict[str, Any]:
        """Reload the current page."""
        page = self._pages.get(page_id, self.page)
        await page.reload()
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return {"status": "success", "url": page.url, "title": await page.title()}

    async def get_all_links(self, page_id: str = "main") -> List[str]:
        """Get all links on the current page."""
        page = self._pages.get(page_id, self.page)
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(href => href.startsWith('http'))
        }""")
        return links

    async def get_all_images(self, page_id: str = "main") -> List[Dict]:
        """Get all images on the current page."""
        page = self._pages.get(page_id, self.page)
        images = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img'))
                .map(img => ({src: img.src, alt: img.alt, width: img.width, height: img.height}))
                .filter(img => img.src.startsWith('http'))
        }""")
        return images

    async def new_tab(self, tab_id: str) -> str:
        """Create a new tab."""
        page = await self.context.new_page()
        self._pages[tab_id] = page
        self._attach_console_listener(tab_id, page)
        return tab_id

    async def switch_tab(self, tab_id: str) -> Dict[str, Any]:
        """Switch to a different tab."""
        if tab_id in self._pages:
            self.page = self._pages[tab_id]
            return {"status": "success", "tab_id": tab_id, "url": self.page.url}
        return {"status": "error", "error": f"Tab not found: {tab_id}"}

    async def close_tab(self, tab_id: str) -> bool:
        """Close a tab."""
        if tab_id in self._pages and tab_id != "main":
            await self._pages[tab_id].close()
            del self._pages[tab_id]
            self._console_logs.pop(tab_id, None)
            return True
        return False

    def _parse_proxy_url(self, proxy_url: str) -> Dict[str, Any]:
        """Parse proxy URL into Playwright proxy config."""
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)

        config = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 8080}",
        }

        if parsed.username:
            config["username"] = parsed.username
        if parsed.password:
            config["password"] = parsed.password

        return config

    async def set_proxy(self, proxy_url: str) -> Dict[str, Any]:
        """
        Set proxy for browser. Requires browser restart to take effect.

        Args:
            proxy_url: Proxy URL — e.g. "http://user:pass@proxy.example.com:8080"
                       or "socks5://proxy.example.com:1080"

        Returns:
            Status and proxy info
        """
        proxy_config = self._parse_proxy_url(proxy_url)
        self._proxy_config = proxy_config

        # Save to config
        self.config.set("browser.proxy", proxy_url)

        return {
            "status": "success",
            "proxy": proxy_config,
            "note": "Proxy will be active after browser restart. Use restart command.",
        }

    async def get_proxy(self) -> Dict[str, Any]:
        """Get current proxy configuration."""
        if not self._proxy_config:
            return {"status": "success", "proxy": None, "message": "No proxy configured"}
        return {"status": "success", "proxy": self._proxy_config}

    async def set_proxy_pool(self, proxy_urls: List[str], rotation_interval: int = 10) -> Dict[str, Any]:
        """
        Set a pool of proxies for automatic rotation. Rotates every N requests.

        Args:
            proxy_urls: List of proxy URLs
                e.g. ["http://proxy1:8080", "socks5://proxy2:1080", "http://user:pass@proxy3:8080"]
            rotation_interval: Rotate proxy every N requests (default: 10)

        Returns:
            Status and pool info
        """
        if not proxy_urls:
            return {"status": "error", "error": "Proxy pool cannot be empty"}

        self._proxy_pool = [self._parse_proxy_url(url) for url in proxy_urls]
        self._proxy_index = 0
        self._proxy_rotation_enabled = True
        self._proxy_rotation_interval = rotation_interval
        self._proxy_request_count = 0

        logger.info(f"Proxy pool configured: {len(self._proxy_pool)} proxies, rotating every {rotation_interval} requests")

        return {
            "status": "success",
            "pool_size": len(self._proxy_pool),
            "rotation_interval": rotation_interval,
            "proxies": [p.get("server", "N/A") for p in self._proxy_pool],
            "note": "Proxy rotation requires browser restart. Use restart command.",
        }

    async def rotate_proxy(self) -> Dict[str, Any]:
        """
        Manually rotate to the next proxy in the pool.
        Restarts the browser with the new proxy.

        Returns:
            Status and new proxy info
        """
        if not self._proxy_pool:
            return {"status": "error", "error": "No proxy pool configured. Use set_proxy_pool first."}

        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_pool)
        self._proxy_config = self._proxy_pool[self._proxy_index]

        # Save cookies before restart
        try:
            await self._save_cookies("default")
        except Exception:
            pass

        # Close and relaunch with new proxy
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        self.browser = None
        self.context = None
        self.page = None
        self._pages.clear()

        await self._launch_browser()

        current = self._proxy_pool[self._proxy_index]
        logger.info(f"Rotated to proxy {self._proxy_index + 1}/{len(self._proxy_pool)}: {current.get('server', 'N/A')}")

        return {
            "status": "success",
            "proxy_index": self._proxy_index,
            "proxy": current,
            "total_proxies": len(self._proxy_pool),
        }

    async def get_proxy_pool(self) -> Dict[str, Any]:
        """Get current proxy pool status."""
        if not self._proxy_pool:
            return {"status": "success", "pool": None, "message": "No proxy pool configured"}

        return {
            "status": "success",
            "pool_size": len(self._proxy_pool),
            "current_index": self._proxy_index,
            "rotation_enabled": self._proxy_rotation_enabled,
            "proxies": [p.get("server", "N/A") for p in self._proxy_pool],
        }

    async def _maybe_rotate_proxy(self):
        """Auto-rotate proxy if pool is configured and threshold is reached."""
        if not self._proxy_rotation_enabled or not self._proxy_pool:
            return

        self._proxy_request_count = getattr(self, "_proxy_request_count", 0) + 1
        interval = getattr(self, "_proxy_rotation_interval", 10)

        if self._proxy_request_count >= interval:
            self._proxy_request_count = 0
            try:
                result = await self.rotate_proxy()
                if result.get("status") == "success":
                    logger.info(f"Auto-rotated proxy to index {self._proxy_index}")
            except Exception as e:
                logger.warning(f"Proxy auto-rotation failed: {e}")

    async def emulate_device(self, device: str) -> Dict[str, Any]:
        """
        Emulate a mobile/tablet/desktop device.

        Available devices:
            Mobile: iphone_se, iphone_14, iphone_14_pro_max, galaxy_s23, pixel_8
            Tablet: ipad, ipad_pro, galaxy_tab_s9
            Desktop: desktop_1080, desktop_1440, desktop_4k

        Args:
            device: Device preset name
        """
        if device not in self.DEVICE_PRESETS:
            return {
                "status": "error",
                "error": f"Unknown device: {device}",
                "available_devices": list(self.DEVICE_PRESETS.keys()),
            }

        preset = self.DEVICE_PRESETS[device]
        self._current_device = device

        # Create new context with device settings
        old_context = self.context

        context_options = {
            "viewport": {"width": preset["width"], "height": preset["height"]},
            "device_scale_factor": preset["device_scale_factor"],
            "is_mobile": preset["device_scale_factor"] > 1 and preset["width"] < 500,
            "has_touch": preset["device_scale_factor"] > 1,
            "user_agent": preset["user_agent"] or self.config.get("browser.user_agent"),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "ignore_https_errors": True,
        }

        self.context = await self.browser.new_context(**context_options)
        await self.context.add_init_script(ANTI_DETECTION_JS)
        await self.context.route("**/*", self._handle_request)

        # Migrate pages
        for page_id, old_page in list(self._pages.items()):
            try:
                url = old_page.url
                new_page = await self.context.new_page()
                self._pages[page_id] = new_page
                if page_id == "main":
                    self.page = new_page
                if url and url != "about:blank":
                    await new_page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await old_page.close()
            except Exception as e:
                logger.warning(f"Failed to migrate page {page_id}: {e}")

        # Close old context
        if old_context:
            try:
                await old_context.close()
            except Exception:
                pass

        logger.info(f"Device emulation: {device} ({preset['width']}x{preset['height']})")

        return {
            "status": "success",
            "device": device,
            "viewport": {"width": preset["width"], "height": preset["height"]},
            "device_scale_factor": preset["device_scale_factor"],
            "is_mobile": preset["device_scale_factor"] > 1 and preset["width"] < 500,
            "user_agent": preset["user_agent"] or self.config.get("browser.user_agent"),
        }

    async def list_devices(self) -> Dict[str, Any]:
        """List all available device emulation presets."""
        devices = {}
        for name, preset in self.DEVICE_PRESETS.items():
            devices[name] = {
                "viewport": f"{preset['width']}x{preset['height']}",
                "device_scale_factor": preset["device_scale_factor"],
                "type": "desktop" if preset["device_scale_factor"] <= 1 else
                        "mobile" if preset["width"] < 500 else
                        "tablet" if preset["width"] < 1920 else
                        "desktop",
            }
        return {"status": "success", "devices": devices, "current": self._current_device}

    async def save_session(self, name: str = "default") -> Dict[str, Any]:
        """
        Save full browser session state: cookies, localStorage, sessionStorage.
        Can be restored later with restore_session().
        """
        session_dir = Path(os.path.expanduser("~/.agent-os/sessions"))
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save storage state (cookies + localStorage)
        state = await self.context.storage_state()
        state_path = session_dir / f"{name}.json"

        # Also capture sessionStorage from all pages
        session_data = {}
        for page_id, page in self._pages.items():
            try:
                storage = await page.evaluate("""() => {
                    const data = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        data[key] = sessionStorage.getItem(key);
                    }
                    return data;
                }""")
                if storage:
                    session_data[page_id] = storage
            except Exception:
                pass

        state["session_storage"] = session_data
        state["saved_at"] = time.time()
        state["device"] = self._current_device
        state["urls"] = {pid: page.url for pid, page in self._pages.items() if page.url != "about:blank"}

        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Session saved: {name} ({state_path})")

        return {
            "status": "success",
            "name": name,
            "path": str(state_path),
            "cookies": len(state.get("cookies", [])),
            "pages": list(state.get("urls", {}).keys()),
        }

    async def restore_session(self, name: str = "default") -> Dict[str, Any]:
        """
        Restore a previously saved browser session.
        Recreates cookies, localStorage, sessionStorage, and navigates to saved URLs.
        """
        session_dir = Path(os.path.expanduser("~/.agent-os/sessions"))
        state_path = session_dir / f"{name}.json"

        if not state_path.exists():
            return {"status": "error", "error": f"Session not found: {name}"}

        with open(state_path, "r") as f:
            state = json.load(f)

        # Close existing context
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass

        # Create new context with saved state
        context_options = {
            "user_agent": self.config.get("browser.user_agent"),
            "viewport": self.config.get("browser.viewport", {"width": 1920, "height": 1080}),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "ignore_https_errors": True,
        }

        # Remove session_storage from state before passing to Playwright
        storage_state = {k: v for k, v in state.items() if k not in ("session_storage", "saved_at", "device", "urls")}
        context_options["storage_state"] = storage_state

        self.context = await self.browser.new_context(**context_options)
        await self.context.add_init_script(ANTI_DETECTION_JS)
        await self.context.route("**/*", self._handle_request)

        # Recreate pages with saved URLs
        saved_urls = state.get("urls", {})
        self._pages = {}

        for page_id, url in saved_urls.items():
            try:
                page = await self.context.new_page()
                self._pages[page_id] = page
                if page_id == "main":
                    self.page = page
                if url and url != "about:blank":
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)

                # Restore sessionStorage
                session_storage = state.get("session_storage", {}).get(page_id, {})
                if session_storage:
                    for key, value in session_storage.items():
                        try:
                            await page.evaluate(
                                "(k, v) => sessionStorage.setItem(k, v)",
                                key, value
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Failed to restore page {page_id}: {e}")

        # Ensure main page exists
        if "main" not in self._pages:
            self.page = await self.context.new_page()
            self._pages["main"] = self.page

        device = state.get("device", "desktop_1080")
        self._current_device = device

        logger.info(f"Session restored: {name}")

        return {
            "status": "success",
            "name": name,
            "cookies": len(state.get("cookies", [])),
            "pages_restored": list(saved_urls.keys()),
            "device": device,
            "saved_at": state.get("saved_at"),
        }

    async def list_sessions(self) -> Dict[str, Any]:
        """List all saved sessions."""
        session_dir = Path(os.path.expanduser("~/.agent-os/sessions"))
        sessions = []

        if session_dir.exists():
            for path in session_dir.glob("*.json"):
                try:
                    with open(path) as f:
                        state = json.load(f)
                    sessions.append({
                        "name": path.stem,
                        "cookies": len(state.get("cookies", [])),
                        "pages": list(state.get("urls", {}).keys()),
                        "device": state.get("device", "unknown"),
                        "saved_at": state.get("saved_at"),
                    })
                except Exception:
                    continue

        return {"status": "success", "sessions": sessions}

    async def delete_session(self, name: str) -> Dict[str, Any]:
        """Delete a saved session."""
        session_dir = Path(os.path.expanduser("~/.agent-os/sessions"))
        state_path = session_dir / f"{name}.json"

        if not state_path.exists():
            return {"status": "error", "error": f"Session not found: {name}"}

        state_path.unlink()
        return {"status": "success", "deleted": name}

    async def stop(self):
        """Clean shutdown."""
        # Save cookies before closing
        await self._save_cookies("default")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser stopped")
