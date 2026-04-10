"""
Agent-OS Agent Server — Production Edition
WebSocket + REST API with full auth, validation, rate limiting, and audit logging.
"""
import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Any
from aiohttp import web

import websockets

logger = logging.getLogger("agent-os.server")


class AgentServer:
    """
    Dual-protocol agent server:
    - WebSocket (port 8000): For real-time agent communication
    - HTTP REST (port 8001): For curl/simple integrations

    Production features:
    - API key + JWT authentication
    - Per-user rate limiting via Redis
    - Input validation and sanitization
    - Usage tracking and audit logging
    - Structured error responses
    """

    def __init__(self, config, browser, session_manager, persistent_manager=None,
                 auth_middleware=None, api_key_manager=None, user_manager=None,
                 redis_client=None):
        self.config = config
        self.browser = browser
        self.session_manager = session_manager
        self.persistent_manager = persistent_manager
        self.auth_middleware = auth_middleware
        self.api_key_manager = api_key_manager
        self.user_manager = user_manager
        self.redis = redis_client
        self._ws_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._ws_server = None
        self._http_app = None
        self._http_runner = None
        self._start_time = time.time()

        # Smart Wait + Auto Heal + Auto Retry + Recording + Multi-Agent engines (lazy init)
        self._smart_wait = None
        self._auto_heal = None
        self._auto_retry = None
        self._recorder = None
        self._replay = None
        self._analyzer = None
        self._agent_hub = None
        self._proxy_manager = None

        # In-memory rate limiting fallback
        self._rate_limits: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._rate_max_requests = config.get("server.rate_limit_max", 60)
        self._rate_window_seconds = config.get("server.rate_limit_window", 60)
        self._rate_cleanup_task = None

    async def start(self):
        """Start both WebSocket and HTTP servers."""
        ws_host = self.config.get("server.host", "0.0.0.0")
        ws_port = self.config.get("server.ws_port", 8000)
        http_port = self.config.get("server.http_port", 8001)

        # Start WebSocket server
        self._ws_server = await websockets.serve(
            self._ws_handler, ws_host, ws_port,
            ping_interval=30, ping_timeout=10,
            max_size=10 * 1024 * 1024,  # 10MB max message
        )
        logger.info(f"WebSocket server listening on ws://{ws_host}:{ws_port}")

        # Start HTTP server with auth middleware
        self._http_app = web.Application(
            middlewares=self._get_middlewares(),
            client_max_size=self.config.get("server.max_request_body_kb", 1024) * 1024,
        )
        self._setup_routes()
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        site = web.TCPSite(self._http_runner, ws_host, http_port)
        await site.start()
        logger.info(f"HTTP server listening on http://{ws_host}:{http_port}")

        # Start rate limit cleanup task (for in-memory fallback)
        self._rate_cleanup_task = asyncio.create_task(self._rate_limit_cleanup_loop())

    async def stop(self):
        """Stop both servers."""
        if self._rate_cleanup_task:
            self._rate_cleanup_task.cancel()
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
        if self._http_runner:
            await self._http_runner.cleanup()
        logger.info("Agent servers stopped")

    def _get_middlewares(self):
        """Build middleware chain."""
        middlewares = [self._cors_middleware]

        # Add auth middleware if configured
        if self.auth_middleware:
            from src.auth.middleware import create_auth_middleware
            middlewares.insert(0, create_auth_middleware(self.auth_middleware))

        # Add request timing middleware
        middlewares.append(self._timing_middleware)

        return middlewares

    def _validate_token_legacy(self, token: str) -> bool:
        """Legacy token validation (backward compat). Uses constant-time comparison."""
        if not token:
            return False
        import hmac as _hmac
        allowed = self.config.get("server.allowed_tokens", [])
        if allowed:
            for allowed_token in allowed:
                if _hmac.compare_digest(token, allowed_token):
                    return True
            return False
        configured = self.config.get("server.agent_token")
        if configured:
            return _hmac.compare_digest(token, configured)
        return False

    async def _authenticate_ws(self, token: str) -> Optional[dict]:
        """
        Authenticate WebSocket connection.
        Tries: API key → JWT → legacy token.
        Returns auth context dict or None.
        """
        # Try API key
        if self.api_key_manager and token.startswith("aos_"):
            auth = await self.api_key_manager.authenticate(token)
            if auth:
                return auth

        # Try JWT
        if self.auth_middleware and not token.startswith("aos_"):
            payload = self.auth_middleware.jwt.verify_token(token, token_type="access")
            if payload:
                return {
                    "user_id": payload["sub"],
                    "api_key_id": payload.get("key_id"),
                    "scopes": payload.get("scopes", []),
                    "auth_method": "jwt",
                }

        # Legacy token fallback
        if self.config.get("security.allow_legacy_token_auth", True):
            if self._validate_token_legacy(token):
                return {
                    "user_id": "legacy",
                    "api_key_id": None,
                    "scopes": ["browser"],
                    "auth_method": "legacy_token",
                }

        return None

    def _check_rate_limit(self, identifier: str) -> bool:
        """In-memory rate limit check (fallback when Redis unavailable)."""
        now = time.time()
        window = self._rate_window_seconds
        max_req = self._rate_max_requests
        timestamps = self._rate_limits[identifier]
        cutoff = now - window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()
        if len(timestamps) >= max_req:
            return False
        timestamps.append(now)
        return True

    async def _rate_limit_cleanup_loop(self):
        """Periodically clean up stale rate limit entries."""
        while True:
            try:
                await asyncio.sleep(120)
                now = time.time()
                cutoff = now - self._rate_window_seconds
                stale = [k for k, ts in self._rate_limits.items()
                         if not ts or ts[-1] < cutoff]
                for k in stale:
                    del self._rate_limits[k]
                if len(self._rate_limits) > 50000:
                    sorted_keys = sorted(
                        self._rate_limits.keys(),
                        key=lambda k: self._rate_limits[k][-1] if self._rate_limits[k] else 0
                    )
                    for k in sorted_keys[:10000]:
                        del self._rate_limits[k]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limit cleanup error: {e}")

    def _get_cors_headers(self, request=None) -> Dict[str, str]:
        """Return CORS headers for API responses. Uses configured allowed origins."""
        allowed_origins = self.config.get("server.cors_allowed_origins", [])
        cors_origin = self.config.get("server.cors_origin", "")

        # If specific origins configured, validate against request Origin
        if allowed_origins and request:
            origin = request.headers.get("Origin", "")
            if origin in allowed_origins:
                cors_origin = origin
            else:
                cors_origin = ""  # Reject — no CORS header set
        elif not cors_origin:
            # Default: deny cross-origin if nothing configured
            cors_origin = ""

        headers = {
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
            "Access-Control-Max-Age": "86400",
            "Access-Control-Expose-Headers": "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset",
        }
        if cors_origin:
            headers["Access-Control-Allow-Origin"] = cors_origin
        return headers

    def _setup_routes(self):
        """Setup HTTP routes."""
        async def _cors_preflight(request: web.Request) -> web.Response:
            return web.Response(headers=self._get_cors_headers())

        self._http_app.router.add_route("OPTIONS", "/{path:.*}", _cors_preflight)

        # Public endpoints (no auth)
        self._http_app.router.add_get("/status", self._handle_status)
        self._http_app.router.add_get("/health", self._handle_health)
        self._http_app.router.add_get("/commands", self._handle_commands_list)

        # Auth endpoints
        self._http_app.router.add_post("/auth/register", self._handle_register)
        self._http_app.router.add_post("/auth/login", self._handle_login)
        self._http_app.router.add_post("/auth/refresh", self._handle_refresh)
        self._http_app.router.add_post("/auth/api-keys", self._handle_create_api_key)
        self._http_app.router.add_get("/auth/api-keys", self._handle_list_api_keys)
        self._http_app.router.add_delete("/auth/api-keys/{key_prefix}", self._handle_revoke_api_key)

        # Authenticated command endpoint
        self._http_app.router.add_post("/command", self._handle_command)

        # Debug endpoints
        self._http_app.router.add_get("/debug", self._handle_debug)
        self._http_app.router.add_get("/screenshot", self._handle_screenshot)

        # Persistent browser routes
        if self.persistent_manager:
            self._http_app.router.add_get("/persistent/health", self._handle_persistent_health)
            self._http_app.router.add_get("/persistent/users", self._handle_persistent_users)
            self._http_app.router.add_post("/persistent/command", self._handle_persistent_command)

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        """Add CORS headers to all responses. Validates origin against config."""
        response = await handler(request)
        for key, value in self._get_cors_headers(request).items():
            response.headers[key] = value
        return response

    @web.middleware
    async def _timing_middleware(self, request: web.Request, handler):
        """Add request timing, correlation ID, and structured logging."""
        import uuid
        start = time.time()
        request_id = str(uuid.uuid4())
        request["request_id"] = request_id
        try:
            response = await handler(request)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"Request error: {request.method} {request.path} ({elapsed:.0f}ms) [{request_id}]: {e}")
            return web.json_response(
                {"status": "error", "error": "Internal server error", "request_id": request_id},
                status=500,
                headers=self._get_cors_headers(),
            )
        elapsed = (time.time() - start) * 1000
        response.headers["X-Response-Time"] = f"{elapsed:.0f}ms"
        response.headers["X-Request-ID"] = request_id
        if elapsed > 5000:
            logger.warning(f"Slow request: {request.method} {request.path} ({elapsed:.0f}ms) [{request_id}]")
        return response

    # ─── WebSocket Handler ───────────────────────────────────

    async def _ws_handler(self, websocket, path):
        """Handle WebSocket connections from agents."""
        client_id = f"ws-{id(websocket)}"

        try:
            first_msg = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            data = json.loads(first_msg)
            token = data.get("token", "")

            auth_context = await self._authenticate_ws(token)
            if not auth_context:
                await websocket.send(json.dumps({
                    "status": "error",
                    "error": "Invalid authentication token"
                }))
                await websocket.close(code=4001)
                return

            self._ws_clients[client_id] = websocket
            logger.info(f"Agent connected via WebSocket: {client_id} (user: {auth_context['user_id']})")
            await websocket.send(json.dumps({
                "status": "authenticated",
                "client_id": client_id,
                "user_id": auth_context["user_id"],
            }))

        except (asyncio.TimeoutError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"WebSocket auth failed: {e}")
            try:
                await websocket.close(code=4001)
            except Exception:
                pass
            return

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    token = data.get("token", "")

                    # Re-authenticate each message
                    auth_context = await self._authenticate_ws(token)
                    if not auth_context:
                        await websocket.send(json.dumps({
                            "status": "error", "error": "Invalid token"
                        }))
                        continue

                    # Rate limit
                    if self.redis:
                        allowed, _, _ = await self.redis.check_rate_limit(
                            f"ws:{auth_context['user_id']}",
                            auth_context.get("requests_per_minute", self._rate_max_requests),
                            self._rate_window_seconds,
                        )
                        if not allowed:
                            await websocket.send(json.dumps({
                                "status": "error", "error": "Rate limit exceeded"
                            }))
                            continue
                    elif not self._check_rate_limit(f"ws:{client_id}"):
                        await websocket.send(json.dumps({
                            "status": "error", "error": "Rate limit exceeded"
                        }))
                        continue

                    # Validate input
                    try:
                        from src.validation.schemas import validate_command_payload
                        validated_data = validate_command_payload(data)
                    except Exception as ve:
                        await websocket.send(json.dumps({
                            "status": "error", "error": f"Validation error: {str(ve)}"
                        }))
                        continue

                    # Track usage
                    start = time.time()
                    result = await self._process_command(validated_data, auth_context)
                    duration_ms = int((time.time() - start) * 1000)

                    # Log usage
                    if self.user_manager:
                        await self.user_manager.log_usage(
                            user_id=auth_context["user_id"],
                            command=validated_data.get("command", "unknown"),
                            status=result.get("status", "error"),
                            duration_ms=duration_ms,
                            api_key_id=auth_context.get("api_key_id"),
                            client_ip="websocket",
                        )

                    await websocket.send(json.dumps(result))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"status": "error", "error": "Invalid JSON"}))
                except Exception as e:
                    logger.error(f"WS error: {e}")
                    await websocket.send(json.dumps({"status": "error", "error": str(e)}))
        finally:
            self._ws_clients.pop(client_id, None)
            logger.info(f"Agent disconnected: {client_id}")

    # ─── HTTP Handlers ──────────────────────────────────────

    async def _handle_register(self, request: web.Request) -> web.Response:
        """POST /auth/register — Register a new user."""
        if not self.user_manager:
            return web.json_response(
                {"status": "error", "error": "User management not enabled"},
                status=501, headers=self._get_cors_headers(),
            )
        try:
            data = await request.json()
            email = data.get("email", "").strip()
            username = data.get("username", "").strip()
            password = data.get("password", "")

            if not email or not username or not password:
                return web.json_response(
                    {"status": "error", "error": "email, username, and password required"},
                    status=400, headers=self._get_cors_headers(),
                )

            user = await self.user_manager.create_user(
                email=email, username=username, password=password,
                display_name=data.get("display_name"),
                organization=data.get("organization"),
            )

            # Log audit
            await self.user_manager.log_audit(
                user_id=user["id"], action="user.register",
                success=True, client_ip=request.remote,
            )

            return web.json_response({"status": "success", "user": user},
                                      headers=self._get_cors_headers())
        except ValueError as e:
            return web.json_response(
                {"status": "error", "error": str(e)},
                status=400, headers=self._get_cors_headers(),
            )
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return web.json_response(
                {"status": "error", "error": "Registration failed"},
                status=500, headers=self._get_cors_headers(),
            )

    async def _handle_login(self, request: web.Request) -> web.Response:
        """POST /auth/login — Authenticate and get JWT tokens."""
        if not self.user_manager or not self.auth_middleware:
            return web.json_response(
                {"status": "error", "error": "Auth not enabled"},
                status=501, headers=self._get_cors_headers(),
            )
        try:
            data = await request.json()
            login = data.get("username") or data.get("email", "")
            password = data.get("password", "")

            if not login or not password:
                return web.json_response(
                    {"status": "error", "error": "username/email and password required"},
                    status=400, headers=self._get_cors_headers(),
                )

            # Brute-force protection
            client_ip = request.remote or "unknown"
            identifier = f"{client_ip}:{login}"
            if not self.auth_middleware.check_login_attempts(identifier):
                lockout = self.auth_middleware.get_lockout_remaining(identifier)
                return web.json_response(
                    {"status": "error", "error": f"Too many failed attempts. Try again in {lockout} seconds."},
                    status=429, headers=self._get_cors_headers(),
                )

            user = await self.user_manager.authenticate_user(login, password)
            if not user:
                self.auth_middleware.record_login_failure(identifier)
                await self.user_manager.log_audit(
                    user_id=None, action="user.login_failed",
                    success=False, client_ip=request.remote,
                    details={"login": login},
                )
                return web.json_response(
                    {"status": "error", "error": "Invalid credentials"},
                    status=401, headers=self._get_cors_headers(),
                )

            # Successful login
            self.auth_middleware.record_login_success(identifier)

            tokens = self.auth_middleware.jwt.create_token_pair(
                user_id=user["user_id"],
                scopes=user.get("scopes", []),
            )

            await self.user_manager.log_audit(
                user_id=user["user_id"], action="user.login",
                success=True, client_ip=request.remote,
            )

            return web.json_response({
                "status": "success",
                **tokens,
                "user": {
                    "id": user["user_id"],
                    "username": user["username"],
                    "plan": user["plan"],
                },
            }, headers=self._get_cors_headers())

        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response(
                {"status": "error", "error": "Login failed"},
                status=500, headers=self._get_cors_headers(),
            )

    async def _handle_refresh(self, request: web.Request) -> web.Response:
        """POST /auth/refresh — Get new access token from refresh token."""
        if not self.auth_middleware:
            return web.json_response(
                {"status": "error", "error": "Auth not enabled"},
                status=501, headers=self._get_cors_headers(),
            )
        try:
            data = await request.json()
            refresh_token = data.get("refresh_token", "")

            if not refresh_token:
                return web.json_response(
                    {"status": "error", "error": "refresh_token required"},
                    status=400, headers=self._get_cors_headers(),
                )

            new_tokens = self.auth_middleware.jwt.refresh_access_token(refresh_token)
            if not new_tokens:
                return web.json_response(
                    {"status": "error", "error": "Invalid or expired refresh token"},
                    status=401, headers=self._get_cors_headers(),
                )

            return web.json_response(
                {"status": "success", **new_tokens},
                headers=self._get_cors_headers(),
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "error": str(e)},
                status=400, headers=self._get_cors_headers(),
            )

    async def _handle_create_api_key(self, request: web.Request) -> web.Response:
        """POST /auth/api-keys — Create a new API key."""
        if not self.api_key_manager:
            return web.json_response(
                {"status": "error", "error": "API key management not enabled"},
                status=501, headers=self._get_cors_headers(),
            )

        # Must be authenticated via JWT
        auth = request.get("auth_context")
        if not auth:
            return web.json_response(
                {"status": "error", "error": "Authentication required"},
                status=401, headers=self._get_cors_headers(),
            )

        try:
            data = await request.json()
            key_data = await self.api_key_manager.create_key(
                user_id=auth["user_id"],
                name=data.get("name", "Unnamed Key"),
                scopes=data.get("scopes"),
                requests_per_minute=data.get("requests_per_minute", 60),
                requests_per_day=data.get("requests_per_day", 10000),
                expires_in_days=data.get("expires_in_days"),
            )

            if self.user_manager:
                await self.user_manager.log_audit(
                    user_id=auth["user_id"], action="api_key.create",
                    success=True, client_ip=request.remote,
                    details={"key_prefix": key_data["key_prefix"], "name": data.get("name")},
                )

            return web.json_response(
                {"status": "success", "api_key": key_data},
                headers=self._get_cors_headers(),
            )
        except Exception as e:
            return web.json_response(
                {"status": "error", "error": str(e)},
                status=400, headers=self._get_cors_headers(),
            )

    async def _handle_list_api_keys(self, request: web.Request) -> web.Response:
        """GET /auth/api-keys — List user's API keys."""
        auth = request.get("auth_context")
        if not auth:
            return web.json_response(
                {"status": "error", "error": "Authentication required"},
                status=401, headers=self._get_cors_headers(),
            )

        if not self.api_key_manager:
            return web.json_response(
                {"status": "error", "error": "API key management not enabled"},
                status=501, headers=self._get_cors_headers(),
            )

        keys = await self.api_key_manager.list_keys(auth["user_id"])
        return web.json_response(
            {"status": "success", "keys": keys, "count": len(keys)},
            headers=self._get_cors_headers(),
        )

    async def _handle_revoke_api_key(self, request: web.Request) -> web.Response:
        """DELETE /auth/api-keys/{key_prefix} — Revoke an API key."""
        auth = request.get("auth_context")
        if not auth:
            return web.json_response(
                {"status": "error", "error": "Authentication required"},
                status=401, headers=self._get_cors_headers(),
            )

        if not self.api_key_manager:
            return web.json_response(
                {"status": "error", "error": "API key management not enabled"},
                status=501, headers=self._get_cors_headers(),
            )

        key_prefix = request.match_info["key_prefix"]
        revoked = await self.api_key_manager.revoke_key(key_prefix, auth["user_id"])

        if revoked and self.user_manager:
            await self.user_manager.log_audit(
                user_id=auth["user_id"], action="api_key.revoke",
                success=True, client_ip=request.remote,
                details={"key_prefix": key_prefix},
            )

        return web.json_response(
            {"status": "success" if revoked else "error",
             "message": "Key revoked" if revoked else "Key not found"},
            status=200 if revoked else 404,
            headers=self._get_cors_headers(),
        )

    async def _handle_command(self, request: web.Request) -> web.Response:
        """Handle HTTP POST /command — main command endpoint."""
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"status": "error", "error": "Invalid JSON body"},
                status=400, headers=self._get_cors_headers(),
            )

        # Auth context injected by middleware
        auth_context = request.get("auth_context")
        if not auth_context:
            # Fallback: try legacy token auth
            token = data.get("token", "")
            if self.config.get("security.allow_legacy_token_auth", True):
                if self._validate_token_legacy(token):
                    auth_context = {
                        "user_id": "legacy",
                        "api_key_id": None,
                        "scopes": ["browser"],
                        "auth_method": "legacy_token",
                    }

            if not auth_context:
                return web.json_response(
                    {"status": "error", "error": "Invalid or missing authentication"},
                    status=401, headers=self._get_cors_headers(),
                )

        # Validate and sanitize input
        try:
            from src.validation.schemas import validate_command_payload
            validated_data = validate_command_payload(data)
        except Exception as ve:
            return web.json_response(
                {"status": "error", "error": f"Validation error: {str(ve)}"},
                status=400, headers=self._get_cors_headers(),
            )

        # Execute command
        start = time.time()
        result = await self._process_command(validated_data, auth_context)
        duration_ms = int((time.time() - start) * 1000)

        # Log usage
        if self.user_manager:
            await self.user_manager.log_usage(
                user_id=auth_context["user_id"],
                command=validated_data.get("command", "unknown"),
                status=result.get("status", "error"),
                duration_ms=duration_ms,
                api_key_id=auth_context.get("api_key_id"),
                client_ip=request.remote,
            )

        return web.json_response(result, headers=self._get_cors_headers())

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /status."""
        status = {
            "status": "running",
            "version": "3.0.0",
            "uptime_seconds": int(time.time() - self._start_time),
            "active_sessions": len(self.session_manager.list_active_sessions()),
            "active_ws_clients": len(self._ws_clients),
            "browser_active": self.browser.browser is not None,
            "persistent_browser_enabled": self.persistent_manager is not None,
            "auth_enabled": {
                "api_keys": self.api_key_manager is not None,
                "jwt": self.auth_middleware is not None,
                "legacy_token": self.config.get("security.allow_legacy_token_auth", True),
            },
        }
        if self.persistent_manager:
            ph = self.persistent_manager.get_health()
            status["persistent_browser"] = ph.get("summary", {})
        return web.json_response(status)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /health — deep health check."""
        checks = {"server": "healthy"}

        # Database health
        try:
            from src.infra.database import get_db
            db = get_db()
            db_health = await db.health_check()
            checks["database"] = db_health["status"]
        except Exception:
            checks["database"] = "not_configured"

        # Redis health
        if self.redis:
            redis_health = await self.redis.health_check()
            checks["redis"] = redis_health["status"]
            checks["redis_mode"] = redis_health.get("mode", "unknown")
        else:
            checks["redis"] = "not_configured"

        # Browser health — verify actual browser is responsive
        if self.browser.browser:
            try:
                # Quick check: can we get the current page?
                if self.browser.page:
                    await self.browser.page.title()
                checks["browser"] = "healthy"
            except Exception as e:
                checks["browser"] = f"degraded: {e}"
        else:
            checks["browser"] = "not_running"

        overall = "healthy" if all(
            v in ("healthy", "not_configured") for v in checks.values()
        ) else "degraded"

        return web.json_response({
            "status": overall,
            "checks": checks,
            "timestamp": time.time(),
        })

    async def _handle_commands_list(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /commands — list all available commands."""
        # Same command list as before, truncated for brevity
        commands = self._get_command_definitions()
        return web.json_response(commands)

    async def _handle_debug(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /debug."""
        return web.json_response({
            "sessions": self.session_manager.list_active_sessions(),
            "uptime": int(time.time() - self._start_time),
            "ws_clients": len(self._ws_clients),
            "blocked_requests": getattr(self.browser, '_blocked_requests', 0),
            "tabs": list(getattr(self.browser, '_pages', {}).keys()),
        })

    async def _handle_screenshot(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /screenshot."""
        try:
            b64 = await self.browser.screenshot()
            return web.Response(body=b64, content_type="text/plain")
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ─── Persistent Browser Endpoints ────────────────────────

    async def _handle_persistent_health(self, request: web.Request) -> web.Response:
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        return web.json_response(self.persistent_manager.get_health())

    async def _handle_persistent_users(self, request: web.Request) -> web.Response:
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        return web.json_response({"users": self.persistent_manager.list_users()})

    async def _handle_persistent_command(self, request: web.Request) -> web.Response:
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        try:
            data = await request.json()
            auth_context = request.get("auth_context")
            if not auth_context:
                return web.json_response({"status": "error", "error": "Authentication required"}, status=401)

            user_id = data.get("user_id") or auth_context.get("user_id")
            command = data.get("command")
            if not command:
                return web.json_response({"status": "error", "error": "Missing 'command'"}, status=400)

            result = await self.persistent_manager.execute_for_user(user_id, command, data)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=400)

    # ─── Command Processing ─────────────────────────────────

    async def _process_command(self, data: Dict, auth_context: Dict = None) -> Dict[str, Any]:
        """Process any agent command with auth context."""
        command = data.get("command", "").lower()
        if not command:
            return {"status": "error", "error": "Missing 'command'"}

        # Get or create session
        token = data.get("token", auth_context.get("user_id", "unknown") if auth_context else "unknown")
        session = self.session_manager.get_session_by_token(token)
        if not session:
            session = self.session_manager.create_session(token)

        session.commands_executed += 1

        try:
            result = await self._execute_command(command, data, session)
            result["session_id"] = session.session_id
            return result
        except Exception as e:
            logger.error(f"Command error [{command}]: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "session_id": session.session_id}

    async def _execute_command(self, command: str, data: Dict, session) -> Dict:
        """Route command to appropriate handler."""
        handlers = {
            "navigate": self._cmd_navigate,
            "fill-form": self._cmd_fill_form,
            "click": self._cmd_click,
            "type": self._cmd_type,
            "press": self._cmd_press,
            "screenshot": self._cmd_screenshot,
            "get-content": self._cmd_get_content,
            "get-dom": self._cmd_get_dom,
            "scroll": self._cmd_scroll,
            "hover": self._cmd_hover,
            "select": self._cmd_select,
            "upload": self._cmd_upload,
            "wait": self._cmd_wait,
            "evaluate-js": self._cmd_evaluate_js,
            "back": self._cmd_back,
            "forward": self._cmd_forward,
            "reload": self._cmd_reload,
            "get-links": self._cmd_get_links,
            "get-images": self._cmd_get_images,
            "right-click": self._cmd_right_click,
            "context-action": self._cmd_context_action,
            "drag-drop": self._cmd_drag_drop,
            "drag-offset": self._cmd_drag_offset,
            "double-click": self._cmd_double_click,
            "clear-input": self._cmd_clear_input,
            "checkbox": self._cmd_checkbox,
            "get-text": self._cmd_get_text,
            "get-attr": self._cmd_get_attr,
            "viewport": self._cmd_viewport,
            "add-extension": self._cmd_add_extension,
            "console-logs": self._cmd_console_logs,
            "get-cookies": self._cmd_get_cookies,
            "set-cookie": self._cmd_set_cookie,
            "scan-xss": self._cmd_scan_xss,
            "scan-sqli": self._cmd_scan_sqli,
            "scan-sensitive": self._cmd_scan_sensitive,
            "transcribe": self._cmd_transcribe,
            "auto-login": self._cmd_auto_login,
            "save-creds": self._cmd_save_creds,
            "fill-job": self._cmd_fill_job,
            "tabs": self._cmd_tabs,
            # Smart Element Finder
            "smart-find": self._cmd_smart_find,
            "smart-find-all": self._cmd_smart_find_all,
            "smart-click": self._cmd_smart_click,
            "smart-fill": self._cmd_smart_fill,
            # Workflow Engine
            "workflow": self._cmd_workflow,
            "workflow-template": self._cmd_workflow_template,
            "workflow-json": self._cmd_workflow_json,
            "workflow-save": self._cmd_workflow_save,
            "workflow-list": self._cmd_workflow_list,
            "workflow-status": self._cmd_workflow_status,
            # Network Capture
            "network-start": self._cmd_network_start,
            "network-stop": self._cmd_network_stop,
            "network-get": self._cmd_network_get,
            "network-apis": self._cmd_network_apis,
            "network-detail": self._cmd_network_detail,
            "network-stats": self._cmd_network_stats,
            "network-export": self._cmd_network_export,
            "network-clear": self._cmd_network_clear,
            # Page Analyzer
            "page-summary": self._cmd_page_summary,
            "page-tables": self._cmd_page_tables,
            "page-structured": self._cmd_page_structured,
            "page-emails": self._cmd_page_emails,
            "page-phones": self._cmd_page_phones,
            "page-accessibility": self._cmd_page_accessibility,
            "page-seo": self._cmd_page_seo,
            # Proxy
            "set-proxy": self._cmd_set_proxy,
            "get-proxy": self._cmd_get_proxy,
            # Mobile Emulation
            "emulate-device": self._cmd_emulate_device,
            "list-devices": self._cmd_list_devices,
            # Session Save/Restore
            "save-session": self._cmd_save_session,
            "restore-session": self._cmd_restore_session,
            "list-sessions": self._cmd_list_sessions,
            "delete-session": self._cmd_delete_session,
            # Smart Wait
            "smart-wait": self._cmd_smart_wait,
            "smart-wait-network": self._cmd_smart_wait_network,
            "smart-wait-dom": self._cmd_smart_wait_dom,
            "smart-wait-element": self._cmd_smart_wait_element,
            "smart-wait-page": self._cmd_smart_wait_page,
            "smart-wait-js": self._cmd_smart_wait_js,
            "smart-wait-compose": self._cmd_smart_wait_compose,
            # Auto Heal
            "heal-click": self._cmd_heal_click,
            "heal-fill": self._cmd_heal_fill,
            "heal-wait": self._cmd_heal_wait,
            "heal-hover": self._cmd_heal_hover,
            "heal-double-click": self._cmd_heal_double_click,
            "heal-selector": self._cmd_heal_selector,
            "heal-fingerprint": self._cmd_heal_fingerprint,
            "heal-fingerprint-page": self._cmd_heal_fingerprint_page,
            "heal-stats": self._cmd_heal_stats,
            "heal-clear": self._cmd_heal_clear,
            # Auto Retry
            "retry-execute": self._cmd_retry_execute,
            "retry-navigate": self._cmd_retry_navigate,
            "retry-click": self._cmd_retry_click,
            "retry-fill": self._cmd_retry_fill,
            "retry-api-call": self._cmd_retry_api_call,
            "retry-stats": self._cmd_retry_stats,
            "retry-health": self._cmd_retry_health,
            "retry-circuit-breakers": self._cmd_retry_circuit_breakers,
            "retry-reset-circuit": self._cmd_retry_reset_circuit,
            "retry-reset-all-circuits": self._cmd_retry_reset_all_circuits,
            # Session Recording
            "record-start": self._cmd_record_start,
            "record-stop": self._cmd_record_stop,
            "record-pause": self._cmd_record_pause,
            "record-resume": self._cmd_record_resume,
            "record-annotate": self._cmd_record_annotate,
            "record-status": self._cmd_record_status,
            "record-list": self._cmd_record_list,
            "record-delete": self._cmd_record_delete,
            # Replay
            "replay-load": self._cmd_replay_load,
            "replay-play": self._cmd_replay_play,
            "replay-stop": self._cmd_replay_stop,
            "replay-pause": self._cmd_replay_pause,
            "replay-resume": self._cmd_replay_resume,
            "replay-step": self._cmd_replay_step,
            "replay-jump": self._cmd_replay_jump,
            "replay-position": self._cmd_replay_position,
            "replay-events": self._cmd_replay_events,
            "replay-export-workflow": self._cmd_replay_export_workflow,
            "analyze": self._cmd_analyze,
            "analyze-search": self._cmd_analyze_search,
            # Multi-Agent Hub
            "hub-register": self._cmd_hub_register,
            "hub-unregister": self._cmd_hub_unregister,
            "hub-heartbeat": self._cmd_hub_heartbeat,
            "hub-status": self._cmd_hub_status,
            "hub-agents": self._cmd_hub_agents,
            "hub-lock": self._cmd_hub_lock,
            "hub-unlock": self._cmd_hub_unlock,
            "hub-locks": self._cmd_hub_locks,
            "hub-task-create": self._cmd_hub_task_create,
            "hub-task-claim": self._cmd_hub_task_claim,
            "hub-task-start": self._cmd_hub_task_start,
            "hub-task-complete": self._cmd_hub_task_complete,
            "hub-task-fail": self._cmd_hub_task_fail,
            "hub-task-cancel": self._cmd_hub_task_cancel,
            "hub-tasks": self._cmd_hub_tasks,
            "hub-broadcast": self._cmd_hub_broadcast,
            "hub-events": self._cmd_hub_events,
            "hub-memory-set": self._cmd_hub_memory_set,
            "hub-memory-get": self._cmd_hub_memory_get,
            "hub-memory-delete": self._cmd_hub_memory_delete,
            "hub-memory-list": self._cmd_hub_memory_list,
            "hub-handoff": self._cmd_hub_handoff,
            "hub-audit": self._cmd_hub_audit,
            # Proxy Rotation
            "proxy-add": self._cmd_proxy_add,
            "proxy-remove": self._cmd_proxy_remove,
            "proxy-load-file": self._cmd_proxy_load_file,
            "proxy-load-api": self._cmd_proxy_load_api,
            "proxy-get": self._cmd_proxy_get,
            "proxy-record": self._cmd_proxy_record,
            "proxy-check": self._cmd_proxy_check,
            "proxy-check-all": self._cmd_proxy_check_all,
            "proxy-list": self._cmd_proxy_list,
            "proxy-enable": self._cmd_proxy_enable,
            "proxy-disable": self._cmd_proxy_disable,
            "proxy-strategy": self._cmd_proxy_strategy,
            "proxy-stats": self._cmd_proxy_stats,
            "proxy-save": self._cmd_proxy_save,
            "proxy-load": self._cmd_proxy_load,
        }

        handler = handlers.get(command)
        if not handler:
            return {"status": "error", "error": f"Unknown command: {command}"}

        return await handler(data, session)

    # ─── Lazy-Init Engines ──────────────────────────────────

    def _get_smart_wait(self):
        if self._smart_wait is None:
            from src.tools.smart_wait import SmartWait
            self._smart_wait = SmartWait(self.browser)
        return self._smart_wait

    def _get_auto_heal(self):
        if self._auto_heal is None:
            from src.tools.auto_heal import AutoHeal
            self._auto_heal = AutoHeal(self.browser, smart_wait=self._get_smart_wait())
        return self._auto_heal

    def _get_auto_retry(self):
        if self._auto_retry is None:
            from src.tools.auto_retry import AutoRetry
            self._auto_retry = AutoRetry(self.browser, smart_wait=self._get_smart_wait(), auto_heal=self._get_auto_heal())
        return self._auto_retry

    def _get_recorder(self):
        if self._recorder is None:
            from src.tools.session_recording import SessionRecorder
            self._recorder = SessionRecorder(self.browser)
        return self._recorder

    def _get_replay(self):
        if self._replay is None:
            from src.tools.session_recording import SessionReplay
            self._replay = SessionReplay(self.browser)
        return self._replay

    def _get_analyzer(self):
        if self._analyzer is None:
            from src.tools.session_recording import SessionAnalyzer
            self._analyzer = SessionAnalyzer()
        return self._analyzer

    def _get_agent_hub(self):
        if self._agent_hub is None:
            from src.tools.multi_agent import AgentHub
            self._agent_hub = AgentHub(self.browser, self.session_manager)
        return self._agent_hub

    def _get_proxy_manager(self):
        if self._proxy_manager is None:
            from src.tools.proxy_rotation import ProxyManager
            self._proxy_manager = ProxyManager()
        return self._proxy_manager

    # ─── Command Handlers (same as before) ──────────────────

    async def _cmd_navigate(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await self.browser.navigate(url, page_id=data.get("page_id", "main"),
                                           wait_until=data.get("wait_until", "domcontentloaded"))

    async def _cmd_fill_form(self, data: Dict, session) -> Dict:
        fields = data.get("fields", {})
        if not fields:
            return {"status": "error", "error": "Missing 'fields'"}
        return await self.browser.fill_form(fields)

    async def _cmd_click(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.click(selector)

    async def _cmd_type(self, data: Dict, session) -> Dict:
        text = data.get("text")
        if not text:
            return {"status": "error", "error": "Missing 'text'"}
        return await self.browser.type_text(text)

    async def _cmd_press(self, data: Dict, session) -> Dict:
        key = data.get("key")
        if not key:
            return {"status": "error", "error": "Missing 'key'"}
        return await self.browser.press_key(key)

    async def _cmd_screenshot(self, data: Dict, session) -> Dict:
        b64 = await self.browser.screenshot(full_page=data.get("full_page", False))
        return {"status": "success", "screenshot": b64, "format": "png"}

    async def _cmd_get_content(self, data: Dict, session) -> Dict:
        content = await self.browser.get_content()
        return {"status": "success", **content}

    async def _cmd_get_dom(self, data: Dict, session) -> Dict:
        dom = await self.browser.get_dom_snapshot()
        return {"status": "success", "dom_snapshot": dom}

    async def _cmd_scroll(self, data: Dict, session) -> Dict:
        return await self.browser.scroll(data.get("direction", "down"), data.get("amount", 500))

    async def _cmd_hover(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.hover(selector)

    async def _cmd_select(self, data: Dict, session) -> Dict:
        selector, value = data.get("selector"), data.get("value")
        if not selector or not value:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        return await self.browser.select_option(selector, value)

    async def _cmd_upload(self, data: Dict, session) -> Dict:
        selector, file_path = data.get("selector"), data.get("file_path")
        if not selector or not file_path:
            return {"status": "error", "error": "Missing 'selector' or 'file_path'"}
        return await self.browser.upload_file(selector, file_path)

    async def _cmd_wait(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.wait_for_element(selector, timeout=data.get("timeout", 10000))

    async def _cmd_evaluate_js(self, data: Dict, session) -> Dict:
        script = data.get("script")
        if not script:
            return {"status": "error", "error": "Missing 'script'"}
        result = await self.browser.evaluate_js(script)
        return {"status": "success", "result": result}

    async def _cmd_back(self, data: Dict, session) -> Dict:
        return await self.browser.go_back()

    async def _cmd_forward(self, data: Dict, session) -> Dict:
        return await self.browser.go_forward()

    async def _cmd_reload(self, data: Dict, session) -> Dict:
        return await self.browser.reload()

    async def _cmd_get_links(self, data: Dict, session) -> Dict:
        links = await self.browser.get_all_links()
        return {"status": "success", "links": links, "count": len(links)}

    async def _cmd_get_images(self, data: Dict, session) -> Dict:
        images = await self.browser.get_all_images()
        return {"status": "success", "images": images, "count": len(images)}

    async def _cmd_right_click(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.right_click(selector)

    async def _cmd_context_action(self, data: Dict, session) -> Dict:
        selector, action_text = data.get("selector"), data.get("action_text")
        if not selector or not action_text:
            return {"status": "error", "error": "Missing 'selector' or 'action_text'"}
        return await self.browser.context_action(selector, action_text)

    async def _cmd_drag_drop(self, data: Dict, session) -> Dict:
        source, target = data.get("source"), data.get("target")
        if not source or not target:
            return {"status": "error", "error": "Missing 'source' or 'target'"}
        return await self.browser.drag_and_drop(source, target)

    async def _cmd_drag_offset(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.drag_by_offset(selector, data.get("x", 0), data.get("y", 0))

    async def _cmd_double_click(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.double_click(selector)

    async def _cmd_clear_input(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.clear_input(selector)

    async def _cmd_checkbox(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.set_checkbox(selector, data.get("checked", True))

    async def _cmd_get_text(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.get_element_text(selector)

    async def _cmd_get_attr(self, data: Dict, session) -> Dict:
        selector, attribute = data.get("selector"), data.get("attribute")
        if not selector or not attribute:
            return {"status": "error", "error": "Missing 'selector' or 'attribute'"}
        return await self.browser.get_element_attribute(selector, attribute)

    async def _cmd_viewport(self, data: Dict, session) -> Dict:
        return await self.browser.set_viewport(data.get("width", 1920), data.get("height", 1080))

    async def _cmd_add_extension(self, data: Dict, session) -> Dict:
        path = data.get("extension_path")
        if not path:
            return {"status": "error", "error": "Missing 'extension_path'"}
        return await self.browser.add_extension(path)

    async def _cmd_console_logs(self, data: Dict, session) -> Dict:
        return await self.browser.get_console_logs(page_id=data.get("page_id", "main"), clear=data.get("clear", False))

    async def _cmd_get_cookies(self, data: Dict, session) -> Dict:
        return await self.browser.get_cookies()

    async def _cmd_set_cookie(self, data: Dict, session) -> Dict:
        name, value = data.get("name"), data.get("value")
        if not name or not value:
            return {"status": "error", "error": "Missing 'name' or 'value'"}
        return await self.browser.set_cookie(name=name, value=value, domain=data.get("domain"),
                                              path=data.get("path", "/"), secure=data.get("secure"),
                                              http_only=data.get("http_only", False),
                                              same_site=data.get("same_site"))

    async def _cmd_scan_xss(self, data: Dict, session) -> Dict:
        from src.tools.scanner import XSSScanner
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await XSSScanner(self.browser).scan(url)

    async def _cmd_scan_sqli(self, data: Dict, session) -> Dict:
        from src.tools.scanner import SQLiScanner
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await SQLiScanner(self.browser).scan(url)

    async def _cmd_scan_sensitive(self, data: Dict, session) -> Dict:
        from src.tools.scanner import SensitiveDataScanner
        return await SensitiveDataScanner().scan_page(self.browser)

    async def _cmd_transcribe(self, data: Dict, session) -> Dict:
        from src.tools.transcriber import Transcriber
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await Transcriber(self.config).transcribe_from_url(url, data.get("language", "auto"))

    async def _cmd_auto_login(self, data: Dict, session) -> Dict:
        from src.security.auth_handler import AuthHandler
        url, domain = data.get("url"), data.get("domain")
        if not url or not domain:
            return {"status": "error", "error": "Missing 'url' or 'domain'"}
        return await AuthHandler(self.config).auto_login(self.browser, url, domain)

    async def _cmd_save_creds(self, data: Dict, session) -> Dict:
        from src.security.auth_handler import AuthHandler
        domain = data.get("domain")
        if not domain:
            return {"status": "error", "error": "Missing 'domain'"}
        AuthHandler(self.config).save_credentials(domain, {"username": data.get("username", ""), "password": data.get("password", "")})
        return {"status": "success", "message": f"Credentials saved for {domain}"}

    async def _cmd_fill_job(self, data: Dict, session) -> Dict:
        from src.tools.form_filler import FormFiller
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await FormFiller(self.browser).fill_job_application(url, data.get("profile", {}))

    async def _cmd_tabs(self, data: Dict, session) -> Dict:
        action, tab_id = data.get("action", "list"), data.get("tab_id")
        if action == "list":
            return {"status": "success", "tabs": list(self.browser._pages.keys())}
        elif action == "new":
            tid = tab_id or f"tab-{len(self.browser._pages)}"
            await self.browser.new_tab(tid)
            return {"status": "success", "tab_id": tid}
        elif action == "switch":
            if tab_id:
                return await self.browser.switch_tab(tab_id)
            return {"status": "error", "error": "Missing 'tab_id'"}
        elif action == "close":
            if tab_id:
                return {"status": "success" if await self.browser.close_tab(tab_id) else "error"}
            return {"status": "error", "error": "Missing 'tab_id'"}
        return {"status": "error", "error": f"Unknown tab action: {action}"}

    # ─── Smart Finder ───────────────────────────────────────

    async def _cmd_smart_find(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        desc = data.get("description")
        if not desc:
            return {"status": "error", "error": "Missing 'description'"}
        return await SmartElementFinder(self.browser).find(desc, tag=data.get("tag"), timeout=data.get("timeout", 5000))

    async def _cmd_smart_find_all(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        desc = data.get("description")
        if not desc:
            return {"status": "error", "error": "Missing 'description'"}
        return await SmartElementFinder(self.browser).find_all(desc, tag=data.get("tag"))

    async def _cmd_smart_click(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        text = data.get("text")
        if not text:
            return {"status": "error", "error": "Missing 'text'"}
        return await SmartElementFinder(self.browser).click_text(text, tag=data.get("tag"), timeout=data.get("timeout", 5000))

    async def _cmd_smart_fill(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        label, value = data.get("label"), data.get("value")
        if not label or value is None:
            return {"status": "error", "error": "Missing 'label' or 'value'"}
        return await SmartElementFinder(self.browser).fill_text(label, value, timeout=data.get("timeout", 5000))

    # ─── Workflow ───────────────────────────────────────────

    async def _cmd_workflow(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        steps = data.get("steps")
        if not steps:
            return {"status": "error", "error": "Missing 'steps'"}
        return await WorkflowEngine(self.browser).execute(steps, variables=data.get("variables"), on_error=data.get("on_error", "abort"), retry_count=data.get("retry_count", 0), step_delay_ms=data.get("step_delay_ms", 0))

    async def _cmd_workflow_template(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        name = data.get("template_name")
        if not name:
            return {"status": "error", "error": "Missing 'template_name'"}
        return await WorkflowEngine(self.browser).execute_template(name, data.get("variables"))

    async def _cmd_workflow_json(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        j = data.get("json")
        if not j:
            return {"status": "error", "error": "Missing 'json'"}
        return await WorkflowEngine(self.browser).execute_from_json(j)

    async def _cmd_workflow_save(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        name, steps = data.get("name"), data.get("steps")
        if not name or not steps:
            return {"status": "error", "error": "Missing 'name' or 'steps'"}
        return WorkflowEngine(self.browser).save_template(name, steps, data.get("variables"), data.get("description", ""))

    async def _cmd_workflow_list(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        return {"status": "success", "templates": WorkflowEngine(self.browser).list_templates()}

    async def _cmd_workflow_status(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        wid = data.get("workflow_id")
        if not wid:
            return {"status": "error", "error": "Missing 'workflow_id'"}
        return WorkflowEngine(self.browser).get_status(wid)

    # ─── Network Capture ────────────────────────────────────

    async def _cmd_network_start(self, data: Dict, session) -> Dict:
        from src.tools.network_capture import NetworkCapture
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            self._network_capture = NetworkCapture(self.browser)
        return await self._network_capture.start_capture(page_id=data.get("page_id", "main"), url_pattern=data.get("url_pattern"), resource_types=data.get("resource_types"), methods=data.get("methods"), capture_body=data.get("capture_body", False))

    async def _cmd_network_stop(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.stop_capture(page_id=data.get("page_id", "main"))

    async def _cmd_network_get(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_captured(page_id=data.get("page_id", "main"), url_pattern=data.get("url_pattern"), resource_type=data.get("resource_type"), method=data.get("method"), status_code=data.get("status_code"), api_only=data.get("api_only", False), limit=data.get("limit", 100), offset=data.get("offset", 0))

    async def _cmd_network_apis(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_apis(page_id=data.get("page_id", "main"))

    async def _cmd_network_detail(self, data: Dict, session) -> Dict:
        rid = data.get("request_id")
        if not rid:
            return {"status": "error", "error": "Missing 'request_id'"}
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_request_detail(rid)

    async def _cmd_network_stats(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return self._network_capture.get_stats(page_id=data.get("page_id", "main"))

    async def _cmd_network_export(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        fmt = data.get("format", "json")
        if fmt == "har":
            return await self._network_capture.export_har(page_id=data.get("page_id", "main"), filename=data.get("filename"))
        return await self._network_capture.export_json(page_id=data.get("page_id", "main"), filename=data.get("filename"))

    async def _cmd_network_clear(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.clear(page_id=data.get("page_id", "main"))

    # ─── Page Analyzer ─────────────────────────────────────

    async def _cmd_page_summary(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).summarize(page_id=data.get("page_id", "main"))

    async def _cmd_page_tables(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).extract_tables(page_id=data.get("page_id", "main"))

    async def _cmd_page_structured(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).extract_structured_data(page_id=data.get("page_id", "main"))

    async def _cmd_page_emails(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).find_emails(page_id=data.get("page_id", "main"))

    async def _cmd_page_phones(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).find_phone_numbers(page_id=data.get("page_id", "main"))

    async def _cmd_page_accessibility(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).accessibility_check(page_id=data.get("page_id", "main"))

    async def _cmd_page_seo(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        return await PageAnalyzer(self.browser).seo_audit(page_id=data.get("page_id", "main"))

    # ─── Proxy ─────────────────────────────────────────────

    async def _cmd_set_proxy(self, data: Dict, session) -> Dict:
        url = data.get("proxy_url")
        if not url:
            return {"status": "error", "error": "Missing 'proxy_url'"}
        return await self.browser.set_proxy(url)

    async def _cmd_get_proxy(self, data: Dict, session) -> Dict:
        return await self.browser.get_proxy()

    # ─── Mobile Emulation ──────────────────────────────────

    async def _cmd_emulate_device(self, data: Dict, session) -> Dict:
        device = data.get("device")
        if not device:
            return {"status": "error", "error": "Missing 'device'"}
        return await self.browser.emulate_device(device)

    async def _cmd_list_devices(self, data: Dict, session) -> Dict:
        return await self.browser.list_devices()

    # ─── Session Save/Restore ──────────────────────────────

    async def _cmd_save_session(self, data: Dict, session) -> Dict:
        return await self.browser.save_session(data.get("name", "default"))

    async def _cmd_restore_session(self, data: Dict, session) -> Dict:
        return await self.browser.restore_session(data.get("name", "default"))

    async def _cmd_list_sessions(self, data: Dict, session) -> Dict:
        return await self.browser.list_sessions()

    async def _cmd_delete_session(self, data: Dict, session) -> Dict:
        name = data.get("name")
        if not name:
            return {"status": "error", "error": "Missing 'name'"}
        return await self.browser.delete_session(name)

    # ─── Smart Wait ────────────────────────────────────────

    async def _cmd_smart_wait(self, data: Dict, session) -> Dict:
        return await self._get_smart_wait().auto(selector=data.get("selector"), idle_ms=data.get("idle_ms", 500), dom_stable_ms=data.get("dom_stable_ms", 300), timeout_ms=data.get("timeout_ms", 30000), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_network(self, data: Dict, session) -> Dict:
        return await self._get_smart_wait().network_idle(idle_ms=data.get("idle_ms", 500), timeout_ms=data.get("timeout_ms", 30000), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_dom(self, data: Dict, session) -> Dict:
        return await self._get_smart_wait().dom_stable(stability_ms=data.get("stability_ms", 300), timeout_ms=data.get("timeout_ms", 15000), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_element(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_smart_wait().element_ready(selector=selector, timeout_ms=data.get("timeout_ms", 15000), require_interactable=data.get("require_interactable", True), wait_for_animation=data.get("wait_for_animation", True), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_page(self, data: Dict, session) -> Dict:
        return await self._get_smart_wait().page_ready(timeout_ms=data.get("timeout_ms", 30000), require_images=data.get("require_images", True), require_fonts=data.get("require_fonts", True), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_js(self, data: Dict, session) -> Dict:
        expr = data.get("expression")
        if not expr:
            return {"status": "error", "error": "Missing 'expression'"}
        return await self._get_smart_wait().js_condition(expression=expr, timeout_ms=data.get("timeout_ms", 10000), poll_ms=data.get("poll_ms"), page_id=data.get("page_id", "main"))

    async def _cmd_smart_wait_compose(self, data: Dict, session) -> Dict:
        conditions = data.get("conditions")
        if not conditions:
            return {"status": "error", "error": "Missing 'conditions'"}
        return await self._get_smart_wait().compose(conditions=conditions, mode=data.get("mode", "all"), timeout_ms=data.get("timeout_ms", 30000), page_id=data.get("page_id", "main"))

    # ─── Auto Heal ─────────────────────────────────────────

    async def _cmd_heal_click(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().click(selector=s, page_id=data.get("page_id", "main"), timeout_ms=data.get("timeout_ms", 5000))

    async def _cmd_heal_fill(self, data: Dict, session) -> Dict:
        s, v = data.get("selector"), data.get("value")
        if not s or v is None:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        return await self._get_auto_heal().fill(selector=s, value=v, page_id=data.get("page_id", "main"), timeout_ms=data.get("timeout_ms", 5000))

    async def _cmd_heal_wait(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().wait(selector=s, page_id=data.get("page_id", "main"), timeout_ms=data.get("timeout_ms", 10000))

    async def _cmd_heal_hover(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().hover(selector=s, page_id=data.get("page_id", "main"), timeout_ms=data.get("timeout_ms", 5000))

    async def _cmd_heal_double_click(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().double_click(selector=s, page_id=data.get("page_id", "main"), timeout_ms=data.get("timeout_ms", 5000))

    async def _cmd_heal_selector(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().heal_selector(broken_selector=s, page_id=data.get("page_id", "main"))

    async def _cmd_heal_fingerprint(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_heal().fingerprint(selector=s, page_id=data.get("page_id", "main"))

    async def _cmd_heal_fingerprint_page(self, data: Dict, session) -> Dict:
        return await self._get_auto_heal().fingerprint_page(page_id=data.get("page_id", "main"))

    async def _cmd_heal_stats(self, data: Dict, session) -> Dict:
        return self._get_auto_heal().get_stats()

    async def _cmd_heal_clear(self, data: Dict, session) -> Dict:
        self._get_auto_heal().clear_cache()
        return {"status": "success", "message": "Healing caches cleared"}

    # ─── Auto Retry ────────────────────────────────────────

    async def _cmd_retry_execute(self, data: Dict, session) -> Dict:
        command = data.get("inner_command") or data.get("command_payload", {}).get("command")
        if not command:
            return {"status": "error", "error": "Missing 'inner_command'"}
        payload = data.get("command_payload", data)
        payload["command"] = command
        async def action():
            return await self._execute_command(command, payload, session)
        return await self._get_auto_retry().execute(operation=command, action=action, params=payload, deduplicate=data.get("deduplicate", False))

    async def _cmd_retry_navigate(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await self._get_auto_retry().navigate(url=url, page_id=data.get("page_id", "main"), wait_until=data.get("wait_until", "domcontentloaded"))

    async def _cmd_retry_click(self, data: Dict, session) -> Dict:
        s = data.get("selector")
        if not s:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self._get_auto_retry().click(selector=s, page_id=data.get("page_id", "main"))

    async def _cmd_retry_fill(self, data: Dict, session) -> Dict:
        s, v = data.get("selector"), data.get("value")
        if not s or v is None:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        return await self._get_auto_retry().fill(selector=s, value=v, page_id=data.get("page_id", "main"))

    async def _cmd_retry_api_call(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return await self._get_auto_retry().api_call(url=url, method=data.get("method", "GET"), headers=data.get("headers"), body=data.get("body"))

    async def _cmd_retry_stats(self, data: Dict, session) -> Dict:
        return self._get_auto_retry().get_stats()

    async def _cmd_retry_health(self, data: Dict, session) -> Dict:
        return self._get_auto_retry().get_health()

    async def _cmd_retry_circuit_breakers(self, data: Dict, session) -> Dict:
        return {"status": "success", "circuit_breakers": self._get_auto_retry().get_circuit_breakers()}

    async def _cmd_retry_reset_circuit(self, data: Dict, session) -> Dict:
        op = data.get("operation")
        if not op:
            return {"status": "error", "error": "Missing 'operation'"}
        return self._get_auto_retry().reset_circuit_breaker(op)

    async def _cmd_retry_reset_all_circuits(self, data: Dict, session) -> Dict:
        return self._get_auto_retry().reset_all_circuit_breakers()

    # ─── Session Recording ─────────────────────────────────

    async def _cmd_record_start(self, data: Dict, session) -> Dict:
        return await self._get_recorder().start(name=data.get("name"), screenshot_interval_ms=data.get("screenshot_interval_ms", 2000), screenshot_on_event=data.get("screenshot_on_event", True), capture_network=data.get("capture_network", True), capture_console=data.get("capture_console", True), capture_dom=data.get("capture_dom", True), capture_scroll=data.get("capture_scroll", True), capture_cookies=data.get("capture_cookies", True), tags=data.get("tags"), page_id=data.get("page_id", "main"))

    async def _cmd_record_stop(self, data: Dict, session) -> Dict:
        return await self._get_recorder().stop(save=data.get("save", True))

    async def _cmd_record_pause(self, data: Dict, session) -> Dict:
        return await self._get_recorder().pause()

    async def _cmd_record_resume(self, data: Dict, session) -> Dict:
        return await self._get_recorder().resume()

    async def _cmd_record_annotate(self, data: Dict, session) -> Dict:
        text = data.get("text")
        if not text:
            return {"status": "error", "error": "Missing 'text'"}
        return await self._get_recorder().annotate(text=text, category=data.get("category", "note"), page_id=data.get("page_id", "main"))

    async def _cmd_record_status(self, data: Dict, session) -> Dict:
        rec = self._get_recorder()
        if not rec.is_recording():
            return {"status": "not_recording"}
        r = rec.get_recording()
        return {"status": "recording", "recording_id": r.recording_id if r else None, "name": r.name if r else None, "event_count": len(r.events) if r else 0}

    async def _cmd_record_list(self, data: Dict, session) -> Dict:
        from src.tools.session_recording import SessionRecorder
        return {"status": "success", "recordings": SessionRecorder.list_recordings()}

    async def _cmd_record_delete(self, data: Dict, session) -> Dict:
        rid = data.get("recording_id")
        if not rid:
            return {"status": "error", "error": "Missing 'recording_id'"}
        from src.tools.session_recording import SessionRecorder
        return {"status": "success", "deleted": SessionRecorder.delete_recording(rid)}

    # ─── Replay ────────────────────────────────────────────

    async def _cmd_replay_load(self, data: Dict, session) -> Dict:
        rid = data.get("recording_id")
        if not rid:
            return {"status": "error", "error": "Missing 'recording_id'"}
        return await self._get_replay().load(rid)

    async def _cmd_replay_play(self, data: Dict, session) -> Dict:
        return await self._get_replay().play(speed=data.get("speed", 1.0), from_event=data.get("from_event", 0), to_event=data.get("to_event"), skip_types=data.get("skip_types"), verify_screenshots=data.get("verify_screenshots", False))

    async def _cmd_replay_stop(self, data: Dict, session) -> Dict:
        return await self._get_replay().stop()

    async def _cmd_replay_pause(self, data: Dict, session) -> Dict:
        return await self._get_replay().pause()

    async def _cmd_replay_resume(self, data: Dict, session) -> Dict:
        return await self._get_replay().resume()

    async def _cmd_replay_step(self, data: Dict, session) -> Dict:
        return await self._get_replay().step()

    async def _cmd_replay_jump(self, data: Dict, session) -> Dict:
        return await self._get_replay().jump_to(event_index=data.get("event_index"), elapsed_ms=data.get("elapsed_ms"))

    async def _cmd_replay_position(self, data: Dict, session) -> Dict:
        return self._get_replay().get_position()

    async def _cmd_replay_events(self, data: Dict, session) -> Dict:
        return self._get_replay().get_event_list(offset=data.get("offset", 0), limit=data.get("limit", 50), event_type=data.get("event_type"))

    async def _cmd_replay_export_workflow(self, data: Dict, session) -> Dict:
        return await self._get_replay().export_as_workflow(include_navigations=data.get("include_navigations", True))

    async def _cmd_analyze(self, data: Dict, session) -> Dict:
        rid = data.get("recording_id")
        if not rid:
            return {"status": "error", "error": "Missing 'recording_id'"}
        return self._get_analyzer().analyze(rid)

    async def _cmd_analyze_search(self, data: Dict, session) -> Dict:
        rid = data.get("recording_id")
        if not rid:
            return {"status": "error", "error": "Missing 'recording_id'"}
        return self._get_analyzer().search(rid, event_type=data.get("event_type"), query=data.get("query"), from_ms=data.get("from_ms"), to_ms=data.get("to_ms"), limit=data.get("limit", 100))

    # ─── Multi-Agent Hub ───────────────────────────────────

    async def _cmd_hub_register(self, data: Dict, session) -> Dict:
        return await self._get_agent_hub().register_agent(agent_id=data.get("agent_id"), name=data.get("name"), role=data.get("role", "operator"), capabilities=data.get("capabilities"), metadata=data.get("metadata"))

    async def _cmd_hub_unregister(self, data: Dict, session) -> Dict:
        aid = data.get("agent_id")
        if not aid:
            return {"status": "error", "error": "Missing 'agent_id'"}
        return await self._get_agent_hub().unregister_agent(aid)

    async def _cmd_hub_heartbeat(self, data: Dict, session) -> Dict:
        aid = data.get("agent_id")
        if not aid:
            return {"status": "error", "error": "Missing 'agent_id'"}
        return await self._get_agent_hub().heartbeat(aid)

    async def _cmd_hub_status(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().get_status()

    async def _cmd_hub_agents(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().get_agents(alive_only=data.get("alive_only", True))

    async def _cmd_hub_lock(self, data: Dict, session) -> Dict:
        aid, res = data.get("agent_id"), data.get("resource")
        if not aid or not res:
            return {"status": "error", "error": "Missing 'agent_id' or 'resource'"}
        return await self._get_agent_hub().acquire_lock(agent_id=aid, resource=res, lock_type=data.get("lock_type", "exclusive"), ttl_seconds=data.get("ttl_seconds"), timeout_ms=data.get("timeout_ms", 5000))

    async def _cmd_hub_unlock(self, data: Dict, session) -> Dict:
        aid, lid = data.get("agent_id"), data.get("lock_id")
        if not aid or not lid:
            return {"status": "error", "error": "Missing 'agent_id' or 'lock_id'"}
        return await self._get_agent_hub().release_lock(aid, lid)

    async def _cmd_hub_locks(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().get_locks(resource=data.get("resource"), agent_id=data.get("agent_id"))

    async def _cmd_hub_task_create(self, data: Dict, session) -> Dict:
        title = data.get("title")
        if not title:
            return {"status": "error", "error": "Missing 'title'"}
        return await self._get_agent_hub().create_task(title=title, description=data.get("description", ""), assigned_to=data.get("assigned_to"), assigned_by=data.get("assigned_by"), priority=data.get("priority", 0), tags=data.get("tags"), dependencies=data.get("dependencies"), max_retries=data.get("max_retries", 0))

    async def _cmd_hub_task_claim(self, data: Dict, session) -> Dict:
        aid = data.get("agent_id")
        if not aid:
            return {"status": "error", "error": "Missing 'agent_id'"}
        return await self._get_agent_hub().claim_task(aid, task_id=data.get("task_id"), tags=data.get("tags"))

    async def _cmd_hub_task_start(self, data: Dict, session) -> Dict:
        aid, tid = data.get("agent_id"), data.get("task_id")
        if not aid or not tid:
            return {"status": "error", "error": "Missing 'agent_id' or 'task_id'"}
        return await self._get_agent_hub().start_task(aid, tid)

    async def _cmd_hub_task_complete(self, data: Dict, session) -> Dict:
        aid, tid = data.get("agent_id"), data.get("task_id")
        if not aid or not tid:
            return {"status": "error", "error": "Missing 'agent_id' or 'task_id'"}
        return await self._get_agent_hub().complete_task(aid, tid, result=data.get("result"))

    async def _cmd_hub_task_fail(self, data: Dict, session) -> Dict:
        aid, tid = data.get("agent_id"), data.get("task_id")
        if not aid or not tid:
            return {"status": "error", "error": "Missing 'agent_id' or 'task_id'"}
        return await self._get_agent_hub().fail_task(aid, tid, error=data.get("error", ""))

    async def _cmd_hub_task_cancel(self, data: Dict, session) -> Dict:
        tid = data.get("task_id")
        if not tid:
            return {"status": "error", "error": "Missing 'task_id'"}
        return await self._get_agent_hub().cancel_task(tid, cancelled_by=data.get("cancelled_by"))

    async def _cmd_hub_tasks(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().get_tasks(status=data.get("status"), assigned_to=data.get("assigned_to"), tags=data.get("tags"), limit=data.get("limit", 50))

    async def _cmd_hub_broadcast(self, data: Dict, session) -> Dict:
        sid, topic = data.get("sender_id"), data.get("topic")
        if not sid or not topic:
            return {"status": "error", "error": "Missing 'sender_id' or 'topic'"}
        return await self._get_agent_hub().broadcast(sender_id=sid, topic=topic, payload=data.get("payload", {}), ttl_seconds=data.get("ttl_seconds"))

    async def _cmd_hub_events(self, data: Dict, session) -> Dict:
        aid = data.get("agent_id")
        if not aid:
            return {"status": "error", "error": "Missing 'agent_id'"}
        return self._get_agent_hub().get_events(agent_id=aid, topic=data.get("topic"), since_seconds=data.get("since_seconds"), limit=data.get("limit", 50))

    async def _cmd_hub_memory_set(self, data: Dict, session) -> Dict:
        aid, key = data.get("agent_id"), data.get("key")
        if not aid or not key:
            return {"status": "error", "error": "Missing 'agent_id' or 'key'"}
        return await self._get_agent_hub().memory_set(agent_id=aid, key=key, value=data.get("value"), ttl_seconds=data.get("ttl_seconds", 0), access=data.get("access", "shared"))

    async def _cmd_hub_memory_get(self, data: Dict, session) -> Dict:
        aid, key = data.get("agent_id"), data.get("key")
        if not aid or not key:
            return {"status": "error", "error": "Missing 'agent_id' or 'key'"}
        return await self._get_agent_hub().memory_get(aid, key)

    async def _cmd_hub_memory_delete(self, data: Dict, session) -> Dict:
        aid, key = data.get("agent_id"), data.get("key")
        if not aid or not key:
            return {"status": "error", "error": "Missing 'agent_id' or 'key'"}
        return await self._get_agent_hub().memory_delete(aid, key)

    async def _cmd_hub_memory_list(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().memory_list(prefix=data.get("prefix"), agent_id=data.get("agent_id"))

    async def _cmd_hub_handoff(self, data: Dict, session) -> Dict:
        fid, tid = data.get("from_agent_id"), data.get("to_agent_id")
        if not fid or not tid:
            return {"status": "error", "error": "Missing 'from_agent_id' or 'to_agent_id'"}
        return await self._get_agent_hub().handoff(from_agent_id=fid, to_agent_id=tid, resource=data.get("resource", "page:main"), context=data.get("context"))

    async def _cmd_hub_audit(self, data: Dict, session) -> Dict:
        return self._get_agent_hub().get_audit(agent_id=data.get("agent_id"), action=data.get("action"), since_seconds=data.get("since_seconds"), limit=data.get("limit", 100))

    # ─── Proxy Rotation ────────────────────────────────────

    async def _cmd_proxy_add(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        return self._get_proxy_manager().add_proxy(url=url, country=data.get("country", ""), region=data.get("region", ""), tags=data.get("tags", []), weight=data.get("weight", 1.0), max_requests_per_minute=data.get("max_requests_per_minute", 0))

    async def _cmd_proxy_remove(self, data: Dict, session) -> Dict:
        pid = data.get("proxy_id")
        if not pid:
            return {"status": "error", "error": "Missing 'proxy_id'"}
        return self._get_proxy_manager().remove_proxy(pid)

    async def _cmd_proxy_load_file(self, data: Dict, session) -> Dict:
        fp = data.get("filepath")
        if not fp:
            return {"status": "error", "error": "Missing 'filepath'"}
        return self._get_proxy_manager().load_proxies(fp, proxy_type=data.get("proxy_type", "http"))

    async def _cmd_proxy_load_api(self, data: Dict, session) -> Dict:
        api_url = data.get("api_url")
        if not api_url:
            return {"status": "error", "error": "Missing 'api_url'"}
        return await self._get_proxy_manager().load_from_api(api_url, api_key=data.get("api_key"))

    async def _cmd_proxy_get(self, data: Dict, session) -> Dict:
        return await self._get_proxy_manager().get_proxy(domain=data.get("domain"), session_id=data.get("session_id"), country=data.get("country"), tags=data.get("tags"), with_failover=data.get("with_failover", True))

    async def _cmd_proxy_record(self, data: Dict, session) -> Dict:
        pid = data.get("proxy_id")
        if not pid:
            return {"status": "error", "error": "Missing 'proxy_id'"}
        return self._get_proxy_manager().record_result(proxy_id=pid, success=data.get("success", True), latency_ms=data.get("latency_ms", 0), status_code=data.get("status_code", 0), error=data.get("error", ""))

    async def _cmd_proxy_check(self, data: Dict, session) -> Dict:
        pid = data.get("proxy_id")
        if not pid:
            return {"status": "error", "error": "Missing 'proxy_id'"}
        return await self._get_proxy_manager().check_proxy(pid)

    async def _cmd_proxy_check_all(self, data: Dict, session) -> Dict:
        return await self._get_proxy_manager().check_all()

    async def _cmd_proxy_list(self, data: Dict, session) -> Dict:
        return self._get_proxy_manager().list_proxies(status=data.get("status"), country=data.get("country"))

    async def _cmd_proxy_enable(self, data: Dict, session) -> Dict:
        pid = data.get("proxy_id")
        if not pid:
            return {"status": "error", "error": "Missing 'proxy_id'"}
        return self._get_proxy_manager().enable_proxy(pid)

    async def _cmd_proxy_disable(self, data: Dict, session) -> Dict:
        pid = data.get("proxy_id")
        if not pid:
            return {"status": "error", "error": "Missing 'proxy_id'"}
        return self._get_proxy_manager().disable_proxy(pid)

    async def _cmd_proxy_strategy(self, data: Dict, session) -> Dict:
        strategy = data.get("strategy")
        if not strategy:
            return {"status": "error", "error": "Missing 'strategy'"}
        return self._get_proxy_manager().set_strategy(strategy)

    async def _cmd_proxy_stats(self, data: Dict, session) -> Dict:
        return self._get_proxy_manager().get_stats()

    async def _cmd_proxy_save(self, data: Dict, session) -> Dict:
        return self._get_proxy_manager().save(filename=data.get("filename", "proxies.json"))

    async def _cmd_proxy_load(self, data: Dict, session) -> Dict:
        return self._get_proxy_manager().load(filename=data.get("filename", "proxies.json"))

    # ─── Command Definitions (for /commands endpoint) ──────

    def _get_command_definitions(self) -> dict:
        """Return command definitions. Kept as dict for /commands endpoint."""
        return {
            "navigate": {"params": {"url": "string"}, "description": "Navigate to a URL"},
            "click": {"params": {"selector": "string"}, "description": "Click an element"},
            "type": {"params": {"text": "string"}, "description": "Type text into focused element"},
            "screenshot": {"params": {"full_page": "bool"}, "description": "Take a screenshot"},
            "get-content": {"params": {}, "description": "Get page HTML and text"},
            "get-dom": {"params": {}, "description": "Get structured DOM snapshot"},
            "fill-form": {"params": {"fields": "dict"}, "description": "Fill form fields"},
            "scroll": {"params": {"direction": "up|down", "amount": "int"}, "description": "Scroll the page"},
            "smart-click": {"params": {"text": "string"}, "description": "Click element by visible text"},
            "workflow": {"params": {"steps": "list"}, "description": "Execute multi-step workflow"},
            "tabs": {"params": {"action": "list|new|close|switch"}, "description": "Manage browser tabs"},
        }
