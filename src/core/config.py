"""
Agent-OS Configuration Management — Production Edition
Handles all settings, with database/Redis/JWT config support.
"""
import os
import yaml
import secrets
import hashlib
import hmac
import copy
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_CONFIG = {
    "server": {
        "host": os.environ.get("AGENT_OS_HOST", "127.0.0.1"),
        "ws_port": 8000,
        "http_port": 8001,
        "debug_port": 8002,
        "max_connections": 100,
        "cors_origin": "",
        "cors_allowed_origins": [],
        "agent_token": None,
        "allowed_tokens": [],
        "rate_limit_max": 60,
        "rate_limit_window": 60,
        "request_timeout_seconds": 120,
        "max_request_body_kb": 1024,
    },
    "database": {
        "enabled": False,
        "dsn": "postgresql+asyncpg://agent_os:agent_os@localhost:5432/agent_os",
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600,
    },
    "redis": {
        "enabled": False,
        "url": "redis://localhost:6379/0",
        "fallback_on_failure": True,
    },
    "jwt": {
        "secret_key": None,  # Auto-generated if not set
        "algorithm": "HS256",
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30,
        "issuer": "agent-os",
    },
    "browser": {
        "headless": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "max_ram_mb": 500,
        "page_timeout_ms": 30000,
        "proxy": None,
        "device": "desktop_1080",
        "locale": "en-US",
        "timezone_id": "America/New_York",
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
        "session_encryption": True,
        "enable_api_key_auth": True,
        "enable_jwt_auth": True,
        "allow_legacy_token_auth": False,
        "max_login_attempts": 5,
        "lockout_duration_minutes": 15,
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
    },
    "logging": {
        "level": "INFO",
        "json_logs": True,
        "service_name": "agent-os",
    },
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
            return self._deep_merge(DEFAULT_CONFIG, loaded)
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

    def set(self, dotted_key: str, value: Any, save: bool = False):
        """Set config value by dotted path. Only saves to disk if save=True."""
        keys = dotted_key.split(".")
        target = self.config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        if save:
            self.save()

    def generate_agent_token(self, agent_name: str) -> str:
        """Generate a secure agent token."""
        random_suffix = secrets.token_hex(16)
        return f"{agent_name}-{random_suffix}"

    def hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_token(self, provided_token: str, stored_hash: str) -> bool:
        """Constant-time token verification to prevent timing attacks."""
        provided_hash = self.hash_token(provided_token)
        return hmac.compare_digest(provided_hash, stored_hash)
