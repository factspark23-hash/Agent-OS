#!/usr/bin/env python3
"""
Agent-OS OpenAI / Claude Tool-Use Connector
Converts Agent-OS commands into OpenAI function-calling / Claude tool-use schemas.

Usage:
    from openai_connector import get_tools, call_tool

    # For OpenAI
    tools = get_tools("openai")   # Returns OpenAI function definitions

    # For Claude
    tools = get_tools("claude")   # Returns Claude tool definitions

    # Call any tool
    result = await call_tool("browser_navigate", {"url": "https://example.com"})
"""
import json
import os
import httpx
from typing import Dict, List, Any

AGENT_OS_URL = os.environ.get("AGENT_OS_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_OS_TOKEN", "openai-connector-default")


# ─── Canonical Tool Definitions (38 tools — same as MCP) ──────
# Single source of truth. Both OpenAI and Claude formats are generated from this.

_TOOL_DEFS = [
    # ─── Web-Need Router (use first before any browser tool!) ────
    {
        "name": "browser_route",
        "description": (
            "Decide whether a query needs web/browser access or can be answered from your own knowledge. "
            "USE THIS FIRST before any browser tool to avoid unnecessary web requests. "
            "Returns: needs_web (bool), action (answer_from_knowledge|search|browse|hybrid), "
            "confidence, reason, suggested_commands, search_queries. "
            "Rule-based, zero-cost, sub-millisecond."
        ),
        "params": {
            "query": {"type": "string", "description": "The user question or task to analyze"},
            "context": {"type": "string", "description": "Optional conversation context"},
        },
        "required": ["query"],
    },
    {
        "name": "browser_navigate",
        "description": (
            "Navigate to a URL using a real Chromium browser with anti-detection. "
            "USE WHEN: (1) Site requires login or JavaScript rendering, "
            "(2) You need to click, fill forms, or interact, "
            "(3) Site blocks simple HTTP requests (Instagram, Facebook, etc.). "
            "DO NOT USE WHEN: (1) You only need to read a static article (use browser_fetch), "
            "(2) The question is factual and answerable from knowledge (no browser needed)."
        ),
        "params": {"url": {"type": "string", "description": "URL to navigate to"}},
        "required": ["url"],
    },
    {
        "name": "browser_get_content",
        "description": "Get the current page's HTML content and extracted text.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_get_dom",
        "description": "Get a structured DOM snapshot of the current page for detailed analysis.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page. Returns base64-encoded PNG.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_click",
        "description": "Click an element on the page using a CSS selector. Simulates human-like Bezier mouse movement.",
        "params": {"selector": {"type": "string", "description": "CSS selector for the element to click"}},
        "required": ["selector"],
    },
    {
        "name": "browser_fill_form",
        "description": "Fill multiple form fields with human-like typing rhythm. Keys are CSS selectors, values are the text to type.",
        "params": {
            "fields": {
                "type": "object",
                "description": "Dictionary mapping CSS selectors to values, e.g. {'#email': 'user@example.com', '#password': 'secret'}",
                "additionalProperties": {"type": "string"},
            }
        },
        "required": ["fields"],
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the page up or down.",
        "params": {
            "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction"},
            "amount": {"type": "integer", "description": "Pixels to scroll (default 500)"},
        },
        "required": [],
    },
    {
        "name": "browser_evaluate_js",
        "description": "Execute JavaScript code in the current page context and return the result.",
        "params": {"script": {"type": "string", "description": "JavaScript code to execute"}},
        "required": ["script"],
    },
    {
        "name": "browser_scan_xss",
        "description": "Scan a URL for Cross-Site Scripting (XSS) vulnerabilities. Returns findings with payloads.",
        "params": {"url": {"type": "string", "description": "URL to scan"}},
        "required": ["url"],
    },
    {
        "name": "browser_scan_sqli",
        "description": "Scan a URL for SQL injection vulnerabilities. Tests URL parameters with various SQLi payloads.",
        "params": {"url": {"type": "string", "description": "URL to scan"}},
        "required": ["url"],
    },
    {
        "name": "browser_transcribe",
        "description": "Transcribe audio or video from a URL using local Whisper. Supports YouTube and direct media URLs.",
        "params": {
            "url": {"type": "string", "description": "URL of the video/audio to transcribe"},
            "language": {"type": "string", "description": "Language code (e.g. 'en', 'zh') or 'auto'"},
        },
        "required": ["url"],
    },
    {
        "name": "browser_save_credentials",
        "description": "Save login credentials for a domain. Stored with AES-256 encryption.",
        "params": {
            "domain": {"type": "string", "description": "Domain, e.g. 'github.com'"},
            "username": {"type": "string", "description": "Username or email"},
            "password": {"type": "string", "description": "Password"},
        },
        "required": ["domain", "username", "password"],
    },
    {
        "name": "browser_auto_login",
        "description": "Automatically log in to a website using previously saved encrypted credentials.",
        "params": {
            "url": {"type": "string", "description": "Login page URL"},
            "domain": {"type": "string", "description": "Domain with saved credentials"},
        },
        "required": ["url", "domain"],
    },
    {
        "name": "browser_tabs",
        "description": "Manage browser tabs: list all tabs, create a new tab, switch to a tab, or close a tab.",
        "params": {
            "action": {"type": "string", "enum": ["list", "new", "close", "switch"], "description": "Tab action"},
            "tab_id": {"type": "string", "description": "Tab ID (required for close/switch, optional for new)"},
        },
        "required": ["action"],
    },
    {
        "name": "browser_status",
        "description": "Get Agent-OS server status: uptime, active sessions, browser state, version.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_type",
        "description": "Type text into the currently focused element with realistic human-like delays between keystrokes.",
        "params": {"text": {"type": "string", "description": "Text to type"}},
        "required": ["text"],
    },
    {
        "name": "browser_press",
        "description": "Press a keyboard key (Enter, Tab, Escape, Backspace, ArrowUp, ArrowDown, etc.).",
        "params": {"key": {"type": "string", "description": "Key name, e.g. 'Enter', 'Tab', 'Escape', 'Backspace'"}},
        "required": ["key"],
    },
    {
        "name": "browser_hover",
        "description": "Hover the mouse over an element to trigger hover states or tooltips.",
        "params": {"selector": {"type": "string", "description": "CSS selector for the element"}},
        "required": ["selector"],
    },
    {
        "name": "browser_back",
        "description": "Navigate back in browser history.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_forward",
        "description": "Navigate forward in browser history.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_reload",
        "description": "Reload the current page.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_get_links",
        "description": "Extract all links (href, text) from the current page.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_get_images",
        "description": "Extract all images from the current page with src, alt, width, and height.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_wait",
        "description": "Wait for an element to appear on the page before continuing.",
        "params": {
            "selector": {"type": "string", "description": "CSS selector to wait for"},
            "timeout": {"type": "integer", "description": "Timeout in milliseconds (default 10000)"},
        },
        "required": ["selector"],
    },
    {
        "name": "browser_scan_sensitive",
        "description": "Scan the current page for exposed sensitive data: API keys, tokens, emails, IP addresses, private keys.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_smart_find",
        "description": "Find an element by visible text or description. No CSS selector needed.",
        "params": {
            "description": {"type": "string", "description": "What to find — e.g. 'Sign In', 'email', 'Submit button'"},
            "tag": {"type": "string", "description": "Optional tag filter: button, input, a, etc."},
            "timeout": {"type": "integer", "description": "Max wait time in ms"},
        },
        "required": ["description"],
    },
    {
        "name": "browser_smart_click",
        "description": "Click an element by its visible text. No CSS selector needed.",
        "params": {
            "text": {"type": "string", "description": "Visible text of the element to click"},
            "tag": {"type": "string", "description": "Optional tag filter"},
            "timeout": {"type": "integer", "description": "Max wait time in ms"},
        },
        "required": ["text"],
    },
    {
        "name": "browser_smart_fill",
        "description": "Find an input field by its label/placeholder text and fill it.",
        "params": {
            "label": {"type": "string", "description": "Label or placeholder text of the input field"},
            "value": {"type": "string", "description": "Value to fill in"},
            "timeout": {"type": "integer", "description": "Max wait time in ms"},
        },
        "required": ["label", "value"],
    },
    {
        "name": "browser_workflow",
        "description": "Execute a multi-step browser workflow. Supports variables, retries, error handling.",
        "params": {
            "steps": {"type": "array", "description": "Array of step objects, each with 'command' + params"},
            "variables": {"type": "object", "description": "Template variables for {{var}} substitution"},
            "on_error": {"type": "string", "description": "Error handling: abort, skip, or retry"},
            "retry_count": {"type": "integer", "description": "Retries per step on failure"},
            "step_delay_ms": {"type": "integer", "description": "Delay between steps in ms"},
        },
        "required": ["steps"],
    },
    {
        "name": "browser_network_start",
        "description": "Start capturing all network requests. Filter by URL pattern, method, or resource type.",
        "params": {
            "url_pattern": {"type": "string", "description": "Only capture URLs matching this regex"},
            "resource_types": {"type": "array", "description": "Filter: document, script, xhr, fetch, image"},
            "methods": {"type": "array", "description": "Filter: GET, POST, PUT, DELETE"},
            "capture_body": {"type": "boolean", "description": "Capture response bodies"},
        },
        "required": [],
    },
    {
        "name": "browser_network_get",
        "description": "Get captured network requests with optional filters.",
        "params": {
            "url_pattern": {"type": "string", "description": "Filter URLs by regex"},
            "resource_type": {"type": "string", "description": "Filter by type"},
            "method": {"type": "string", "description": "Filter by HTTP method"},
            "status_code": {"type": "integer", "description": "Filter by status code"},
            "api_only": {"type": "boolean", "description": "Only return API calls"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
        },
        "required": [],
    },
    {
        "name": "browser_network_apis",
        "description": "Discover all API endpoints from captured network traffic.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_page_summary",
        "description": "Analyze page: title, headings, content, forms, links, tech stack, readability.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_page_tables",
        "description": "Extract all HTML tables as structured data.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_page_seo",
        "description": "Basic SEO audit: title, meta, H1, alt text, canonical, Open Graph. Returns score.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_emulate_device",
        "description": "Emulate a mobile/tablet/desktop device.",
        "params": {
            "device": {"type": "string", "description": "Preset: iphone_14, galaxy_s23, ipad, pixel_8, desktop_1080"},
        },
        "required": ["device"],
    },
    {
        "name": "browser_set_proxy",
        "description": "Set proxy for the browser. HTTP, HTTPS, SOCKS5.",
        "params": {
            "proxy_url": {"type": "string", "description": "Proxy URL: http://user:pass@host:port or socks5://host:port"},
        },
        "required": ["proxy_url"],
    },
    {
        "name": "browser_save_session",
        "description": "Save full browser state: cookies, localStorage, tabs.",
        "params": {
            "name": {"type": "string", "description": "Session name"},
        },
        "required": [],
    },
    {
        "name": "browser_restore_session",
        "description": "Restore a previously saved browser session.",
        "params": {
            "name": {"type": "string", "description": "Session name to restore", "default": "default"},
        },
        "required": [],
    },

    # ─── Web Query Router (No LLM — Rule-Based) ──────────────
    {
        "name": "browser_classify_query",
        "description": "Classify whether a query needs web/browser access. Returns needs_web (bool), confidence, category, reason, and suggested_strategy. Pure rule-based — no LLM. Call BEFORE deciding whether to use the browser.",
        "params": {
            "query": {"type": "string", "description": "The user's query to classify"},
        },
        "required": ["query"],
    },
    {
        "name": "browser_needs_web",
        "description": "Quick check: does this query need web access? Returns boolean + confidence. Lightweight endpoint for agents that need a yes/no before using browser.",
        "params": {
            "query": {"type": "string", "description": "The user's query to check"},
        },
        "required": ["query"],
    },
    {
        "name": "browser_query_strategy",
        "description": "Get recommended strategy for handling a query. Strategies: use_browser, try_http_first, no_web_needed, probably_no_web, uncertain_consider_web.",
        "params": {
            "query": {"type": "string", "description": "The user's query to analyze"},
        },
        "required": ["query"],
    },
    {
        "name": "browser_router_stats",
        "description": "Get Web Query Router classification statistics.",
        "params": {},
        "required": [],
    },
]

