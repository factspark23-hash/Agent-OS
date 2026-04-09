"""
Agent-OS Stealth Browser Engine
Advanced anti-detection with real Chrome, cookie persistence, proxy support,
network traffic logging, and retry-based error recovery.
"""
import asyncio
import json
import base64
import random
import time
import logging
import os
import pickle
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from src.core.retry import retry, retry_async

logger = logging.getLogger("agent-os.browser")

# Maximum entries per page in the network log circular buffer
_NETWORK_LOG_LIMIT = 1000
# Maximum post_data size to capture (bytes)
_MAX_POST_DATA_CAPTURE = 1024


# ─── Advanced Anti-Detection JavaScript ───────────────────────
# Injected into every page to fool bot detection systems

ANTI_DETECTION_JS = """
// === AGENT-OS STEALTH MODE v2.0 ===

// 1. Remove ALL webdriver traces
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;

// 2. Realistic plugins (Chrome's actual plugin list)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1, item: () => null, namedItem: () => null},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1, item: () => null, namedItem: () => null},
            {name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 2, item: () => null, namedItem: () => null}
        ];
        plugins.length = 3;
        plugins.item = (i) => plugins[i] || null;
        plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
        plugins.refresh = () => {};
        return plugins;
    }
});

// 3. Languages
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'language', {get: () => 'en-US'});

// 4. Platform
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});

// 5. Hardware info
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});

// 6. Connection
Object.defineProperty(navigator, 'connection', {
    get: () => ({rtt: 50, downlink: 10, effectiveType: '4g', saveData: false, type: 'wifi'})
});

// 7. Permissions override
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        originalQuery(parameters)
);

// 8. Chrome runtime (must exist for real Chrome)
window.chrome = {
    app: {isInstalled: false, InstallState: {INSTALLED: 'installed', DISABLED: 'disabled', NOT_INSTALLED: 'not_installed'}, RunningState: {CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running'}},
    runtime: {
        OnInstalledReason: {CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update'},
        OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
        PlatformArch: {ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
        PlatformNaclArch: {ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
        PlatformOs: {ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win'},
        RequestUpdateCheckStatus: {NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available'},
        connect: function() {},
        sendMessage: function() {},
    },
    csi: function() { return {onloadT: Date.now(), pageT: Date.now(), startE: Date.now()}; },
    loadTimes: function() {
        return {
            commitLoadTime: Date.now() / 1000,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000,
            finishLoadTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000,
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000,
            startLoadTime: Date.now() / 1000,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true
        };
    }
};

// 9. WebGL fingerprint (real Intel GPU)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    if (param === 35661) return 16;  // MAX_TEXTURE_IMAGE_UNITS
    if (param === 34076) return 16384;  // MAX_TEXTURE_SIZE
    if (param === 34921) return 16;  // MAX_VARYING_VECTORS
    if (param === 36347) return 1024;  // MAX_VERTEX_UNIFORM_VECTORS
    if (param === 36349) return 1024;  // MAX_FRAGMENT_UNIFORM_VECTORS
    if (param === 34024) return 16384;  // MAX_RENDERBUFFER_SIZE
    if (param === 3386) return [16384, 16384];  // MAX_VIEWPORT_DIMS
    return getParameter.call(this, param);
};

// 10. Canvas fingerprint noise (subtle, not random each time)
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const context = this.getContext('2d');
    if (context && this.width > 0 && this.height > 0) {
        // Add tiny noise to defeat canvas fingerprinting
        const imageData = context.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < imageData.data.length; i += 100) {
            imageData.data[i] = imageData.data[i] ^ 1;  // XOR single bit
        }
        context.putImageData(imageData, 0, 0);
    }
    return toDataURL.apply(this, arguments);
};

// 11. Audio context fingerprint
const audioContext = window.AudioContext || window.webkitAudioContext;
if (audioContext) {
    const origCreateOscillator = audioContext.prototype.createOscillator;
    audioContext.prototype.createOscillator = function() {
        const osc = origCreateOscillator.call(this);
        const origConnect = osc.connect;
        osc.connect = function(dest) {
            return origConnect.call(this, dest);
        };
        return osc;
    };
}

// 12. Block WebRTC IP leak
const origRTCPeerConnection = window.RTCPeerConnection;
if (origRTCPeerConnection) {
    window.RTCPeerConnection = function(...args) {
        const pc = new origRTCPeerConnection(...args);
        const origCreateOffer = pc.createOffer;
        pc.createOffer = function(options) {
            return origCreateOffer.call(pc, options).then(offer => {
                offer.sdp = offer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                return offer;
            });
        };
        return pc;
    };
    window.RTCPeerConnection.prototype = origRTCPeerConnection.prototype;
}

// 13. Notification permission
Object.defineProperty(Notification, 'permission', {get: () => 'default'});

// 14. Media devices (fake realistic list)
if (navigator.mediaDevices) {
    const origEnumerateDevices = navigator.mediaDevices.enumerateDevices;
    navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await origEnumerateDevices.call(this);
        return [
            {deviceId: 'default', kind: 'audioinput', label: 'Default - Microphone', groupId: 'group1'},
            {deviceId: 'default', kind: 'audiooutput', label: 'Default - Speaker', groupId: 'group1'},
            {deviceId: '', kind: 'videoinput', label: '', groupId: ''},
        ];
    };
}

console.log('[Agent-OS] Stealth patches loaded v2.0');
"""

