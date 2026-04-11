"""
Agent-OS Evasion Engine
Real fingerprint generation, cloudscraper integration, unified HTTP engine.
"""

import json
import logging
import random
import hashlib
import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger("agent-os.evasion")


# ═══════════════════════════════════════════════════════════════
# REALISTIC BROWSER DATA — sourced from real browser telemetry
# ═══════════════════════════════════════════════════════════════

# GPU renderers actually seen in Chrome on Windows (real data)
WINDOWS_WEBGL_RENDERERS = [
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
]

MAC_WEBGL_RENDERERS = [
    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M1, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M2, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M2 Pro, OpenGL 4.1)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel Iris Plus Graphics 640, OpenGL 4.1)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon Pro 5500M, OpenGL 4.1)"),
]

LINUX_WEBGL_RENDERERS = [
    ("Mesa", "Mesa Intel(R) UHD Graphics 630 (CFL GT2)"),
    ("Mesa", "Mesa Intel(R) HD Graphics 620 (KBL GT2)"),
    ("Mesa", "llvmpipe (LLVM 15.0.7, 256 bits)"),
    ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060 6GB/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
    ("AMD", "AMD Radeon RX 6700 XT (navi22, LLVM 15.0.7, DRM 3.49, 6.1.0-18-amd64)"),
]

# Screen resolutions with market share weights (approximate %)
SCREEN_RESOLUTIONS = [
    # (width, height, weight)
    (1920, 1080, 25),
    (1536, 864, 12),
    (1366, 768, 10),
    (1440, 900, 8),
    (1280, 720, 7),
    (2560, 1440, 6),
    (1600, 900, 5),
    (1280, 1024, 4),
    (3840, 2160, 3),
    (2560, 1080, 3),
    (1680, 1050, 2),
]

# CPU core counts with distribution
CPU_CORES = [
    (4, 15), (8, 35), (6, 20), (12, 12), (16, 8), (2, 5), (10, 5),
]

# RAM amounts in GB with distribution
DEVICE_MEMORY_GB = [
    (8, 30), (16, 35), (4, 15), (32, 10), (2, 5), (64, 5),
]

# Chrome version distribution (approximate market share)
CHROME_VERSIONS = [
    ("124", 20), ("123", 18), ("122", 15), ("121", 12),
    ("120", 10), ("119", 8), ("116", 5), ("110", 4),
]

# Timezone distribution
TIMEZONES = [
    ("America/New_York", 20), ("America/Chicago", 10),
    ("America/Los_Angeles", 15), ("America/Denver", 5),
    ("Europe/London", 12), ("Europe/Berlin", 10),
    ("Europe/Paris", 8), ("Asia/Tokyo", 5),
    ("Asia/Shanghai", 5), ("America/Phoenix", 3),
    ("America/Anchorage", 2), ("Pacific/Honolulu", 2),
    ("America/Toronto", 3),
]


def _weighted_choice(items: list) -> Any:
    """Pick from a list of (value, weight) tuples using weighted random."""
    total = sum(item[-1] for item in items)
    r = random.uniform(0, total)
    cumulative = 0
    for item in items:
        cumulative += item[-1]
        if r <= cumulative:
            # Return everything except the weight
            return item[0] if len(item) == 2 else tuple(item[:-1])
    last = items[-1]
    return last[0] if len(last) == 2 else tuple(last[:-1])