# Command map: tool name → (API command name, param keys)
_COMMAND_MAP = {
    "browser_route": ("route", ["query", "context"]),
    "browser_navigate": ("navigate", ["url"]),
    "browser_get_content": ("get-content", []),
    "browser_get_dom": ("get-dom", []),
    "browser_screenshot": ("screenshot", []),
    "browser_click": ("click", ["selector"]),
    "browser_fill_form": ("fill-form", ["fields"]),
    "browser_scroll": ("scroll", ["direction", "amount"]),
    "browser_evaluate_js": ("evaluate-js", ["script"]),
    "browser_scan_xss": ("scan-xss", ["url"]),
    "browser_scan_sqli": ("scan-sqli", ["url"]),
    "browser_transcribe": ("transcribe", ["url", "language"]),
    "browser_save_credentials": ("save-creds", ["domain", "username", "password"]),
    "browser_auto_login": ("auto-login", ["url", "domain"]),
    "browser_tabs": ("tabs", ["action", "tab_id"]),
    "browser_status": ("status", []),
    "browser_type": ("type", ["text"]),
    "browser_press": ("press", ["key"]),
    "browser_hover": ("hover", ["selector"]),
    "browser_back": ("back", []),
    "browser_forward": ("forward", []),
    "browser_reload": ("reload", []),
    "browser_get_links": ("get-links", []),
    "browser_get_images": ("get-images", []),
    "browser_wait": ("wait", ["selector", "timeout"]),
    "browser_scan_sensitive": ("scan-sensitive", []),
    "browser_smart_find": ("smart-find", ["description", "tag", "timeout"]),
    "browser_smart_click": ("smart-click", ["text", "tag", "timeout"]),
    "browser_smart_fill": ("smart-fill", ["label", "value", "timeout"]),
    "browser_workflow": ("workflow", ["steps", "variables", "on_error", "retry_count", "step_delay_ms"]),
    "browser_network_start": ("network-start", ["url_pattern", "resource_types", "methods", "capture_body"]),
    "browser_network_get": ("network-get", ["url_pattern", "resource_type", "method", "status_code", "api_only", "limit", "offset"]),
    "browser_network_apis": ("network-apis", []),
    "browser_page_summary": ("page-summary", []),
    "browser_page_tables": ("page-tables", []),
    "browser_page_seo": ("page-seo", []),
    "browser_emulate_device": ("emulate-device", ["device"]),
    "browser_set_proxy": ("set-proxy", ["proxy_url"]),
    "browser_save_session": ("save-session", ["name"]),
    "browser_restore_session": ("restore-session", ["name"]),
    # Web Query Router
    "browser_classify_query": ("classify-query", ["query"]),
    "browser_needs_web": ("needs-web", ["query"]),
    "browser_query_strategy": ("query-strategy", ["query"]),
    "browser_router_stats": ("router-stats", []),
}


