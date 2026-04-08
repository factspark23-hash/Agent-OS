"""
Agent-OS Test Suite
Comprehensive tests for all components.
Run with: python -m pytest tests/ -v
"""
import asyncio
import sys
import os
import time
import pytest
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config, DEFAULT_CONFIG
from src.core.session import SessionManager, Session
from src.security.human_mimicry import HumanMimicry
from src.security.captcha_bypass import CaptchaBypass


# ─── Config Tests ─────────────────────────────────────────────

class TestConfig:
    def test_default_config(self):
        """Test default config has all required keys."""
        config = Config("/tmp/test-agent-os-config.yaml")
        assert config.get("server.ws_port") == 8000
        assert config.get("browser.headless") is True
        assert config.get("session.timeout_minutes") == 15

    def test_set_and_get(self):
        """Test setting and getting config values."""
        config = Config("/tmp/test-agent-os-config2.yaml")
        config.set("browser.max_ram_mb", 450)
        assert config.get("browser.max_ram_mb") == 450

    def test_generate_token(self):
        """Test token generation."""
        config = Config("/tmp/test-agent-os-config3.yaml")
        token = config.generate_agent_token("claude")
        assert token.startswith("claude-")
        assert len(token) > 10

    def test_token_validation(self):
        """Test that generated tokens validate correctly."""
        config = Config("/tmp/test-token-val.yaml")
        token = config.generate_agent_token("test-agent")
        assert config.validate_token(token) is True
        assert config.validate_token("fake-token") is False
        assert config.validate_token("") is False
        assert config.validate_token(None) is False

    def test_register_token(self):
        """Test registering an existing token."""
        config = Config("/tmp/test-register-token.yaml")
        config.register_token("my-custom-token", "cli")
        assert config.validate_token("my-custom-token") is True

    def test_merge_defaults(self):
        """Test that missing config keys get default values."""
        config = Config("/tmp/test-merge-defaults.yaml")
        # Set a partial config
        config.config = {"server": {"host": "0.0.0.0"}}
        merged = config._merge_defaults(DEFAULT_CONFIG, config.config)
        assert merged["server"]["host"] == "0.0.0.0"
        assert merged["server"]["ws_port"] == 8000  # default filled
        assert merged["browser"]["headless"] is True


# ─── Session Tests ─────────────────────────────────────────────

class TestSession:
    def test_create_session(self):
        """Test session creation."""
        config = Config("/tmp/test-session-config.yaml")
        sm = SessionManager(config)
        session = sm.create_session("test-token-123")
        assert session.session_id is not None
        assert session.agent_token == "test-token-123"
        assert session.active is True

    def test_session_expiry(self):
        """Test session timeout."""
        session = Session("test-id", "test-token")
        session.expires_at = time.time() - 100
        assert session.is_expired

    def test_get_by_token(self):
        """Test finding session by token."""
        config = Config("/tmp/test-session-config2.yaml")
        sm = SessionManager(config)
        sm.create_session("my-agent-token")
        found = sm.get_session_by_token("my-agent-token")
        assert found is not None
        assert found.agent_token == "my-agent-token"

    def test_list_active(self):
        """Test listing active sessions."""
        config = Config("/tmp/test-session-config3.yaml")
        sm = SessionManager(config)
        sm.create_session("token-1")
        sm.create_session("token-2")
        active = sm.list_active_sessions()
        assert len(active) == 2


# ─── Human Mimicry Tests ─────────────────────────────────────

class TestHumanMimicry:
    def test_typing_delay(self):
        """Test typing delay is within range."""
        mimicry = HumanMimicry()
        delay = mimicry.typing_delay()
        assert 40 <= delay <= 300

    def test_mouse_path(self):
        """Test mouse path generation."""
        mimicry = HumanMimicry()
        path = mimicry.mouse_path(500, 300)
        assert len(path) >= 5
        assert abs(path[-1][0] - 500) < 10
        assert abs(path[-1][1] - 300) < 10

    def test_mouse_path_is_curved(self):
        """Test that mouse paths are not straight lines."""
        mimicry = HumanMimicry()
        path = mimicry.mouse_path(200, 200)
        deviations = []
        for i in range(1, len(path) - 1):
            t = i / len(path)
            expected_x = 200 * t
            expected_y = 200 * t
            dev = abs(path[i][0] - expected_x) + abs(path[i][1] - expected_y)
            deviations.append(dev)
        assert sum(d > 1 for d in deviations) > 0

    def test_word_pause(self):
        """Test word pause timing."""
        mimicry = HumanMimicry()
        pause = mimicry.word_pause()
        assert 150 <= pause <= 1500

    def test_page_read_time(self):
        """Test page read time estimation."""
        mimicry = HumanMimicry()
        time_1000 = mimicry.page_read_time(1000)
        time_5000 = mimicry.page_read_time(5000)
        assert time_5000 > time_1000


