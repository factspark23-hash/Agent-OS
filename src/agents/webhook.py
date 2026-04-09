"""
Agent-OS Webhook / Event System
Allows external services to receive real-time notifications about browser events.
"""
import asyncio
import hashlib
import hmac
import logging
import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger("agent-os.webhook")


@dataclass
class Webhook:
    """Represents a registered webhook endpoint."""
    url: str
    events: List[str]
    secret: str = ""
    webhook_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: float = field(default_factory=time.time)
    last_triggered: float = 0
    trigger_count: int = 0
    failures: int = 0
    active: bool = True


class WebhookManager:
    """Manages webhook registrations and event dispatching."""

    SUPPORTED_EVENTS = [
        "navigation",
        "click",
        "form_submit",
        "form_fill",
        "screenshot",
        "error",
        "session_start",
        "session_end",
        "download",
        "alert",
        "page_load",
        "network_error",
        "scan_complete",
        "transcription_complete",
    ]

    def __init__(self, config) -> None:
        self._webhooks: Dict[str, Webhook] = {}
        self._max_webhooks = 10
        self._timeout = 10  # seconds per delivery attempt
        self._max_retries = 3
        self._failure_threshold = 10  # consecutive failures before deactivation

    async def register(self, url: str, events: List[str], secret: str = "") -> Dict:
        """Register a new webhook endpoint.

        Args:
            url: The HTTP(S) URL to receive POST events.
            events: List of event types to subscribe to.
            secret: Optional HMAC-SHA256 secret for payload signing.

        Returns:
            Dict with status, webhook_id, and subscribed events.
        """
        try:
            # Validate URL format
            if not url.startswith(("http://", "https://")):
                return {"status": "error", "error": "URL must start with http:// or https://"}

            # Check max webhooks
            if len(self._webhooks) >= self._max_webhooks:
                return {"status": "error", "error": f"Maximum {self._max_webhooks} webhooks allowed"}

            # Reject duplicate URLs
            for wh in self._webhooks.values():
                if wh.url == url:
                    return {"status": "error", "error": f"Webhook already registered for URL: {url}"}

            # Validate events
            invalid = [e for e in events if e not in self.SUPPORTED_EVENTS]
            if invalid:
                return {
                    "status": "error",
                    "error": f"Unknown event type(s): {invalid}. Supported: {self.SUPPORTED_EVENTS}",
                }

            wh = Webhook(url=url, events=events, secret=secret)
            self._webhooks[wh.webhook_id] = wh
            logger.info(f"Webhook registered: {wh.webhook_id} -> {url} (events: {events})")

            return {
                "status": "success",
                "webhook_id": wh.webhook_id,
                "events": events,
                "url": url,
            }
        except Exception as e:
            logger.error(f"Failed to register webhook: {e}")
            return {"status": "error", "error": str(e)}

    async def unregister(self, webhook_id: str) -> Dict:
        """Remove a registered webhook.

        Args:
            webhook_id: The webhook ID returned during registration.

        Returns:
            Dict with status and confirmation.
        """
        try:
            if webhook_id not in self._webhooks:
                return {"status": "error", "error": f"Webhook not found: {webhook_id}"}
            wh = self._webhooks.pop(webhook_id)
            logger.info(f"Webhook unregistered: {webhook_id} ({wh.url})")
            return {"status": "success", "webhook_id": webhook_id, "url": wh.url}
        except Exception as e:
            logger.error(f"Failed to unregister webhook: {e}")
            return {"status": "error", "error": str(e)}

    def list_webhooks(self) -> List[Dict]:
        """List all registered webhooks without exposing secrets.

        Returns:
            List of webhook dicts with id, url, events, active, etc.
        """
        result = []
        for wh in self._webhooks.values():
            result.append({
                "webhook_id": wh.webhook_id,
                "url": wh.url,
                "events": wh.events,
                "active": wh.active,
                "created_at": wh.created_at,
                "last_triggered": wh.last_triggered,
                "trigger_count": wh.trigger_count,
                "failures": wh.failures,
                "has_secret": bool(wh.secret),
            })
        return result

    async def dispatch(self, event_type: str, data: Dict) -> None:
        """Fire an event to all matching webhooks (fire-and-forget).

        Each matching webhook receives its own asyncio task so that slow
        deliveries don't block the caller. Failures are logged but never
        propagated.

        Args:
            event_type: The event name (e.g. "navigation", "click").
            data: The event payload.
        """
        tasks = []
        for wh in self._webhooks.values():
            if wh.active and event_type in wh.events:
                tasks.append(asyncio.create_task(self._deliver(wh, event_type, data)))

        if tasks:
            # Let them run in the background — don't await
            logger.debug(f"Dispatching '{event_type}' to {len(tasks)} webhook(s)")

    async def _deliver(self, webhook: Webhook, event_type: str, data: Dict) -> None:
        """Deliver an event to a single webhook with retries.

        POST JSON body with event type, timestamp, data, and webhook_id.
        Signs with HMAC-SHA256 if secret is configured.
        Retries up to 3 times on network errors with exponential backoff.
        Deactivates after 10 consecutive failures.
        """
        import json
        from datetime import datetime, timezone

        body = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "webhook_id": webhook.webhook_id,
        }
        body_str = json.dumps(body)

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "Agent-OS-Webhook/2.0",
        }

        # HMAC-SHA256 signature
        if webhook.secret:
            sig = hmac.new(
                webhook.secret.encode(),
                body_str.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Agent-OS-Signature"] = f"sha256={sig}"

        for attempt in range(1, self._max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(webhook.url, data=body_str, headers=headers) as resp:
                        if resp.status < 400:
                            webhook.trigger_count += 1
                            webhook.last_triggered = time.time()
                            webhook.failures = 0  # reset consecutive failures
                            logger.debug(
                                f"Webhook {webhook.webhook_id} delivered '{event_type}' "
                                f"(attempt {attempt}, HTTP {resp.status})"
                            )
                            return
                        else:
                            logger.warning(
                                f"Webhook {webhook.webhook_id} returned HTTP {resp.status} "
                                f"on attempt {attempt}"
                            )
            except Exception as e:
                logger.warning(
                    f"Webhook {webhook.webhook_id} delivery attempt {attempt} failed: {e}"
                )

            # Exponential backoff between retries
            if attempt < self._max_retries:
                await asyncio.sleep(2 ** (attempt - 1))

        # All retries exhausted
        webhook.failures += 1
        logger.error(
            f"Webhook {webhook.webhook_id} failed after {self._max_retries} attempts "
            f"(consecutive failures: {webhook.failures})"
        )

        if webhook.failures >= self._failure_threshold:
            webhook.active = False
            logger.error(
                f"Webhook {webhook.webhook_id} deactivated after "
                f"{self._failure_threshold} consecutive failures"
            )

    async def test_webhook(self, webhook_id: str) -> Dict:
        """Send a test ping event to verify a webhook is reachable.

        Args:
            webhook_id: The webhook ID to test.

        Returns:
            Dict with status and delivery result.
        """
        try:
            if webhook_id not in self._webhooks:
                return {"status": "error", "error": f"Webhook not found: {webhook_id}"}

            wh = self._webhooks[webhook_id]

            # Save and temporarily force active
            orig_active = wh.active
            wh.active = True

            await self._deliver(wh, "ping", {
                "message": "Agent-OS webhook test ping",
                "webhook_url": wh.url,
            })

            wh.active = orig_active
            return {
                "status": "success",
                "webhook_id": webhook_id,
                "message": "Test ping delivered successfully",
            }
        except Exception as e:
            logger.error(f"Webhook test failed for {webhook_id}: {e}")
            return {"status": "error", "error": str(e)}
