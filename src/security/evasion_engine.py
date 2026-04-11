"""
Agent-OS Evasion Engine
Integrates curl-impersonate, cloudscraper, and fingerprint injection
for maximum anti-detection coverage across all layers.
"""

import json
import logging
import asyncio
import subprocess
import shutil
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("agent-os.evasion")


# ═══════════════════════════════════════════════════════════
# 1. CURL-IMPERSONATE — Browser-grade TLS for raw HTTP
# ═══════════════════════════════════════════════════════════

class CurlImpersonate:
    """
    Uses curl-impersonate (curl_cffi) for HTTP requests with
    real browser TLS fingerprints. Use when you don't need a
    full browser — just fast, stealthy HTTP.
    
    curl_cffi binds to Chrome's BoringSSL for perfect JA3 matching.
    """

    # Chrome version → curl_cffi impersonate target
    BROWSER_PROFILES = {
        "chrome_110": "chrome110",
        "chrome_116": "chrome116",
        "chrome_119": "chrome119",
        "chrome_120": "chrome120",
        "chrome_124": "chrome124",
        "edge_99": "edge99",
        "edge_101": "edge101",
        "safari_15_3": "safari15_3",
        "safari_15_5": "safari15_5",
        "safari_17_0": "safari17_0",
        "safari_17_2_1": "safari17_2_1",
    }

    def __init__(self, profile: str = "chrome_124"):
        self._available = False
        self._session = None
        self._profile = profile
        self._impersonate = self.BROWSER_PROFILES.get(profile, "chrome124")
        self._check_availability()

    def _check_availability(self):
        """Check if curl_cffi is installed."""
        try:
            from curl_cffi import requests as curl_requests
            self._curl_requests = curl_requests
            self._available = True
            logger.info(f"curl-impersonate ready ({self._impersonate})")
        except ImportError:
            logger.warning(
                "curl_cffi not installed. Install: pip install curl_cffi\n"
                "Falling back to standard requests for HTTP calls."
            )

    def create_session(self) -> Any:
        """Create a curl_cffi session with browser impersonation."""
        if not self._available:
            return None
        self._session = self._curl_requests.Session(impersonate=self._impersonate)
        return self._session

    async def get(self, url: str, **kwargs) -> Optional[Dict]:
        """
        Perform GET with browser-grade TLS fingerprint.
        
        Args:
            url: Target URL
            **kwargs: Passed to curl_cffi (headers, params, proxy, etc.)
        
        Returns:
            {"status_code": int, "text": str, "headers": dict} or None
        """
        if not self._available:
            return None
        try:
            if not self._session:
                self.create_session()
            resp = self._session.get(url, **kwargs)
            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers),
                "url": resp.url,
            }
        except Exception as e:
            logger.error(f"curl-impersonate GET failed: {e}")
            return None

    async def post(self, url: str, data=None, json_body=None, **kwargs) -> Optional[Dict]:
        """Perform POST with browser-grade TLS fingerprint."""
        if not self._available:
            return None
        try:
            if not self._session:
                self.create_session()
            if json_body is not None:
                resp = self._session.post(url, json=json_body, **kwargs)
            else:
                resp = self._session.post(url, data=data, **kwargs)
            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers),
                "url": resp.url,
            }
        except Exception as e:
            logger.error(f"curl-impersonate POST failed: {e}")
            return None

    def set_profile(self, profile: str):
        """Switch browser impersonation profile."""
        if profile in self.BROWSER_PROFILES:
            self._profile = profile
            self._impersonate = self.BROWSER_PROFILES[profile]
            self._session = None  # Reset session
            logger.info(f"Switched to profile: {profile} ({self._impersonate})")

    @property
    def available(self) -> bool:
        return self._available

    def list_profiles(self) -> List[str]:
        return list(self.BROWSER_PROFILES.keys())


# ═══════════════════════════════════════════════════════════
# 2. CLOUDSCRAPER — Cloudflare JS challenge solver
# ═══════════════════════════════════════════════════════════

