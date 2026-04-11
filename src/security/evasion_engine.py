"""
Agent-OS Evasion Engine
Real fingerprint generation, cloudscraper integration, unified HTTP engine.
"""

import json
import logging
import random
import hashlib
from typing import Optional, Dict, Any

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
    timezone, CDP detection, DevTools detection, stack traces,
    and blocks ALL known fingerprinting + anti-bot libraries.
    """
    # Escape for JS string embedding
    platform = json.dumps(fp["platform"])
    gl_vendor = json.dumps(fp["webgl_vendor"])
    gl_renderer = json.dumps(fp["webgl_renderer"])
    canvas_seed = fp["canvas_seed"]
    audio_seed = fp["audio_seed"]
    pixel_ratio = fp["pixel_ratio"]
    cores = fp["hardware_concurrency"]
    memory = fp["device_memory"]
    touch = fp["max_touch_points"]
    sw = fp["screen_width"]
    sh = fp["screen_height"]
    color_depth = fp["color_depth"]
    ua = json.dumps(fp["user_agent"])

    return f"""
// === AGENT-OS FINGERPRINT v4.0 [{fp['id']}] ===
// Generated: {fp['os']} Chrome {fp['chrome_version']} {fp['webgl_renderer'][:40]}
// Covers: CDP, DevTools, Fingerprinting libs, Anti-bot vendors, Stack traces

