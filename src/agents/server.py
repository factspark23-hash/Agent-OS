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

from src.agents.webhook import WebhookManager

logger = logging.getLogger("agent-os.server")


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

        # Webhook manager
        self.webhook_manager = WebhookManager(config)

        # Lazy-loaded modules (avoids import-time overhead)
        self._element_finder = None
        self._data_extractor = None
        self._markdown_converter = None

    def _get_element_finder(self):
        """Lazy-init element finder."""
        if self._element_finder is None:
            from src.tools.element_finder import ElementFinder
            self._element_finder = ElementFinder(self.browser)
        return self._element_finder

    def _get_data_extractor(self):
        """Lazy-init data extractor."""
        if self._data_extractor is None:
            from src.tools.extractor import DataExtractor
            self._data_extractor = DataExtractor(self.browser)
        return self._data_extractor

    def _get_markdown_converter(self):
        """Lazy-init markdown converter."""
        if self._markdown_converter is None:
            from src.tools.markdown_converter import MarkdownConverter
            self._markdown_converter = MarkdownConverter(self.browser)
        return self._markdown_converter

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
        return web.json_response({
            "status": "running",
            "uptime_seconds": int(time.time() - self._start_time),
            "active_sessions": len(self.session_manager.list_active_sessions()),
            "active_ws_clients": len(self._ws_clients),
            "browser_active": self.browser.browser is not None,
            "version": "2.0.0"
        })

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
            # --- New commands ---
            "find-element": {"params": {"description": "string (text, role, aria-label, or natural language)", "method": "string (optional: text|role|aria-label|smart, default smart)", "exact": "bool (optional, for text method)"}, "description": "Find an element by text, ARIA role, aria-label, or natural language"},
            "find-all-interactive": {"params": {"page_id": "string (optional)"}, "description": "Find all interactive elements (buttons, inputs, links, selects) on the page"},
            "extract": {"params": {"type": "string (tables|lists|articles|jsonld|metadata|links|all)", "page_id": "string (optional)"}, "description": "Extract structured data from the page (tables, lists, articles, JSON-LD, metadata, links)"},
            "get-markdown": {"params": {"page_id": "string (optional)"}, "description": "Convert the current page to clean Markdown"},
            "generate-pdf": {"params": {"page_id": "string (optional)", "format": "string (optional, default A4)", "landscape": "bool (optional)", "margins": "dict (optional)", "scale": "float (optional)"}, "description": "Generate a PDF from the current page"},
            "har-start": {"params": {"page_id": "string (optional, default main)"}, "description": "Start HAR recording for a page"},
            "har-stop": {"params": {"page_id": "string (optional, default main)"}, "description": "Stop HAR recording for a page"},
            "har-save": {"params": {"page_id": "string (optional, default main)", "path": "string (optional, auto-generated if omitted)"}, "description": "Save recorded HAR data to a file"},
            "har-status": {"params": {"page_id": "string (optional, default main)"}, "description": "Get HAR recording status"},
            "set-profile": {"params": {"profile": "string (windows-chrome|mac-safari|linux-firefox|mobile-chrome-android|mobile-safari-ios)"}, "description": "Set browser stealth profile. Requires browser restart."},
            "list-profiles": {"params": {}, "description": "List all available stealth profiles"},
            "get-network-logs": {"params": {"page_id": "string (optional)", "url_pattern": "string (optional)", "status_code": "int (optional)", "resource_type": "string (optional)"}, "description": "Get filtered network request logs"},
            "clear-network-logs": {"params": {"page_id": "string (optional, default main)"}, "description": "Clear captured network logs for a page"},
            "get-api-calls": {"params": {"page_id": "string (optional)", "url_pattern": "string (optional)"}, "description": "Get XHR/Fetch API calls from the network log"},
            "extract-links": {"params": {"page_id": "string (optional)"}, "description": "Extract all links (href, text) with context from the current page"},
            "proxy-rotate": {"params": {}, "description": "Rotate to the next proxy in the configured list. Requires browser restart."},
            "proxy-status": {"params": {}, "description": "Get current proxy configuration and status"},
            "webhook-register": {"params": {"url": "string", "events": ["string"], "secret": "string (optional)"}, "description": "Register a webhook endpoint for real-time browser events"},
            "webhook-list": {"params": {}, "description": "List all registered webhooks"},
            "webhook-remove": {"params": {"webhook_id": "string"}, "description": "Remove a registered webhook"},
            "webhook-test": {"params": {"webhook_id": "string"}, "description": "Send a test ping to verify a webhook is working"},
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
            # Fire session_start webhook
            asyncio.create_task(self.webhook_manager.dispatch("session_start", {
                "session_id": session.session_id,
                "token_prefix": token[:8],
            }))

        session.commands_executed += 1

        try:
            result = await self._execute_command(command, data, session)
            result["session_id"] = session.session_id
            return result
        except Exception as e:
            logger.error(f"Command error: {e}")
            # Fire error webhook
            asyncio.create_task(self.webhook_manager.dispatch("error", {
                "command": command,
                "error": str(e),
                "session_id": session.session_id,
            }))
            return {"status": "error", "error": str(e), "session_id": session.session_id}

    async def _execute_command(self, command: str, data: Dict, session) -> Dict:
        """Route command to appropriate handler."""
        handlers = {
            # Core browser commands
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
            # New commands
            "find-element": self._cmd_find_element,
            "find-all-interactive": self._cmd_find_all_interactive,
            "extract": self._cmd_extract,
            "get-markdown": self._cmd_get_markdown,
            "generate-pdf": self._cmd_generate_pdf,
            "har-start": self._cmd_har_start,
            "har-stop": self._cmd_har_stop,
            "har-save": self._cmd_har_save,
            "har-status": self._cmd_har_status,
            "set-profile": self._cmd_set_profile,
            "list-profiles": self._cmd_list_profiles,
            "get-network-logs": self._cmd_get_network_logs,
            "clear-network-logs": self._cmd_clear_network_logs,
            "get-api-calls": self._cmd_get_api_calls,
            "extract-links": self._cmd_extract_links,
            "proxy-rotate": self._cmd_proxy_rotate,
            "proxy-status": self._cmd_proxy_status,
            "webhook-register": self._cmd_webhook_register,
            "webhook-list": self._cmd_webhook_list,
            "webhook-remove": self._cmd_webhook_remove,
            "webhook-test": self._cmd_webhook_test,
        }

        handler = handlers.get(command)
        if not handler:
            return {"status": "error", "error": f"Unknown command: {command}. Available: {list(handlers.keys())}"}

        return await handler(data, session)

    # ─── Original Command Handlers ────────────────────────────

    async def _cmd_navigate(self, data: Dict, session) -> Dict:
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        page_id = data.get("page_id", "main")
        wait_until = data.get("wait_until", "domcontentloaded")
        result = await self.browser.navigate(url, page_id=page_id, wait_until=wait_until)
        # Fire webhook on success
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("navigation", {
                "url": result.get("url"),
                "title": result.get("title"),
                "status_code": result.get("status_code"),
                "session_id": session.session_id,
            }))
        return result

    async def _cmd_fill_form(self, data: Dict, session) -> Dict:
        fields = data.get("fields", {})
        if not fields:
            return {"status": "error", "error": "Missing 'fields' dictionary"}
        result = await self.browser.fill_form(fields)
        # Fire webhook on success
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("form_submit", {
                "fields": list(fields.keys()),
                "filled": result.get("filled", []),
                "session_id": session.session_id,
            }))
        return result

    async def _cmd_click(self, data: Dict, session) -> Dict:
        selector = data.get("selector")
        if not selector:
            return {"status": "error", "error": "Missing 'selector'"}
        result = await self.browser.click(selector)
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("click", {
                "selector": selector,
                "session_id": session.session_id,
            }))
        return result

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
        result = {"status": "success", "screenshot": b64, "format": "png"}
        asyncio.create_task(self.webhook_manager.dispatch("screenshot", {
            "full_page": full_page,
            "session_id": session.session_id,
        }))
        return result

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
        result = await scanner.scan(url)
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("scan_complete", {
                "type": "xss",
                "url": url,
                "vulnerabilities_found": result.get("vulnerabilities_found", 0),
                "session_id": session.session_id,
            }))
        return result

    async def _cmd_scan_sqli(self, data: Dict, session) -> Dict:
        from src.tools.scanner import SQLiScanner
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        scanner = SQLiScanner(self.browser)
        result = await scanner.scan(url)
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("scan_complete", {
                "type": "sqli",
                "url": url,
                "vulnerabilities_found": result.get("vulnerabilities_found", 0),
                "session_id": session.session_id,
            }))
        return result

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
        result = await transcriber.transcribe_from_url(url, data.get("language", "auto"))
        if result.get("status") == "success":
            asyncio.create_task(self.webhook_manager.dispatch("transcription_complete", {
                "url": url,
                "session_id": session.session_id,
            }))
        return result

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

    # ─── New Command Handlers ─────────────────────────────────

    async def _cmd_find_element(self, data: Dict, session) -> Dict:
        """Find an element by text, ARIA role, aria-label, placeholder, or natural language."""
        try:
            page_id = data.get("page_id", "main")
            finder = self._get_element_finder()

            # Support multiple parameter styles
            text_param = data.get("text")
            role_param = data.get("role")
            aria_param = data.get("aria")
            placeholder_param = data.get("placeholder")
            description = data.get("description")

            if text_param:
                tag = data.get("tag")
                exact = data.get("exact", False)
                return await finder.find_by_text(text_param, exact=exact, tag=tag, page_id=page_id)
            elif role_param:
                name = data.get("name")
                return await finder.find_by_role(role_param, name=name, page_id=page_id)
            elif aria_param:
                return await finder.find_by_aria_label(aria_param, page_id=page_id)
            elif placeholder_param:
                return await finder.find_by_placeholder(placeholder_param, page_id=page_id)
            elif description:
                # Natural language smart search, or explicit method override
                method = data.get("method", "smart")
                if method == "text":
                    return await finder.find_by_text(description, page_id=page_id, exact=data.get("exact", False))
                elif method == "role":
                    name = data.get("name")
                    return await finder.find_by_role(description, name=name, page_id=page_id)
                elif method == "aria-label":
                    return await finder.find_by_aria_label(description, page_id=page_id)
                else:
                    return await finder.find_smart(description, page_id=page_id)
            else:
                return {"status": "error", "error": "Missing parameter. Provide one of: description, text, role, aria, placeholder"}
        except Exception as e:
            logger.error(f"find-element failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_find_all_interactive(self, data: Dict, session) -> Dict:
        """Find all interactive elements on the page."""
        try:
            page_id = data.get("page_id", "main")
            finder = self._get_element_finder()
            return await finder.find_all_interactive(page_id=page_id)
        except Exception as e:
            logger.error(f"find-all-interactive failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_extract(self, data: Dict, session) -> Dict:
        """Extract structured data from the page."""
        try:
            extract_type = data.get("type", "all")
            page_id = data.get("page_id", "main")

            extractor = self._get_data_extractor()

            if extract_type == "tables":
                return await extractor.extract_tables(page_id)
            elif extract_type == "lists":
                return await extractor.extract_lists(page_id)
            elif extract_type == "articles":
                return await extractor.extract_articles(page_id)
            elif extract_type == "jsonld":
                return await extractor.extract_jsonld(page_id)
            elif extract_type == "metadata":
                return await extractor.extract_metadata(page_id)
            elif extract_type == "links":
                return await extractor.extract_links_structured(page_id)
            elif extract_type == "all":
                return await extractor.extract_all(page_id)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown extract type: {extract_type}. Use tables|lists|articles|jsonld|metadata|links|all",
                }
        except Exception as e:
            logger.error(f"extract failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_get_markdown(self, data: Dict, session) -> Dict:
        """Convert current page to Markdown."""
        try:
            page_id = data.get("page_id", "main")
            options = data.get("options", {})
            converter = self._get_markdown_converter()
            return await converter.page_to_markdown(page_id=page_id, options=options)
        except Exception as e:
            logger.error(f"get-markdown failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_generate_pdf(self, data: Dict, session) -> Dict:
        """Generate PDF from current page."""
        try:
            page_id = data.get("page_id", "main")
            options = data.get("options")
            # Also accept top-level options for backward compat
            if options is None:
                options = {}
                for key in ("format", "landscape", "margins", "margin", "scale",
                            "print_background", "header_template", "footer_template",
                            "prefer_css_page_size"):
                    if key in data:
                        options[key] = data[key]
            return await self.browser.generate_pdf(
                page_id=page_id, options=options or None,
            )
        except Exception as e:
            logger.error(f"generate-pdf failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_har_start(self, data: Dict, session) -> Dict:
        """Start HAR recording using the production HARRecorder."""
        try:
            page_id = data.get("page_id", "main")
            from src.tools.har_recorder import HARRecorder
            if self.browser._har_recorder is None:
                self.browser._har_recorder = HARRecorder(self.browser)
            return await self.browser._har_recorder.start_recording(page_id=page_id)
        except Exception as e:
            logger.error(f"har-start failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_har_stop(self, data: Dict, session) -> Dict:
        """Stop HAR recording."""
        try:
            page_id = data.get("page_id", "main")
            if self.browser._har_recorder is None:
                return {"status": "error", "error": "No HAR recording active. Start one with har-start."}
            return await self.browser._har_recorder.stop_recording(page_id=page_id)
        except Exception as e:
            logger.error(f"har-stop failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_har_save(self, data: Dict, session) -> Dict:
        """Save HAR recording to .har file."""
        try:
            if self.browser._har_recorder is None:
                return {"status": "error", "error": "No HAR recording active. Start one with har-start."}
            filename = data.get("filename") or data.get("path")
            return await self.browser._har_recorder.save_recording(filename=filename)
        except Exception as e:
            logger.error(f"har-save failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_har_status(self, data: Dict, session) -> Dict:
        """Get HAR recording status."""
        try:
            if self.browser._har_recorder is None:
                return {"status": "idle", "recording": False, "entry_count": 0}
            return await self.browser._har_recorder.get_recording_status()
        except Exception as e:
            logger.error(f"har-status failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_set_profile(self, data: Dict, session) -> Dict:
        """Set browser stealth profile (applies immediately via context swap)."""
        try:
            profile_name = data.get("profile") or data.get("profile_name")
            if not profile_name:
                return {"status": "error", "error": "Missing 'profile'"}
            return await self.browser.apply_stealth_profile(profile_name)
        except Exception as e:
            logger.error(f"set-profile failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_list_profiles(self, data: Dict, session) -> Dict:
        """List all available stealth profiles."""
        try:
            from src.security.stealth_profiles import StealthProfileManager
            names = StealthProfileManager.list_profiles()
            return {
                "status": "success",
                "profiles": names,
                "count": len(names),
            }
        except Exception as e:
            logger.error(f"list-profiles failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_get_network_logs(self, data: Dict, session) -> Dict:
        """Get filtered network request logs."""
        try:
            page_id = data.get("page_id", "main")
            filter_url = data.get("url_pattern")
            filter_status = data.get("status_code")
            filter_type = data.get("resource_type")
            limit = data.get("limit", 100)

            return self.browser.get_network_logs(
                page_id=page_id,
                filter_url=filter_url,
                filter_status=filter_status,
                filter_type=filter_type,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"get-network-logs failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_clear_network_logs(self, data: Dict, session) -> Dict:
        """Clear captured network logs."""
        try:
            page_id = data.get("page_id")
            return self.browser.clear_network_logs(page_id=page_id)
        except Exception as e:
            logger.error(f"clear-network-logs failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_get_api_calls(self, data: Dict, session) -> Dict:
        """Get XHR/Fetch API calls from network logs."""
        try:
            page_id = data.get("page_id", "main")
            filter_url = data.get("url_pattern")
            limit = data.get("limit", 100)

            return self.browser.get_api_calls(
                page_id=page_id,
                filter_url=filter_url,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"get-api-calls failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_extract_links(self, data: Dict, session) -> Dict:
        """Extract all links with categorization (navigation, footer, content, external, internal, social, download)."""
        try:
            page_id = data.get("page_id", "main")
            extractor = self._get_data_extractor()
            return await extractor.extract_links_structured(page_id)
        except Exception as e:
            logger.error(f"extract-links failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_proxy_rotate(self, data: Dict, session) -> Dict:
        """Rotate to next proxy."""
        try:
            return await self.browser.rotate_proxy()
        except Exception as e:
            logger.error(f"proxy-rotate failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _cmd_proxy_status(self, data: Dict, session) -> Dict:
        """Get proxy configuration status."""
        try:
            current = self.config.get("browser.proxy")
            proxies = self.config.get("browser.proxies", [])
            safe_proxy = self.browser.get_current_proxy()
            return {
                "status": "success",
                "current_proxy": current,
                "active_proxy": safe_proxy,
                "available_proxies": len(proxies),
                "proxy_list": proxies,
                "active_index": self.browser._proxy_index % len(proxies) if proxies else None,
            }
        except Exception as e:
            logger.error(f"proxy-status failed: {e}")
            return {"status": "error", "error": str(e)}

    # ─── Webhook Command Handlers ─────────────────────────────

    async def _cmd_webhook_register(self, data: Dict, session) -> Dict:
        """Register a webhook endpoint."""
        url = data.get("url")
        if not url:
            return {"status": "error", "error": "Missing 'url'"}
        events = data.get("events")
        if not events or not isinstance(events, list):
            return {"status": "error", "error": "Missing or invalid 'events' (must be a list)"}
        secret = data.get("secret", "")
        return await self.webhook_manager.register(url, events, secret)

    async def _cmd_webhook_list(self, data: Dict, session) -> Dict:
        """List all registered webhooks."""
        webhooks = self.webhook_manager.list_webhooks()
        return {"status": "success", "webhooks": webhooks, "count": len(webhooks)}

    async def _cmd_webhook_remove(self, data: Dict, session) -> Dict:
        """Remove a registered webhook."""
        webhook_id = data.get("webhook_id")
        if not webhook_id:
            return {"status": "error", "error": "Missing 'webhook_id'"}
        return await self.webhook_manager.unregister(webhook_id)

    async def _cmd_webhook_test(self, data: Dict, session) -> Dict:
        """Test a webhook by sending a ping."""
        webhook_id = data.get("webhook_id")
        if not webhook_id:
            return {"status": "error", "error": "Missing 'webhook_id'"}
        return await self.webhook_manager.test_webhook(webhook_id)
