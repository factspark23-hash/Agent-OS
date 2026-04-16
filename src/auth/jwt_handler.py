"""
Agent-OS JWT Authentication
Production-grade JWT handling with refresh tokens, token blacklisting,
and secure defaults.
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import jwt as pyjwt

logger = logging.getLogger("agent-os.auth.jwt")


class JWTHandler:
    """
    JWT token management.

    Access tokens: short-lived (15 min), used for API authentication.
    Refresh tokens: long-lived (30 days), used to obtain new access tokens.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256",
                 access_token_expire_minutes: int = 15,
                 refresh_token_expire_days: int = 30,
                 issuer: str = "agent-os"):
        if len(secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_expire = timedelta(days=refresh_token_expire_days)
        self.issuer = issuer
        self._blacklist: set = set()  # In production, use Redis
        self._user_tokens: Dict[str, set] = {}  # user_id → set of JTIs
        self._blacklist_file = Path(os.path.expanduser("~/.agent-os/jwt_blacklist.json"))
        self._load_blacklist()

    def create_access_token(self, user_id: str, api_key_id: str = None,
                            scopes: list = None, extra: dict = None) -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iss": self.issuer,
            "iat": now,
            "exp": now + self.access_expire,
            "type": "access",
            "jti": secrets.token_hex(16),
        }
        if api_key_id:
            payload["key_id"] = api_key_id
        if scopes:
            payload["scopes"] = scopes
        if extra:
            payload.update(extra)

        token = pyjwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        # Track JTI for user (for bulk revocation)
        jti = payload["jti"]
        if user_id not in self._user_tokens:
            self._user_tokens[user_id] = set()
        self._user_tokens[user_id].add(jti)

        return token

    def create_refresh_token(self, user_id: str, api_key_id: str = None) -> str:
        """Create a long-lived refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iss": self.issuer,
            "iat": now,
            "exp": now + self.refresh_expire,
            "type": "refresh",
            "jti": secrets.token_hex(16),
        }
        if api_key_id:
            payload["key_id"] = api_key_id

        return pyjwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, user_id: str, api_key_id: str = None,
                          scopes: list = None) -> Dict[str, Any]:
        """Create both access and refresh tokens."""
        return {
            "access_token": self.create_access_token(user_id, api_key_id, scopes),
            "refresh_token": self.create_refresh_token(user_id, api_key_id),
            "token_type": "bearer",
            "expires_in": int(self.access_expire.total_seconds()),
        }

    def _load_blacklist(self):
        """Load blacklist from disk on startup."""
        try:
            if self._blacklist_file.exists():
                data = json.loads(self._blacklist_file.read_text())
                self._blacklist = set(data.get("blacklist", []))
                self._user_tokens = {k: set(v) for k, v in data.get("user_tokens", {}).items()}
                logger.info(f"Loaded {len(self._blacklist)} blacklisted tokens from disk")
        except Exception as e:
            logger.warning(f"Failed to load JWT blacklist: {e}")

    def _save_blacklist(self):
        """Persist blacklist to disk."""
        try:
            self._blacklist_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "blacklist": list(self._blacklist),
                "user_tokens": {k: list(v) for k, v in self._user_tokens.items()},
            }
            self._blacklist_file.write_text(json.dumps(data))
            self._blacklist_file.chmod(0o600)
        except Exception as e:
            logger.warning(f"Failed to save JWT blacklist: {e}")

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """
        Verify and decode a JWT token.
        Returns payload dict if valid, None if invalid/expired.
        """
        try:
            payload = pyjwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
            )

            # Check type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None

            # Check blacklist
            jti = payload.get("jti")
            if jti and jti in self._blacklist:
                logger.warning(f"Token {jti} is blacklisted")
                return None

            return payload

        except pyjwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except pyjwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Use a refresh token to get a new access token pair."""
        payload = self.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None

        # Blacklist old refresh token (rotation)
        jti = payload.get("jti")
        if jti:
            self._blacklist.add(jti)
            self._save_blacklist()

        return self.create_token_pair(
            user_id=payload["sub"],
            api_key_id=payload.get("key_id"),
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its JTI to the blacklist."""
        try:
            # Decode without verification to get JTI
            payload = pyjwt.decode(
                token,
                options={"verify_signature": False},
            )
            jti = payload.get("jti")
            if jti:
                self._blacklist.add(jti)
                self._save_blacklist()
                return True
        except Exception:
            pass
        return False

    def revoke_all_user_tokens(self, user_id: str):
        """
        Revoke all tokens for a user.
        Uses tracked JTIs per user_id to blacklist all their tokens.
        """
        jtis = self._user_tokens.get(user_id, set())
        if jtis:
            self._blacklist.update(jtis)
            self._user_tokens[user_id] = set()
            self._save_blacklist()
            logger.info(f"Revoked {len(jtis)} tokens for user {user_id}")
        else:
            logger.info(f"No tracked tokens to revoke for user {user_id}")

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for secure storage (e.g., API keys)."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        return hmac.compare_digest(a.encode(), b.encode())
