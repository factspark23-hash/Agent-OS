"""
Agent-OS Auth Middleware
Integrates JWT + API key authentication into aiohttp server.
Provides per-user rate limiting, scope checking, and audit logging.
"""
import logging
import time
from functools import wraps
from typing import Optional

from aiohttp import web

from src.auth.jwt_handler import JWTHandler
from src.auth.api_key_manager import APIKeyManager

logger = logging.getLogger("agent-os.auth.middleware")


class AuthMiddleware:
    """
    Authentication and authorization middleware for aiohttp.

    Supports two auth methods:
    1. Bearer JWT token (Authorization: Bearer <token>)
    2. API key (token field in JSON body, or X-API-Key header)

    Provides:
    - Per-user rate limiting via Redis
    - Scope-based authorization
    - Request context injection (user_id, api_key_id, scopes)
    - Audit logging
    """

    def __init__(self, jwt_handler: JWTHandler, api_key_manager: APIKeyManager,
                 redis_client=None):
        self.jwt = jwt_handler
        self.api_keys = api_key_manager
        self.redis = redis_client

    async def authenticate_request(self, request: web.Request,
                                   body: dict = None) -> Optional[dict]:
        """
        Extract and validate authentication from request.
        Returns auth context dict if valid, None if unauthorized.
        """
        # Method 1: Bearer JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = self.jwt.verify_token(token, token_type="access")
            if payload:
                return {
                    "user_id": payload["sub"],
                    "api_key_id": payload.get("key_id"),
                    "scopes": payload.get("scopes", []),
                    "auth_method": "jwt",
                }
            return None

        # Method 2: API key from header
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            auth = await self.api_keys.authenticate(api_key)
            if auth:
                auth["auth_method"] = "api_key"
                return auth
            return None

        # Method 3: API key from body (for POST requests)
        if body and body.get("token"):
            token = body["token"]
            # Check if it's an API key (starts with aos_)
            if token.startswith("aos_"):
                auth = await self.api_keys.authenticate(token)
                if auth:
                    auth["auth_method"] = "api_key"
                    return auth
            # Otherwise try as JWT
            payload = self.jwt.verify_token(token, token_type="access")
            if payload:
                return {
                    "user_id": payload["sub"],
                    "api_key_id": payload.get("key_id"),
                    "scopes": payload.get("scopes", []),
                    "auth_method": "jwt",
                }

        return None

    async def check_rate_limit(self, auth_context: dict) -> tuple:
        """
        Check rate limit for the authenticated user.
        Returns: (allowed: bool, headers: dict)
        """
        if not self.redis:
            return True, {}

        user_id = auth_context["user_id"]
        rpm = auth_context.get("requests_per_minute", 60)

        allowed, current, remaining = await self.redis.check_rate_limit(
            f"user:{user_id}",
            max_requests=rpm,
            window_seconds=60,
        )

        headers = {
            "X-RateLimit-Limit": str(rpm),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(time.time()) + 60),
        }

        return allowed, headers

    def require_scope(self, scope: str):
        """Decorator to require a specific scope for an endpoint."""
        def decorator(handler):
            @wraps(handler)
            async def wrapper(request: web.Request) -> web.Response:
                auth = request.get("auth_context")
                if not auth:
                    return web.json_response(
                        {"status": "error", "error": "Authentication required"},
                        status=401
                    )
                scopes = auth.get("scopes", [])
                if isinstance(scopes, list):
                    has_scope = scope in scopes or "admin" in scopes
                elif isinstance(scopes, dict):
                    has_scope = scopes.get(scope, False) or scopes.get("admin", False)
                else:
                    has_scope = False

                if not has_scope:
                    return web.json_response(
                        {"status": "error", "error": f"Missing required scope: {scope}"},
                        status=403
                    )
                return await handler(request)
            return wrapper
        return decorator


def create_auth_middleware(auth_mw: AuthMiddleware):
    """
    Create aiohttp middleware that handles auth + rate limiting.
    """
    @web.middleware
    async def middleware(request: web.Request, handler):
        # Skip auth for health/status endpoints
        skip_paths = {"/status", "/health", "/commands", "/favicon.ico"}
        if request.path in skip_paths:
            return await handler

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await handler

        # Parse body for POST requests
        body = None
        if request.method == "POST" and request.content_type == "application/json":
            try:
                body = await request.json()
            except Exception:
                pass

        # Authenticate
        auth_context = await auth_mw.authenticate_request(request, body)
        if not auth_context:
            return web.json_response(
                {"status": "error", "error": "Invalid or missing authentication. Use API key (X-API-Key header or token field) or JWT Bearer token."},
                status=401,
            )

        # Rate limit
        allowed, rate_headers = await auth_mw.check_rate_limit(auth_context)
        if not allowed:
            resp = web.json_response(
                {"status": "error", "error": "Rate limit exceeded. Slow down."},
                status=429,
            )
            for k, v in rate_headers.items():
                resp.headers[k] = v
            return resp

        # Inject auth context into request
        request["auth_context"] = auth_context

        # Call handler
        response = await handler(request)

        # Add rate limit headers
        for k, v in rate_headers.items():
            response.headers[k] = v

        return response

    return middleware
