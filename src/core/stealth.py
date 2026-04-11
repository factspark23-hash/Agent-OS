"""
Agent-OS Shared Stealth Constants
Single source of truth for anti-detection JS, bot-blocking patterns, and fake responses.
Used by both browser.py and persistent_browser.py.
"""

# ─── Anti-Detection JavaScript ──────────────────────────────
# Injected into every page via context.add_init_script()

ANTI_DETECTION_JS = """
// === AGENT-OS STEALTH MODE v4.0 ===
// Multi-layer anti-detection: CDP + JS + behavior + iframe propagation

(function() {
'use strict';

// ═══════════════════════════════════════════════════════════════
// LAYER 0: toString() CLOAKING — must run FIRST
// ═══════════════════════════════════════════════════════════════
// Cloudflare, PerimeterX, and others call .toString() on overridden
// functions and check if the result contains "[native code]".
// Without this, ALL our patches are detectable.

const nativeToString = Function.prototype.toString;
const nativeToStringStr = nativeToString.call(nativeToString);

// Map of overridden functions → their spoofed toString() name
const _overriddenFns = new Map();

function spoofToString(fn, originalName) {
    _overriddenFns.set(fn, originalName);
}

// Override toString itself to handle our cloaked functions
Function.prototype.toString = function toString() {
    // If someone calls toString on toString, return the real deal
    if (this === Function.prototype.toString) {
        return nativeToStringStr;
    }
    // If this is one of our overridden functions, return native-looking string
    if (_overriddenFns.has(this)) {
        const name = _overriddenFns.get(this);
        return 'function ' + name + '() { [native code] }';
    }
    // For normal functions, use the real toString
    return nativeToString.call(this);
};

// Mark our toString override as native-looking too
spoofToString(Function.prototype.toString, 'toString');

// ═══════════════════════════════════════════════════════════════
// LAYER 1: navigator.webdriver removal
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
    enumerable: false
});
delete navigator.__proto__.webdriver;

// ═══════════════════════════════════════════════════════════════
// LAYER 2: Realistic plugins (Chrome's actual plugin list)
// ═══════════════════════════════════════════════════════════════

const _plugins = [
    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
    {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
];

const pluginArray = {
    length: 3,
    item: function(i) { return _plugins[i] || null; },
    namedItem: function(n) { return _plugins.find(function(p) { return p.name === n; }) || null; },
    refresh: function() {}
};
for (let i = 0; i < _plugins.length; i++) {
    pluginArray[i] = _plugins[i];
}

Object.defineProperty(navigator, 'plugins', {
    get: function() { return pluginArray; },
    configurable: true
});

// ═══════════════════════════════════════════════════════════════
// LAYER 3: Languages
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(navigator, 'languages', {get: function() { return ['en-US', 'en']; }, configurable: true});
Object.defineProperty(navigator, 'language', {get: function() { return 'en-US'; }, configurable: true});

// ═══════════════════════════════════════════════════════════════
// LAYER 4: Platform
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(navigator, 'platform', {get: function() { return 'Win32'; }, configurable: true});

// ═══════════════════════════════════════════════════════════════
// LAYER 5: Hardware info
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(navigator, 'hardwareConcurrency', {get: function() { return 8; }, configurable: true});
Object.defineProperty(navigator, 'deviceMemory', {get: function() { return 8; }, configurable: true});
Object.defineProperty(navigator, 'maxTouchPoints', {get: function() { return 0; }, configurable: true});

// ═══════════════════════════════════════════════════════════════
// LAYER 6: Connection
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(navigator, 'connection', {
    get: function() { return {rtt: 50, downlink: 10, effectiveType: '4g', saveData: false, type: 'wifi'}; },
    configurable: true
});

// ═══════════════════════════════════════════════════════════════
// LAYER 7: Permissions override
// ═══════════════════════════════════════════════════════════════

const _origPermissionsQuery = window.navigator.permissions.query;
window.navigator.permissions.query = function(parameters) {
    if (parameters.name === 'notifications') {
        return Promise.resolve({state: Notification.permission});
    }
    return _origPermissionsQuery.call(this, parameters);
};
spoofToString(window.navigator.permissions.query, 'query');

// ═══════════════════════════════════════════════════════════════
// LAYER 8: Chrome runtime (must exist for real Chrome)
// ═══════════════════════════════════════════════════════════════

window.chrome = {
    app: {
        isInstalled: false,
        InstallState: {INSTALLED: 'installed', DISABLED: 'disabled', NOT_INSTALLED: 'not_installed'},
        RunningState: {CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running'}
    },
    runtime: {
        OnInstalledReason: {CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update'},
        OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
        PlatformArch: {ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
        PlatformNaclArch: {ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
        PlatformOs: {ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win'},
        RequestUpdateCheckStatus: {NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available'},
        connect: function() {},
        sendMessage: function() {}
    },
    csi: function() { return {onloadT: Date.now(), pageT: Date.now(), startE: Date.now()}; },
    loadTimes: function() {
        var now = Date.now() / 1000;
        return {
            commitLoadTime: now,
            connectionInfo: 'h2',
            finishDocumentLoadTime: now,
            finishLoadTime: now,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: now,
            npnNegotiatedProtocol: 'h2',
            requestTime: now,
            startLoadTime: now,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true
        };
    }
};

// ═══════════════════════════════════════════════════════════════
// LAYER 9: WebGL fingerprint (real Intel GPU)
// ═══════════════════════════════════════════════════════════════

const _origGetParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    // UNMASKED_VENDOR_WEBGL
    if (param === 37445) return 'Intel Inc.';
    // UNMASKED_RENDERER_WEBGL
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    // MAX_TEXTURE_IMAGE_UNITS
    if (param === 35661) return 16;
    // MAX_TEXTURE_SIZE
    if (param === 3379) return 16384;
    // MAX_CUBE_MAP_TEXTURE_SIZE
    if (param === 34076) return 16384;
    // MAX_RENDERBUFFER_SIZE
    if (param === 34024) return 16384;
    // MAX_VIEWPORT_DIMS
    if (param === 3386) return [16384, 16384];
    // MAX_VERTEX_ATTRIBS
    if (param === 34921) return 16;
    // MAX_VERTEX_UNIFORM_VECTORS
    if (param === 36347) return 1024;
    // MAX_FRAGMENT_UNIFORM_VECTORS
    if (param === 36349) return 1024;
    return _origGetParameter.call(this, param);
};
spoofToString(WebGLRenderingContext.prototype.getParameter, 'getParameter');

// Also patch WebGL2 if present
if (typeof WebGL2RenderingContext !== 'undefined') {
    const _origGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Intel Inc.';
        if (param === 37446) return 'Intel Iris OpenGL Engine';
        if (param === 35661) return 16;
        if (param === 3379) return 16384;
        if (param === 34076) return 16384;
        if (param === 34024) return 16384;
        if (param === 3386) return [16384, 16384];
        if (param === 34921) return 16;
        if (param === 36347) return 1024;
        if (param === 36349) return 1024;
        return _origGetParameter2.call(this, param);
    };
    spoofToString(WebGL2RenderingContext.prototype.getParameter, 'getParameter');
}

// ═══════════════════════════════════════════════════════════════
// LAYER 10: Canvas fingerprint noise
// ═══════════════════════════════════════════════════════════════

const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    var context = this.getContext('2d');
    if (context && this.width > 0 && this.height > 0) {
        var imageData = context.getImageData(0, 0, this.width, this.height);
        for (var i = 0; i < imageData.data.length; i += 100) {
            imageData.data[i] = imageData.data[i] ^ 1;
        }
        context.putImageData(imageData, 0, 0);
    }
    return _origToDataURL.apply(this, arguments);
};
spoofToString(HTMLCanvasElement.prototype.toDataURL, 'toDataURL');

// Also spoof toBlob
const _origToBlob = HTMLCanvasElement.prototype.toBlob;
HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
    var context = this.getContext('2d');
    if (context && this.width > 0 && this.height > 0) {
        var imageData = context.getImageData(0, 0, this.width, this.height);
        for (var i = 0; i < imageData.data.length; i += 100) {
            imageData.data[i] = imageData.data[i] ^ 1;
        }
        context.putImageData(imageData, 0, 0);
    }
    return _origToBlob.call(this, callback, type, quality);
};
spoofToString(HTMLCanvasElement.prototype.toBlob, 'toBlob');

// ═══════════════════════════════════════════════════════════════
// LAYER 11: Audio context fingerprint
// ═══════════════════════════════════════════════════════════════

var _AudioContext = window.AudioContext || window.webkitAudioContext;
if (_AudioContext) {
    var _origCreateOscillator = _AudioContext.prototype.createOscillator;
    _AudioContext.prototype.createOscillator = function() {
        var osc = _origCreateOscillator.call(this);
        var _origConnect = osc.connect;
        osc.connect = function(dest) {
            return _origConnect.call(this, dest);
        };
        return osc;
    };
    spoofToString(_AudioContext.prototype.createOscillator, 'createOscillator');

    // Also patch AnalyserNode to prevent frequency analysis fingerprinting
    if (_AudioContext.prototype.createAnalyser) {
        var _origCreateAnalyser = _AudioContext.prototype.createAnalyser;
        _AudioContext.prototype.createAnalyser = function() {
            var analyser = _origCreateAnalyser.call(this);
            var _origGetFloatFrequencyData = analyser.getFloatFrequencyData;
            analyser.getFloatFrequencyData = function(array) {
                _origGetFloatFrequencyData.call(this, array);
                for (var i = 0; i < array.length; i++) {
                    array[i] += Math.random() * 0.0001;
                }
            };
            return analyser;
        };
        spoofToString(_AudioContext.prototype.createAnalyser, 'createAnalyser');
    }
}

// ═══════════════════════════════════════════════════════════════
// LAYER 12: Block WebRTC IP leak
// ═══════════════════════════════════════════════════════════════

var _origRTCPeerConnection = window.RTCPeerConnection;
if (_origRTCPeerConnection) {
    window.RTCPeerConnection = function() {
        var pc = new _origRTCPeerConnection(arguments[0]);
        var _origCreateOffer = pc.createOffer;
        pc.createOffer = function(options) {
            return _origCreateOffer.call(pc, options).then(function(offer) {
                offer.sdp = offer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                return offer;
            });
        };
        return pc;
    };
    window.RTCPeerConnection.prototype = _origRTCPeerConnection.prototype;
}

// ═══════════════════════════════════════════════════════════════
// LAYER 13: Notification permission
// ═══════════════════════════════════════════════════════════════

Object.defineProperty(Notification, 'permission', {get: function() { return 'default'; }, configurable: true});

// ═══════════════════════════════════════════════════════════════
// LAYER 14: Media devices (fake realistic list)
// ═══════════════════════════════════════════════════════════════

if (navigator.mediaDevices) {
    var _origEnumerateDevices = navigator.mediaDevices.enumerateDevices;
    navigator.mediaDevices.enumerateDevices = function() {
        return Promise.resolve([
            {deviceId: 'default', kind: 'audioinput', label: 'Default - Microphone', groupId: 'group1'},
            {deviceId: 'communications', kind: 'audioinput', label: 'Communications - Microphone', groupId: 'group1'},
            {deviceId: 'default', kind: 'audiooutput', label: 'Default - Speaker', groupId: 'group1'},
            {deviceId: 'communications', kind: 'audiooutput', label: 'Communications - Speaker', groupId: 'group1'},
            {deviceId: '', kind: 'videoinput', label: '', groupId: ''}
        ]);
    };
    spoofToString(navigator.mediaDevices.enumerateDevices, 'enumerateDevices');
}

// ═══════════════════════════════════════════════════════════════
// LAYER 15: Screen fingerprint consistency
// ═══════════════════════════════════════════════════════════════
// These values are injected as placeholders and replaced at runtime
// from Python using the active BrowserProfile values.

var SCREEN_W = __AGENT_OS_SCREEN_WIDTH__;
var SCREEN_H = __AGENT_OS_SCREEN_HEIGHT__;
var DEVICE_PIXEL_RATIO = __AGENT_OS_DEVICE_PIXEL_RATIO__;

Object.defineProperty(screen, 'width', {get: function() { return SCREEN_W; }, configurable: true});
Object.defineProperty(screen, 'height', {get: function() { return SCREEN_H; }, configurable: true});
Object.defineProperty(screen, 'availWidth', {get: function() { return SCREEN_W; }, configurable: true});
Object.defineProperty(screen, 'availHeight', {get: function() { return SCREEN_H - 40; }, configurable: true});
Object.defineProperty(screen, 'colorDepth', {get: function() { return 24; }, configurable: true});
Object.defineProperty(screen, 'pixelDepth', {get: function() { return 24; }, configurable: true});

Object.defineProperty(window, 'outerWidth', {get: function() { return SCREEN_W; }, configurable: true});
Object.defineProperty(window, 'outerHeight', {get: function() { return SCREEN_H + 74; }, configurable: true});
Object.defineProperty(window, 'screenX', {get: function() { return 0; }, configurable: true});
Object.defineProperty(window, 'screenY', {get: function() { return 0; }, configurable: true});
Object.defineProperty(window, 'devicePixelRatio', {get: function() { return DEVICE_PIXEL_RATIO; }, configurable: true});

// ═══════════════════════════════════════════════════════════════
// LAYER 16: Battery API
// ═══════════════════════════════════════════════════════════════
// Some fingerprinting libraries read battery status.
// Return a plausible "plugged in, mostly charged" state.

if (navigator.getBattery) {
    var _fakeBattery = {
        charging: true,
        chargingTime: 0,
        dischargingTime: Infinity,
        level: 0.87,
        addEventListener: function() {},
        removeEventListener: function() {},
        onchargingchange: null,
        onchargingtimechange: null,
        ondischargingtimechange: null,
        onlevelchange: null
    };
    Object.defineProperty(navigator, 'getBattery', {
        get: function() {
            return function() { return Promise.resolve(_fakeBattery); };
        },
        configurable: true
    });
}

// ═══════════════════════════════════════════════════════════════
// LAYER 17: Font enumeration block
// ═══════════════════════════════════════════════════════════════
// Fingerprinting libraries probe installed fonts via document.fonts.
// We neuter the enumeration API while keeping real rendering intact.

if (document.fonts) {
    // check() always reports any font as available
    var _origFontsCheck = document.fonts.check;
    document.fonts.check = function(font, text) {
        return true;
    };
    spoofToString(document.fonts.check, 'check');

    // load() resolves immediately without actually loading
    var _origFontsLoad = document.fonts.load;
    document.fonts.load = function(font, text) {
        return Promise.resolve([]);
    };
    spoofToString(document.fonts.load, 'load');

    // Replace the iterator to return empty (no font enumeration)
    if (document.fonts[Symbol.iterator]) {
        var _origFontsIterator = document.fonts[Symbol.iterator];
        document.fonts[Symbol.iterator] = function() {
            return {next: function() { return {done: true}; }};
        };
    }
}

// ═══════════════════════════════════════════════════════════════
// LAYER 18: Timing consistency
// ═══════════════════════════════════════════════════════════════
// performance.timeOrigin reveals when the browser started.
// Real browsers have this set to a value well before page load.
// We set it to a realistic offset from Date.now().

var NAV_START = Date.now() - Math.floor(Math.random() * 300 + 500);

// Override performance.timeOrigin
try {
    Object.defineProperty(performance, 'timeOrigin', {
        get: function() { return NAV_START; },
        configurable: true
    });
} catch(e) {}

// Override performance.now() to stay consistent with our timeOrigin
var _origPerfNow = performance.now.bind(performance);
performance.now = function() {
    return Date.now() - NAV_START;
};
spoofToString(performance.now, 'now');

// ═══════════════════════════════════════════════════════════════
// LAYER 19: Error stack cleaning
// ═══════════════════════════════════════════════════════════════
// Detection scripts parse Error stack traces looking for Playwright,
// Node.js, or automation framework references. We sanitize these.

var _origError = Error;
var _origPrepareStackTrace = Error.prepareStackTrace;

// Patterns that indicate automation in stack traces
var STACK_SANITIZE_PATTERNS = [
    /playwright/gi,
    /puppeteer/gi,
    /selenium/gi,
    /chromedriver/gi,
    /geckodriver/gi,
    /node_modules/gi,
    /__puppeteer/gi,
    /__cdp/gi,
    /at\s+.*?__evaluate/gi,
    /InjectedScript/gi,
    /Runtime\.evaluate/gi,
    /Page\.addScriptToEvaluateOnNewDocument/gi
];

// Override prepareStackTrace to clean automation references
Error.prepareStackTrace = function(error, frames) {
    if (_origPrepareStackTrace) {
        var stack = _origPrepareStackTrace(error, frames);
        if (typeof stack === 'string') {
            for (var p = 0; p < STACK_SANITIZE_PATTERNS.length; p++) {
                stack = stack.replace(STACK_SANITIZE_PATTERNS[p], '');
            }
            // Remove empty lines left by sanitization
            stack = stack.split('\\n').filter(function(line) { return line.trim().length > 0; }).join('\\n');
        }
        return stack;
    }
    return error.stack;
};

// Also override Error.prototype.stack getter for non-V8 engines
try {
    var _origStackGetter = Object.getOwnPropertyDescriptor(Error.prototype, 'stack');
    if (_origStackGetter && _origStackGetter.get) {
        Object.defineProperty(Error.prototype, 'stack', {
            get: function() {
                var stack = _origStackGetter.get.call(this);
                if (typeof stack === 'string') {
                    for (var p = 0; p < STACK_SANITIZE_PATTERNS.length; p++) {
                        stack = stack.replace(STACK_SANITIZE_PATTERNS[p], '');
                    }
                    stack = stack.split('\\n').filter(function(line) { return line.trim().length > 0; }).join('\\n');
                }
                return stack;
            },
            configurable: true
        });
    }
} catch(e) {}

// ═══════════════════════════════════════════════════════════════
// LAYER 20: Iframe stealth propagation
// ═══════════════════════════════════════════════════════════════
// Pages with iframes can detect automation in the parent but not
// the child (or vice versa). We propagate our patches to every
// iframe as it's added to the DOM.

function patchFrame(frame) {
    try {
        var win = frame.contentWindow;
        if (!win || !win.navigator) return;

        // Core patches for iframe
        Object.defineProperty(win.navigator, 'webdriver', {get: function() { return undefined; }, configurable: true});

        // Chrome runtime in iframe
        win.chrome = window.chrome;

        // Plugins in iframe
        Object.defineProperty(win.navigator, 'plugins', {
            get: function() { return pluginArray; },
            configurable: true
        });

        // Languages
        Object.defineProperty(win.navigator, 'languages', {get: function() { return ['en-US', 'en']; }, configurable: true});
        Object.defineProperty(win.navigator, 'platform', {get: function() { return 'Win32'; }, configurable: true});
        Object.defineProperty(win.navigator, 'hardwareConcurrency', {get: function() { return 8; }, configurable: true});
        Object.defineProperty(win.navigator, 'deviceMemory', {get: function() { return 8; }, configurable: true});

    } catch(e) {
        // Cross-origin frames throw SecurityError — silently ignore
    }
}

// Patch existing iframes
document.querySelectorAll('iframe').forEach(patchFrame);

// Watch for dynamically added iframes
var _frameObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
            if (node.nodeType !== 1) return; // Element nodes only
            if (node.tagName === 'IFRAME') patchFrame(node);
            // Check for nested iframes in added subtrees
            if (node.querySelectorAll) {
                node.querySelectorAll('iframe').forEach(patchFrame);
            }
        });
    });
});

// Start observing once DOM is ready
if (document.documentElement) {
    _frameObserver.observe(document.documentElement, {childList: true, subtree: true});
} else {
    document.addEventListener('DOMContentLoaded', function() {
        _frameObserver.observe(document.documentElement, {childList: true, subtree: true});
    });
}

// ═══════════════════════════════════════════════════════════════
// DONE
// ═══════════════════════════════════════════════════════════════

console.log('[Agent-OS] Stealth patches loaded v4.0 (20 layers)');

})();
"""

