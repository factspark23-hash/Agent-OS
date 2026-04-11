"""
Agent-OS Shared Stealth Constants
Single source of truth for anti-detection JS, bot-blocking patterns, and fake responses.
Used by both browser.py and persistent_browser.py.
"""

# ─── Anti-Detection JavaScript ──────────────────────────────
# Injected into every page via context.add_init_script()

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
    if (param === 35661) return 16;
    if (param === 34076) return 16384;
    if (param === 34921) return 16;
    if (param === 36347) return 1024;
    if (param === 36349) return 1024;
    if (param === 34024) return 16384;
    if (param === 3386) return [16384, 16384];
    return getParameter.call(this, param);
};

// 10. Canvas fingerprint noise
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    const context = this.getContext('2d');
    if (context && this.width > 0 && this.height > 0) {
        const imageData = context.getImageData(0, 0, this.width, this.height);
        for (let i = 0; i < imageData.data.length; i += 100) {
            imageData.data[i] = imageData.data[i] ^ 1;
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

# ─── Bot Detection URL Patterns ─────────────────────────────
# Checked against every outgoing request. Matching requests are blocked
# and a fake "human verified" response is returned instead.

BOT_DETECTION_URLS = [
    "recaptcha", "captcha", "hcaptcha", "turnstile",
    "perimeterx", "datadome", "cloudflare-challenge",
    "challenges.cloudflare.com",
    "cloudflare.com/cdn-cgi/challenge",
    "cloudflareinsights.com",
    "static.cloudflareinsights.com",
    "managed-challenge",
    "no-connection",
    "check-bot", "verify-human", "bot-detection",
    "akamai-bot", "imperva", "f5-bot",
    "distil", "shape-security", "kasada",
    "botmanager", "radar", "fingerprint",
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
        "captcha.geo.datadome",
        "datadome.co",
        "incapdns.net",
        "shapesecurity.com",
        "kasada.io",
    ]

    for domain in BLOCK_DOMAINS:
        if domain in url_lower:
            # Determine which type and return appropriate fake response
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
        ]
        for pattern in SCRIPT_BLOCK_DOMAINS:
            if pattern in url_lower:
                return True, None  # Return empty body

    return False, None