def _to_openai_schema(tool: dict) -> dict:
    """Convert canonical tool def to OpenAI function-calling format."""
    props = {}
    for pname, pschema in tool["params"].items():
        prop = {"type": pschema["type"]}
        if "description" in pschema:
            prop["description"] = pschema["description"]
        if "enum" in pschema:
            prop["enum"] = pschema["enum"]
        if "additionalProperties" in pschema:
            prop["additionalProperties"] = pschema["additionalProperties"]
        props[pname] = prop

    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": {
                "type": "object",
                "properties": props,
                "required": tool["required"],
            },
        },
    }


def _to_claude_schema(tool: dict) -> dict:
    """Convert canonical tool def to Claude tool-use format."""
    props = {}
    for pname, pschema in tool["params"].items():
        prop = {"type": pschema["type"]}
        if "description" in pschema:
            prop["description"] = pschema["description"]
        if "enum" in pschema:
            prop["enum"] = pschema["enum"]
        if "additionalProperties" in pschema:
            prop["additionalProperties"] = pschema["additionalProperties"]
        props[pname] = prop

    return {
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": tool["required"],
        },
    }


# Pre-generate both formats
OPENAI_TOOLS = [_to_openai_schema(t) for t in _TOOL_DEFS]
CLAUDE_TOOLS = [_to_claude_schema(t) for t in _TOOL_DEFS]