def generate_fingerprint(
    os_target: str = "windows",
    device_type: str = "desktop",
    chrome_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a realistic, randomized browser fingerprint.
    Uses weighted distributions based on real-world browser statistics.

    Args:
        os_target: "windows", "mac", or "linux"
        device_type: "desktop" or "mobile"
        chrome_version: Specific Chrome version, or None for random

    Returns:
        Complete fingerprint dict
    """
    if chrome_version is None:
        chrome_version = _weighted_choice(CHROME_VERSIONS)

    # Pick screen resolution
    screen_w, screen_h = _weighted_choice(SCREEN_RESOLUTIONS)

    # Pick hardware
    cores = _weighted_choice(CPU_CORES)
    memory = _weighted_choice(DEVICE_MEMORY_GB)
    timezone = _weighted_choice(TIMEZONES)

    # Pick GPU based on OS
    if os_target == "windows":
        gl_vendor, gl_renderer = random.choice(WINDOWS_WEBGL_RENDERERS)
        platform = "Win32"
        ua_os = "Windows NT 10.0; Win64; x64"
    elif os_target == "mac":
        gl_vendor, gl_renderer = random.choice(MAC_WEBGL_RENDERERS)
        platform = "MacIntel"
        ua_os = "Macintosh; Intel Mac OS X 10_15_7"
        # Macs commonly have higher pixel ratios
        screen_w, screen_h = _weighted_choice([
            (1440, 900, 20), (1680, 1050, 15), (1920, 1080, 15),
            (2560, 1600, 10), (2560, 1440, 10), (3024, 1964, 8),
            (3456, 2234, 7), (2880, 1800, 8), (1512, 982, 7),
        ])
    else:
        gl_vendor, gl_renderer = random.choice(LINUX_WEBGL_RENDERERS)
        platform = "Linux x86_64"
        ua_os = "X11; Linux x86_64"

    # Pixel ratio (Mac = 2x usually, Windows/Linux = 1x)
    if os_target == "mac":
        pixel_ratio = random.choice([1, 2, 2, 2, 2])  # Most Macs are Retina
    else:
        pixel_ratio = random.choice([1, 1, 1, 1, 1.25, 1.5])

    # Touch support
    max_touch = 0
    is_mobile = False
    if device_type == "mobile":
        max_touch = random.choice([5, 10])
        is_mobile = True
        ua_os = "Linux; Android 14; Pixel 8"

    # Canvas noise seed (unique per fingerprint)
    canvas_seed = random.randint(1, 2**31)

    # Audio context seed
    audio_seed = random.randint(1, 2**31)

    # User agent
    if device_type == "mobile":
        user_agent = (
            f"Mozilla/5.0 ({ua_os}) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36"
        )
    else:
        user_agent = (
            f"Mozilla/5.0 ({ua_os}) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"
        )

    # Generate unique fingerprint ID for consistency
    fp_id = hashlib.md5(
        f"{user_agent}{gl_renderer}{canvas_seed}{audio_seed}".encode()
    ).hexdigest()[:12]

    return {
        "id": fp_id,
        "chrome_version": chrome_version,
        "user_agent": user_agent,
        "platform": platform,
        "os": os_target,
        "device_type": device_type,
        "hardware_concurrency": cores,
        "device_memory": memory,
        "max_touch_points": max_touch,
        "screen_width": screen_w,
        "screen_height": screen_h,
        "color_depth": 24,
        "pixel_ratio": pixel_ratio,
        "is_mobile": is_mobile,
        "webgl_vendor": gl_vendor,
        "webgl_renderer": gl_renderer,
        "timezone": timezone,
        "canvas_seed": canvas_seed,
        "audio_seed": audio_seed,
        "languages": ["en-US", "en"],
    }


def build_fingerprint_injection_js(fp: Dict[str, Any]) -> str:
    """
    Build JavaScript to inject a fingerprint into a Playwright page.
    This is injected via context.add_init_script() and runs BEFORE
    any page scripts.

    The fingerprint covers: navigator, screen, WebGL, canvas, audio,
    timezone, and blocks known fingerprinting libraries.
    """
    # Escape for JS string embedding
    ua = json.dumps(fp["user_agent"])
    platform = json.dumps(fp["platform"])
    gl_vendor = json.dumps(fp["webgl_vendor"])
    gl_renderer = json.dumps(fp["webgl_renderer"])
    canvas_seed = fp["canvas_seed"]
    audio_seed = fp["audio_seed"]
    timezone = json.dumps(fp["timezone"])
    pixel_ratio = fp["pixel_ratio"]
    cores = fp["hardware_concurrency"]
    memory = fp["device_memory"]
    touch = fp["max_touch_points"]
    sw = fp["screen_width"]
    sh = fp["screen_height"]
    color_depth = fp["color_depth"]
    is_mobile = json.dumps(fp["is_mobile"])

    return f"""
// === AGENT-OS FINGERPRINT v3.0 [{fp['id']}] ===
// Generated: {fp['os']} Chrome {fp['chrome_version']} {fp['webgl_renderer'][:40]}

(function() {{
'use strict';

// ── BLOCK FINGERPRINTING LIBRARIES ──
const blocked = [
    'fingerprintjs', 'fingerprint2', 'fingerprint3',
    'clientjs', 'thumbmark', 'fpjs', 'openfingerprint',
    'sardine', 'iovation', 'threatmetrix', 'nethra',
    'seon', 'ipqualityscore', 'fraudlabs'
];
const origFetch = window.fetch;
window.fetch = function(url, opts) {{
    if (blocked.some(b => String(url).toLowerCase().includes(b))) {{
        return Promise.resolve(new Response('{{"error":"blocked"}}', {{status: 200}}));
    }}
    return origFetch.apply(this, arguments);
}};
const origXHR = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url) {{
    if (blocked.some(b => String(url).toLowerCase().includes(b))) {{
        this._blocked = true;
        return;
    }}
    return origXHR.apply(this, arguments);
}};

// ── NAVIGATOR OVERRIDES ──
Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
delete navigator.__proto__.webdriver;

Object.defineProperty(navigator, 'platform', {{ get: () => {platform} }});
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {cores} }});
Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {memory} }});
Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {touch} }});
Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});

