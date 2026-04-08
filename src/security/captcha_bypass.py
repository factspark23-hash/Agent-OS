"""
Agent-OS CAPTCHA Bypass System
Blocks bot-detection queries at the network level and returns fake human responses.
This is the core anti-detection technology.
"""
import re
import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger("agent-os.captcha-bypass")


@dataclass
class BlockedEndpoint:
    """A bot detection endpoint that's been blocked."""
    url: str
    pattern_matched: str
    fake_response: dict
    timestamp: float = 0


class CaptchaBypass:
    """
    CAPTCHA prevention engine.
    
    Strategy: Don't SOLVE CAPTCHAs — PREVENT them from loading.
    We intercept bot-detection scripts and queries, returning fake "human verified" responses.
    """

    # URL patterns that trigger bot detection
    DETECTION_PATTERNS = [
        # Google reCAPTCHA
        r"recaptcha\.net",
        r"google\.com/recaptcha",
        r"gstatic\.com/recaptcha",
        r"googleapis\.com/recaptcha",
        # hCaptcha
        r"hcaptcha\.com",
        # Cloudflare Turnstile
        r"challenges\.cloudflare\.com",
        r"turnstile",
        # PerimeterX
        r"captcha\.px-cloud\.net",
        r"perimeterx",
        r"px-cdn\.net",
        r"px-client\.net",
        # DataDome
        r"datadome\.co",
        r"captcha\.geo\.datadome",
        # Imperva/Incapsula
        r"imperva\.com",
        r"incapdns\.net",
        # Akamai Bot Manager
        r"akamai-bot",
        r"akadns\.net.*bot",
        # Shape Security
        r"shapesecurity\.com",
        # Kasada
        r"kasada\.io",
        # Generic bot detection
        r"bot-detection",
        r"botdetect",
        r"verify-human",
        r"check-bot",
        r"anti-bot",
        r"captcha",
        r"challenge\.php",
    ]

    # JavaScript patterns that detect bots
    BOT_DETECTION_JS_PATTERNS = [
        "navigator.webdriver",
        "window.cdc_adoQpoasnfa76pfcZLmcfl_Array",
        "window.cdc_adoQpoasnfa76pfcZLmcfl_Promise",
        "window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol",
        "phantom",
        "__nightmare",
        "_selenium",
        "_phantom",
        "callPhantom",
        "__webdriver_evaluate",
        "__selenium_evaluate",
        "__fxdriver_evaluate",
        "__driver_unwrapped",
        "__webdriver_unwrapped",
        "__selenium_unwrapped",
        "__fxdriver_unwrapped",
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.DETECTION_PATTERNS]
        self._blocked: List[BlockedEndpoint] = []
        self._stats = {
            "total_blocked": 0,
            "by_type": {},
        }

    def is_bot_detection(self, url: str) -> bool:
        """Check if a URL is a bot detection endpoint."""
        url_lower = url.lower()
        for pattern in self._compiled_patterns:
            if pattern.search(url_lower):
                return True
        return False

    def get_detection_type(self, url: str) -> str:
        """Identify which type of bot detection this is."""
        url_lower = url.lower()
        type_map = {
            "recaptcha": ["recaptcha", "gstatic.com/recaptcha"],
            "hcaptcha": ["hcaptcha"],
            "cloudflare": ["challenges.cloudflare", "turnstile"],
            "perimeterx": ["perimeterx", "px-cloud", "px-cdn", "px-client"],
            "datadome": ["datadome"],
            "imperva": ["imperva", "incapdns"],
            "akamai": ["akamai"],
            "shape": ["shapesecurity"],
            "kasada": ["kasada"],
        }
        for det_type, patterns in type_map.items():
            if any(p in url_lower for p in patterns):
                return det_type
        return "generic"

    def get_fake_response(self, detection_type: str) -> dict:
        """Generate a convincing fake human verification response."""
        responses = {
            "recaptcha": {
                "success": True,
                "score": round(random.uniform(0.85, 0.99), 2),
                "action": "login",
                "challenge_ts": "2026-04-08T12:00:00Z",
                "hostname": "localhost"
            },
            "hcaptcha": {
                "success": True,
                "challenge_ts": "2026-04-08T12:00:00Z",
                "hostname": "localhost",
                "credit": False
            },
            "cloudflare": {
                "success": True,
                "cf_clearance": "agent_os_clearance_token_2026",
                "ray": "fake_ray_id"
            },
            "perimeterx": {
                "status": 0,
                "uuid": "agent-os-fake-uuid",
                "vid": "agent-os-fake-vid",
                "risk_score": random.randint(1, 15),
                "action": "captcha_pass"
            },
            "datadome": {
                "status": "allowed",
                "cookie": "datadome=verified_agent_os",
                "response": "human"
            },
            "imperva": {
                "result": "human",
                "confidence": round(random.uniform(0.9, 0.99), 2)
            },
            "akamai": {
                "bot_score": random.randint(90, 100),
                "classification": "human"
            },
            "shape": {
                "blocked": False,
                "human": True
            },
            "kasada": {
                "verified": True,
                "token": "agent-os-kasada-token"
            },
            "generic": {
                "human": True,
                "verified": True,
                "score": round(random.uniform(0.9, 0.99), 2)
            }
        }
        return responses.get(detection_type, responses["generic"])

    def block_request(self, url: str) -> Optional[dict]:
        """
        Check if a request should be blocked.
        Returns fake response if blocked, None if allowed.
        """
        if self.is_bot_detection(url):
            detection_type = self.get_detection_type(url)
            fake_response = self.get_fake_response(detection_type)

            self._blocked.append(BlockedEndpoint(
                url=url,
                pattern_matched=detection_type,
                fake_response=fake_response,
            ))

            self._stats["total_blocked"] += 1
            self._stats["by_type"][detection_type] = self._stats["by_type"].get(detection_type, 0) + 1

            logger.info(f"Blocked {detection_type} detection: {url[:80]}...")
            return fake_response

        return None

    def sanitize_js(self, html: str) -> str:
        """
        Remove bot detection JavaScript from HTML before execution.
        This prevents detection scripts from running at all.
        """
        sanitized = html

        # Remove webdriver detection
        sanitized = re.sub(
            r'navigator\.__defineGetter__\(\s*["\']webdriver["\'].*?\)',
            'navigator.__defineGetter__("webdriver", () => false)',
            sanitized,
            flags=re.DOTALL
        )

        # Remove detection script blocks
        for pattern in self.BOT_DETECTION_JS_PATTERNS:
            sanitized = re.sub(
                rf'<script[^>]*>.*?{re.escape(pattern)}.*?</script>',
                '<!-- Agent-OS: bot detection script blocked -->',
                sanitized,
                flags=re.DOTALL | re.IGNORECASE
            )

        return sanitized

    def get_stats(self) -> dict:
        """Get bypass statistics."""
        return {
            "total_blocked": self._stats["total_blocked"],
            "by_type": dict(self._stats["by_type"]),
            "recent_blocks": [
                {
                    "url": b.url[:100],
                    "type": b.pattern_matched
                }
                for b in self._blocked[-10:]
            ]
        }

    def get_blocklist_update(self) -> List[str]:
        """Return current detection patterns for external updates."""
        return self.DETECTION_PATTERNS.copy()


import random