# ─── Screen Dimension Template Replacer ─────────────────────

def apply_screen_dimensions(stealth_js: str, screen_width: int, screen_height: int, device_pixel_ratio: float = 1.0) -> str:
    """Replace screen dimension placeholders in stealth JS with real profile values.

    Called from browser.py when injecting init scripts so each page gets
    screen dimensions matching its BrowserProfile.
    """
    js = stealth_js.replace("__AGENT_OS_SCREEN_WIDTH__", str(screen_width))
    js = js.replace("__AGENT_OS_SCREEN_HEIGHT__", str(screen_height))
    js = js.replace("__AGENT_OS_DEVICE_PIXEL_RATIO__", str(device_pixel_ratio))
    return js


# ─── Bot Detection URL Patterns ─────────────────────────────
# Checked against every outgoing request. Matching requests are blocked
# and a fake "human verified" response is returned instead.

BOT_DETECTION_URLS = [
    "recaptcha", "captcha", "hcaptcha", "turnstile",
    "perimeterx", "datadome", "cloudflare-challenge",
    "challenges.cloudflare.com",
    "cloudflare.com/cdn-cgi/challenge",
    "cloudflareinsights.com",
    "managed-challenge",
    "no-connection",
    "check-bot", "verify-human", "bot-detection",
    "akamai-bot", "imperva", "f5-bot",
    "distil", "shape-security", "kasada",
    "botmanager", "radar", "fingerprint",
    "arkoselabs", "funcaptcha", "threatmetrix",
    "iovation", "nethra", "sardine", "seon.io",
    "ipqualityscore", "fraudlabs",
]