// Plugins
Object.defineProperty(navigator, 'plugins', {{
    get: () => {{
        const p = [
            {{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer',description:'Portable Document Format',length:1,item:()=>null,namedItem:()=>null}},
            {{name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai',description:'',length:1,item:()=>null,namedItem:()=>null}},
            {{name:'Native Client',filename:'internal-nacl-plugin',description:'',length:2,item:()=>null,namedItem:()=>null}}
        ];
        p.length = 3; p.item = i => p[i]||null; p.namedItem = n => p.find(x=>x.name===n)||null; p.refresh = ()=>{{}};
        return p;
    }}
}});

// Connection
Object.defineProperty(navigator, 'connection', {{
    get: () => ({{rtt: {random.randint(20,100)}, downlink: {random.randint(5,50)}, effectiveType: '4g', saveData: false, type: 'wifi'}})
}});

// ── SCREEN OVERRIDES ──
Object.defineProperty(screen, 'width', {{ get: () => {sw} }});
Object.defineProperty(screen, 'height', {{ get: () => {sh} }});
Object.defineProperty(screen, 'availWidth', {{ get: () => {sw} }});
Object.defineProperty(screen, 'availHeight', {{ get: () => {sh - random.randint(30,80)} }});
Object.defineProperty(screen, 'colorDepth', {{ get: () => {color_depth} }});
Object.defineProperty(screen, 'pixelDepth', {{ get: () => {color_depth} }});
Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {pixel_ratio} }});

// ── WEBGL FINGERPRINT ──
const origGetParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {{
    if (param === 37445) return {gl_vendor};
    if (param === 37446) return {gl_renderer};
    if (param === 35661) return {random.randint(16,32)};    // MAX_TEXTURE_IMAGE_UNITS
    if (param === 34076) return {random.randint(16384,32768)}; // MAX_TEXTURE_SIZE
    if (param === 34921) return {random.randint(16,32)};    // MAX_VARYING_VECTORS
    if (param === 36347) return {random.randint(1024,4096)}; // MAX_VERTEX_UNIFORM_VECTORS
    if (param === 36349) return {random.randint(1024,4096)}; // MAX_FRAGMENT_UNIFORM_VECTORS
    if (param === 34024) return {random.randint(16384,32768)}; // MAX_RENDERBUFFER_SIZE
    if (param === 3386) return [{random.randint(16384,32768)}, {random.randint(16384,32768)}]; // MAX_VIEWPORT_DIMS
    return origGetParam.call(this, param);
}};

// WebGL2 too
if (typeof WebGL2RenderingContext !== 'undefined') {{
    const origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return {gl_vendor};
        if (param === 37446) return {gl_renderer};
        return origGetParam2.call(this, param);
    }};
}}

// ── CANVAS FINGERPRINT NOISE ──
const _canvasSeed = {canvas_seed};
function seededRandom(seed) {{
    let s = seed;
    return function() {{
        s = (s * 16807 + 0) % 2147483647;
        return (s - 1) / 2147483646;
    }};
}}

