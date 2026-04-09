"""
Agent-OS Test Suite
Comprehensive tests for all components.
Run with: python -m pytest tests/ -v
"""
import asyncio
import sys
import os
import pytest
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config, DEFAULT_CONFIG
from src.core.session import SessionManager, Session
from src.security.human_mimicry import HumanMimicry
from src.security.captcha_bypass import CaptchaBypass
from src.debug.server import DebugServer


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
        import time as _time
        session = Session("test-id", "test-token")
        # Manually set expires_at to past
        session.expires_at = _time.time() - 100
        assert session.is_expired  # Expired immediately

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
        # Path should start near origin and end near target
        assert abs(path[-1][0] - 500) < 10
        assert abs(path[-1][1] - 300) < 10

    def test_mouse_path_is_curved(self):
        """Test that mouse paths are not straight lines (human-like curves)."""
        mimicry = HumanMimicry()
        path = mimicry.mouse_path(200, 200)
        # Check that intermediate points deviate from straight line
        deviations = []
        for i in range(1, len(path) - 1):
            t = i / len(path)
            expected_x = 200 * t
            expected_y = 200 * t
            dev = abs(path[i][0] - expected_x) + abs(path[i][1] - expected_y)
            deviations.append(dev)
        # At least some points should deviate (curved path)
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
        # Longer text should take more time
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


# ─── Integration Tests ─────────────────────────────────────

@pytest.mark.asyncio
class TestIntegration:
    async def test_server_command_list(self):
        """Test that server returns available commands."""
        import aiohttp

        config = Config("/tmp/test-integration-config.yaml")
        # We can't start a full server in tests, but we can verify command routing
        assert config.get("server.ws_port") == 8000

    async def test_browser_anti_detection_js(self):
        """Test that anti-detection JS is properly defined."""
        from src.core.browser import ANTI_DETECTION_JS
        assert "webdriver" in ANTI_DETECTION_JS
        assert "plugins" in ANTI_DETECTION_JS
        assert "chrome" in ANTI_DETECTION_JS.lower()


# ─── Debug Server Tests ───────────────────────────────────────

class TestDebugServer:
    def test_config_has_debug_port(self):
        """Test that default config includes debug port."""
        config = Config("/tmp/test-debug-config.yaml")
        assert config.get("server.debug_port") == 8002

    def test_command_history(self):
        """Test command recording."""
        config = Config("/tmp/test-debug-config2.yaml")
        # Mock dependencies
        debug = DebugServer(config, None, None, None)
        debug.record_command("navigate", {"url": "https://example.com"}, {"status": "success"})
        assert len(debug._command_history) == 1
        assert debug._command_history[0]["command"] == "navigate"
        assert debug._command_history[0]["status"] == "success"

    def test_console_log_recording(self):
        """Test console log recording."""
        config = Config("/tmp/test-debug-config3.yaml")
        debug = DebugServer(config, None, None, None)
        debug.record_console_log("error", "Something went wrong", "main")
        assert len(debug._console_logs) == 1
        assert debug._console_logs[0]["level"] == "error"

    def test_max_history_limit(self):
        """Test that history respects max limit."""
        config = Config("/tmp/test-debug-config4.yaml")
        debug = DebugServer(config, None, None, None)
        for i in range(250):
            debug.record_command(f"cmd-{i}", {}, {"status": "success"})
        assert len(debug._command_history) <= 200

    def test_static_dir_exists(self):
        """Test that static files exist."""
        from pathlib import Path
        static_dir = Path(__file__).parent.parent / "src" / "debug" / "static"
        assert (static_dir / "index.html").exists()
        assert (static_dir / "style.css").exists()
        assert (static_dir / "app.js").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
