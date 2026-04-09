"""
Agent-OS Agent Server
WebSocket + REST API for any AI agent to connect and control the browser.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any
from aiohttp import web

import websockets

logger = logging.getLogger("agent-os.server")


class AgentServer:
    """
    Dual-protocol agent server:
    - WebSocket (port 8000): For real-time agent communication
    - HTTP REST (port 8001): For curl/simple integrations
    """

    def __init__(self, config, browser, session_manager, persistent_manager=None):
        self.config = config
        self.browser = browser
        self.session_manager = session_manager
        self.persistent_manager = persistent_manager
        self._ws_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self._ws_server = None
        self._http_app = None
        self._http_runner = None
        self._start_time = time.time()

        # Smart Wait + Auto Heal + Auto Retry engines (lazy init)
        self._smart_wait = None
        self._auto_heal = None
        self._auto_retry = None

    async def start(self):
        """Start both WebSocket and HTTP servers."""
        ws_host = self.config.get("server.host", "127.0.0.1")
        ws_port = self.config.get("server.ws_port", 8000)
        http_port = self.config.get("server.http_port", 8001)

        # Start WebSocket server
        self._ws_server = await websockets.serve(
            self._ws_handler, ws_host, ws_port,
            ping_interval=30, ping_timeout=10
        )
        logger.info(f"WebSocket server listening on ws://{ws_host}:{ws_port}")

        # Start HTTP server
        self._http_app = web.Application()
        self._setup_routes()
        self._http_runner = web.AppRunner(self._http_app)
        await self._http_runner.setup()
        site = web.TCPSite(self._http_runner, ws_host, http_port)
        await site.start()
        logger.info(f"HTTP server listening on http://{ws_host}:{http_port}")

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
        self._http_app.router.add_get("/debug", self._handle_debug)
        self._http_app.router.add_get("/screenshot", self._handle_screenshot)

        # Persistent browser routes (if enabled)
        if self.persistent_manager:
            self._http_app.router.add_get("/persistent/health", self._handle_persistent_health)
            self._http_app.router.add_get("/persistent/users", self._handle_persistent_users)
            self._http_app.router.add_post("/persistent/command", self._handle_persistent_command)

    async def _ws_handler(self, websocket, path):
        """Handle WebSocket connections from agents."""
        client_id = f"ws-{id(websocket)}"
        self._ws_clients[client_id] = websocket
        logger.info(f"Agent connected via WebSocket: {client_id}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
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
        try:
            data = await request.json()
            result = await self._process_command(data)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=400)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /status."""
        status = {
            "status": "running",
            "uptime_seconds": int(time.time() - self._start_time),
            "active_sessions": len(self.session_manager.list_active_sessions()),
            "active_ws_clients": len(self._ws_clients),
            "browser_active": self.browser.browser is not None,
            "persistent_browser_enabled": self.persistent_manager is not None,
            "version": "2.0.0"
        }
        if self.persistent_manager:
            ph = self.persistent_manager.get_health()
            status["persistent_browser"] = ph["summary"]
        return web.json_response(status)

    async def _handle_commands_list(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /commands — list all available commands."""
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
            "console-logs": {"params": {"page_id": "string (optional)", "clear": "bool (optional)"}, "description": "Get browser console logs (log, warn, error, pageerror)"},
            "get-cookies": {"params": {}, "description": "Get all cookies"},
            "set-cookie": {"params": {"name": "string", "value": "string", "domain": "string (optional, auto-inferred)", "path": "string (default /)", "secure": "bool (auto-detected)", "http_only": "bool", "same_site": "Strict|Lax|None"}, "description": "Set a cookie with full control"},
            "scan-xss": {"params": {"url": "string"}, "description": "Scan URL for XSS vulnerabilities"},
            "scan-sqli": {"params": {"url": "string"}, "description": "Scan URL for SQL injection"},
            "scan-sensitive": {"params": {}, "description": "Scan page for sensitive data exposure"},
            "transcribe": {"params": {"url": "string", "language": "string (optional)"}, "description": "Transcribe video/audio from URL"},
            "save-creds": {"params": {"domain": "string", "username": "string", "password": "string"}, "description": "Save credentials for auto-login"},
            "auto-login": {"params": {"url": "string", "domain": "string"}, "description": "Auto-login using saved credentials"},
            "fill-job": {"params": {"url": "string", "profile": "dict"}, "description": "Auto-fill job application form"},
            "tabs": {"params": {"action": "list|new|close|switch", "tab_id": "string (optional)"}, "description": "Manage browser tabs"},

            # Smart Element Finder
            "smart-find": {"params": {"description": "string", "tag": "string (optional)", "timeout": "int (ms)"}, "description": "Find element by visible text/label — no CSS selector needed"},
            "smart-find-all": {"params": {"description": "string", "tag": "string (optional)"}, "description": "Find ALL matching elements by text, ranked by relevance"},
            "smart-click": {"params": {"text": "string", "tag": "string (optional)", "timeout": "int (ms)"}, "description": "Click element by its visible text"},
            "smart-fill": {"params": {"label": "string", "value": "string", "timeout": "int (ms)"}, "description": "Find input by label/placeholder and fill it"},

            # Workflow Engine
            "workflow": {"params": {"steps": "list[dict]", "variables": "dict (optional)", "on_error": "abort|skip|retry", "retry_count": "int", "step_delay_ms": "int"}, "description": "Execute multi-step workflow"},
            "workflow-template": {"params": {"template_name": "string", "variables": "dict (optional)"}, "description": "Execute a saved workflow template"},
            "workflow-json": {"params": {"json": "string"}, "description": "Execute workflow from JSON string"},
            "workflow-save": {"params": {"name": "string", "steps": "list[dict]", "variables": "dict (optional)", "description": "string"}, "description": "Save workflow as reusable template"},
            "workflow-list": {"params": {}, "description": "List all workflow templates"},
            "workflow-status": {"params": {"workflow_id": "string"}, "description": "Get status of running workflow"},

            # Network Capture
            "network-start": {"params": {"page_id": "string (optional)", "url_pattern": "string (regex, optional)", "resource_types": "list (optional)", "methods": "list (optional)", "capture_body": "bool"}, "description": "Start capturing network requests"},
            "network-stop": {"params": {"page_id": "string (optional)"}, "description": "Stop capturing and get summary"},
            "network-get": {"params": {"page_id": "string (optional)", "url_pattern": "string", "resource_type": "string", "method": "string", "status_code": "int", "api_only": "bool", "limit": "int", "offset": "int"}, "description": "Get captured requests with filters"},
            "network-apis": {"params": {"page_id": "string (optional)"}, "description": "Discover all API endpoints from captured traffic"},
            "network-detail": {"params": {"request_id": "string"}, "description": "Get full details of a captured request"},
            "network-stats": {"params": {"page_id": "string (optional)"}, "description": "Get network capture statistics"},
            "network-export": {"params": {"page_id": "string (optional)", "format": "json|har", "filename": "string (optional)"}, "description": "Export captured requests to file"},
            "network-clear": {"params": {"page_id": "string (optional)"}, "description": "Clear captured requests"},

            # Page Analyzer
            "page-summary": {"params": {"page_id": "string (optional)"}, "description": "Analyze page: title, headings, content, forms, links, tech stack"},
            "page-tables": {"params": {"page_id": "string (optional)"}, "description": "Extract all tables as structured data"},
            "page-structured": {"params": {"page_id": "string (optional)"}, "description": "Extract JSON-LD and Microdata structured data"},
            "page-emails": {"params": {"page_id": "string (optional)"}, "description": "Find all email addresses on page"},
            "page-phones": {"params": {"page_id": "string (optional)"}, "description": "Find all phone numbers on page"},
            "page-accessibility": {"params": {"page_id": "string (optional)"}, "description": "Basic accessibility audit"},
            "page-seo": {"params": {"page_id": "string (optional)"}, "description": "Basic SEO audit with score"},

            # Proxy Support
            "set-proxy": {"params": {"proxy_url": "string"}, "description": "Set proxy (http://user:pass@host:port or socks5://host:port)"},
            "get-proxy": {"params": {}, "description": "Get current proxy configuration"},

            # Mobile Emulation
            "emulate-device": {"params": {"device": "string"}, "description": "Emulate mobile/tablet/desktop device"},
            "list-devices": {"params": {}, "description": "List all available device presets"},

            # Session Save/Restore
            "save-session": {"params": {"name": "string (optional)"}, "description": "Save full browser state (cookies, localStorage, tabs)"},
            "restore-session": {"params": {"name": "string (optional)"}, "description": "Restore previously saved browser state"},
            "list-sessions": {"params": {}, "description": "List all saved sessions"},
            "delete-session": {"params": {"name": "string"}, "description": "Delete a saved session"},

            # Smart Wait Engine
            "smart-wait": {"params": {"selector": "string (optional)", "idle_ms": "int (default 500)", "dom_stable_ms": "int (default 300)", "timeout_ms": "int (default 30000)", "page_id": "string (optional)"}, "description": "Auto smart wait — combines page_ready + network_idle + dom_stable + optional element_ready"},
            "smart-wait-network": {"params": {"idle_ms": "int (default 500)", "timeout_ms": "int (default 30000)", "page_id": "string (optional)"}, "description": "Wait for network to go idle (no in-flight requests for idle_ms)"},
            "smart-wait-dom": {"params": {"stability_ms": "int (default 300)", "timeout_ms": "int (default 15000)", "page_id": "string (optional)"}, "description": "Wait for DOM mutations to stop"},
            "smart-wait-element": {"params": {"selector": "string", "timeout_ms": "int (default 15000)", "require_interactable": "bool (default true)", "wait_for_animation": "bool (default true)", "page_id": "string (optional)"}, "description": "Wait for element to be visible, interactable, and not animating"},
            "smart-wait-page": {"params": {"timeout_ms": "int (default 30000)", "require_images": "bool (default true)", "require_fonts": "bool (default true)", "page_id": "string (optional)"}, "description": "Wait for page fully loaded (docs, images, fonts, frameworks)"},
            "smart-wait-js": {"params": {"expression": "string", "timeout_ms": "int (default 10000)", "poll_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Wait for JavaScript expression to become truthy"},
            "smart-wait-compose": {"params": {"conditions": "list[dict]", "mode": "all|any (default all)", "timeout_ms": "int (default 30000)", "page_id": "string (optional)"}, "description": "Wait for multiple conditions with AND/OR logic"},

            # Auto-Heal Engine
            "heal-click": {"params": {"selector": "string", "timeout_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Click with auto-heal — recovers if selector breaks"},
            "heal-fill": {"params": {"selector": "string", "value": "string", "timeout_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Fill form field with auto-heal"},
            "heal-wait": {"params": {"selector": "string", "timeout_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Wait for element with auto-heal"},
            "heal-hover": {"params": {"selector": "string", "timeout_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Hover with auto-heal"},
            "heal-double-click": {"params": {"selector": "string", "timeout_ms": "int (optional)", "page_id": "string (optional)"}, "description": "Double-click with auto-heal"},
            "heal-selector": {"params": {"selector": "string", "page_id": "string (optional)"}, "description": "Manually heal a broken selector"},
            "heal-fingerprint": {"params": {"selector": "string", "page_id": "string (optional)"}, "description": "Capture element fingerprint for future healing"},
            "heal-fingerprint-page": {"params": {"page_id": "string (optional)"}, "description": "Auto-fingerprint all interactive elements on the page"},
            "heal-stats": {"params": {}, "description": "Get auto-heal statistics and healing history"},
            "heal-clear": {"params": {}, "description": "Clear all healing caches"},

            # Auto-Retry Engine
            "retry-execute": {"params": {"inner_command": "string", "command_payload": "dict", "deduplicate": "bool (optional)"}, "description": "Execute any command with intelligent retry, error classification, circuit breaker, and budget"},
            "retry-navigate": {"params": {"url": "string", "page_id": "string (optional)", "wait_until": "string (optional)"}, "description": "Navigate with intelligent retry + smart_wait post-check"},
            "retry-click": {"params": {"selector": "string", "page_id": "string (optional)"}, "description": "Click with intelligent retry + auto-heal fallback"},
            "retry-fill": {"params": {"selector": "string", "value": "string", "page_id": "string (optional)"}, "description": "Fill form with intelligent retry + auto-heal fallback"},
            "retry-api-call": {"params": {"url": "string", "method": "string (default GET)", "headers": "dict (optional)", "body": "dict (optional)"}, "description": "API call with intelligent retry (respects Retry-After headers)"},
            "retry-stats": {"params": {}, "description": "Get comprehensive retry statistics (per-operation, per-error-class, history)"},
            "retry-health": {"params": {}, "description": "Quick health check — open circuits and budget status"},
            "retry-circuit-breakers": {"params": {}, "description": "Get state of all circuit breakers"},
            "retry-reset-circuit": {"params": {"operation": "string"}, "description": "Force-reset a specific circuit breaker"},
            "retry-reset-all-circuits": {"params": {}, "description": "Force-reset all circuit breakers"},
        }
        return web.json_response(commands)

    async def _handle_debug(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /debug."""
        return web.json_response({
            "sessions": self.session_manager.list_active_sessions(),
            "uptime": int(time.time() - self._start_time),
            "ws_clients": len(self._ws_clients),
            "blocked_requests": self.browser._blocked_requests,
            "tabs": list(self.browser._pages.keys()),
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
        """Handle HTTP GET /persistent/health."""
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        return web.json_response(self.persistent_manager.get_health())

    async def _handle_persistent_users(self, request: web.Request) -> web.Response:
        """Handle HTTP GET /persistent/users."""
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        return web.json_response({"users": self.persistent_manager.list_users()})

    async def _handle_persistent_command(self, request: web.Request) -> web.Response:
        """Handle HTTP POST /persistent/command."""
        if not self.persistent_manager:
            return web.json_response({"error": "Persistent browser not enabled"}, status=404)
        try:
            data = await request.json()
            token = data.get("token")
            user_id = data.get("user_id")
            command = data.get("command")

            if not token:
                return web.json_response({"status": "error", "error": "Missing 'token'"}, status=400)
            if not user_id:
                return web.json_response({"status": "error", "error": "Missing 'user_id'"}, status=400)
            if not command:
                return web.json_response({"status": "error", "error": "Missing 'command'"}, status=400)

            result = await self.persistent_manager.execute_for_user(user_id, command, data)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=400)

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
        }

        handler = handlers.get(command)
        if not handler:
            return {"status": "error", "error": f"Unknown command: {command}. Available: {list(handlers.keys())}"}

        return await handler(data, session)

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
        page_id = data.get("page_id", "main")
        clear = data.get("clear", False)
        return await self.browser.get_console_logs(page_id=page_id, clear=clear)

    async def _cmd_get_cookies(self, data: Dict, session) -> Dict:
        return await self.browser.get_cookies()

    async def _cmd_set_cookie(self, data: Dict, session) -> Dict:
        name = data.get("name")
        value = data.get("value")
        if not name or not value:
            return {"status": "error", "error": "Missing 'name' or 'value'"}
        return await self.browser.set_cookie(
            name=name,
            value=value,
            domain=data.get("domain"),
            path=data.get("path", "/"),
            secure=data.get("secure"),
            http_only=data.get("http_only", False),
            same_site=data.get("same_site"),
        )

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

    # ─── Smart Element Finder ───────────────────────────────

    async def _cmd_smart_find(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        description = data.get("description")
        if not description:
            return {"status": "error", "error": "Missing 'description'"}
        finder = SmartElementFinder(self.browser)
        return await finder.find(
            description,
            tag=data.get("tag"),
            timeout=data.get("timeout", 5000),
        )

    async def _cmd_smart_find_all(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        description = data.get("description")
        if not description:
            return {"status": "error", "error": "Missing 'description'"}
        finder = SmartElementFinder(self.browser)
        return await finder.find_all(description, tag=data.get("tag"))

    async def _cmd_smart_click(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        text = data.get("text")
        if not text:
            return {"status": "error", "error": "Missing 'text'"}
        finder = SmartElementFinder(self.browser)
        return await finder.click_text(text, tag=data.get("tag"), timeout=data.get("timeout", 5000))

    async def _cmd_smart_fill(self, data: Dict, session) -> Dict:
        from src.tools.smart_finder import SmartElementFinder
        label = data.get("label")
        value = data.get("value")
        if not label or value is None:
            return {"status": "error", "error": "Missing 'label' or 'value'"}
        finder = SmartElementFinder(self.browser)
        return await finder.fill_text(label, value, timeout=data.get("timeout", 5000))

    # ─── Workflow Engine ────────────────────────────────────

    async def _cmd_workflow(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        steps = data.get("steps")
        if not steps:
            return {"status": "error", "error": "Missing 'steps'"}
        engine = WorkflowEngine(self.browser)
        return await engine.execute(
            steps,
            variables=data.get("variables"),
            on_error=data.get("on_error", "abort"),
            retry_count=data.get("retry_count", 0),
            step_delay_ms=data.get("step_delay_ms", 0),
        )

    async def _cmd_workflow_template(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        template_name = data.get("template_name")
        if not template_name:
            return {"status": "error", "error": "Missing 'template_name'"}
        engine = WorkflowEngine(self.browser)
        return await engine.execute_template(template_name, data.get("variables"))

    async def _cmd_workflow_json(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        json_str = data.get("json")
        if not json_str:
            return {"status": "error", "error": "Missing 'json'"}
        engine = WorkflowEngine(self.browser)
        return await engine.execute_from_json(json_str)

    async def _cmd_workflow_save(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        name = data.get("name")
        steps = data.get("steps")
        if not name or not steps:
            return {"status": "error", "error": "Missing 'name' or 'steps'"}
        engine = WorkflowEngine(self.browser)
        return engine.save_template(name, steps, data.get("variables"), data.get("description", ""))

    async def _cmd_workflow_list(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        engine = WorkflowEngine(self.browser)
        return {"status": "success", "templates": engine.list_templates()}

    async def _cmd_workflow_status(self, data: Dict, session) -> Dict:
        from src.tools.workflow import WorkflowEngine
        workflow_id = data.get("workflow_id")
        if not workflow_id:
            return {"status": "error", "error": "Missing 'workflow_id'"}
        engine = WorkflowEngine(self.browser)
        return engine.get_status(workflow_id)

    # ─── Network Capture ────────────────────────────────────

    async def _cmd_network_start(self, data: Dict, session) -> Dict:
        from src.tools.network_capture import NetworkCapture
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            self._network_capture = NetworkCapture(self.browser)
        return await self._network_capture.start_capture(
            page_id=data.get("page_id", "main"),
            url_pattern=data.get("url_pattern"),
            resource_types=data.get("resource_types"),
            methods=data.get("methods"),
            capture_body=data.get("capture_body", False),
        )

    async def _cmd_network_stop(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.stop_capture(page_id=data.get("page_id", "main"))

    async def _cmd_network_get(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_captured(
            page_id=data.get("page_id", "main"),
            url_pattern=data.get("url_pattern"),
            resource_type=data.get("resource_type"),
            method=data.get("method"),
            status_code=data.get("status_code"),
            api_only=data.get("api_only", False),
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
        )

    async def _cmd_network_apis(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_apis(page_id=data.get("page_id", "main"))

    async def _cmd_network_detail(self, data: Dict, session) -> Dict:
        request_id = data.get("request_id")
        if not request_id:
            return {"status": "error", "error": "Missing 'request_id'"}
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.get_request_detail(request_id)

    async def _cmd_network_stats(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return self._network_capture.get_stats(page_id=data.get("page_id", "main"))

    async def _cmd_network_export(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        fmt = data.get("format", "json")
        page_id = data.get("page_id", "main")
        filename = data.get("filename")
        if fmt == "har":
            return await self._network_capture.export_har(page_id=page_id, filename=filename)
        return await self._network_capture.export_json(page_id=page_id, filename=filename)

    async def _cmd_network_clear(self, data: Dict, session) -> Dict:
        if not hasattr(self, '_network_capture') or self._network_capture is None:
            return {"status": "error", "error": "Network capture not started"}
        return await self._network_capture.clear(page_id=data.get("page_id", "main"))

    # ─── Page Analyzer ─────────────────────────────────────

    async def _cmd_page_summary(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.summarize(page_id=data.get("page_id", "main"))

    async def _cmd_page_tables(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.extract_tables(page_id=data.get("page_id", "main"))

    async def _cmd_page_structured(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.extract_structured_data(page_id=data.get("page_id", "main"))

    async def _cmd_page_emails(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.find_emails(page_id=data.get("page_id", "main"))

    async def _cmd_page_phones(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.find_phone_numbers(page_id=data.get("page_id", "main"))

    async def _cmd_page_accessibility(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.accessibility_check(page_id=data.get("page_id", "main"))

    async def _cmd_page_seo(self, data: Dict, session) -> Dict:
        from src.tools.page_analyzer import PageAnalyzer
        analyzer = PageAnalyzer(self.browser)
        return await analyzer.seo_audit(page_id=data.get("page_id", "main"))

    # ─── Proxy ─────────────────────────────────────────────

    async def _cmd_set_proxy(self, data: Dict, session) -> Dict:
        proxy_url = data.get("proxy_url")
        if not proxy_url:
            return {"status": "error", "error": "Missing 'proxy_url'"}
        return await self.browser.set_proxy(proxy_url)

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
        name = data.get("name", "default")
        return await self.browser.save_session(name)

    async def _cmd_restore_session(self, data: Dict, session) -> Dict:
        name = data.get("name", "default")
        return await self.browser.restore_session(name)

    async def _cmd_list_sessions(self, data: Dict, session) -> Dict:
        return await self.browser.list_sessions()

    async def _cmd_delete_session(self, data: Dict, session) -> Dict:
        name = data.get("name")
        if not name:
            return {"status": "error", "error": "Missing 'name'"}
        return await self.browser.delete_session(name)

    # ─── Smart Wait Commands ────────────────────────────────

    async def _cmd_smart_wait(self, data: Dict, session) -> Dict:
        """Auto smart wait — combines page_ready + network_idle + dom_stable + optional element_ready."""
        wait = self._get_smart_wait()
        return await wait.auto(
            selector=data.get("selector"),
            idle_ms=data.get("idle_ms", 500),
            dom_stable_ms=data.get("dom_stable_ms", 300),
            timeout_ms=data.get("timeout_ms", 30000),
            require_interactable=data.get("require_interactable", True),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_network(self, data: Dict, session) -> Dict:
        """Wait for network to go idle (no in-flight requests)."""
        wait = self._get_smart_wait()
        return await wait.network_idle(
            idle_ms=data.get("idle_ms", 500),
            timeout_ms=data.get("timeout_ms", 30000),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_dom(self, data: Dict, session) -> Dict:
        """Wait for DOM mutations to stop."""
        wait = self._get_smart_wait()
        return await wait.dom_stable(
            stability_ms=data.get("stability_ms", 300),
            timeout_ms=data.get("timeout_ms", 15000),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_element(self, data: Dict, session) -> Dict:
        """Wait for element to be visible, interactable, and not animating."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        wait = self._get_smart_wait()
        return await wait.element_ready(
            selector=selector,
            timeout_ms=data.get("timeout_ms", 15000),
            require_interactable=data.get("require_interactable", True),
            wait_for_animation=data.get("wait_for_animation", True),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_page(self, data: Dict, session) -> Dict:
        """Wait for page to be fully loaded (docs, images, fonts, frameworks)."""
        wait = self._get_smart_wait()
        return await wait.page_ready(
            timeout_ms=data.get("timeout_ms", 30000),
            require_images=data.get("require_images", True),
            require_fonts=data.get("require_fonts", True),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_js(self, data: Dict, session) -> Dict:
        """Wait for JavaScript expression to become truthy."""
        expression = data.get("expression")
        if not expression:
            return {"status": "error", "error": "Missing 'expression'"}
        wait = self._get_smart_wait()
        return await wait.js_condition(
            expression=expression,
            timeout_ms=data.get("timeout_ms", 10000),
            poll_ms=data.get("poll_ms"),
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_smart_wait_compose(self, data: Dict, session) -> Dict:
        """Wait for multiple conditions (AND/OR logic)."""
        conditions = data.get("conditions")
        if not conditions:
            return {"status": "error", "error": "Missing 'conditions' list"}
        wait = self._get_smart_wait()
        return await wait.compose(
            conditions=conditions,
            mode=data.get("mode", "all"),
            timeout_ms=data.get("timeout_ms", 30000),
            page_id=data.get("page_id", "main"),
        )

    # ─── Auto Heal Commands ─────────────────────────────────

    async def _cmd_heal_click(self, data: Dict, session) -> Dict:
        """Click with auto-heal — recovers if selector breaks."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.click(
            selector=selector,
            page_id=data.get("page_id", "main"),
            timeout_ms=data.get("timeout_ms", 5000),
        )

    async def _cmd_heal_fill(self, data: Dict, session) -> Dict:
        """Fill form field with auto-heal."""
        selector = data.get("selector")
        value = data.get("value")
        if not selector or value is None:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        heal = self._get_auto_heal()
        return await heal.fill(
            selector=selector,
            value=value,
            page_id=data.get("page_id", "main"),
            timeout_ms=data.get("timeout_ms", 5000),
        )

    async def _cmd_heal_wait(self, data: Dict, session) -> Dict:
        """Wait for element with auto-heal."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.wait(
            selector=selector,
            page_id=data.get("page_id", "main"),
            timeout_ms=data.get("timeout_ms", 10000),
        )

    async def _cmd_heal_hover(self, data: Dict, session) -> Dict:
        """Hover with auto-heal."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.hover(
            selector=selector,
            page_id=data.get("page_id", "main"),
            timeout_ms=data.get("timeout_ms", 5000),
        )

    async def _cmd_heal_double_click(self, data: Dict, session) -> Dict:
        """Double-click with auto-heal."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.double_click(
            selector=selector,
            page_id=data.get("page_id", "main"),
            timeout_ms=data.get("timeout_ms", 5000),
        )

    async def _cmd_heal_selector(self, data: Dict, session) -> Dict:
        """Manually heal a broken selector."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.heal_selector(
            broken_selector=selector,
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_heal_fingerprint(self, data: Dict, session) -> Dict:
        """Capture fingerprint of an element for future healing."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        heal = self._get_auto_heal()
        return await heal.fingerprint(
            selector=selector,
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_heal_fingerprint_page(self, data: Dict, session) -> Dict:
        """Auto-fingerprint all interactive elements on the page."""
        heal = self._get_auto_heal()
        return await heal.fingerprint_page(page_id=data.get("page_id", "main"))

    async def _cmd_heal_stats(self, data: Dict, session) -> Dict:
        """Get auto-heal statistics and history."""
        heal = self._get_auto_heal()
        return heal.get_stats()

    async def _cmd_heal_clear(self, data: Dict, session) -> Dict:
        """Clear all healing caches."""
        heal = self._get_auto_heal()
        heal.clear_cache()
        return {"status": "success", "message": "Healing caches cleared"}

    # ─── Auto Retry Commands ────────────────────────────────

    async def _cmd_retry_execute(self, data: Dict, session) -> Dict:
        """Execute any command with intelligent retry."""
        command = data.get("inner_command") or data.get("command_payload", {}).get("command")
        if not command:
            return {"status": "error", "error": "Missing 'inner_command' or 'command_payload.command'"}

        # Build the action callable from inner command
        payload = data.get("command_payload", data)
        payload["command"] = command

        async def action():
            return await self._execute_command(command, payload, session)

        retry = self._get_auto_retry()
        return await retry.execute(
            operation=command,
            action=action,
            params=payload,
            deduplicate=data.get("deduplicate", False),
        )

    async def _cmd_retry_navigate(self, data: Dict, session) -> Dict:
        """Navigate with intelligent retry + smart_wait."""
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        retry = self._get_auto_retry()
        return await retry.navigate(
            url=url,
            page_id=data.get("page_id", "main"),
            wait_until=data.get("wait_until", "domcontentloaded"),
        )

    async def _cmd_retry_click(self, data: Dict, session) -> Dict:
        """Click with intelligent retry + auto-heal."""
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        retry = self._get_auto_retry()
        return await retry.click(
            selector=selector,
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_retry_fill(self, data: Dict, session) -> Dict:
        """Fill form field with intelligent retry + auto-heal."""
        selector = data.get("selector")
        value = data.get("value")
        if not selector or value is None:
            return {"status": "error", "error": "Missing 'selector' or 'value'"}
        retry = self._get_auto_retry()
        return await retry.fill(
            selector=selector,
            value=value,
            page_id=data.get("page_id", "main"),
        )

    async def _cmd_retry_api_call(self, data: Dict, session) -> Dict:
        """API call with intelligent retry."""
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        retry = self._get_auto_retry()
        return await retry.api_call(
            url=url,
            method=data.get("method", "GET"),
            headers=data.get("headers"),
            body=data.get("body"),
        )

    async def _cmd_retry_stats(self, data: Dict, session) -> Dict:
        """Get comprehensive retry statistics."""
        retry = self._get_auto_retry()
        return retry.get_stats()

    async def _cmd_retry_health(self, data: Dict, session) -> Dict:
        """Quick health check — circuit breakers + budget."""
        retry = self._get_auto_retry()
        return retry.get_health()

    async def _cmd_retry_circuit_breakers(self, data: Dict, session) -> Dict:
        """Get state of all circuit breakers."""
        retry = self._get_auto_retry()
        return {"status": "success", "circuit_breakers": retry.get_circuit_breakers()}

    async def _cmd_retry_reset_circuit(self, data: Dict, session) -> Dict:
        """Reset a specific circuit breaker."""
        operation = data.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing 'operation'"}
        retry = self._get_auto_retry()
        return retry.reset_circuit_breaker(operation)

    async def _cmd_retry_reset_all_circuits(self, data: Dict, session) -> Dict:
        """Reset all circuit breakers."""
        retry = self._get_auto_retry()
        return retry.reset_all_circuit_breakers()