# Bot detection patterns to block
BOT_DETECTION_URLS = [
    "recaptcha", "captcha", "hcaptcha", "turnstile",
    "perimeterx", "datadome", "cloudflare-challenge",
    "check-bot", "verify-human", "bot-detection",
    "akamai-bot", "imperva", "f5-bot",
    "distil", "shape-security", "kasada",
    "botmanager", "radar", "fingerprint",
]

# Fake human responses for blocked bot detection endpoints
FAKE_RESPONSES = {
    "recaptcha": {"success": True, "score": 0.95, "action": "login", "challenge_ts": "2026-04-08T12:00:00Z"},
    "captcha": {"status": "verified", "human": True, "score": 0.92},
    "perimeterx": {"status": 0, "uuid": "fake-uuid-agent-os", "vid": "fake-vid", "risk_score": 5},
    "datadome": {"status": 200, "headers": {"x-datadome": "pass"}, "cookie": "human-verified"},
    "cloudflare": {"success": True, "cf_clearance": "agent-os-clearance-token"},
    "bot-detection": {"human": True, "verified": True, "timestamp": 1700000000},
}


class AgentBrowser:
    """Core browser engine with advanced anti-detection for AI agents.

    Features:
        - Stealth patches injected on every page
        - Proxy rotation (single or multiple proxies)
        - Network traffic logging with circular buffers
        - Retry-based error recovery for navigation and interaction
        - Human-like mouse movement and typing via HumanMimicry
    """

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
        # Proxy support
        self._proxy_index: int = 0
        self._current_proxy_info: Optional[Dict[str, str]] = None
        # Network logging: page_id → list of request/response entries
        self._network_logs: Dict[str, List[Dict]] = {}
        # Active stealth profile
        self._active_profile: Optional[Dict] = None
        # Current profile name (string identifier)
        self._current_profile: Optional[str] = None
        # HAR recorder instance (lazy init via src.tools.har_recorder)
        self._har_recorder = None

    # ─── Proxy Helpers ────────────────────────────────────────

    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """Get the current proxy configuration from config.

        Checks ``browser.proxies`` (rotation list) first, then falls back to
        ``browser.proxy`` (single proxy).  Supports http, https, and socks5.

        Returns:
            Playwright-compatible proxy dict, or None if no proxy configured.
        """
        # Rotation list takes priority
        proxies: List[str] = self.config.get("browser.proxies", [])
        if proxies:
            idx = self._proxy_index % len(proxies)
            proxy_url = proxies[idx]
            parsed = self._parse_proxy_url(proxy_url)
            self._current_proxy_info = parsed
            logger.info(f"Using proxy #{idx}: {parsed.get('server', proxy_url)}")
            return parsed

        # Single proxy
        proxy = self.config.get("browser.proxy")
        if proxy:
            if isinstance(proxy, dict):
                # Already in Playwright format
                self._current_proxy_info = proxy
                return proxy
            parsed = self._parse_proxy_url(proxy)
            self._current_proxy_info = parsed
            return parsed

        return None

    def _parse_proxy_url(self, proxy_input: Any) -> Dict[str, str]:
        """Parse a proxy URL or dict into Playwright proxy config.

        Supports:
            - ``http://user:pass@host:port``
            - ``https://host:port``
            - ``socks5://host:port``
            - dict with keys: server, username, password, protocol

        Returns:
            Dict with ``server`` (required), ``username``, ``password`` (optional).
        """
        if isinstance(proxy_input, dict):
            # Already structured — normalise keys
            result: Dict[str, str] = {}
            server = proxy_input.get("server", "")
            protocol = proxy_input.get("protocol", "")
            if protocol and "://" not in server:
                server = f"{protocol}://{server}"
            result["server"] = server
            if proxy_input.get("username"):
                result["username"] = proxy_input["username"]
            if proxy_input.get("password"):
                result["password"] = proxy_input["password"]
            return result

        # String URL
        from urllib.parse import urlparse
        proxy_str = str(proxy_input)
        parsed = urlparse(proxy_str)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or proxy_str
        port = parsed.port
        if not port:
            port = 1080 if "socks" in scheme else 8080
        config: Dict[str, str] = {
            "server": f"{scheme}://{host}:{port}",
        }
        if parsed.username:
            config["username"] = parsed.username
        if parsed.password:
            config["password"] = parsed.password
        return config

    async def rotate_proxy(self) -> Dict[str, Any]:
        """Rotate to the next proxy in the list and restart the browser context.

        Creates a brand-new browser context with the new proxy.  All existing
        pages are re-created under the new context so that future requests
        go through the rotated proxy.

        Returns:
            Dict with status and proxy info.
        """
        proxies: List[str] = self.config.get("browser.proxies", [])
        if not proxies:
            return {"status": "error", "error": "No proxies configured. Set browser.proxies first."}

        self._proxy_index = (self._proxy_index + 1) % len(proxies)
        proxy_url = proxies[self._proxy_index]
        proxy_config = self._parse_proxy_url(proxy_url)

        logger.info(f"Rotating to proxy #{self._proxy_index}: {proxy_config.get('server')}")

        # Restart browser with new proxy
        try:
            # Close existing context and browser
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()

            headless = self.config.get("browser.headless", True)
            launch_args = self._build_launch_args()
            launch_options: Dict[str, Any] = {
                "headless": headless,
                "args": launch_args,
                "proxy": proxy_config,
            }

            self.browser = await self.playwright.chromium.launch(**launch_options)

            # Re-create context
            context_options = self._build_context_options()
            self.context = await self.browser.new_context(**context_options)
            await self.context.add_init_script(ANTI_DETECTION_JS)
            if self._active_profile:
                from src.security.stealth_profiles import generate_stealth_js
                profile_js = generate_stealth_js(self._active_profile)
                await self.context.add_init_script(profile_js)
            await self.context.route("**/*", self._handle_request)
            self.context.on("download", self._handle_download)

            # Re-create main page
            self.page = await self.context.new_page()
            self._pages.clear()
            self._pages["main"] = self.page
            self._attach_console_listener("main", self.page)
            self._attach_network_listener("main", self.page)

            self._current_proxy_info = proxy_config

            return {
                "status": "success",
                "proxy_index": self._proxy_index,
                "proxy_server": proxy_config.get("server"),
                "total_proxies": len(proxies),
                "message": "Browser restarted with new proxy.",
            }
        except Exception as e:
            logger.error(f"Proxy rotation failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_current_proxy(self) -> Optional[Dict[str, str]]:
        """Return the currently active proxy config (sans password)."""
        if not self._current_proxy_info:
            return None
        safe = {k: v for k, v in self._current_proxy_info.items() if k != "password"}
        return safe

    # ─── Launch helpers ───────────────────────────────────────

    def _build_launch_args(self) -> List[str]:
        """Build Chrome launch arguments."""
        return [
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
            "--disable-web-security",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
        ]

    def _build_context_options(self) -> Dict[str, Any]:
        """Build browser context options from config."""
        return {
            "user_agent": self.config.get("browser.user_agent"),
            "viewport": self.config.get("browser.viewport", {"width": 1920, "height": 1080}),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation", "notifications"],
            "color_scheme": "light",
            "device_scale_factor": 1.0,
            "has_touch": False,
            "is_mobile": False,
            "java_script_enabled": True,
            "ignore_https_errors": True,
        }

    # ─── Lifecycle ────────────────────────────────────────────

    async def start(self, profile: Optional[Dict] = None):
        """Launch the browser with stealth settings and optional proxy."""
        self._cookie_dir.mkdir(parents=True, exist_ok=True)
        self._download_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = await async_playwright().start()

        headless = self.config.get("browser.headless", True)
        launch_args = self._build_launch_args()

        proxy_config = self._get_proxy_config()
        launch_options: Dict[str, Any] = {
            "headless": headless,
            "args": launch_args,
        }
        if proxy_config:
            launch_options["proxy"] = proxy_config
            logger.info(f"Browser launching with proxy: {proxy_config.get('server')}")

        self.browser = await self.playwright.chromium.launch(**launch_options)

        # Create context with realistic settings
        storage_state = self._load_cookies("default")
        context_options = self._build_context_options()

        # Auto-apply profile from config if not explicitly provided
        if not profile:
            profile_name = self.config.get("browser.profile")
            if profile_name:
                from src.security.stealth_profiles import StealthProfileManager
                profile = StealthProfileManager.get_profile(profile_name)
                if profile:
                    self._current_profile = profile_name
                    logger.info("Auto-applying stealth profile from config: %s", profile_name)
                else:
                    logger.warning("Config profile '%s' not found, using defaults", profile_name)

        # Apply stealth profile if provided
        if profile:
            from src.security.stealth_profiles import apply_profile_to_context_options
            context_options = apply_profile_to_context_options(profile, context_options)
            self._active_profile = profile

        if storage_state:
            context_options["storage_state"] = storage_state

        self.context = await self.browser.new_context(**context_options)

        # Inject stealth script on every page
        await self.context.add_init_script(ANTI_DETECTION_JS)

        # Inject profile-specific stealth if profile active
        if profile:
            from src.security.stealth_profiles import generate_stealth_js
            profile_js = generate_stealth_js(profile)
            await self.context.add_init_script(profile_js)

        # Set up request interception for bot detection blocking
        await self.context.route("**/*", self._handle_request)

        # Set up download handler
        self.context.on("download", self._handle_download)

        self.page = await self.context.new_page()
        self._pages["main"] = self.page
        self._attach_console_listener("main", self.page)
        self._attach_network_listener("main", self.page)

        logger.info("Browser started with stealth patches v2.0")

    # ─── Console & Network Listeners ─────────────────────────

    def _attach_console_listener(self, page_id: str, page: Page):
        """Attach console and error listeners to a page.

        Maintains a circular buffer of the last 200 console entries per page.
        """
        self._console_logs[page_id] = []

        def on_console(msg):
            entry = {
                "type": msg.type,
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
            if len(logs) > 200:
                del logs[:len(logs) - 200]

        def on_page_error(error):
            entry = {
                "type": "pageerror",
                "text": str(error),
                "location": {"url": "", "line": 0, "column": 0},
                "timestamp": time.time(),
            }
            logs = self._console_logs[page_id]
            logs.append(entry)
            if len(logs) > 200:
                del logs[:len(logs) - 200]

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

    def _attach_network_listener(self, page_id: str, page: Page):
        """Attach network request/response logging to a page.

        Captures request and response data, correlating them by URL.
        Maintains a circular buffer of ``_NETWORK_LOG_LIMIT`` entries per page.

        For each request the following fields are captured:
            url, method, resource_type, headers, timestamp, post_data (first 1KB)

        For each response the following fields are captured:
            status, response_headers, content_type, response_size, timing

        Timing includes: request_start, response_start (from Playwright response.timing).
        """
        self._network_logs[page_id] = []
        # Pending requests dict: request_id → log_entry  (for correlation)
        pending: Dict[int, Dict[str, Any]] = {}

        def on_request(request) -> None:
            try:
                # Capture post_data (first 1KB only to cap memory)
                post_data = None
                raw_post = request.post_data
                if raw_post:
                    post_data = raw_post[:_MAX_POST_DATA_CAPTURE]

                entry: Dict[str, Any] = {
                    "url": request.url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                    "headers": dict(request.headers),
                    "timestamp": time.time(),
                    "post_data": post_data,
                    # Response fields (filled later)
                    "status": None,
                    "response_headers": None,
                    "content_type": None,
                    "response_size": None,
                    "timing": None,
                }

                # Store as pending keyed by Python id of the request object
                req_id = id(request)
                pending[req_id] = entry

                logs = self._network_logs[page_id]
                logs.append(entry)
                # Enforce circular buffer limit
                if len(logs) > _NETWORK_LOG_LIMIT:
                    del logs[:len(logs) - _NETWORK_LOG_LIMIT]
            except Exception as e:
                logger.debug(f"Network listener on_request error: {e}")

        def on_response(response) -> None:
            try:
                req_id = id(response.request)
                entry = pending.pop(req_id, None)
                if entry is None:
                    # Fallback: try to find by URL (less reliable)
                    for e in reversed(self._network_logs.get(page_id, [])):
                        if e["url"] == response.url and e["status"] is None:
                            entry = e
                            break

                if entry is not None:
                    entry["status"] = response.status
                    entry["response_headers"] = dict(response.headers)
                    entry["content_type"] = response.headers.get("content-type", "")
                    try:
                        entry["response_size"] = int(response.headers.get("content-length", 0))
                    except (ValueError, TypeError):
                        entry["response_size"] = 0

                    # Capture Playwright timing info
                    try:
                        timing = response.request.timing
                        if timing:
                            entry["timing"] = {
                                "request_start": timing.get("startTime", 0),
                                "response_start": timing.get("responseStart", 0),
                                "response_end": timing.get("responseEnd", 0),
                            }
                    except Exception:
                        entry["timing"] = None
            except Exception as e:
                logger.debug(f"Network listener on_response error: {e}")

        def on_request_failed(request) -> None:
            try:
                req_id = id(request)
                entry = pending.pop(req_id, None)
                if entry is not None:
                    entry["status"] = 0  # 0 indicates a failed request
                    entry["content_type"] = "error"
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("requestfailed", on_request_failed)

    # ─── Network Log API ──────────────────────────────────────

    def get_network_logs(
        self,
        page_id: str = "main",
        filter_url: Optional[str] = None,
        filter_status: Optional[int] = None,
        filter_type: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get filtered network request logs for a page.

        Args:
            page_id:      Tab / page identifier.
            filter_url:   Substring match on URL (case-sensitive).
            filter_status: Exact match on HTTP status code.
            filter_type:  Match on resource_type (e.g. "xhr", "fetch", "document").
            limit:        Maximum number of entries to return (most recent first).

        Returns:
            Dict with status, filtered logs, counts.
        """
        logs = self._network_logs.get(page_id, [])

        if not logs:
            return {
                "status": "success",
                "page_id": page_id,
                "logs": [],
                "returned": 0,
                "total_captured": 0,
            }

        filtered = logs
        if filter_url:
            filtered = [l for l in filtered if filter_url in l.get("url", "")]
        if filter_status is not None:
            filtered = [l for l in filtered if l.get("status") == filter_status]
        if filter_type:
            filtered = [l for l in filtered if l.get("resource_type") == filter_type]

        # Most recent first, capped by limit
        result = list(reversed(filtered[-limit:]))

        return {
            "status": "success",
            "page_id": page_id,
            "logs": result,
            "returned": len(result),
            "total_filtered": len(filtered),
            "total_captured": len(logs),
        }

    def clear_network_logs(self, page_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear network logs for a specific page or all pages.

        Args:
            page_id: If provided, clear only this page. Otherwise clear all.

        Returns:
            Dict with status and count of cleared entries.
        """
        if page_id:
            count = len(self._network_logs.get(page_id, []))
            self._network_logs[page_id] = []
            logger.info(f"Cleared {count} network log entries for page '{page_id}'")
            return {"status": "success", "page_id": page_id, "cleared": count}

        total = sum(len(v) for v in self._network_logs.values())
        self._network_logs.clear()
        logger.info(f"Cleared {total} network log entries across all pages")
        return {"status": "success", "page_id": "all", "cleared": total}

    def get_api_calls(
        self,
        page_id: str = "main",
        filter_url: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get only XHR and Fetch (API) requests from the network log.

        Args:
            page_id:    Tab / page identifier.
            filter_url: Optional substring filter on URL.
            limit:      Maximum entries to return.

        Returns:
            Dict with status, filtered API calls, counts.
        """
        logs = self._network_logs.get(page_id, [])

        api_calls = [
            l for l in logs
            if l.get("resource_type") in ("xhr", "fetch")
        ]

        if filter_url:
            api_calls = [l for l in api_calls if filter_url in l.get("url", "")]

        result = list(reversed(api_calls[-limit:]))

        return {
            "status": "success",
            "page_id": page_id,
            "api_calls": result,
            "returned": len(result),
            "total_api_calls": len(api_calls),
            "total_captured": len(logs),
        }

    # ─── Cookie Helpers ───────────────────────────────────────

    def _load_cookies(self, profile: str) -> Optional[Dict]:
        """Load saved cookies for a profile."""
        cookie_file = self._cookie_dir / f"{profile}.json"
        if cookie_file.exists():
            try:
                with open(cookie_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    async def _save_cookies(self, profile: str = "default"):
        """Save current cookies for persistence."""
        if self.context:
            state = await self.context.storage_state()
            cookie_file = self._cookie_dir / f"{profile}.json"
            with open(cookie_file, "w") as f:
                json.dump(state, f)
            logger.info(f"Cookies saved for profile: {profile}")

    # ─── Download & Request Interception ──────────────────────

    async def _handle_download(self, download):
        """Handle file downloads."""
        download_path = self._download_dir / download.suggested_filename
        await download.save_as(download_path)
        logger.info(f"Downloaded: {download_path}")

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
            for pattern in ["recaptcha", "captcha", "botdetect", "fingerprint", "kasada", "perimeterx"]:
                if pattern in url:
                    logger.debug(f"Blocked bot detection script: {request.url}")
                    await route.fulfill(status=200, body="")
                    return

        # Allow all other requests
        await route.continue_()

    # ─── Navigation & Interaction (with retry) ────────────────

    @retry_async(max_retries=3, backoff_base=1.0, backoff_max=15.0)
    async def navigate(self, url: str, page_id: str = "main", wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        """Navigate to a URL with human-like timing and automatic retry.

        Retries up to 3 times on transient navigation failures (timeouts,
        connection resets, etc.).  Permanent errors like DNS resolution
        failures are not retried.
        """
        page = self._pages.get(page_id, self.page)

        # Human-like delay before navigation
        await asyncio.sleep(random.uniform(0.3, 1.2))

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

    @retry_async(max_retries=2, backoff_base=0.5, backoff_max=5.0)
    async def click(self, selector: str, page_id: str = "main") -> Dict[str, Any]:
        """Click an element with human-like mouse movement.

        Retries up to 2 times on transient failures (element detached,
        click intercepted, etc.).
        """
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

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

    @retry_async(max_retries=2, backoff_base=0.5, backoff_max=5.0)
    async def fill_form(self, fields: Dict[str, str], page_id: str = "main") -> Dict[str, Any]:
        """Fill form fields with human-like typing.

        Retries field-level operations on transient failures.
        """
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

    @retry_async(max_retries=2, backoff_base=0.5, backoff_max=5.0)
    async def type_text(self, text: str, page_id: str = "main") -> Dict[str, Any]:
        """Type text with human-like delays (into focused element).

        Retries on transient keyboard input failures.
        """
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

        for char in text:
            await page.keyboard.type(char, delay=mimicry.typing_delay())

        return {"status": "success", "typed": len(text)}

    # ─── Other interaction methods (unchanged) ────────────────

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
        except Exception as e:
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
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

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
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

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
        from src.security.human_mimicry import HumanMimicry
        page = self._pages.get(page_id, self.page)
        mimicry = HumanMimicry()

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
        """Load a Chrome extension (CRX unpacked directory). Requires headed mode."""
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
        self._attach_network_listener(tab_id, page)
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
            self._network_logs.pop(tab_id, None)
            return True
        return False

    async def set_proxy(self, proxy_url: str) -> Dict[str, Any]:
        """Set a single proxy and restart the browser."""
        self.config.set("browser.proxy", proxy_url)
        return {"status": "success", "message": "Proxy set. Restart browser to apply.", "proxy": proxy_url}

    async def generate_pdf(self, page_id: str = "main", options: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate a PDF of the current page.

        Saves the PDF to ``~/.agent-os/downloads/`` with a timestamped filename.

        Args:
            page_id: Tab to generate PDF from (default "main").
            options: PDF generation options:
                - format: Paper format — "A4", "Letter", "Legal", "Tabloid",
                  or ``{"width": 8.5, "height": 11}`` in inches.
                - landscape: Boolean, landscape orientation.
                - margin: Dict with ``top``, ``right``, ``bottom``, ``left``
                  values as CSS strings (e.g. ``"1cm"``).
                - print_background: Include background graphics (default True).
                - scale: Page scale factor, 0.1 to 2 (default 1).
                - header_template: HTML string for page header.
                - footer_template: HTML string for page footer.
                - prefer_css_page_size: Use CSS-defined page size (default False).

        Returns:
            Dict with ``status``, ``file_path``, ``file_size``, and ``filename``.
        """
        page = self._pages.get(page_id, self.page)
        if page is None:
            return {"status": "error", "error": f"Page '{page_id}' not found."}

        # Build Playwright pdf() kwargs
        pdf_options: Dict[str, Any] = {
            "format": "A4",
            "print_background": True,
            "margin": {"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
        }

        if options:
            # Format: string name or custom {width, height} in inches
            if "format" in options:
                fmt = options["format"]
                if isinstance(fmt, dict):
                    pdf_options["width"] = f"{fmt.get('width', 8.5)}in"
                    pdf_options["height"] = f"{fmt.get('height', 11)}in"
                    pdf_options.pop("format", None)
                else:
                    pdf_options["format"] = fmt

            if "landscape" in options:
                pdf_options["landscape"] = bool(options["landscape"])

            # Accept both "margin" and "margins" as key
            margin = options.get("margin") or options.get("margins")
            if margin and isinstance(margin, dict):
                pdf_options["margin"] = {
                    "top": str(margin.get("top", "1cm")),
                    "right": str(margin.get("right", "1cm")),
                    "bottom": str(margin.get("bottom", "1cm")),
                    "left": str(margin.get("left", "1cm")),
                }

            if "print_background" in options:
                pdf_options["print_background"] = bool(options["print_background"])

            if "scale" in options:
                scale = float(options["scale"])
                pdf_options["scale"] = max(0.1, min(2.0, scale))

            if "header_template" in options:
                pdf_options["header_template"] = str(options["header_template"])

            if "footer_template" in options:
                pdf_options["footer_template"] = str(options["footer_template"])

            if "prefer_css_page_size" in options:
                pdf_options["prefer_css_page_size"] = bool(options["prefer_css_page_size"])

        try:
            pdf_bytes = await page.pdf(**pdf_options)

            # Ensure download directory exists
            self._download_dir.mkdir(parents=True, exist_ok=True)

            # Build safe filename
            title = await page.title()
            safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (title or ""))[:50]
            filename = f"{safe_title or 'page'}_{int(time.time())}.pdf"
            pdf_path = self._download_dir / filename
            pdf_path.write_bytes(pdf_bytes)

            logger.info("PDF generated: %s (%d bytes)", pdf_path, len(pdf_bytes))
            return {
                "status": "success",
                "file_path": str(pdf_path),
                "file_size": len(pdf_bytes),
                "filename": filename,
            }
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def apply_stealth_profile(self, profile_name: str) -> Dict[str, Any]:
        """Apply a stealth profile to the running browser.

        Creates a new browser context with the profile's fingerprint settings,
        migrates cookies, and injects profile-specific anti-detection JS.
        Does NOT require a full browser restart — only a context swap.

        Args:
            profile_name: Name of the profile (e.g. "windows-chrome", "mac-safari").

        Returns:
            Dict with status, profile details, and cookies migrated count.
        """
        from src.security.stealth_profiles import StealthProfileManager
        manager = StealthProfileManager()
        result = await manager.apply_profile(self, profile_name)
        if result.get("status") == "success":
            self._current_profile = profile_name
        return result

    async def set_stealth_profile(self, profile_name: str) -> Dict[str, Any]:
        """Apply a stealth profile (alias for apply_stealth_profile).

        Kept for backward compatibility. Delegates to apply_stealth_profile.

        Args:
            profile_name: Name of the profile to apply.

        Returns:
            Dict with status and profile details.
        """
        return await self.apply_stealth_profile(profile_name)

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
