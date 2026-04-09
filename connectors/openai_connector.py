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


# ─── Canonical Tool Definitions ───────────────────────────────
# Single source of truth. Both OpenAI and Claude formats are generated from this.

_TOOL_DEFS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL. Built-in anti-detection bypasses CAPTCHAs, reCAPTCHA, hCaptcha, Cloudflare Turnstile, and other bot protection.",
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
    # ── New: Element Finder ──
    {
        "name": "browser_find_element",
        "description": "Find an element by text, ARIA role, aria-label, or natural language description (e.g., 'the login button', 'search input').",
        "params": {
            "description": {"type": "string", "description": "Element description: text, role name, aria-label, or natural language"},
            "method": {"type": "string", "enum": ["smart", "text", "role", "aria-label"], "description": "Search strategy (default: smart)"},
            "exact": {"type": "boolean", "description": "Exact text match (text method only)"},
        },
        "required": ["description"],
    },
    {
        "name": "browser_find_all_interactive",
        "description": "Find all interactive elements (buttons, inputs, links, selects) on the page.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    # ── New: Data Extraction ──
    {
        "name": "browser_extract",
        "description": "Extract structured data from the page: tables, lists, articles, JSON-LD, metadata, links, or all.",
        "params": {
            "type": {"type": "string", "enum": ["tables", "lists", "articles", "jsonld", "metadata", "links", "all"], "description": "Extraction type (default: all)"},
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    # ── New: Markdown ──
    {
        "name": "browser_get_markdown",
        "description": "Convert the current page to clean Markdown. Strips ads, nav, footer, scripts, styles.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    # ── New: PDF ──
    {
        "name": "browser_generate_pdf",
        "description": "Generate a PDF from the current page. Saves to the downloads directory.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
            "format": {"type": "string", "description": "Page format: A4, Letter, etc. (default: A4)"},
            "landscape": {"type": "boolean", "description": "Landscape orientation"},
            "scale": {"type": "number", "description": "Scale factor (0.1-2.0)"},
        },
        "required": [],
    },
    # ── New: HAR Recording ──
    {
        "name": "browser_har_start",
        "description": "Start HAR (HTTP Archive) recording for a page.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    {
        "name": "browser_har_stop",
        "description": "Stop HAR recording for a page.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    {
        "name": "browser_har_save",
        "description": "Save recorded HAR data to a JSON file.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
            "path": {"type": "string", "description": "Output file path (auto-generated if omitted)"},
        },
        "required": [],
    },
    {
        "name": "browser_har_status",
        "description": "Get HAR recording status (active, request count, duration).",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    # ── New: Stealth Profiles ──
    {
        "name": "browser_set_profile",
        "description": "Apply a stealth browser profile to mimic a specific OS/browser combination. Requires browser restart.",
        "params": {
            "profile": {"type": "string", "enum": ["windows-chrome", "mac-safari", "linux-firefox", "mobile-chrome-android", "mobile-safari-ios"], "description": "Stealth profile name"},
        },
        "required": ["profile"],
    },
    {
        "name": "browser_list_profiles",
        "description": "List all available stealth profiles with descriptions.",
        "params": {},
        "required": [],
    },
    # ── New: Network Logs ──
    {
        "name": "browser_get_network_logs",
        "description": "Get network request logs, optionally filtered by URL pattern, status code, or resource type.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
            "url_pattern": {"type": "string", "description": "Filter by URL substring"},
            "status_code": {"type": "integer", "description": "Filter by HTTP status code"},
            "resource_type": {"type": "string", "description": "Resource type (document, xhr, fetch, script, image, etc.)"},
        },
        "required": [],
    },
    {
        "name": "browser_clear_network_logs",
        "description": "Clear captured network request logs for a page.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
        },
        "required": [],
    },
    {
        "name": "browser_get_api_calls",
        "description": "Get XHR/Fetch API calls from the network log.",
        "params": {
            "page_id": {"type": "string", "description": "Tab ID (default: main)"},
            "url_pattern": {"type": "string", "description": "Filter by URL substring"},
        },
        "required": [],
    },
    # ── New: Proxy ──
    {
        "name": "browser_proxy_rotate",
        "description": "Rotate to the next proxy in the configured proxy list. Requires browser restart.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_proxy_status",
        "description": "Get current proxy configuration and status.",
        "params": {},
        "required": [],
    },
    # ── New: Webhooks ──
    {
        "name": "browser_webhook_register",
        "description": "Register a webhook endpoint to receive real-time browser events.",
        "params": {
            "url": {"type": "string", "description": "HTTP(S) URL to receive POST events"},
            "events": {"type": "array", "items": {"type": "string"}, "description": "Event types: navigation, click, form_submit, screenshot, error, session_start, session_end, etc."},
            "secret": {"type": "string", "description": "Optional HMAC-SHA256 secret for signing payloads"},
        },
        "required": ["url", "events"],
    },
    {
        "name": "browser_webhook_list",
        "description": "List all registered webhooks.",
        "params": {},
        "required": [],
    },
    {
        "name": "browser_webhook_remove",
        "description": "Remove a registered webhook by ID.",
        "params": {
            "webhook_id": {"type": "string", "description": "Webhook ID to remove"},
        },
        "required": ["webhook_id"],
    },
    {
        "name": "browser_webhook_test",
        "description": "Send a test ping to verify a webhook is working.",
        "params": {
            "webhook_id": {"type": "string", "description": "Webhook ID to test"},
        },
        "required": ["webhook_id"],
    },
]

# Command map: tool name → (API command name, param keys)
_COMMAND_MAP = {
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
    # New commands
    "browser_find_element": ("find-element", ["description", "method", "exact"]),
    "browser_find_all_interactive": ("find-all-interactive", ["page_id"]),
    "browser_extract": ("extract", ["type", "page_id"]),
    "browser_get_markdown": ("get-markdown", ["page_id"]),
    "browser_generate_pdf": ("generate-pdf", ["page_id", "format", "landscape", "scale"]),
    "browser_har_start": ("har-start", ["page_id"]),
    "browser_har_stop": ("har-stop", ["page_id"]),
    "browser_har_save": ("har-save", ["page_id", "path"]),
    "browser_har_status": ("har-status", ["page_id"]),
    "browser_set_profile": ("set-profile", ["profile"]),
    "browser_list_profiles": ("list-profiles", []),
    "browser_get_network_logs": ("get-network-logs", ["page_id", "url_pattern", "status_code", "resource_type"]),
    "browser_clear_network_logs": ("clear-network-logs", ["page_id"]),
    "browser_get_api_calls": ("get-api-calls", ["page_id", "url_pattern"]),
    "browser_proxy_rotate": ("proxy-rotate", []),
    "browser_proxy_status": ("proxy-status", []),
    "browser_webhook_register": ("webhook-register", ["url", "events", "secret"]),
    "browser_webhook_list": ("webhook-list", []),
    "browser_webhook_remove": ("webhook-remove", ["webhook_id"]),
    "browser_webhook_test": ("webhook-test", ["webhook_id"]),
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
        if "items" in pschema:
            prop["items"] = pschema["items"]
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
        if "items" in pschema:
            prop["items"] = pschema["items"]
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
