"""
Agent-OS Authentication Handler
Handles auto-login, session cookie injection, and local credential vault.
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional, List
from cryptography.fernet import Fernet

logger = logging.getLogger("agent-os.auth")


class AuthHandler:
    """Manages authentication for automated browsing."""

    def __init__(self, config):
        self.config = config
        self.vault_path = Path(os.path.expanduser("~/.agent-os/vault.enc"))
        # Key stored separately from vault data
        self._key = self._get_or_create_key()
        self._fernet = Fernet(self._key)

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for the vault.

        Key is stored in a separate directory from the vault file
        to avoid a single-point compromise. On Linux, we use
        ~/.agent-os/keys/ with 0700 permissions.
        """
        # Use separate key directory
        key_dir = Path(os.path.expanduser("~/.agent-os/keys"))
        key_dir.mkdir(parents=True, exist_ok=True)
        key_dir.chmod(0o700)

        key_path = key_dir / "vault.key"
        if key_path.exists():
            key_bytes = key_path.read_bytes()
            # Validate it's a proper Fernet key
            try:
                Fernet(key_bytes)
                return key_bytes
            except Exception:
                logger.warning("Corrupt vault key, regenerating...")
                key_path.unlink()

        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        logger.info("New vault encryption key generated")
        return key

    def save_credentials(self, domain: str, credentials: Dict[str, str]):
        """Save encrypted credentials for a domain."""
        vault = self._load_vault()
        vault[domain] = credentials
        encrypted = self._fernet.encrypt(json.dumps(vault).encode())
        self.vault_path.write_bytes(encrypted)
        logger.info(f"Credentials saved for {domain}")

    def get_credentials(self, domain: str) -> Optional[Dict[str, str]]:
        """Get credentials for a domain."""
        vault = self._load_vault()
        return vault.get(domain)

    def list_domains(self) -> List[str]:
        """List domains with saved credentials."""
        return list(self._load_vault().keys())

    def delete_credentials(self, domain: str):
        """Delete credentials for a domain."""
        vault = self._load_vault()
        if domain in vault:
            del vault[domain]
            encrypted = self._fernet.encrypt(json.dumps(vault).encode())
            self.vault_path.write_bytes(encrypted)

    def _load_vault(self) -> Dict:
        """Load and decrypt the credential vault."""
        if not self.vault_path.exists():
            return {}
        try:
            encrypted = self.vault_path.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to load vault: {e}")
            return {}

    async def auto_login(self, browser, url: str, domain: str) -> Dict:
        """Attempt auto-login using stored credentials."""
        creds = self.get_credentials(domain)
        if not creds:
            return {"status": "error", "error": f"No credentials stored for {domain}"}

        await browser.navigate(url)

        # Common login form selectors
        email_selectors = [
            'input[type="email"]', 'input[name="email"]', 'input[name="username"]',
            'input[id="email"]', 'input[id="username"]', 'input[placeholder*="email"]',
            'input[placeholder*="username"]', 'input[type="text"][name*="user"]',
            'input[type="text"][name*="email"]',
        ]
        password_selectors = [
            'input[type="password"]', 'input[name="password"]',
            'input[id="password"]', 'input[placeholder*="password"]',
        ]

        result = await browser.fill_form({
            "email": creds.get("username", creds.get("email", "")),
            "password": creds.get("password", ""),
        })

        # Try to click submit
        submit_selectors = [
            'button[type="submit"]', 'input[type="submit"]',
            'button:has-text("Sign in")', 'button:has-text("Log in")',
            'button:has-text("Login")', 'button:has-text("Submit")',
        ]
        for sel in submit_selectors:
            click_result = await browser.click(sel)
            if click_result.get("status") == "success":
                break

        return {"status": "success", "domain": domain, "filled_fields": result.get("filled", [])}