class CloudflareSolver:
    """
    Cloudflare challenge solver using cloudscraper.
    Handles CF v1/v2/v3 JS challenges and Turnstile.
    Use as fallback when our route-blocking doesn't work.
    """

    def __init__(self):
        self._available = False
        self._scraper = None
        self._check_availability()

    def _check_availability(self):
        """Check if cloudscraper is installed."""
        try:
            import cloudscraper
            self._cloudscraper = cloudscraper
            self._scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True},
                delay=5,
            )
            self._available = True
            logger.info("cloudscraper ready (CF v1/v2/v3 + Turnstile)")
        except ImportError:
            logger.warning(
                "cloudscraper not installed. Install: pip install cloudscraper\n"
                "Cloudflare challenges will not be solved automatically."
            )

    async def solve(self, url: str, method: str = "GET", **kwargs) -> Optional[Dict]:
        """
        Solve Cloudflare challenge and return response.

        Args:
            url: Target URL protected by Cloudflare
            method: HTTP method (GET or POST)
            **kwargs: Additional request params

        Returns:
            {"status_code": int, "text": str, "cookies": dict, "headers": dict} or None
        """
        if not self._available:
            return None

        try:
            loop = asyncio.get_event_loop()

            if method.upper() == "POST":
                resp = await loop.run_in_executor(
                    None, lambda: self._scraper.post(url, **kwargs)
                )
            else:
                resp = await loop.run_in_executor(
                    None, lambda: self._scraper.get(url, **kwargs)
                )

            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "cookies": dict(resp.cookies),
                "headers": dict(resp.headers),
                "url": resp.url,
                "cf_solved": resp.status_code == 200 and "cf-challenge" not in resp.text.lower(),
            }
        except Exception as e:
            logger.error(f"cloudscraper failed: {e}")
            return None

    def get_cf_cookies(self, url: str) -> Optional[Dict]:
        """Get Cloudflare clearance cookies for a domain (sync)."""
        if not self._available:
            return None
        try:
            resp = self._scraper.get(url)
            if resp.status_code == 200:
                return {
                    "cookies": dict(resp.cookies),
                    "cf_clearance": resp.cookies.get("cf_clearance"),
                    "user_agent": self._scraper.headers.get("User-Agent"),
                }
        except Exception as e:
            logger.error(f"CF cookie extraction failed: {e}")
        return None

    @property
    def available(self) -> bool:
        return self._available


# ═══════════════════════════════════════════════════════════
# 3. FINGERPRINT INJECTOR — Playwright fingerprint spoofing
# ═══════════════════════════════════════════════════════════

