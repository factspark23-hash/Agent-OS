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

# All 38 tools — same set as MCP, OpenAI, and Claude connectors
TOOLS_MANIFEST = {
    "name": "agent-os-browser",
    "version": "1.0.0",
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
        {
            "name": "browser_smart_find",
            "description": "Find an element by visible text or description. No CSS selector needed.",
            "parameters": {
                "description": {"type": "string", "required": True, "description": "What to find"},
                "tag": {"type": "string", "required": False, "description": "Optional tag filter"},
                "timeout": {"type": "integer", "required": False, "default": 5000, "description": "Max wait ms"},
            },
        },
        {
            "name": "browser_smart_click",
            "description": "Click an element by its visible text. No CSS selector needed.",
            "parameters": {
                "text": {"type": "string", "required": True, "description": "Visible text of element"},
                "tag": {"type": "string", "required": False, "description": "Optional tag filter"},
                "timeout": {"type": "integer", "required": False, "default": 5000, "description": "Max wait ms"},
            },
        },
        {
            "name": "browser_smart_fill",
            "description": "Find input by label/placeholder and fill it.",
            "parameters": {
                "label": {"type": "string", "required": True, "description": "Label or placeholder text"},
                "value": {"type": "string", "required": True, "description": "Value to fill"},
                "timeout": {"type": "integer", "required": False, "default": 5000, "description": "Max wait ms"},
            },
        },
        {
            "name": "browser_workflow",
            "description": "Execute multi-step workflow. Supports variables, retries, error handling.",
            "parameters": {
                "steps": {"type": "array", "required": True, "description": "Array of step objects"},
                "variables": {"type": "object", "required": False, "description": "Template variables"},
                "on_error": {"type": "string", "required": False, "default": "abort", "description": "abort/skip/retry"},
                "retry_count": {"type": "integer", "required": False, "default": 0},
                "step_delay_ms": {"type": "integer", "required": False, "default": 0},
            },
        },
        {
            "name": "browser_network_start",
            "description": "Start capturing network requests.",
            "parameters": {
                "url_pattern": {"type": "string", "required": False, "description": "Regex filter"},
                "resource_types": {"type": "array", "required": False, "description": "Filter by type"},
                "methods": {"type": "array", "required": False, "description": "Filter by method"},
                "capture_body": {"type": "boolean", "required": False, "default": False},
            },
        },
        {
            "name": "browser_network_get",
            "description": "Get captured network requests with filters.",
            "parameters": {
                "url_pattern": {"type": "string", "required": False},
                "resource_type": {"type": "string", "required": False},
                "method": {"type": "string", "required": False},
                "status_code": {"type": "integer", "required": False},
                "api_only": {"type": "boolean", "required": False, "default": False},
                "limit": {"type": "integer", "required": False, "default": 100},
                "offset": {"type": "integer", "required": False, "default": 0},
            },
        },
        {
            "name": "browser_network_apis",
            "description": "Discover API endpoints from captured traffic.",
            "parameters": {},
        },
        {
            "name": "browser_page_summary",
            "description": "Analyze page: title, headings, content, forms, links, tech stack.",
            "parameters": {},
        },
        {
            "name": "browser_page_tables",
            "description": "Extract all HTML tables as structured data.",
            "parameters": {},
        },
        {
            "name": "browser_page_seo",
            "description": "SEO audit with score and issues.",
            "parameters": {},
        },
        {
            "name": "browser_emulate_device",
            "description": "Emulate mobile/tablet/desktop device.",
            "parameters": {
                "device": {"type": "string", "required": True, "description": "iphone_14, galaxy_s23, ipad, pixel_8, desktop_1080"},
            },
        },
        {
            "name": "browser_set_proxy",
            "description": "Set proxy. HTTP, HTTPS, SOCKS5.",
            "parameters": {
                "proxy_url": {"type": "string", "required": True, "description": "Proxy URL"},
            },
        },
        {
            "name": "browser_save_session",
            "description": "Save full browser state.",
            "parameters": {
                "name": {"type": "string", "required": False, "default": "default"},
            },
        },
        {
            "name": "browser_restore_session",
            "description": "Restore saved browser state.",
            "parameters": {
                "name": {"type": "string", "required": False, "default": "default"},
            },
        },

        # Web Query Router (No LLM — Rule-Based)
        {
            "name": "browser_classify_query",
            "description": "Classify whether a query needs web/browser access. Returns needs_web, confidence, category, reason, strategy. No LLM — pure rules. Call BEFORE deciding to use browser.",
            "parameters": {
                "query": {"type": "string", "required": True, "description": "The user's query to classify"},
            },
        },
        {
            "name": "browser_needs_web",
            "description": "Quick check: does this query need web access? Returns boolean + confidence.",
            "parameters": {
                "query": {"type": "string", "required": True, "description": "The user's query to check"},
            },
        },
        {
            "name": "browser_query_strategy",
            "description": "Get recommended strategy: use_browser, try_http_first, no_web_needed, probably_no_web, uncertain_consider_web.",
            "parameters": {
                "query": {"type": "string", "required": True, "description": "The user's query to analyze"},
            },
        },
        {
            "name": "browser_router_stats",
            "description": "Web Query Router classification statistics.",
            "parameters": {},
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
    "browser_smart_find": "smart-find",
    "browser_smart_click": "smart-click",
    "browser_smart_fill": "smart-fill",
    "browser_workflow": "workflow",
    "browser_network_start": "network-start",
    "browser_network_get": "network-get",
    "browser_network_apis": "network-apis",
    "browser_page_summary": "page-summary",
    "browser_page_tables": "page-tables",
    "browser_page_seo": "page-seo",
    "browser_emulate_device": "emulate-device",
    "browser_set_proxy": "set-proxy",
    "browser_save_session": "save-session",
    "browser_restore_session": "restore-session",
    # Web Query Router
    "browser_classify_query": "classify-query",
    "browser_needs_web": "needs-web",
    "browser_query_strategy": "query-strategy",
    "browser_router_stats": "router-stats",
}


def get_manifest() -> dict:
    """
    Return the tools manifest for registration with OpenClaw.

    Returns:
        Dict with name, version, description, and tools list
    """
    return TOOLS_MANIFEST


def get_tool_names() -> list:
    """Return the names of all 38 available tools."""
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