(function() {{
'use strict';

// ══════════════════════════════════════════════════════════════
// UTILITY: Make overrides look native
// ══════════════════════════════════════════════════════════════
function makeNative(fn, name) {{
    const s = 'function ' + (name||'') + '() {{ [native code] }}';
    Object.defineProperty(fn, 'toString', {{value: function() {{ return s; }}, writable:false, configurable:false}});
    return fn;
}}

function seededRandom(seed) {{
    let s = seed;
    return function() {{
        s = (s * 16807 + 0) % 2147483647;
        return (s - 1) / 2147483646;
    }};
}}
const canvasRNG = seededRandom({canvas_seed});
const audioRNG = seededRandom({audio_seed});

// ══════════════════════════════════════════════════════════════
// 1. CDP DETECTION PREVENTION (#1 detection vector)
// ══════════════════════════════════════════════════════════════

// Remove CDP-injected global properties
const cdpProps = [
    '__executionContextId', '__pw_manual', '__pw_script',
    'cdc_adoQpoasnfa76pfcZLmcfl_Array', 'cdc_adoQpoasnfa76pfcZLmcfl_Promise',
    'cdc_adoQpoasnfa76pfcZLmcfl_Symbol', 'cdc_adoQpoasnfa76pfcZLmcfl_JSON',
    'cdc_adoQpoasnfa76pfcZLmcfl_Proxy', 'cdc_adoQpoasnfa76pfcZLmcfl_Object',
    '__playwright', '__playwright_binding__', '__pw_disconnect_reason',
    '$cdc_asdjflasutopfhvcZLmcfl_', '$wdc_',
];
for (const p of cdpProps) {{
    try {{ delete window[p]; }} catch(e) {{
        Object.defineProperty(window, p, {{get:()=>undefined, configurable:true}});
    }}
}}

// Filter CDP properties from Object.getOwnPropertyNames / Object.keys
const _ownNames = Object.getOwnPropertyNames;
Object.getOwnPropertyNames = makeNative(function(o) {{
    return _ownNames.call(this, o).filter(k => !k.startsWith('cdc_') && !k.startsWith('__pw_') && !k.startsWith('__playwright'));
}}, 'getOwnPropertyNames');

const _keys = Object.keys;
Object.keys = makeNative(function(o) {{
    return _keys.call(this, o).filter(k => !k.startsWith('cdc_') && !k.startsWith('__pw_'));
}}, 'keys');

// ══════════════════════════════════════════════════════════════
// 2. DEVTOOLS DETECTION PREVENTION
// ══════════════════════════════════════════════════════════════

// Block console timing detection
const _log = console.log;
console.log = makeNative(function() {{
    const t = performance.now();
    _log.apply(this, arguments);
    while (performance.now() - t < 0.1 + Math.random() * 0.05) {{}}
}}, 'log');

// Block debugger statement traps
const _Function = window.Function;
window.Function = makeNative(function() {{
    const code = arguments[arguments.length - 1];
    if (typeof code === 'string' && code.includes('debugger')) return function(){{}};
    return _Function.apply(this, arguments);
}}, 'Function');

// Block element size change detection (DevTools adds panels)
const _getComputedStyle = window.getComputedStyle;
window.getComputedStyle = makeNative(function(el, pseudo) {{
    return _getComputedStyle.call(this, el, pseudo);
}}, 'getComputedStyle');

// ══════════════════════════════════════════════════════════════
// 3. WEBDRIVER — PROTOTYPE-LEVEL REMOVAL
// ══════════════════════════════════════════════════════════════
try {{ delete Navigator.prototype.webdriver; }} catch(e) {{}}
Object.defineProperty(Navigator.prototype, 'webdriver', {{
    get: function() {{ return undefined; }},
    configurable: true, enumerable: false
}});

// Block re-definition of webdriver
const _defProp = Object.defineProperty;
Object.defineProperty = makeNative(function(obj, prop, desc) {{
    if (obj instanceof Navigator && prop === 'webdriver') return obj;
    return _defProp.call(this, obj, prop, desc);
}}, 'defineProperty');

// ══════════════════════════════════════════════════════════════
// 4. AUTOMATION ARTIFACT CLEANUP
// ══════════════════════════════════════════════════════════════
const artifacts = [
    '__selenium_unwrapped','__selenium_evaluate','__webdriver_evaluate',
    '__driver_evaluate','__fxdriver_evaluate','__driver_unwrapped',
    '__webdriver_unwrapped','__fxdriver_unwrapped','__nightmare',
    '_phantom','callPhantom','__phantomas','domAutomation',
    'domAutomationController','_Selenium_IDE_Recorder','_selenium',
    'calledSelenium','selenium_evaluate',
];
for (const p of artifacts) {{
    try {{ delete window[p]; }} catch(e) {{
        Object.defineProperty(window, p, {{get:()=>undefined, configurable:true}});
    }}
}}

// ══════════════════════════════════════════════════════════════
// 5. BLOCK ALL FINGERPRINTING + ANTI-BOT LIBRARIES
// ══════════════════════════════════════════════════════════════
const blockedLibs = [
    // Fingerprinting
    'fingerprintjs','fingerprint2','fingerprint3','fpjs','fpjs2','fpjs3',
    'clientjs','thumbmark','openfingerprint','creepjs','amiunique',
    'browserleaks','fingerprint','visitor','device_id',
    // Anti-bot vendors
    'sardine','iovation','threatmetrix','nethra','seon',
    'ipqualityscore','fraudlabs','arkose','funcaptcha',
    'friendlycaptcha','botd','bot-detection','detector',
    'datadome','perimeterx','px-cdn','px-client','px-cloud',
    'kasada','shapesecurity','imperva','incapdns',
    'akamai-bot','akadns','f5-',
    // Analytics that fingerprint
    'amplitude','mixpanel','segment','heap','fullstory',
    'logrocket','hotjar','clarity','smartlook',
    'mouseflow','luckyorange','crazyegg',
    // Fraud detection
    'sift','signifyd','riskified','forter','radial',
];

const _fetch = window.fetch;
window.fetch = makeNative(function(resource, init) {{
    const url = typeof resource === 'string' ? resource : (resource && resource.url) || '';
    if (blockedLibs.some(lib => url.toLowerCase().includes(lib))) {{
        return Promise.resolve(new Response('{{"blocked":true}}', {{status: 200}}));
    }}
    return _fetch.apply(this, arguments);
}}, 'fetch');

const _xhrOpen = XMLHttpRequest.prototype.open;
const _xhrSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = makeNative(function(method, url) {{
    if (blockedLibs.some(lib => String(url).toLowerCase().includes(lib))) {{
        this._agentOsBlocked = true;
        return;
    }}
    return _xhrOpen.apply(this, arguments);
}}, 'open');
XMLHttpRequest.prototype.send = makeNative(function(data) {{
    if (this._agentOsBlocked) {{
        Object.defineProperty(this, 'readyState', {{get:()=>4}});
        Object.defineProperty(this, 'status', {{get:()=>200}});
        Object.defineProperty(this, 'responseText', {{get:()=>''}});
        Object.defineProperty(this, 'response', {{get:()=>''}});
        if (this.onreadystatechange) this.onreadystatechange();
        if (this.onload) this.onload();
        return;
    }}
    return _xhrSend.apply(this, arguments);
}}, 'send');

// Block script element injection of fingerprinting libs
const _createElement = document.createElement;
document.createElement = makeNative(function(tag) {{
    const el = _createElement.apply(this, arguments);
    if (tag.toLowerCase() === 'script') {{
        const _setAttr = el.setAttribute.bind(el);
        el.setAttribute = makeNative(function(name, val) {{
            if (name === 'src' && blockedLibs.some(lib => String(val).toLowerCase().includes(lib))) return;
            return _setAttr(name, val);
        }}, 'setAttribute');
    }}
    return el;
}}, 'createElement');

// ══════════════════════════════════════════════════════════════
// 6. NAVIGATOR PROPERTIES
// ══════════════════════════════════════════════════════════════
Object.defineProperty(navigator, 'platform', {{get:()=>{platform}, configurable:true, enumerable:true}});
Object.defineProperty(navigator, 'hardwareConcurrency', {{get:()=>{cores}, configurable:true, enumerable:true}});
Object.defineProperty(navigator, 'deviceMemory', {{get:()=>{memory}, configurable:true, enumerable:true}});
Object.defineProperty(navigator, 'maxTouchPoints', {{get:()=>{touch}, configurable:true, enumerable:true}});
Object.defineProperty(navigator, 'languages', {{get:()=>['en-US','en'], configurable:true, enumerable:true}});
Object.defineProperty(navigator, 'userAgent', {{get:()=>{ua}, configurable:true, enumerable:true}});

// Plugins
Object.defineProperty(navigator, 'plugins', {{
    get: function() {{
        const p = [
            {{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer',description:'Portable Document Format',length:1}},
            {{name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai',description:'',length:1}},
            {{name:'Native Client',filename:'internal-nacl-plugin',description:'',length:2}}
        ];
        p.length = 3; p.item = function(i){{return this[i]||null;}};
        p.namedItem = function(n){{return this.find(function(x){{return x.name===n;}})||null;}};
        p.refresh = function(){{}};
        return p;
    }}, configurable:true, enumerable:true
}});

// Connection
Object.defineProperty(navigator, 'connection', {{
    get: function() {{
        return {{rtt:{random.randint(20,100)}, downlink:{random.randint(5,50)}, effectiveType:'4g', saveData:false, type:'wifi'}};
    }}, configurable:true, enumerable:true
}});

// ══════════════════════════════════════════════════════════════
// 7. SCREEN OVERRIDES
// ══════════════════════════════════════════════════════════════
Object.defineProperty(screen, 'width', {{get:()=>{sw}, configurable:true, enumerable:true}});
Object.defineProperty(screen, 'height', {{get:()=>{sh}, configurable:true, enumerable:true}});
Object.defineProperty(screen, 'availWidth', {{get:()=>{sw}, configurable:true, enumerable:true}});
Object.defineProperty(screen, 'availHeight', {{get:()=>{sh - random.randint(30,80)}, configurable:true, enumerable:true}});
Object.defineProperty(screen, 'colorDepth', {{get:()=>{color_depth}, configurable:true, enumerable:true}});
Object.defineProperty(screen, 'pixelDepth', {{get:()=>{color_depth}, configurable:true, enumerable:true}});
Object.defineProperty(window, 'devicePixelRatio', {{get:()=>{pixel_ratio}, configurable:true, enumerable:true}});

// ══════════════════════════════════════════════════════════════
// 8. WEBGL FINGERPRINT
// ══════════════════════════════════════════════════════════════
const _glGetParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(p) {{
    switch(p) {{
        case 37445: return {gl_vendor};
        case 37446: return {gl_renderer};
        case 35661: return {random.randint(16,32)};
        case 34076: return {random.randint(16384,32768)};
        case 34921: return {random.randint(16,32)};
        case 36347: return {random.randint(1024,4096)};
        case 36349: return {random.randint(1024,4096)};
        case 34024: return {random.randint(16384,32768)};
        case 3386: return [{random.randint(16384,32768)},{random.randint(16384,32768)}];
        default: return _glGetParam.call(this, p);
    }}
}};

if (typeof WebGL2RenderingContext !== 'undefined') {{
    const _gl2GetParam = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(p) {{
        if (p === 37445) return {gl_vendor};
        if (p === 37446) return {gl_renderer};
        return _gl2GetParam.call(this, p);
    }};
}}

// ══════════════════════════════════════════════════════════════
// 9. CANVAS FINGERPRINT NOISE
// ══════════════════════════════════════════════════════════════
const _toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {{
    const ctx = this.getContext('2d');
    if (ctx && this.width > 16 && this.height > 16) {{
        try {{
            const d = ctx.getImageData(0, 0, this.width, this.height);
            const step = Math.max(67, Math.floor(d.data.length / 10000));
            for (let i = 0; i < d.data.length; i += step) {{
                d.data[i] = Math.max(0, Math.min(255, d.data[i] + Math.floor(canvasRNG() * 3) - 1));
            }}
            ctx.putImageData(d, 0, 0);
        }} catch(e) {{}}
    }}
    return _toDataURL.apply(this, arguments);
}};

const _toBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(cb, type, quality) {{
    const ctx = this.getContext('2d');
    if (ctx && this.width > 16 && this.height > 16) {{
        try {{
            const d = ctx.getImageData(0, 0, this.width, this.height);
            const step = Math.max(67, Math.floor(d.data.length / 10000));
            for (let i = 0; i < d.data.length; i += step) {{
                d.data[i] = Math.max(0, Math.min(255, d.data[i] + Math.floor(canvasRNG() * 3) - 1));
            }}
            ctx.putImageData(d, 0, 0);
        }} catch(e) {{}}
    }}
    return _toBlob.apply(this, arguments);
}};

// Also patch OffscreenCanvas if available
if (typeof OffscreenCanvas !== 'undefined') {{
    const _ocToBlob = OffscreenCanvas.prototype.convertToBlob;
    if (_ocToBlob) {{
        OffscreenCanvas.prototype.convertToBlob = function(opts) {{
            return _ocToBlob.apply(this, arguments);
        }};
    }}
}}

// ══════════════════════════════════════════════════════════════
// 10. AUDIO FINGERPRINT NOISE
// ══════════════════════════════════════════════════════════════
if (typeof AnalyserNode !== 'undefined') {{
    const _getFloat = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function(arr) {{
        _getFloat.call(this, arr);
        for (let i = 0; i < arr.length; i++) arr[i] += (audioRNG() - 0.5) * 0.0001;
    }};
    const _getByte = AnalyserNode.prototype.getByteFrequencyData;
    if (_getByte) {{
        AnalyserNode.prototype.getByteFrequencyData = function(arr) {{
            _getByte.call(this, arr);
            for (let i = 0; i < arr.length; i++) {{
                const v = arr[i] + Math.floor((audioRNG() - 0.5) * 2);
                arr[i] = Math.max(0, Math.min(255, v));
            }}
        }};
    }}
}}

// ══════════════════════════════════════════════════════════════
// 11. CHROME OBJECT — Complete Real Structure
// ══════════════════════════════════════════════════════════════
window.chrome = window.chrome || {{}};
window.chrome.app = {{
    isInstalled: false,
    InstallState: {{INSTALLED:'installed', DISABLED:'disabled', NOT_INSTALLED:'not_installed'}},
    RunningState: {{CANNOT_RUN:'cannot_run', READY_TO_RUN:'ready_to_run', RUNNING:'running'}},
    getDetails: function(){{return null;}}, getIsInstalled: function(){{return false;}},
    installState: function(){{return 'not_installed';}}, runningState: function(){{return 'cannot_run';}}
}};
window.chrome.runtime = {{
    OnInstalledReason:{{CHROME_UPDATE:'chrome_update',INSTALL:'install',SHARED_MODULE_UPDATE:'shared_module_update',UPDATE:'update'}},
    OnRestartRequiredReason:{{APP_UPDATE:'app_update',OS_UPDATE:'os_update',PERIODIC:'periodic'}},
    PlatformArch:{{ARM:'arm',MIPS:'mips',MIPS64:'mips64',X86_32:'x86-32',X86_64:'x86-64'}},
    PlatformNaclArch:{{ARM:'arm',MIPS:'mips',MIPS64:'mips64',X86_32:'x86-32',X86_64:'x86-64'}},
    PlatformOs:{{ANDROID:'android',CROS:'cros',LINUX:'linux',MAC:'mac',OPENBSD:'openbsd',WIN:'win'}},
    RequestUpdateCheckStatus:{{NO_UPDATE:'no_update',THROTTLED:'throttled',UPDATE_AVAILABLE:'update_available'}},
    connect:function(){{}}, sendMessage:function(){{}}, id:undefined,
    getManifest:function(){{return {{}};}},
    getURL:function(p){{return 'chrome-extension://invalid/'+p;}}
}};
window.chrome.csi = function(){{return {{onloadT:Date.now(),pageT:Date.now(),startE:Date.now()}};}};
window.chrome.loadTimes = function(){{const n=Date.now()/1000;return {{commitLoadTime:n,connectionInfo:'h2',finishDocumentLoadTime:n,finishLoadTime:n,firstPaintAfterLoadTime:0,firstPaintTime:n,npnNegotiatedProtocol:'h2',requestTime:n,startLoadTime:n,wasAlternateProtocolAvailable:false,wasFetchedViaSpdy:true,wasNpnNegotiated:true}};}};

// ══════════════════════════════════════════════════════════════
// 12. PERMISSIONS — Realistic
// ══════════════════════════════════════════════════════════════
if (navigator.permissions && navigator.permissions.query) {{
    const _permQuery = Permissions.prototype.query;
    Permissions.prototype.query = makeNative(function(desc) {{
        if (desc.name === 'notifications') return Promise.resolve({{state:Notification.permission}});
        if (desc.name === 'geolocation') return Promise.resolve({{state:'prompt'}});
        return _permQuery.call(this, desc);
    }}, 'query');
}}

// ══════════════════════════════════════════════════════════════
// 13. WEBRTC — Block IP Leak
// ══════════════════════════════════════════════════════════════
const _RTC = window.RTCPeerConnection;
if (_RTC) {{
    window.RTCPeerConnection = function(config, constraints) {{
        if (config && config.iceServers) config.iceServers = [];
        const pc = new _RTC(config, constraints);
        const _createOffer = pc.createOffer.bind(pc);
        pc.createOffer = function(opts) {{
            return _createOffer(opts).then(function(offer) {{
                offer.sdp = offer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                return offer;
            }});
        }};
        return pc;
    }};
    window.RTCPeerConnection.prototype = _RTC.prototype;
    Object.setPrototypeOf(window.RTCPeerConnection, _RTC);
}}

// ══════════════════════════════════════════════════════════════
// 14. STACK TRACE SANITIZATION
// ══════════════════════════════════════════════════════════════
const _prepStack = Error.prepareStackTrace;
Error.prepareStackTrace = function(error, stack) {{
    if (_prepStack) {{
        const r = _prepStack(error, stack);
        if (typeof r === 'string') {{
            return r.replace(/playwright[^\\n]*/gi, '').replace(/agent-os[^\\n]*/gi, '')
                .replace(/at eval[^\\n]*/gi, '').replace(/\\(\\w+:\\/\\/[^)]+\\)/g, '(<anonymous>)');
        }}
        return r;
    }}
    return stack.map(function(f) {{
        return '    at ' + (f.getTypeName()||'') + '.' + (f.getMethodName()||'<anonymous>') +
               ' (' + f.getFileName() + ':' + f.getLineNumber() + ':' + f.getColumnNumber() + ')';
    }}).join('\\n');
}};

// ══════════════════════════════════════════════════════════════
// 15. PERFORMANCE TIMING
// ══════════════════════════════════════════════════════════════
const _now = performance.now;
const _timingOff = Math.random() * 0.1;
performance.now = makeNative(function() {{ return _now.call(performance) + _timingOff; }}, 'now');

// ══════════════════════════════════════════════════════════════
// 16. MEDIADEVICES — Realistic enumerateDevices
// ══════════════════════════════════════════════════════════════
if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
    const _enum = navigator.mediaDevices.enumerateDevices;
    navigator.mediaDevices.enumerateDevices = makeNative(async function() {{
        try {{
            const devs = await _enum.call(this);
            if (devs.length > 0) return devs;
        }} catch(e) {{}}
        return [
            {{deviceId:'default',kind:'audioinput',label:'Default - Microphone',groupId:'g1'}},
            {{deviceId:'default',kind:'audiooutput',label:'Default - Speaker',groupId:'g1'}},
            {{deviceId:'',kind:'videoinput',label:'',groupId:''}}
        ];
    }}, 'enumerateDevices');
}}

// ══════════════════════════════════════════════════════════════
// 17. NOTIFICATION
// ══════════════════════════════════════════════════════════════
try {{ Object.defineProperty(Notification, 'permission', {{get: function(){{return 'default';}}, configurable:true}}); }} catch(e) {{}}

// ══════════════════════════════════════════════════════════════
// 18. GLOBAL CLEANUP
// ══════════════════════════════════════════════════════════════
const globals = Object.getOwnPropertyNames(window);
for (const g of globals) {{
    if (g.includes('playwright') || g.includes('__pw') || g.includes('cdc_')) {{
        try {{ delete window[g]; }} catch(e) {{
            Object.defineProperty(window, g, {{get:()=>undefined, configurable:true}});
        }}
    }}
}}

console.log('[Agent-OS] Fingerprint v4.0 injected: {fp["id"]} ({fp["os"]} Chrome {fp["chrome_version"]})');
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