# ─── CAPTCHA Bypass Tests ─────────────────────────────────────

class TestCaptchaBypass:
    def test_detects_recaptcha(self):
        """Test reCAPTCHA URL detection."""
        bypass = CaptchaBypass()
        assert bypass.is_bot_detection("https://www.google.com/recaptcha/api2/anchor")
        assert bypass.is_bot_detection("https://www.gstatic.com/recaptcha/releases/abc123/recaptcha__en.js")

    def test_detects_hcaptcha(self):
        """Test hCaptcha URL detection."""
        bypass = CaptchaBypass()
        assert bypass.is_bot_detection("https://hcaptcha.com/1/api.js")

    def test_detects_perimeterx(self):
        """Test PerimeterX URL detection."""
        bypass = CaptchaBypass()
        assert bypass.is_bot_detection("https://captcha.px-cloud.net/captcha")
        assert bypass.is_bot_detection("https://client.px-cdn.net/bundle.js")

    def test_detects_cloudflare(self):
        """Test Cloudflare Turnstile detection."""
        bypass = CaptchaBypass()
        assert bypass.is_bot_detection("https://challenges.cloudflare.com/turnstile/v0/api.js")

    def test_allows_normal_urls(self):
        """Test that normal URLs are not blocked."""
        bypass = CaptchaBypass()
        assert not bypass.is_bot_detection("https://github.com/login")
        assert not bypass.is_bot_detection("https://google.com/search")
        assert not bypass.is_bot_detection("https://api.example.com/data")

    def test_block_returns_fake_response(self):
        """Test that blocked requests return fake human responses."""
        bypass = CaptchaBypass()
        response = bypass.block_request("https://www.google.com/recaptcha/api2/verify")
        assert response is not None
        assert response.get("success") is True or response.get("human") is True

    def test_stats_tracking(self):
        """Test that bypass statistics are tracked."""
        bypass = CaptchaBypass()
        bypass.block_request("https://recaptcha.net/test")
        bypass.block_request("https://hcaptcha.com/test")
        stats = bypass.get_stats()
        assert stats["total_blocked"] == 2
        assert stats["by_type"]["recaptcha"] == 1
        assert stats["by_type"]["hcaptcha"] == 1


# ─── Security Tests ──────────────────────────────────────────

class TestSecurity:
    def test_no_web_security_flag(self):
        """Ensure --disable-web-security is NOT in browser launch args."""
        import pathlib
        # Read the source and verify the dangerous flag is absent
        source = (pathlib.Path(__file__).parent.parent / "src" / "core" / "browser.py").read_text()
        
        assert "--disable-web-security" not in source

    def test_scanner_no_drop_table(self):
        """Ensure SQLi scanner doesn't include destructive payloads."""
        from src.tools.scanner import SQLiScanner
        for payload in SQLiScanner.PAYLOADS:
            assert "DROP TABLE" not in payload.upper()
            assert "DELETE" not in payload.upper()
            assert "SLEEP" not in payload.upper()

    def test_xss_scanner_no_alert(self):
        """Ensure XSS scanner doesn't use alert() payloads."""
        from src.tools.scanner import XSSScanner
        for payload in XSSScanner.PAYLOADS:
            assert "alert(" not in payload.lower()


# ─── Integration Tests ─────────────────────────────────────

@pytest.mark.asyncio
class TestIntegration:
    async def test_browser_anti_detection_js(self):
        """Test that anti-detection JS is properly defined."""
        import pathlib; source = (pathlib.Path(__file__).parent.parent / "src" / "core" / "browser.py").read_text()
        assert "webdriver" in source
        assert "plugins" in source
        assert "chrome" in source.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
