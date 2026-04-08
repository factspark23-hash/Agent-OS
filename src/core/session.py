"""
Agent-OS Session Manager
Handles session lifecycle, auto-wipe, and sandboxing.
"""
import asyncio
import time
import logging
import secrets
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger("agent-os.session")


@dataclass
class Session:
    """Represents an agent session."""
    session_id: str
    agent_token: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    pages: list = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    blocked_requests: int = 0
    commands_executed: int = 0

    def __post_init__(self):
        if self.expires_at == 0:
            self.expires_at = self.created_at + (15 * 60)  # 15 min default

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def time_remaining(self) -> float:
        return max(0, self.expires_at - time.time())

    @property
    def age(self) -> float:
        return time.time() - self.created_at


class SessionManager:
    """Manages agent sessions with auto-cleanup and sandboxing."""

    def __init__(self, config):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self._cleanup_task = None
        self._max_sessions = config.get("session.max_concurrent", 3)
        self._default_timeout = config.get("session.timeout_minutes", 15) * 60

    async def start(self):
        """Start the session cleanup loop."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self):
        """Stop and wipe all sessions."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for session_id in list(self.sessions.keys()):
            await self.destroy_session(session_id)
        logger.info("All sessions destroyed")

    def create_session(self, agent_token: str, timeout_minutes: Optional[int] = None) -> Session:
        """Create a new session for an agent."""
        # Enforce max concurrent sessions
        active = [s for s in self.sessions.values() if s.active and not s.is_expired]
        if len(active) >= self._max_sessions:
            oldest = min(active, key=lambda s: s.created_at)
            self.sessions[oldest.session_id].active = False

        session_id = secrets.token_urlsafe(16)
        timeout = (timeout_minutes or self.config.get("session.timeout_minutes", 15)) * 60

        session = Session(
            session_id=session_id,
            agent_token=agent_token,
            expires_at=time.time() + timeout,
        )
        self.sessions[session_id] = session
        logger.info(f"Session created: {session_id} (expires in {timeout/60:.0f}min)")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_expired:
            session.active = False
            return None
        return session

    def get_session_by_token(self, agent_token: str) -> Optional[Session]:
        """Get active session by agent token."""
        for session in self.sessions.values():
            if session.agent_token == agent_token and session.active and not session.is_expired:
                return session
        return None

    async def destroy_session(self, session_id: str):
        """Destroy a session and wipe all its data."""
        session = self.sessions.get(session_id)
        if session:
            session.active = False
            # Wipe session data (security)
            session.data.clear()
            session.pages.clear()
            del self.sessions[session_id]
            logger.info(f"Session destroyed and wiped: {session_id}")

    def extend_session(self, session_id: str, minutes: int = 15):
        """Extend session timeout."""
        session = self.sessions.get(session_id)
        if session and session.active:
            session.expires_at = time.time() + (minutes * 60)

    def list_active_sessions(self) -> list:
        """List all active sessions (no sensitive data)."""
        return [
            {
                "session_id": s.session_id,
                "created_at": datetime.fromtimestamp(s.created_at).isoformat(),
                "expires_in_seconds": int(s.time_remaining),
                "commands_executed": s.commands_executed,
                "blocked_requests": s.blocked_requests,
                "active": s.active and not s.is_expired
            }
            for s in self.sessions.values()
        ]

    async def _cleanup_loop(self):
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                expired = [sid for sid, s in self.sessions.items() if s.is_expired]
                for sid in expired:
                    await self.destroy_session(sid)
                if expired:
                    logger.info(f"Cleaned up {len(expired)} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
