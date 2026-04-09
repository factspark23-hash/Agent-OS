"""
Agent-OS Configuration Management
Handles all settings, API tokens, and runtime configuration.
"""
import os
import yaml
import secrets
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "ws_port": 8000,
        "http_port": 8001,
        "max_connections": 10
    },
    "browser": {
        "headless": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "max_ram_mb": 500,
        "page_timeout_ms": 30000,
        "proxy": None,
        "device": "desktop_1080",
    },
    "session": {
        "timeout_minutes": 15,
        "auto_wipe": True,
        "max_concurrent": 3
    },
    "security": {
        "captcha_bypass": True,
        "human_mimicry": True,
        "block_bot_queries": True,
        "session_encryption": True
    },
    "scanner": {
        "max_requests_per_second": 5,
        "max_concurrent_scans": 2,
        "allowed_domains": []
    },
    "transcription": {
        "model": "tiny",
        "language": "auto"
    }
}


class Config:
    """Manages Agent-OS configuration with YAML persistence."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or os.path.expanduser("~/.agent-os/config.yaml"))
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        """Load existing config or create default."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG
        self.save(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def save(self, config: Optional[Dict] = None):
        """Save configuration to disk."""
        with open(self.config_path, "w") as f:
            yaml.dump(config or self.config, f, default_flow_style=False)

    def get(self, dotted_key: str, default=None):
        """Get config value by dotted path (e.g., 'browser.max_ram_mb')."""
        keys = dotted_key.split(".")
        val = self.config
        for k in keys:
            val = val.get(k, {}) if isinstance(val, dict) else default
        return val if val != {} else default

    def set(self, dotted_key: str, value: Any):
        """Set config value by dotted path."""
        keys = dotted_key.split(".")
        target = self.config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        self.save()

    def generate_agent_token(self, agent_name: str) -> str:
        """Generate a secure agent token."""
        random_suffix = secrets.token_hex(3)
        return f"{agent_name}-{random_suffix}"

    def hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
