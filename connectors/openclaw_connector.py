#!/usr/bin/env python3
"""
Agent-OS OpenClaw Integration
Adds Agent-OS browser tools to OpenClaw sessions.

Usage:
    from openclaw_connector import get_manifest, execute_tool

    manifest = get_manifest()  # Register with OpenClaw
    result = await execute_tool("browser_navigate", {"url": "https://example.com"})
"""
import os
import json
import httpx
from typing import Dict, Any, Optional

AGENT_OS_URL = os.environ.get("AGENT_OS_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_OS_TOKEN", "openclaw-agent")

TOOLS_MANIFEST = {
    "name": "agent-os-browser",
    "version": "2.1.0",
    "description": "AI Agent Browser — anti-detection browser automation for any agent",
    "tools": [
        {
            "name": "browser_navigate",
            "description": "Navigate to a URL. Anti-detection bypasses CAPTCHAs, reCAPTCHA, hCaptcha, Cloudflare Turnstile, and bot protection.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "URL to navigate to"}
            },
        },
        {
            "name": "browser_get_content",
            "description": "Get the current page's HTML content and extracted text.",
            "parameters": {},
        },
        {
            "name": "browser_get_dom",
            "description": "Get a structured DOM snapshot of the current page for detailed analysis.",
            "parameters": {},
        },
        {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current page. Returns base64-encoded PNG.",
            "parameters": {},
        },
        {
            "name": "browser_click",
            "description": "Click an element using a CSS selector. Simulates human-like Bezier mouse movement.",
            "parameters": {
                "selector": {"type": "string", "required": True, "description": "CSS selector for the element to click"}
            },
        },
        {
            "name": "browser_fill_form",
            "description": "Fill multiple form fields with human-like typing. Keys are CSS selectors, values are text to type.",
            "parameters": {
                "fields": {"type": "object", "required": True, "description": "Dict mapping CSS selectors to values"}
            },
        },
        {
            "name": "browser_scroll",
            "description": "Scroll the page up or down.",
            "parameters": {
                "direction": {"type": "string", "required": False, "default": "down", "description": "Scroll direction: 'up' or 'down'"},
                "amount": {"type": "integer", "required": False, "default": 500, "description": "Pixels to scroll"},
            },
        },
        {
            "name": "browser_evaluate_js",
            "description": "Execute JavaScript code in the current page context and return the result.",
            "parameters": {
                "script": {"type": "string", "required": True, "description": "JavaScript code to execute"}
            },
        },
        {
            "name": "browser_scan_xss",
            "description": "Scan a URL for Cross-Site Scripting (XSS) vulnerabilities.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "URL to scan"}
            },
        },
        {
            "name": "browser_scan_sqli",
            "description": "Scan a URL for SQL injection vulnerabilities.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "URL to scan"}
            },
        },
        {
            "name": "browser_transcribe",
            "description": "Transcribe audio or video from a URL using local Whisper. Supports YouTube and direct media URLs.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "URL of the video/audio"},
                "language": {"type": "string", "required": False, "default": "auto", "description": "Language code or 'auto'"},
            },
        },
        {
            "name": "browser_save_credentials",
            "description": "Save login credentials for a domain. Stored with AES-256 encryption.",
            "parameters": {
                "domain": {"type": "string", "required": True, "description": "Domain, e.g. 'github.com'"},
                "username": {"type": "string", "required": True, "description": "Username or email"},
                "password": {"type": "string", "required": True, "description": "Password"},
            },
        },
        {
            "name": "browser_auto_login",
            "description": "Automatically log in to a website using previously saved encrypted credentials.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "Login page URL"},
                "domain": {"type": "string", "required": True, "description": "Domain with saved credentials"},
            },
        },
        {
            "name": "browser_tabs",
            "description": "Manage browser tabs: list all tabs, create a new tab, switch to a tab, or close a tab.",
            "parameters": {
                "action": {"type": "string", "required": True, "description": "Tab action: 'list', 'new', 'close', or 'switch'"},
                "tab_id": {"type": "string", "required": False, "description": "Tab ID (required for close/switch)"},
            },
        },
        {
            "name": "browser_status",
            "description": "Get Agent-OS server status: uptime, active sessions, browser state, version.",
            "parameters": {},
        },
        {
            "name": "browser_type",
            "description": "Type text into the currently focused element with realistic human-like delays.",
            "parameters": {
                "text": {"type": "string", "required": True, "description": "Text to type"}
            },
        },
        {
            "name": "browser_press",
            "description": "Press a keyboard key (Enter, Tab, Escape, Backspace, ArrowUp, ArrowDown, etc.).",
            "parameters": {
                "key": {"type": "string", "required": True, "description": "Key name, e.g. 'Enter', 'Tab', 'Escape'"}
            },
        },
        {
            "name": "browser_hover",
            "description": "Hover the mouse over an element to trigger hover states or tooltips.",
            "parameters": {
                "selector": {"type": "string", "required": True, "description": "CSS selector for the element"}
            },
        },
        {
            "name": "browser_back",
            "description": "Navigate back in browser history.",
            "parameters": {},
        },
        {
            "name": "browser_forward",
            "description": "Navigate forward in browser history.",
            "parameters": {},
        },
        {
            "name": "browser_reload",
            "description": "Reload the current page.",
            "parameters": {},
        },
        {
            "name": "browser_get_links",
            "description": "Extract all links (href, text) from the current page.",
            "parameters": {},
        },
        {
            "name": "browser_get_images",
            "description": "Extract all images from the current page with src, alt, width, and height.",
            "parameters": {},
        },
        {
            "name": "browser_wait",
            "description": "Wait for an element to appear on the page before continuing.",
            "parameters": {
                "selector": {"type": "string", "required": True, "description": "CSS selector to wait for"},
                "timeout": {"type": "integer", "required": False, "default": 10000, "description": "Timeout in ms"},
            },
        },
        {
            "name": "browser_scan_sensitive",
            "description": "Scan the current page for exposed sensitive data: API keys, tokens, emails, IPs, private keys.",
            "parameters": {},
        },
        # ── New: Element Finder ──
        {
            "name": "browser_find_element",
            "description": "Find an element by text, ARIA role, aria-label, or natural language (e.g., 'the login button').",
            "parameters": {
                "description": {"type": "string", "required": True, "description": "Element description: text, role, aria-label, or natural language"},
                "method": {"type": "string", "required": False, "default": "smart", "description": "Search strategy: smart, text, role, or aria-label"},
                "exact": {"type": "boolean", "required": False, "default": False, "description": "Exact text match (text method only)"},
            },
        },
        {
            "name": "browser_find_all_interactive",
            "description": "Find all interactive elements (buttons, inputs, links, selects) on the page.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        # ── New: Data Extraction ──
        {
            "name": "browser_extract",
            "description": "Extract structured data: tables, lists, articles, JSON-LD, metadata, links, or all.",
            "parameters": {
                "type": {"type": "string", "required": False, "default": "all", "description": "Extraction type: tables, lists, articles, jsonld, metadata, links, or all"},
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        # ── New: Markdown ──
        {
            "name": "browser_get_markdown",
            "description": "Convert the current page to clean Markdown (strips ads, nav, scripts, styles).",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        # ── New: PDF ──
        {
            "name": "browser_generate_pdf",
            "description": "Generate a PDF from the current page. Saves to downloads directory.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
                "format": {"type": "string", "required": False, "default": "A4", "description": "Page format (A4, Letter, etc.)"},
                "landscape": {"type": "boolean", "required": False, "description": "Landscape orientation"},
                "scale": {"type": "number", "required": False, "description": "Scale factor (0.1-2.0)"},
            },
        },
        # ── New: HAR Recording ──
        {
            "name": "browser_har_start",
            "description": "Start HAR (HTTP Archive) recording for a page.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        {
            "name": "browser_har_stop",
            "description": "Stop HAR recording for a page.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        {
            "name": "browser_har_save",
            "description": "Save recorded HAR data to a JSON file.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
                "path": {"type": "string", "required": False, "description": "Output file path (auto-generated if omitted)"},
            },
        },
        {
            "name": "browser_har_status",
            "description": "Get HAR recording status (active, request count, duration).",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        # ── New: Stealth Profiles ──
        {
            "name": "browser_set_profile",
            "description": "Apply a stealth browser profile. Requires browser restart.",
            "parameters": {
                "profile": {"type": "string", "required": True, "description": "Profile name: windows-chrome, mac-safari, linux-firefox, mobile-chrome-android, mobile-safari-ios"},
            },
        },
        {
            "name": "browser_list_profiles",
            "description": "List all available stealth profiles with descriptions.",
            "parameters": {},
        },
        # ── New: Network Logs ──
        {
            "name": "browser_get_network_logs",
            "description": "Get network request logs, optionally filtered by URL pattern, status code, or resource type.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
                "url_pattern": {"type": "string", "required": False, "description": "Filter by URL substring"},
                "status_code": {"type": "integer", "required": False, "description": "Filter by HTTP status code"},
                "resource_type": {"type": "string", "required": False, "description": "Resource type (document, xhr, fetch, script, etc.)"},
            },
        },
        {
            "name": "browser_clear_network_logs",
            "description": "Clear captured network request logs for a page.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
            },
        },
        {
            "name": "browser_get_api_calls",
            "description": "Get XHR/Fetch API calls from the network log.",
            "parameters": {
                "page_id": {"type": "string", "required": False, "default": "main", "description": "Tab ID"},
                "url_pattern": {"type": "string", "required": False, "description": "Filter by URL substring"},
            },
        },
        # ── New: Proxy ──
        {
            "name": "browser_proxy_rotate",
            "description": "Rotate to the next proxy in the configured list. Requires browser restart.",
            "parameters": {},
        },
        {
            "name": "browser_proxy_status",
            "description": "Get current proxy configuration and status.",
            "parameters": {},
        },
        # ── New: Webhooks ──
        {
            "name": "browser_webhook_register",
            "description": "Register a webhook endpoint to receive real-time browser events.",
            "parameters": {
                "url": {"type": "string", "required": True, "description": "HTTP(S) URL to receive POST events"},
                "events": {"type": "array", "required": True, "description": "Event types: navigation, click, form_submit, screenshot, error, session_start, session_end, etc."},
                "secret": {"type": "string", "required": False, "description": "Optional HMAC-SHA256 secret for signing payloads"},
            },
        },
        {
            "name": "browser_webhook_list",
            "description": "List all registered webhooks.",
            "parameters": {},
        },
        {
            "name": "browser_webhook_remove",
            "description": "Remove a registered webhook by ID.",
            "parameters": {
                "webhook_id": {"type": "string", "required": True, "description": "Webhook ID to remove"},
            },
        },
        {
            "name": "browser_webhook_test",
            "description": "Send a test ping to verify a webhook is working.",
            "parameters": {
                "webhook_id": {"type": "string", "required": True, "description": "Webhook ID to test"},
            },
        },
    ],
}

