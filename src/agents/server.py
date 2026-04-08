"""
Agent-OS Agent Server
WebSocket + REST API for any AI agent to connect and control the browser.
"""
import asyncio
import json
import logging
import time
import ssl
from typing import Dict, Optional, Any
from collections import defaultdict
from aiohttp import web

import websockets

logger = logging.getLogger("agent-os.server")


class RateLimiter:
    """Simple token-bucket rate limiter per IP."""

    def __init__(self, rps: int = 20, burst: int = 40):
        self.rps = rps
        self.burst = burst
        self._buckets: Dict[str, Dict] = defaultdict(lambda: {"tokens": burst, "last": time.time()})

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rps)
        bucket["last"] = now
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False


class AgentServer:
    """
    Dual-protocol agent server:
    - WebSocket (port 8000): For real-time agent communication
    - HTTP REST (port 8001): For curl/simple integrations
    """

    def __init__(self, config, browser, session_manager):
        self.config = config
        self.browser = browser
        self.session_manager = session_manager
        self._ws_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._ws_server = None
        self._http_app = None
        self._http_runner = None
        self._start_time = time.time()
        self._max_connections = config.get("server.max_connections", 10)
        self._rate_limiter = RateLimiter(
            rps=config.get("server.rate_limit_rps", 20),
            burst=config.get("server.rate_limit_burst", 40),
        )

    def _get_cors_origins(self):
        """Get allowed CORS origins from config."""
        return self.config.get("server.cors_origins", ["http://localhost:*"])

    def _cors_headers(self, request: web.Request) -> dict:
        """Generate CORS headers based on config."""
        origin = request.headers.get("Origin", "")
        allowed = self._get_cors_origins()
        # Simple wildcard matching
        for pattern in allowed:
            if pattern == "*" or origin.startswith(pattern.replace("*", "")):
                return {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Access-Control-Max-Age": "3600",
                }
        return {}

    def _check_auth(self, data: Dict) -> bool:
        """Validate agent token."""
        token = data.get("token", "")
        return self.config.validate_token(token)

    def _check_auth_header(self, request: web.Request) -> bool:
        """Validate auth from Authorization header or query param."""
        # Check Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            return self.config.validate_token(token)
        # Check query param
        token = request.query.get("token", "")
        if token:
            return self.config.validate_token(token)
        return False

    def _client_ip(self, request: web.Request) -> str:
        """Get client IP, respecting X-Forwarded-For."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.remote or "unknown"

    async def start(self):
        """Start both WebSocket and HTTP servers."""
        ws_host = self.config.get("server.host", "127.0.0.1")
        ws_port = self.config.get("server.ws_port", 8000)
        http_port = self.config.get("server.http_port", 8001)

        # Build SSL context if TLS configured
        ssl_context = None
        tls_cert = self.config.get("server.tls_cert", "")
        tls_key = self.config.get("server.tls_key", "")
        if tls_cert and tls_key:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(tls_cert, tls_key)
            logger.info("TLS enabled")

        # Start WebSocket server with connection limit
        ws_kwargs = {
            "ping_interval": 30,
            "ping_timeout": 10,
            "max_size": 10 * 1024 * 1024,  # 10MB max message
        }
        if ssl_context:
            ws_kwargs["ssl"] = ssl_context

        self._ws_server = await websockets.serve(
            self._ws_handler, ws_host, ws_port, **ws_kwargs
        )
        protocol = "wss" if ssl_context else "ws"
        logger.info(f"WebSocket server listening on {protocol}://{ws_host}:{ws_port}")

        # Start HTTP server
        self._http_app = web.Application(client_max_size=10 * 1024 * 1024)
        self._setup_routes()
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()

        if ssl_context:
            site = web.TCPSite(self._http_runner, ws_host, http_port, ssl_context=ssl_context)
        else:
            site = web.TCPSite(self._http_runner, ws_host, http_port)
        await site.start()
        protocol = "https" if ssl_context else "http"
        logger.info(f"HTTP server listening on {protocol}://{ws_host}:{http_port}")

    async def stop(self):
        """Stop both servers."""
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
        if self._http_runner:
            await self._http_runner.cleanup()
        logger.info("Agent servers stopped")

    def _setup_routes(self):
        """Setup HTTP routes."""
        self._http_app.router.add_post("/command", self._handle_command)
        self._http_app.router.add_get("/status", self._handle_status)
        self._http_app.router.add_get("/commands", self._handle_commands_list)
        self._http_app.router.add_options("/command", self._handle_cors_preflight)
        self._http_app.router.add_options("/status", self._handle_cors_preflight)

    async def _handle_cors_preflight(self, request: web.Request) -> web.Response:
        """Handle CORS preflight requests."""
        return web.Response(headers=self._cors_headers(request))

    async def _ws_handler(self, websocket, path):
        """Handle WebSocket connections from agents."""
        # Connection limit check
        if len(self._ws_clients) >= self._max_connections:
            await websocket.send(json.dumps({
                "status": "error",
                "error": f"Max connections ({self._max_connections}) reached. Try again later."
            }))
            await websocket.close(1013, "Too many connections")
            return

        client_id = f"ws-{id(websocket)}"
        self._ws_clients[client_id] = websocket
        logger.info(f"Agent connected via WebSocket: {client_id} ({len(self._ws_clients)}/{self._max_connections})")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    # Authenticate
                    if not self._check_auth(data):
                        await websocket.send(json.dumps({
                            "status": "error",
                            "error": "Invalid or missing token"
                        }))
                        continue

                    # Rate limit
                    client_ip = str(id(websocket))
                    if not self._rate_limiter.allow(client_ip):
                        await websocket.send(json.dumps({
                            "status": "error",
                            "error": "Rate limit exceeded. Slow down."
                        }))
                        continue

                    result = await self._process_command(data)
                    await websocket.send(json.dumps(result))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"status": "error", "error": "Invalid JSON"}))
                except Exception as e:
                    logger.error(f"WS error: {e}")
                    await websocket.send(json.dumps({"status": "error", "error": str(e)}))
        finally:
            del self._ws_clients[client_id]
            logger.info(f"Agent disconnected: {client_id}")

    async def _handle_command(self, request: web.Request) -> web.Response:
        """Handle HTTP POST /command."""
        cors = self._cors_headers(request)

        # Rate limit
        client_ip = self._client_ip(request)
        if not self._rate_limiter.allow(client_ip):
            return web.json_response(
                {"status": "error", "error": "Rate limit exceeded"},
                status=429,
                headers=cors,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"status": "error", "error": "Invalid JSON body"},
                status=400,
                headers=cors,
            )

        # Authenticate
        if not self._check_auth(data):
            return web.json_response(
                {"status": "error", "error": "Invalid or missing token"},
                status=401,
                headers=cors,
            )

        result = await self._process_command(data)
        return web.json_response(result, headers=cors)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /status."""
        cors = self._cors_headers(request)
        # Status endpoint requires auth too
        if not self._check_auth_header(request):
            return web.json_response(
                {"status": "error", "error": "Authentication required"},
                status=401,
                headers=cors,
            )
        return web.json_response({
            "status": "running",
            "uptime_seconds": int(time.time() - self._start_time),
            "active_sessions": len(self.session_manager.list_active_sessions()),
            "active_ws_clients": len(self._ws_clients),
            "browser_active": self.browser.browser is not None,
            "version": "2.1.0"
        }, headers=cors)

    async def _handle_commands_list(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /commands — list all available commands."""
        cors = self._cors_headers(request)
        # Commands list is public (needed for discovery), but include CORS
        commands = {
            "navigate": {"params": {"url": "string", "page_id": "string (optional)", "wait_until": "string (optional)"}, "description": "Navigate to a URL"},
            "fill-form": {"params": {"fields": {"selector": "value"}}, "description": "Fill form fields with human-like typing"},
            "click": {"params": {"selector": "string"}, "description": "Click an element (CSS selector)"},
            "type": {"params": {"text": "string"}, "description": "Type text into focused element"},
            "press": {"params": {"key": "string"}, "description": "Press a keyboard key (Enter, Tab, Escape, etc.)"},
            "screenshot": {"params": {"full_page": "bool (optional)"}, "description": "Take a screenshot (returns base64 PNG)"},
            "get-content": {"params": {}, "description": "Get current page HTML and text content"},
            "get-dom": {"params": {}, "description": "Get structured DOM snapshot"},
            "scroll": {"params": {"direction": "up|down", "amount": "int"}, "description": "Scroll the page"},
            "hover": {"params": {"selector": "string"}, "description": "Hover over an element"},
            "select": {"params": {"selector": "string", "value": "string"}, "description": "Select a dropdown option"},
            "upload": {"params": {"selector": "string", "file_path": "string"}, "description": "Upload a file"},
            "wait": {"params": {"selector": "string", "timeout": "int (ms)"}, "description": "Wait for an element to appear"},
            "evaluate-js": {"params": {"script": "string"}, "description": "Execute JavaScript in page context"},
            "back": {"params": {}, "description": "Go back in browser history"},
            "forward": {"params": {}, "description": "Go forward in browser history"},
            "reload": {"params": {}, "description": "Reload the current page"},
            "get-links": {"params": {}, "description": "Get all links on the current page"},
            "get-images": {"params": {}, "description": "Get all images on the current page"},
            "right-click": {"params": {"selector": "string"}, "description": "Right-click an element (opens context menu)"},
            "context-action": {"params": {"selector": "string", "action_text": "string"}, "description": "Right-click and select context menu option (copy, paste, inspect, etc.)"},
            "drag-drop": {"params": {"source": "string", "target": "string"}, "description": "Drag one element and drop on another"},
            "drag-offset": {"params": {"selector": "string", "x": "int", "y": "int"}, "description": "Drag element by pixel offset"},
            "double-click": {"params": {"selector": "string"}, "description": "Double-click an element"},
            "clear-input": {"params": {"selector": "string"}, "description": "Clear an input field"},
            "checkbox": {"params": {"selector": "string", "checked": "bool"}, "description": "Set checkbox state"},
            "get-text": {"params": {"selector": "string"}, "description": "Get text content of an element"},
            "get-attr": {"params": {"selector": "string", "attribute": "string"}, "description": "Get element attribute value"},
            "viewport": {"params": {"width": "int", "height": "int"}, "description": "Change browser viewport size"},
            "add-extension": {"params": {"extension_path": "string"}, "description": "Load a Chrome extension (headed mode only)"},
            "console-logs": {"params": {}, "description": "Get browser console logs"},
            "get-cookies": {"params": {}, "description": "Get all cookies"},
            "set-cookie": {"params": {"name": "string", "value": "string", "domain": "string (optional)"}, "description": "Set a cookie"},
            "scan-xss": {"params": {"url": "string"}, "description": "Scan URL for XSS vulnerabilities"},
            "scan-sqli": {"params": {"url": "string"}, "description": "Scan URL for SQL injection"},
            "scan-sensitive": {"params": {}, "description": "Scan page for sensitive data exposure"},
            "transcribe": {"params": {"url": "string", "language": "string (optional)"}, "description": "Transcribe video/audio from URL"},
            "save-creds": {"params": {"domain": "string", "username": "string", "password": "string"}, "description": "Save credentials for auto-login"},
            "auto-login": {"params": {"url": "string", "domain": "string"}, "description": "Auto-login using saved credentials"},
            "fill-job": {"params": {"url": "string", "profile": "dict"}, "description": "Auto-fill job application form"},
            "tabs": {"params": {"action": "list|new|close|switch", "tab_id": "string (optional)"}, "description": "Manage browser tabs"},
        }
        return web.json_response(commands, headers=cors)

    async def _process_command(self, data: Dict) -> Dict[str, Any]:
        """Process any agent command."""
        token = data.get("token")
        command = data.get("command", "").lower()

        if not token:
            return {"status": "error", "error": "Missing 'token'"}
        if not command:
            return {"status": "error", "error": "Missing 'command'"}

        # Get or create session
        session = self.session_manager.get_session_by_token(token)
        if not session:
            session = self.session_manager.create_session(token)

        session.commands_executed += 1

        try:
            result = await self._execute_command(command, data, session)
            result["session_id"] = session.session_id
            return result
        except Exception as e:
            logger.error(f"Command error: {e}")
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
        }

        handler = handlers.get(command)
        if not handler:
            return {"status": "error", "error": f"Unknown command: {command}. Available: {list(handlers.keys())}"}

        return await handler(data, session)

    # ─── Command Handlers ────────────────────────────────────

    async def _cmd_navigate(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        page_id = data.get("page_id", "main")
        wait_until = data.get("wait_until", "domcontentloaded")
        return await self.browser.navigate(url, page_id=page_id, wait_until=wait_until)

    async def _cmd_fill_form(self, data: Dict, session) -> Dict:
        fields = data.get("fields", {})
        if not fields:
            return {"status": "error", "error": "Missing 'fields' dictionary"}
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
        full_page = data.get("full_page", False)
        b64 = await self.browser.screenshot(full_page=full_page)
        return {"status": "success", "screenshot": b64, "format": "png"}

    async def _cmd_get_content(self, data: Dict, session) -> Dict:
        content = await self.browser.get_content()
        return {"status": "success", **content}

    async def _cmd_get_dom(self, data: Dict, session) -> Dict:
        dom = await self.browser.get_dom_snapshot()
        return {"status": "success", "dom_snapshot": dom}

    async def _cmd_scroll(self, data: Dict, session) -> Dict:
        direction = data.get("direction", "down")
        amount = data.get("amount", 500)
        return await self.browser.scroll(direction, amount)

    async def _cmd_hover(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.hover(selector)

    async def _cmd_select(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        value = data.get("value")
        if not selector or not value:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        return await self.browser.select_option(selector, value)

    async def _cmd_upload(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        file_path = data.get("file_path")
        if not selector or not file_path:
            return {"status": "error", "error": "Missing 'selector' or 'file_path'"}
        return await self.browser.upload_file(selector, file_path)

    async def _cmd_wait(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        timeout = data.get("timeout", 10000)
        return await self.browser.wait_for_element(selector, timeout=timeout)

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
        selector = data.get("selector")
        action_text = data.get("action_text")
        if not selector or not action_text:
            return {"status": "error", "error": "Missing 'selector' or 'action_text'"}
        return await self.browser.context_action(selector, action_text)

    async def _cmd_drag_drop(self, data: Dict, session) -> Dict:
        source = data.get("source")
        target = data.get("target")
        if not source or not target:
            return {"status": "error", "error": "Missing 'source' or 'target'"}
        return await self.browser.drag_and_drop(source, target)

    async def _cmd_drag_offset(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        x = data.get("x", 0)
        y = data.get("y", 0)
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.drag_by_offset(selector, x, y)

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
        checked = data.get("checked", True)
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.set_checkbox(selector, checked)

    async def _cmd_get_text(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        return await self.browser.get_element_text(selector)

    async def _cmd_get_attr(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        attribute = data.get("attribute")
        if not selector or not attribute:
            return {"status": "error", "error": "Missing 'selector' or 'attribute'"}
        return await self.browser.get_element_attribute(selector, attribute)

    async def _cmd_viewport(self, data: Dict, session) -> Dict:
        width = data.get("width", 1920)
        height = data.get("height", 1080)
        return await self.browser.set_viewport(width, height)

    async def _cmd_add_extension(self, data: Dict, session) -> Dict:
        path = data.get("extension_path")
        if not path:
            return {"status": "error", "error": "Missing 'extension_path'"}
        return await self.browser.add_extension(path)

    async def _cmd_console_logs(self, data: Dict, session) -> Dict:
        logs = await self.browser.get_console_logs()
        return {"status": "success", "logs": logs, "count": len(logs)}

    async def _cmd_get_cookies(self, data: Dict, session) -> Dict:
        return await self.browser.get_cookies()

    async def _cmd_set_cookie(self, data: Dict, session) -> Dict:
        name = data.get("name")
        value = data.get("value")
        domain = data.get("domain")
        if not name or not value:
            return {"status": "error", "error": "Missing 'name' or 'value'"}
        return await self.browser.set_cookie(name, value, domain)

    async def _cmd_scan_xss(self, data: Dict, session) -> Dict:
        from src.tools.scanner import XSSScanner
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        scanner = XSSScanner(self.browser)
        return await scanner.scan(url)

    async def _cmd_scan_sqli(self, data: Dict, session) -> Dict:
        from src.tools.scanner import SQLiScanner
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        scanner = SQLiScanner(self.browser)
        return await scanner.scan(url)

    async def _cmd_scan_sensitive(self, data: Dict, session) -> Dict:
        from src.tools.scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner()
        return await scanner.scan_page(self.browser)

    async def _cmd_transcribe(self, data: Dict, session) -> Dict:
        from src.tools.transcriber import Transcriber
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        transcriber = Transcriber(self.config)
        return await transcriber.transcribe_from_url(url, data.get("language", "auto"))

    async def _cmd_auto_login(self, data: Dict, session) -> Dict:
        from src.security.auth_handler import AuthHandler
        auth = AuthHandler(self.config)
        url = data.get("url")
        domain = data.get("domain")
        if not url or not domain:
            return {"status": "error", "error": "Missing 'url' or 'domain'"}
        return await auth.auto_login(self.browser, url, domain)

    async def _cmd_save_creds(self, data: Dict, session) -> Dict:
        from src.security.auth_handler import AuthHandler
        auth = AuthHandler(self.config)
        domain = data.get("domain")
        if not domain:
            return {"status": "error", "error": "Missing 'domain'"}
        auth.save_credentials(domain, {
            "username": data.get("username", ""),
            "password": data.get("password", ""),
        })
        return {"status": "success", "message": f"Credentials saved for {domain}"}

    async def _cmd_fill_job(self, data: Dict, session) -> Dict:
        from src.tools.form_filler import FormFiller
        url = data.get("url")
        profile = data.get("profile", {})
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        filler = FormFiller(self.browser)
        return await filler.fill_job_application(url, profile)

    async def _cmd_tabs(self, data: Dict, session) -> Dict:
        action = data.get("action", "list")
        tab_id = data.get("tab_id")

        if action == "list":
            return {"status": "success", "tabs": list(self.browser._pages.keys())}
        elif action == "new":
            tid = tab_id or f"tab-{len(self.browser._pages)}"
            await self.browser.new_tab(tid)
            return {"status": "success", "tab_id": tid}
        elif action == "switch":
            if tab_id:
                return await self.browser.switch_tab(tab_id)
            return {"status": "error", "error": "Missing 'tab_id' for switch"}
        elif action == "close":
            if tab_id:
                closed = await self.browser.close_tab(tab_id)
                return {"status": "success" if closed else "error", "closed": closed}
            return {"status": "error", "error": "Missing 'tab_id' for close"}
        return {"status": "error", "error": f"Unknown tab action: {action}"}