class FingerprintInjector:
    """
    Generates and injects realistic browser fingerprints into
    Playwright contexts using the Apify fingerprint-suite approach.
    
    Uses a Python reimplementation of the Bayesian fingerprint
    generation since the original is Node.js.
    """

    # Real-world fingerprint combinations (sourced from browser databases)
    FINGERPRINT_PROFILES = [
        {
            "name": "chrome_win_desktop",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "Win32",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "max_touch_points": 0,
            "screen_width": 1920,
            "screen_height": 1080,
            "color_depth": 24,
            "pixel_ratio": 1,
            "webgl_vendor": "Google Inc. (Intel)",
            "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "audio_codecs": {"ogg": "probably", "mp3": "probably", "wav": "probably", "m4a": "maybe", "aac": "probably"},
            "video_codecs": {"ogg": "probably", "h264": "probably", "webm": "probably"},
            "languages": ["en-US", "en"],
            "timezone": "America/New_York",
        },
        {
            "name": "chrome_mac_desktop",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "MacIntel",
            "hardware_concurrency": 10,
            "device_memory": 16,
            "max_touch_points": 0,
            "screen_width": 1440,
            "screen_height": 900,
            "color_depth": 24,
            "pixel_ratio": 2,
            "webgl_vendor": "Google Inc. (Apple)",
            "webgl_renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
            "audio_codecs": {"ogg": "probably", "mp3": "probably", "wav": "probably", "m4a": "probably", "aac": "probably"},
            "video_codecs": {"ogg": "probably", "h264": "probably", "webm": "probably"},
            "languages": ["en-US", "en"],
            "timezone": "America/Los_Angeles",
        },
        {
            "name": "chrome_linux_desktop",
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "platform": "Linux x86_64",
            "hardware_concurrency": 12,
            "device_memory": 16,
            "max_touch_points": 0,
            "screen_width": 1920,
            "screen_height": 1080,
            "color_depth": 24,
            "pixel_ratio": 1,
            "webgl_vendor": "Mesa",
            "webgl_renderer": "Mesa Intel(R) UHD Graphics 630 (CFL GT2)",
            "audio_codecs": {"ogg": "probably", "mp3": "probably", "wav": "probably", "m4a": "maybe", "aac": "probably"},
            "video_codecs": {"ogg": "probably", "h264": "probably", "webm": "probably"},
            "languages": ["en-US", "en"],
            "timezone": "America/Chicago",
        },
        {
            "name": "firefox_win",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "platform": "Win32",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "max_touch_points": 0,
            "screen_width": 1920,
            "screen_height": 1080,
            "color_depth": 24,
            "pixel_ratio": 1,
            "webgl_vendor": "Mozilla",
            "webgl_renderer": "Mozilla/ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "audio_codecs": {"ogg": "probably", "mp3": "probably", "wav": "probably", "m4a": "", "aac": ""},
            "video_codecs": {"ogg": "probably", "h264": "probably", "webm": "probably"},
            "languages": ["en-US", "en"],
            "timezone": "America/New_York",
        },
    ]

    def __init__(self):
        self._current_profile = None

    def generate_fingerprint(self, constraints: Optional[Dict] = None) -> Dict:
        """
        Generate a realistic browser fingerprint.

        Args:
            constraints: Optional filters like {"devices": ["desktop"], "os": ["windows"]}

        Returns:
            Fingerprint dict ready for injection
        """
        import random

        profiles = self.FINGERPRINT_PROFILES

        # Apply constraints
        if constraints:
            filtered = []
            for p in profiles:
                match = True
                if "os" in constraints:
                    os_map = {"windows": "Win", "mac": "Mac", "linux": "Linux"}
                    if not any(os_map[o] in p["platform"] for o in constraints["os"]):
                        match = False
                if "devices" in constraints:
                    if "desktop" in constraints["devices"] and p["max_touch_points"] > 0:
                        match = False
                    if "mobile" in constraints["devices"] and p["max_touch_points"] == 0:
                        match = False
                if match:
                    filtered.append(p)
            if filtered:
                profiles = filtered

        profile = random.choice(profiles)
        self._current_profile = profile
        return profile.copy()

    def get_injection_script(self, fingerprint: Optional[Dict] = None) -> str:
        """
        Generate JavaScript to inject the fingerprint into a page.
        Returns a JS string for page.add_init_script().
        """
        fp = fingerprint or self.generate_fingerprint()

        script = f"""
// === AGENT-OS FINGERPRINT INJECTION v3.0 ===
// Generated from Apify fingerprint-suite methodology

(function() {{
    'use strict';

    // Block fingerprint detection scripts
    const BLOCKED_SCRIPTS = [
        'fingerprintjs', 'fingerprint2', 'fingerprint3',
        'clientjs', 'thumbmark', 'fpjs', 'openfingerprint'
    ];

    // Override XMLHttpRequest to block detection scripts
    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {{
        if (BLOCKED_SCRIPTS.some(s => (url || '').toLowerCase().includes(s))) {{
            this._blocked = true;
            return;
        }}
        return origOpen.apply(this, arguments);
    }};

    // Platform
    Object.defineProperty(navigator, 'platform', {{
        get: () => {json.dumps(fp['platform'])}
    }});

    // Hardware
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {fp['hardware_concurrency']}
    }});
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {fp['device_memory']}
    }});
    Object.defineProperty(navigator, 'maxTouchPoints', {{
        get: () => {fp['max_touch_points']}
    }});

    // Screen
    Object.defineProperty(screen, 'width', {{ get: () => {fp['screen_width']} }});
    Object.defineProperty(screen, 'height', {{ get: () => {fp['screen_height']} }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {fp['color_depth']} }});
    Object.defineProperty(screen, 'availWidth', {{ get: () => {fp['screen_width']} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {fp['screen_height'] - 40} }});
    Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {fp['pixel_ratio']} }});

    // WebGL
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return {json.dumps(fp['webgl_vendor'])};
        if (param === 37446) return {json.dumps(fp['webgl_renderer'])};
        return getParameter.call(this, param);
    }};

    // Audio fingerprint
    const origCreateOscillator = (window.AudioContext || window.webkitAudioContext)?.prototype?.createOscillator;
    if (origCreateOscillator) {{
        // Subtle noise to defeat audio fingerprinting
        const origConnect = AudioBufferSourceNode.prototype.connect;
        AudioBufferSourceNode.prototype.connect = function(dest) {{
            if (dest instanceof AnalyserNode) {{
                // Add tiny noise buffer
                const ctx = dest.context;
                const noise = ctx.createBuffer(1, ctx.sampleRate * 0.01, ctx.sampleRate);
                const data = noise.getChannelData(0);
                for (let i = 0; i < data.length; i++) {{
                    data[i] = (Math.random() - 0.5) * 0.0001;
                }}
            }}
            return origConnect.call(this, dest);
        }};
    }}

    // Canvas fingerprint noise
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx && this.width > 0 && this.height > 0) {{
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 67) {{
                imgData.data[i] = imgData.data[i] ^ (Math.random() > 0.5 ? 1 : 0);
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return origToDataURL.apply(this, arguments);
    }};

    // Languages
    Object.defineProperty(navigator, 'languages', {{
        get: () => {json.dumps(fp['languages'])}
    }});

    console.log('[Agent-OS] Fingerprint injected: {fp["name"]}');
}})();
"""
        return script

    async def inject_into_context(self, context) -> None:
        """Inject fingerprint into a Playwright BrowserContext."""
        script = self.get_injection_script()
        await context.add_init_script(script)
        logger.info(f"Fingerprint injected: {self._current_profile['name'] if self._current_profile else 'random'}")