# Command map: tool name → API command name
_COMMAND_MAP = {
    "browser_navigate": "navigate",
    "browser_get_content": "get-content",
    "browser_get_dom": "get-dom",
    "browser_screenshot": "screenshot",
    "browser_click": "click",
    "browser_fill_form": "fill-form",
    "browser_scroll": "scroll",
    "browser_evaluate_js": "evaluate-js",
    "browser_scan_xss": "scan-xss",
    "browser_scan_sqli": "scan-sqli",
    "browser_transcribe": "transcribe",
    "browser_save_credentials": "save-creds",
    "browser_auto_login": "auto-login",
    "browser_tabs": "tabs",
    "browser_status": "status",
    "browser_type": "type",
    "browser_press": "press",
    "browser_hover": "hover",
    "browser_back": "back",
    "browser_forward": "forward",
    "browser_reload": "reload",
    "browser_get_links": "get-links",
    "browser_get_images": "get-images",
    "browser_wait": "wait",
    "browser_scan_sensitive": "scan-sensitive",
    # New commands
    "browser_find_element": "find-element",
    "browser_find_all_interactive": "find-all-interactive",
    "browser_extract": "extract",
    "browser_get_markdown": "get-markdown",
    "browser_generate_pdf": "generate-pdf",
    "browser_har_start": "har-start",
    "browser_har_stop": "har-stop",
    "browser_har_save": "har-save",
    "browser_har_status": "har-status",
    "browser_set_profile": "set-profile",
    "browser_list_profiles": "list-profiles",
    "browser_get_network_logs": "get-network-logs",
    "browser_clear_network_logs": "clear-network-logs",
    "browser_get_api_calls": "get-api-calls",
    "browser_proxy_rotate": "proxy-rotate",
    "browser_proxy_status": "proxy-status",
    "browser_webhook_register": "webhook-register",
    "browser_webhook_list": "webhook-list",
    "browser_webhook_remove": "webhook-remove",
    "browser_webhook_test": "webhook-test",
}