const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {{
    const ctx = this.getContext('2d');
    if (ctx && this.width > 0 && this.height > 0) {{
        const rng = seededRandom(_canvasSeed + this.width * this.height);
        const imageData = ctx.getImageData(0, 0, this.width, this.height);
        // Modify 0.01% of pixels with seeded noise
        const step = Math.max(67, Math.floor(imageData.data.length / 10000));
        for (let i = 0; i < imageData.data.length; i += step) {{
            const noise = Math.floor(rng() * 3) - 1;
            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
        }}
        ctx.putImageData(imageData, 0, 0);
    }}
    return origToDataURL.apply(this, arguments);
}};

const origToBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(cb, type, quality) {{
    const ctx = this.getContext('2d');
    if (ctx && this.width > 0 && this.height > 0) {{
        const rng = seededRandom(_canvasSeed + this.width * this.height);
        const imageData = ctx.getImageData(0, 0, this.width, this.height);
        const step = Math.max(67, Math.floor(imageData.data.length / 10000));
        for (let i = 0; i < imageData.data.length; i += step) {{
            const noise = Math.floor(rng() * 3) - 1;
            imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
        }}
        ctx.putImageData(imageData, 0, 0);
    }}
    return origToBlob.apply(this, arguments);
}};

// ── AUDIO FINGERPRINT NOISE ──
const _audioSeed = {audio_seed};
const origCreateAnalyser = (window.AudioContext || window.webkitAudioContext)?.prototype?.createAnalyser;
if (origCreateAnalyser) {{
    const origGetFloatFrequencyData = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
        origGetFloatFrequencyData.call(this, array);
        const rng = seededRandom(_audioSeed);
        for (let i = 0; i < array.length; i++) {{
            array[i] += (rng() - 0.5) * 0.0001;
        }}
    }};
}}

// ── CHROME RUNTIME ──
window.chrome = window.chrome || {{}};
window.chrome.app = window.chrome.app || {{
    isInstalled: false,
    InstallState: {{INSTALLED:'installed', DISABLED:'disabled', NOT_INSTALLED:'not_installed'}},
    RunningState: {{CANNOT_RUN:'cannot_run', READY_TO_RUN:'ready_to_run', RUNNING:'running'}}
}};
window.chrome.runtime = window.chrome.runtime || {{
    OnInstalledReason: {{CHROME_UPDATE:'chrome_update',INSTALL:'install',SHARED_MODULE_UPDATE:'shared_module_update',UPDATE:'update'}},
    OnRestartRequiredReason: {{APP_UPDATE:'app_update',OS_UPDATE:'os_update',PERIODIC:'periodic'}},
    PlatformArch: {{ARM:'arm',MIPS:'mips',MIPS64:'mips64',X86_32:'x86-32',X86_64:'x86-64'}},
    PlatformOs: {{ANDROID:'android',CROS:'cros',LINUX:'linux',MAC:'mac',OPENBSD:'openbsd',WIN:'win'}},
    RequestUpdateCheckStatus: {{NO_UPDATE:'no_update',THROTTLED:'throttled',UPDATE_AVAILABLE:'update_available'}},
    connect: function(){{}},
    sendMessage: function(){{}},
}};

// ── PERMISSIONS ──
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) => (
    params.name === 'notifications'
        ? Promise.resolve({{state: Notification.permission}})
        : origQuery(params)
);

// ── BLOCK WEBRTC IP LEAK ──
const origRTC = window.RTCPeerConnection;
if (origRTC) {{
    window.RTCPeerConnection = function(...args) {{
        const pc = new origRTC(...args);
        const origCreateOffer = pc.createOffer;
        pc.createOffer = function(opts) {{
            return origCreateOffer.call(pc, opts).then(offer => {{
                offer.sdp = offer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                return offer;
            }});
        }};
        return pc;
    }};
    window.RTCPeerConnection.prototype = origRTC.prototype;
}}

// ── NOTIFICATION ──
Object.defineProperty(Notification, 'permission', {{get: () => 'default'}});