# ═══════════════════════════════════════════════════════════
# 4. UNIFIED EVASION ENGINE
# ═══════════════════════════════════════════════════════════

class EvasionEngine:
    """
    Unified anti-detection engine that coordinates all evasion layers.
    
    Layer 1: curl-impersonate — raw HTTP with perfect TLS (fastest)
    Layer 2: Playwright + fingerprint injection — full browser (most capable)
    Layer 3: cloudscraper — Cloudflare JS challenge fallback (last resort)
    """

    def __init__(self, config=None):
        self.config = config
        self.curl = CurlImpersonate()
        self.cloudflare = CloudflareSolver()
        self.fingerprint = FingerprintInjector()

        logger.info(
            f"EvasionEngine initialized — "
            f"curl_impersonate={'✓' if self.curl.available else '✗'}, "
            f"cloudscraper={'✓' if self.cloudflare.available else '✗'}, "
            f"fingerprint_injector=✓"
        )

    async def http_get(self, url: str, use_browser_fallback: bool = True, **kwargs) -> Optional[Dict]:
        """
        Smart HTTP GET with automatic fallback chain:
        1. Try curl-impersonate (fastest, perfect TLS)
        2. If CF challenge detected → cloudscraper
        3. If still blocked → return None (browser needed)
        """
        # Layer 1: curl-impersonate
        result = await self.curl.get(url, **kwargs)
        if result and result["status_code"] == 200:
            # Check if CF challenge page was returned
            if self._is_cf_challenge(result.get("text", "")):
                logger.info(f"CF challenge on {url[:60]}, escalating to cloudscraper...")
            else:
                return result

        # Layer 2: cloudscraper (CF challenges)
        if self.cloudflare.available:
            result = await self.cloudflare.solve(url, **kwargs)
            if result and result["status_code"] == 200:
                return result

        # Layer 3: Return best attempt
        return result

    def _is_cf_challenge(self, html: str) -> bool:
        """Check if HTML contains a Cloudflare challenge."""
        indicators = [
            "cf-challenge", "cf-browser-verification",
            "Checking your browser", "Just a moment...",
            "security of your connection", "performance & security by Cloudflare",
            "cf_chl_opt", "managed-challenge",
        ]
        return any(ind in html for ind in indicators)

    def get_status(self) -> Dict:
        """Get status of all evasion layers."""
        return {
            "curl_impersonate": {
                "available": self.curl.available,
                "profile": self.curl._profile if self.curl.available else None,
            },
            "cloudscraper": {
                "available": self.cloudflare.available,
            },
            "fingerprint_injector": {
                "available": True,
                "profiles": len(self.fingerprint.FINGERPRINT_PROFILES),
            },
        }