# Script URL patterns to block entirely (return empty body)
BOT_DETECTION_SCRIPT_PATTERNS = [
    "recaptcha", "captcha", "botdetect", "fingerprint", "kasada", "perimeterx"
]

# ─── Fake Human Verification Responses ──────────────────────

FAKE_RESPONSES = {
    "recaptcha": {"success": True, "score": 0.95, "action": "login", "challenge_ts": "2026-04-08T12:00:00Z"},
    "captcha": {"status": "verified", "human": True, "score": 0.92},
    "perimeterx": {"status": 0, "uuid": "fake-uuid-agent-os", "vid": "fake-vid", "risk_score": 5},
    "datadome": {"status": 200, "headers": {"x-datadome": "pass"}, "cookie": "human-verified"},
    "cloudflare": {"success": True, "cf_clearance": "agent-os-clearance-token"},
    "bot-detection": {"human": True, "verified": True, "timestamp": 1700000000},
    "kasada": {"verified": True, "token": "agent-os-kasada-token"},
    "arkose": {"solved": True, "session_token": "agent-os-arkose-token"},
    "threatmetrix": {"org_id": "agent-os", "result": "pass", "risk_score": 5},
    "iovation": {"result": "pass", "confidence": 0.95},
    "sardine": {"decision": "approve", "risk_score": 10},
    "seon": {"fraud_score": 10, "decision": "approve"},
    "ipqualityscore": {"success": True, "fraud_score": 10, "message": "Low Risk"},
}


