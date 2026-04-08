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
        "host": "0.0.0.0",
        "ws_port": 8000,
        "http_port": 8001,
        "max_connections": 10,
        "tls_cert": "",
        "tls_key": "",
        "cors_origins": ["http://localhost:*"],
        "rate_limit_rps": 20,  # requests per second per IP
        "rate_limit_burst": 40,
    },
    "browser": {
        "headless": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "max_ram_mb": 500,
        "page_timeout_ms": 30000
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
        self._agent_tokens: Dict[str, str] = {}  # token_hash -> agent_name
        self._load_tokens()

    def _load_or_create(self) -> Dict[str, Any]:
        """Load existing config or create default."""
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    return self._merge_defaults(DEFAULT_CONFIG, loaded)
        self.save(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    def _merge_defaults(self, defaults: dict, loaded: dict) -> dict:
        """Merge loaded config with defaults, filling missing keys."""
        result = dict(defaults)
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_defaults(result[key], value)
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
        """Generate a secure agent token and register it."""
        token = f"{agent_name}-{secrets.token_hex(16)}"
        token_hash = self.hash_token(token)
        self._agent_tokens[token_hash] = agent_name
        self._save_tokens()
        return token

    def validate_token(self, token: str) -> bool:
        """Validate an agent token against registered tokens."""
        if not token:
            return False
        token_hash = self.hash_token(token)
        return token_hash in self._agent_tokens

    def register_token(self, token: str, agent_name: str = "cli"):
        """Register an existing token (e.g., from CLI --agent-token)."""
        token_hash = self.hash_token(token)
        self._agent_tokens[token_hash] = agent_name
        self._save_tokens()

    def hash_token(self, token: str) -> str:
        """Hash token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _token_file(self) -> Path:
        return self.config_path.parent / ".tokens"

    def _load_tokens(self):
        """Load registered token hashes."""
        token_file = self._token_file()
        if token_file.exists():
            try:
                with open(token_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line:
                            h, name = line.split(":", 1)
                            self._agent_tokens[h] = name
            except Exception:
                pass

    def _save_tokens(self):
        """Save registered token hashes."""
        token_file = self._token_file()
        with open(token_file, "w") as f:
            for h, name in self._agent_tokens.items():
                f.write(f"{h}:{name}\n")
        token_file.chmod(0o600)
