"""
Agent-OS Stealth Profiles
Predefined browser profiles that mimic real browser fingerprints.
Each profile overrides ANTI_DETECTION_JS values dynamically.

Includes StealthProfileManager for profile lifecycle management,
cookie migration, and custom profile creation.
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("agent-os.stealth-profiles")

CUSTOM_PROFILES_DIR = Path(os.path.expanduser("~/.agent-os/profiles"))

# ─── Predefined Stealth Profiles ─────────────────────────────

STEALTH_PROFILES: Dict[str, Dict[str, Any]] = {
    "windows-chrome": {
        "name": "Windows 10 / Chrome 120",
        "description": "Windows 10, Chrome 120, US locale — most common fingerprint",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "platform": "Win32",
        "device_memory": 8,
        "hardware_concurrency": 8,
        "max_touch_points": 0,
        "timezone": "America/New_York",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Intel Inc.",
        "webgl_renderer": "Intel Iris OpenGL Engine",
        "color_scheme": "light",
        "device_scale_factor": 1,
        "has_touch": False,
        "is_mobile": False,
    },
    "mac-safari": {
        "name": "macOS Sonoma / Safari 17",
        "description": "macOS Sonoma, Safari 17, US locale",
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Safari/605.1.15"
        ),
        "viewport": {"width": 1440, "height": 900},
        "platform": "MacIntel",
        "device_memory": 8,
        "hardware_concurrency": 8,
        "max_touch_points": 0,
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple M1",
        "color_scheme": "light",
        "device_scale_factor": 2,
        "has_touch": False,
        "is_mobile": False,
    },
    "linux-firefox": {
        "name": "Ubuntu Linux / Firefox 120",
        "description": "Ubuntu Linux, Firefox 120, US locale",
        "user_agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) "
            "Gecko/20100101 Firefox/120.0"
        ),
        "viewport": {"width": 1920, "height": 1080},
        "platform": "Linux x86_64",
        "device_memory": 16,
        "hardware_concurrency": 8,
        "max_touch_points": 0,
        "timezone": "America/New_York",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Mesa",
        "webgl_renderer": "Mesa Intel(R) UHD Graphics (CML GT2)",
        "color_scheme": "light",
        "device_scale_factor": 1,
        "has_touch": False,
        "is_mobile": False,
    },
    "mobile-chrome-android": {
        "name": "Android 14 / Chrome Mobile",
        "description": "Android 14, Pixel 8, Chrome Mobile, touch enabled",
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.6099.43 Mobile Safari/537.36"
        ),
        "viewport": {"width": 412, "height": 915},
        "platform": "Linux armv8l",
        "device_memory": 8,
        "hardware_concurrency": 8,
        "max_touch_points": 5,
        "timezone": "America/New_York",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "ARM",
        "webgl_renderer": "Mali-G715",
        "color_scheme": "light",
        "device_scale_factor": 2.625,
        "has_touch": True,
        "is_mobile": True,
    },
    "mobile-safari-ios": {
        "name": "iOS 17 / Safari Mobile",
        "description": "iOS 17, iPhone 15, Safari Mobile, touch enabled",
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.2 Mobile/15E148 Safari/604.1"
        ),
        "viewport": {"width": 390, "height": 844},
        "platform": "iPhone",
        "device_memory": 4,
        "hardware_concurrency": 6,
        "max_touch_points": 5,
        "timezone": "America/New_York",
        "locale": "en-US",
        "languages": ["en-US", "en"],
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU",
        "color_scheme": "light",
        "device_scale_factor": 3,
        "has_touch": True,
        "is_mobile": True,
    },
}


# ─── Legacy helper functions (kept for backward compat) ──────

def get_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    """Get a stealth profile by name (built-in or custom)."""
    if profile_name in STEALTH_PROFILES:
        return STEALTH_PROFILES[profile_name]
    return _load_custom_profile(profile_name)


def list_profiles() -> Dict[str, str]:
    """List all available profiles with descriptions."""
    profiles = {
        name: profile["description"]
        for name, profile in STEALTH_PROFILES.items()
    }
    # Include custom profiles
    for name, profile in _load_all_custom_profiles().items():
        profiles[name] = profile.get("description", "Custom profile")
    return profiles


def generate_stealth_js(profile: Dict[str, Any]) -> str:
    """Generate profile-specific anti-detection JavaScript."""
    return StealthProfileManager.get_anti_detection_js_static(profile)


def apply_profile_to_context_options(profile: Dict[str, Any], context_options: Dict) -> Dict:
    """Apply stealth profile settings to Playwright context options."""
    if "user_agent" in profile:
        context_options["user_agent"] = profile["user_agent"]
    if "viewport" in profile:
        context_options["viewport"] = profile["viewport"]
    if "locale" in profile:
        context_options["locale"] = profile["locale"]
    if "timezone" in profile:
        context_options["timezone_id"] = profile["timezone"]
    if "device_scale_factor" in profile:
        context_options["device_scale_factor"] = float(profile["device_scale_factor"])
    if "has_touch" in profile:
        context_options["has_touch"] = profile["has_touch"]
    if "is_mobile" in profile:
        context_options["is_mobile"] = profile["is_mobile"]
    if "color_scheme" in profile:
        context_options["color_scheme"] = profile["color_scheme"]
    return context_options


# ─── Custom profile persistence ──────────────────────────────

def _load_all_custom_profiles() -> Dict[str, Dict[str, Any]]:
    """Load all custom profiles from disk."""
    if not CUSTOM_PROFILES_DIR.exists():
        return {}
    profiles = {}
    for f in CUSTOM_PROFILES_DIR.glob("*.json"):
        try:
            with open(f, "r") as fh:
                profiles[f.stem] = json.load(fh)
        except Exception as exc:
            logger.warning("Failed to load custom profile %s: %s", f.stem, exc)
    return profiles


def _load_custom_profile(name: str) -> Optional[Dict[str, Any]]:
    """Load a single custom profile from disk."""
    path = CUSTOM_PROFILES_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Failed to load custom profile %s: %s", name, exc)
        return None


def _save_custom_profile(name: str, settings: Dict[str, Any]) -> None:
    """Persist a custom profile to disk."""
    CUSTOM_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = CUSTOM_PROFILES_DIR / f"{name}.json"
    with open(path, "w") as fh:
        json.dump(settings, fh, indent=2)
    logger.info("Custom profile saved: %s", name)


# ─── StealthProfileManager ───────────────────────────────────

class StealthProfileManager:
    """Manages stealth browser profiles with full lifecycle support.

    Handles profile lookup, creation, anti-detection JS generation,
    and applying profiles to browser contexts with cookie migration.
    """

    def __init__(self) -> None:
        self._active_profile_name: Optional[str] = None
        self._active_profile: Optional[Dict[str, Any]] = None

    # ── Query ────────────────────────────────────────────────

    @staticmethod
    def get_profile(name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a profile dict by name.

        Searches built-in profiles first, then custom profiles on disk.

        Args:
            name: Profile identifier (e.g. ``"windows-chrome"``).

        Returns:
            Profile dict or ``None`` if not found.
        """
        return get_profile(name)

    @staticmethod
    def list_profiles() -> List[str]:
        """Return a sorted list of all available profile names.

        Returns:
            List of profile name strings.
        """
        all_profiles = list(STEALTH_PROFILES.keys())
        all_profiles.extend(_load_all_custom_profiles().keys())
        return sorted(set(all_profiles))

    # ── Anti-detection JS ────────────────────────────────────

    @staticmethod
    def get_anti_detection_js(profile: Dict[str, Any]) -> str:
        """Generate profile-specific stealth JavaScript.

        Produces JS that overrides navigator, WebGL, and connection
        properties to match the given profile fingerprint.

        Args:
            profile: A profile dict (built-in or custom).

        Returns:
            JavaScript source string.
        """
        return StealthProfileManager.get_anti_detection_js_static(profile)

    @staticmethod
    def get_anti_detection_js_static(profile: Dict[str, Any]) -> str:
        """Static implementation of anti-detection JS generation."""
        platform = profile.get("platform", "Win32")
        device_memory = profile.get("device_memory", 8)
        hw_concurrency = profile.get("hardware_concurrency", 8)
        webgl_vendor = profile.get("webgl_vendor", "Intel Inc.")
        webgl_renderer = profile.get("webgl_renderer", "Intel Iris OpenGL Engine")
        max_touch = profile.get("max_touch_points", 0)
        locale = profile.get("locale", "en-US")
        languages = profile.get("languages", [locale, locale.split("-")[0]])
        has_touch = str(profile.get("has_touch", False)).lower()
        is_mobile = str(profile.get("is_mobile", False)).lower()
        profile_name = profile.get("name", "Custom")
        viewport = profile.get("viewport", {})
        vp_width = viewport.get("width", 1920) if isinstance(viewport, dict) else 1920
        vp_height = viewport.get("height", 1080) if isinstance(viewport, dict) else 1080

        lang_js = json.dumps(languages)

        # Build JS with careful brace escaping: {{ and }} produce literal { }
        lines = [
            f"// === AGENT-OS STEALTH PROFILE: {profile_name} ===",
            "(function() {",
            "    'use strict';",
            "",
            "    // Platform",
            f"    Object.defineProperty(navigator, 'platform', {{get: () => '{platform}'}});",
            "",
            "    // Hardware",
            f"    Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {hw_concurrency}}});",
            f"    Object.defineProperty(navigator, 'deviceMemory', {{get: () => {device_memory}}});",
            f"    Object.defineProperty(navigator, 'maxTouchPoints', {{get: () => {max_touch}}});",
            "",
            "    // Language",
            f"    Object.defineProperty(navigator, 'language', {{get: () => '{locale}'}});",
            f"    Object.defineProperty(navigator, 'languages', {{get: () => {lang_js}}});",
            "",
            "    // Touch",
            f"    Object.defineProperty(navigator, 'msMaxTouchPoints', {{get: () => {max_touch}}});",
            "",
            "    // User-Agent data (for UA Client Hints API)",
            "    if (navigator.userAgentData) {",
            "        Object.defineProperty(navigator, 'userAgentData', {",
            "            get: () => ({",
            "                brands: [",
            "                    {brand: 'Chromium', version: '120'},",
            "                    {brand: 'Not_A Brand', version: '24'},",
            "                    {brand: 'Google Chrome', version: '120'}",
            "                ],",
            f"                mobile: {is_mobile},",
            f"                platform: '{platform}',",
            "                getHighEntropyValues: function(hints) {",
            "                    return Promise.resolve({",
            "                        brands: [",
            "                            {brand: 'Chromium', version: '120'},",
            "                            {brand: 'Google Chrome', version: '120'}",
            "                        ],",
            f"                        mobile: {is_mobile},",
            f"                        platform: '{platform}',",
            "                        platformVersion: '10.0.0',",
            "                        uaFullVersion: '120.0.6099.130'",
            "                    });",
            "                }",
            "            })",
            "        });",
            "    }",
            "",
            "    // WebGL fingerprint",
            "    const _getParameter = WebGLRenderingContext.prototype.getParameter;",
            "    WebGLRenderingContext.prototype.getParameter = function(param) {",
            f"        if (param === 37445) return '{webgl_vendor}';",
            f"        if (param === 37446) return '{webgl_renderer}';",
            "        return _getParameter.call(this, param);",
            "    };",
            "    if (typeof WebGL2RenderingContext !== 'undefined') {",
            "        const _getParameter2 = WebGL2RenderingContext.prototype.getParameter;",
            "        WebGL2RenderingContext.prototype.getParameter = function(param) {",
            f"            if (param === 37445) return '{webgl_vendor}';",
            f"            if (param === 37446) return '{webgl_renderer}';",
            "            return _getParameter2.call(this, param);",
            "        };",
            "    }",
            "",
            "    // Screen / viewport",
            f"    Object.defineProperty(screen, 'width', {{get: () => {vp_width}}});",
            f"    Object.defineProperty(screen, 'height', {{get: () => {vp_height}}});",
            "",
            f"    console.log('[Agent-OS] Stealth profile applied: {profile_name}');",
            "})();",
        ]
        return "\n".join(lines)

    # ── Apply to browser ─────────────────────────────────────

    async def apply_profile(self, browser: Any, name: str) -> Dict[str, Any]:
        """Apply a named profile to the browser.

        Creates a new browser context with the profile's fingerprint settings,
        migrates cookies from the old context, injects profile-specific
        anti-detection JS, and swaps the active page.

        Args:
            browser: An ``AgentBrowser`` instance.
            name: Profile name to apply.

        Returns:
            Dict with ``status``, ``profile``, and details.
        """
        profile = self.get_profile(name)
        if not profile:
            return {
                "status": "error",
                "error": f"Unknown profile '{name}'. Available: {self.list_profiles()}",
            }

        if not browser.context or not browser.browser:
            return {"status": "error", "error": "Browser not started. Call start() first."}

        logger.info("Applying stealth profile: %s", name)

        # ── Migrate cookies from old context ─────────────────
        old_cookies: List[Dict] = []
        try:
            old_cookies = await browser.context.cookies()
        except Exception:
            pass

        # ── Save storage state ───────────────────────────────
        storage_state: Optional[Dict] = None
        try:
            storage_state = await browser.context.storage_state()
        except Exception:
            pass

        # ── Close old context ────────────────────────────────
        try:
            # Close all pages in old context
            for page in browser._pages.values():
                try:
                    await page.close()
                except Exception:
                    pass
            browser._pages.clear()
            browser._console_logs.clear()
            browser._network_logs.clear()
            await browser.context.close()
        except Exception as exc:
            logger.warning("Error closing old context: %s", exc)

        # ── Build new context options ────────────────────────
        context_options: Dict[str, Any] = {
            "java_script_enabled": True,
            "ignore_https_errors": True,
            "permissions": ["geolocation", "notifications"],
        }
        context_options = apply_profile_to_context_options(profile, context_options)

        if storage_state:
            context_options["storage_state"] = storage_state

        # ── Create new context ───────────────────────────────
        new_context = await browser.browser.new_context(**context_options)
        browser.context = new_context

        # ── Inject base anti-detection JS ────────────────────
        from src.core.browser import ANTI_DETECTION_JS
        await new_context.add_init_script(ANTI_DETECTION_JS)

        # ── Inject profile-specific JS ───────────────────────
        profile_js = self.get_anti_detection_js(profile)
        await new_context.add_init_script(profile_js)

        # ── Migrate cookies if storage_state didn't carry them
        if old_cookies and not storage_state:
            try:
                await new_context.add_cookies(old_cookies)
                logger.info("Migrated %d cookies to new context", len(old_cookies))
            except Exception as exc:
                logger.warning("Cookie migration partially failed: %s", exc)

        # ── Re-attach request blocking ───────────────────────
        await new_context.route("**/*", browser._handle_request)
        new_context.on("download", browser._handle_download)

        # ── Create new page ──────────────────────────────────
        new_page = await new_context.new_page()
        browser.page = new_page
        browser._pages["main"] = new_page
        browser._attach_console_listener("main", new_page)
        browser._attach_network_listener("main", new_page)

        # ── Track on browser ─────────────────────────────────
        browser._active_profile = profile
        self._active_profile_name = name
        self._active_profile = profile

        logger.info("Stealth profile '%s' applied successfully", name)
        return {
            "status": "success",
            "profile": name,
            "details": {
                "name": profile.get("name"),
                "user_agent": profile.get("user_agent"),
                "viewport": profile.get("viewport"),
                "platform": profile.get("platform"),
                "timezone": profile.get("timezone"),
                "locale": profile.get("locale"),
                "is_mobile": profile.get("is_mobile"),
                "has_touch": profile.get("has_touch"),
            },
            "cookies_migrated": len(old_cookies),
        }

    # ── Custom profile CRUD ──────────────────────────────────

    @staticmethod
    def create_custom_profile(name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create or overwrite a custom profile.

        Validates that required fields are present, merges with
        defaults from the ``windows-chrome`` base profile, and
        persists to ``~/.agent-os/profiles/<name>.json``.

        Args:
            name: Unique profile identifier.
            settings: Profile settings (partial or full).

        Returns:
            Dict with ``status`` and the merged profile.
        """
        if not name or not name.strip():
            return {"status": "error", "error": "Profile name cannot be empty."}

        if name in STEALTH_PROFILES:
            return {
                "status": "error",
                "error": f"'{name}' is a built-in profile. Choose a different name.",
            }

        # Merge with sensible defaults
        base = dict(STEALTH_PROFILES["windows-chrome"])
        base.update(settings)
        base["name"] = settings.get("name", name)
        base["description"] = settings.get("description", f"Custom profile: {name}")
        base["_custom"] = True
        base["_created_at"] = time.time()

        # Basic validation
        if "user_agent" not in base or not base["user_agent"]:
            return {"status": "error", "error": "user_agent is required."}
        if "viewport" not in base or not isinstance(base.get("viewport"), dict):
            return {"status": "error", "error": "viewport must be a dict with width/height."}

        _save_custom_profile(name, base)
        logger.info("Custom profile created: %s", name)
        return {"status": "success", "profile": name, "settings": base}

    @staticmethod
    def delete_custom_profile(name: str) -> Dict[str, Any]:
        """Delete a custom profile from disk.

        Args:
            name: Profile name to delete.

        Returns:
            Dict with status.
        """
        if name in STEALTH_PROFILES:
            return {"status": "error", "error": "Cannot delete built-in profiles."}

        path = CUSTOM_PROFILES_DIR / f"{name}.json"
        if not path.exists():
            return {"status": "error", "error": f"Profile '{name}' not found."}

        try:
            path.unlink()
            logger.info("Custom profile deleted: %s", name)
            return {"status": "success", "deleted": name}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    # ── Introspection ────────────────────────────────────────

    @property
    def active_profile_name(self) -> Optional[str]:
        """Name of the currently applied profile, or None."""
        return self._active_profile_name

    @property
    def active_profile(self) -> Optional[Dict[str, Any]]:
        """Dict of the currently applied profile, or None."""
        return self._active_profile
