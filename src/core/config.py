"""
Agent-OS Configuration Management
Handles all settings, API tokens, and runtime configuration.
"""
import os
import yaml
import secrets
import hashlib
import copy
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "ws_port": 8000,
        "http_port": 8001,
        "debug_port": 8002,
        "max_connections": 10,
        "cors_origin": "http://127.0.0.1:8002",
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
    "persistent": {
        "enabled": False,
        "max_instances": 5,
        "max_contexts_per_instance": 50,
        "health_check_interval_seconds": 30,
        "idle_timeout_minutes": 60,
        "memory_cap_mb": 4000,
        "auto_restart": True,
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
                loaded = yaml.safe_load(f) or {}
            # Merge with defaults to ensure all keys exist
            return self._deep_merge(DEFAULT_CONFIG, loaded)
        # Return defaults in memory — don't auto-save to disk
        # (call save() explicitly if persistence is needed)
        return copy.deepcopy(DEFAULT_CONFIG)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge override into base dict. Override values win."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

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
        random_suffix = secrets.token_hex(16)
        return f"{agent_name}-{random_suffix}"

    def hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