console.log('[Agent-OS] Fingerprint v3.0 injected: {fp['id']} ({fp['os']} Chrome {fp['chrome_version']})');
}})();
"""


# ═══════════════════════════════════════════════════════════════
# CLOUDSCRAPER INTEGRATION
# ═══════════════════════════════════════════════════════════════

_CLOUDSCRAPER_AVAILABLE = False
try:
    import cloudscraper as _cloudscraper_module
    _CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    pass


class CloudflareSolver:
    """
    Cloudflare JS challenge solver. Handles CF v1/v2/v3 + Turnstile.
    Use as fallback when Playwright route-blocking isn't enough.
    """

    def __init__(self):
        self._scraper = None
        if _CLOUDSCRAPER_AVAILABLE:
            self._scraper = _cloudscraper_module.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True},
                delay=5,
            )
            logger.info("cloudscraper ready")
        else:
            logger.warning("cloudscraper not installed: pip install cloudscraper")

    def solve(self, url: str, method: str = "GET", **kwargs) -> Optional[Dict[str, Any]]:
        """
        Solve Cloudflare challenge and return response.
        Runs in thread executor to not block async loop.
        """
        if not self._scraper:
            return None
        try:
            if method.upper() == "POST":
                resp = self._scraper.post(url, **kwargs)
            else:
                resp = self._scraper.get(url, **kwargs)

            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "cookies": dict(resp.cookies),
                "headers": dict(resp.headers),
                "url": resp.url,
                "cf_solved": resp.status_code == 200,
            }
        except Exception as e:
            logger.error(f"cloudscraper failed for {url[:60]}: {e}")
            return None

    def get_clearance_cookies(self, url: str) -> Optional[Dict]:
        """Get cf_clearance cookies for reuse in Playwright."""
        if not self._scraper:
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
        return _CLOUDSCRAPER_AVAILABLE


# ═══════════════════════════════════════════════════════════════
# UNIFIED EVASION ENGINE
# ═══════════════════════════════════════════════════════════════

class EvasionEngine:
    """
    Coordinates all evasion layers:
    
    - TLS: curl_cffi for HTTP requests, CDP spoofing for Playwright
    - Fingerprint: Randomized per-session generation + JS injection
    - Cloudflare: cloudscraper fallback for CF challenges
    """

    def __init__(self):
        # TLS engine (curl_cffi)
        from src.core.tls_spoof import TLSFingerprintEngine
        try:
            self.tls = TLSFingerprintEngine()
        except ImportError:
            self.tls = None
            logger.warning("TLS engine unavailable (install curl_cffi)")

        # Cloudflare solver
        self.cloudflare = CloudflareSolver()

        # Active fingerprints (page_id → fingerprint)
        self._fingerprints: Dict[str, Dict] = {}

    def generate_fingerprint(
        self,
        os_target: Optional[str] = None,
        page_id: str = "main",
    ) -> Dict[str, Any]:
        """Generate and store a new fingerprint for a page."""
        if os_target is None:
            os_target = random.choice(["windows", "windows", "windows", "mac", "linux"])

        fp = generate_fingerprint(os_target=os_target)
        self._fingerprints[page_id] = fp
        return fp

    def get_injection_js(self, page_id: str = "main") -> str:
        """Get the JS injection script for a page's fingerprint."""
        fp = self._fingerprints.get(page_id)
        if not fp:
            fp = self.generate_fingerprint(page_id=page_id)
        return build_fingerprint_injection_js(fp)

    async def inject_into_page(self, page, page_id: str = "main"):
        """Generate fingerprint and inject into a Playwright page."""
        js = self.get_injection_js(page_id)
        await page.add_init_script(js)

    def get_fingerprint(self, page_id: str = "main") -> Optional[Dict]:
        return self._fingerprints.get(page_id)

    def list_fingerprints(self) -> Dict[str, str]:
        """Summary of active fingerprints."""
        return {
            pid: f"{fp['os']} Chrome {fp['chrome_version']} / {fp['webgl_renderer'][:30]}"
            for pid, fp in self._fingerprints.items()
        }

    @property
    def status(self) -> Dict:
        return {
            "tls_engine": self.tls.stats if self.tls else {"available": False},
            "cloudflare": {"available": self.cloudflare.available},
            "active_fingerprints": len(self._fingerprints),
        }