def get_tools(format: str = "openai") -> List[Dict]:
    """
    Get tool definitions in the specified format.

    Args:
        format: "openai" for OpenAI function-calling, "claude" for Claude tool-use

    Returns:
        List of tool definitions ready to pass to the API
    """
    if format == "openai":
        return OPENAI_TOOLS
    elif format == "claude":
        return CLAUDE_TOOLS
    else:
        raise ValueError(f"Unknown format: {format!r}. Use 'openai' or 'claude'")


def get_all_tool_names() -> List[str]:
    """Return the names of all available tools."""
    return [t["name"] for t in _TOOL_DEFS]


async def call_tool(tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute an Agent-OS tool via the REST API.

    Args:
        tool_name: Full tool name, e.g. "browser_navigate"
        arguments: Dict of arguments matching the tool's parameters

    Returns:
        JSON response from Agent-OS server
    """
    if arguments is None:
        arguments = {}

    # Handle status as a GET request
    if tool_name == "browser_status":
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{AGENT_OS_URL}/status")
                return resp.json()
            except httpx.ConnectError:
                return {"status": "error", "error": f"Cannot connect to Agent-OS at {AGENT_OS_URL}. Is it running?"}
            except Exception as e:
                return {"status": "error", "error": str(e)}

    if tool_name not in _COMMAND_MAP:
        return {"status": "error", "error": f"Unknown tool: {tool_name}. Available: {get_all_tool_names()}"}

    cmd_name, param_keys = _COMMAND_MAP[tool_name]
    params = {k: arguments[k] for k in param_keys if k in arguments}
    data = {"token": AGENT_TOKEN, "command": cmd_name, **params}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{AGENT_OS_URL}/command", json=data)
            return resp.json()
        except httpx.ConnectError:
            return {"status": "error", "error": f"Cannot connect to Agent-OS at {AGENT_OS_URL}. Is it running?"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ─── Example Usage ────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def demo():
        print(f"Agent-OS Connector — {len(OPENAI_TOOLS)} tools available\n")
        print("=== OpenAI Format (first 2) ===")
        print(json.dumps(OPENAI_TOOLS[:2], indent=2))
        print(f"\n=== Claude Format (first 2) ===")
        print(json.dumps(CLAUDE_TOOLS[:2], indent=2))
        print(f"\nAll tool names:")
        for name in get_all_tool_names():
            print(f"  • {name}")
        print(f"\nAgent-OS URL: {AGENT_OS_URL}")

    asyncio.run(demo())