def handle_request_interception(url: str, resource_type: str):
    """
    Shared request handler for bot detection blocking.
    Returns (should_block: bool, fake_response: dict|None).

    Only blocks KNOWN detection endpoints, not any URL containing keywords.
    This prevents blocking legitimate pages that happen to contain words like
    "captcha" or "turnstile" in their content/path.
    """
    url_lower = url.lower()

    # Only block if the URL is a KNOWN detection endpoint
    # Check for specific detection domains/paths, not just keyword presence
    BLOCK_DOMAINS = [
        "google.com/recaptcha",
        "gstatic.com/recaptcha",
        "recaptcha.net",
        "hcaptcha.com",
        "challenges.cloudflare.com",
        "cloudflare.com/cdn-cgi/challenge",
        "captcha.px-cloud.net",
        "px-cdn.net",
        "px-client.net",
        "px-captcha.net",
        "captcha.geo.datadome",
        "js.datadome.co",
        "datadome.co",
        "incapdns.net",
        "_Incapsula_Resource",
        "shapesecurity.com",
        "kasada.io",
        "k-i.co",
        "arkoselabs.com",
        "funcaptcha.co",
        "funcaptcha.com",
        "threatmetrix.com",
        "nethra",
        "iovation.com",
        "sardine.com",
        "seon.io",
        "ipqualityscore.com",
        "fingerprintjs.com",
        "fpjs.io",
        "fingerprint.com",
        "botd.fpjs.io",
        "netacea.com",
        "reblaze.com",
    ]

    for domain in BLOCK_DOMAINS:
        if domain in url_lower:
            if "recaptcha" in url_lower or "gstatic.com/recaptcha" in url_lower:
                return True, FAKE_RESPONSES.get("recaptcha", {"human": True})
            elif "hcaptcha" in url_lower:
                return True, FAKE_RESPONSES.get("captcha", {"human": True})
            elif "cloudflare" in url_lower or "turnstile" in url_lower:
                return True, FAKE_RESPONSES.get("cloudflare", {"human": True})
            elif "perimeterx" in url_lower or "px-" in url_lower:
                return True, FAKE_RESPONSES.get("perimeterx", {"human": True})
            elif "datadome" in url_lower:
                return True, FAKE_RESPONSES.get("datadome", {"human": True})
            elif "kasada" in url_lower or "k-i.co" in url_lower:
                return True, FAKE_RESPONSES.get("kasada", {"human": True})
            elif "arkoselabs" in url_lower or "funcaptcha" in url_lower:
                return True, FAKE_RESPONSES.get("arkose", {"human": True})
            elif "threatmetrix" in url_lower or "nethra" in url_lower:
                return True, FAKE_RESPONSES.get("threatmetrix", {"human": True})
            elif "iovation" in url_lower:
                return True, FAKE_RESPONSES.get("iovation", {"human": True})
            elif "sardine" in url_lower:
                return True, FAKE_RESPONSES.get("sardine", {"human": True})
            elif "seon" in url_lower:
                return True, FAKE_RESPONSES.get("seon", {"human": True})
            elif "ipqualityscore" in url_lower:
                return True, FAKE_RESPONSES.get("ipqualityscore", {"human": True})
            elif "fingerprint" in url_lower or "fpjs" in url_lower or "botd" in url_lower:
                return True, {"human": True, "fingerprint": "blocked"}
            elif "netacea" in url_lower or "reblaze" in url_lower:
                return True, {"human": True}
            else:
                return True, {"human": True}

    # Block bot detection scripts by domain (not by keyword)
    if resource_type == "script":
        SCRIPT_BLOCK_DOMAINS = [
            "recaptcha",
            "hcaptcha",
            "botdetect",
            "perimeterx",
            "kasada",
            "datadome",
            "arkoselabs",
            "funcaptcha",
            "threatmetrix",
            "iovation",
            "sardine",
            "seon.io",
            "ipqualityscore",
            "fingerprintjs",
            "fpjs.io",
            "botd",
            "netacea",
            "reblaze",
        ]
        for pattern in SCRIPT_BLOCK_DOMAINS:
            if pattern in url_lower:
                return True, None  # Return empty body

    return False, None