def get_manifest() -> dict:
    """
    Return the tools manifest for registration with OpenClaw.

    Returns:
        Dict with name, version, description, and tools list
    """
    return TOOLS_MANIFEST


def get_tool_names() -> list:
    """Return the names of all available tools."""
    return [t["name"] for t in TOOLS_MANIFEST["tools"]]


async def execute_tool(tool_name: str, params: dict = None) -> dict:
    """
    Execute an Agent-OS tool via the REST API.

    Args:
        tool_name: Full tool name, e.g. "browser_navigate"
        params: Dict of parameters matching the tool's definition

    Returns:
        JSON response from Agent-OS server
    """
    if params is None:
        params = {}

    # Handle status as GET
    if tool_name == "browser_status":
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{AGENT_OS_URL}/status")
                return resp.json()
            except httpx.ConnectError:
                return {"status": "error", "error": f"Cannot connect to Agent-OS at {AGENT_OS_URL}. Is it running?"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

    cmd = _COMMAND_MAP.get(tool_name)
    if not cmd:
        return {"status": "error", "error": f"Unknown tool: {tool_name}. Available: {get_tool_names()}"}

    data = {"token": AGENT_TOKEN, "command": cmd, **params}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{AGENT_OS_URL}/command", json=data)
            return resp.json()
        except httpx.ConnectError:
            return {"status": "error", "error": f"Cannot connect to Agent-OS at {AGENT_OS_URL}. Is it running?"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    manifest = get_manifest()
    print(f"Agent-OS OpenClaw Connector — {len(manifest['tools'])} tools\n")
    for t in manifest["tools"]:
        print(f"  • {t['name']}: {t['description'][:60]}...")
    print(f"\nAgent-OS URL: {AGENT_OS_URL}")
    print(f"\nFull manifest:\n{json.dumps(manifest, indent=2)}")
