#!/usr/bin/env python3
"""
Agent-OS MCP Server
Model Context Protocol server for Agent-OS browser automation.
Allows Claude, Codex, and other MCP-compatible agents to control the browser.

Usage:
    python mcp_server.py                    # Starts MCP server on stdio
    AGENT_OS_URL=http://localhost:8001 python mcp_server.py
"""
import os
import json
import sys
import logging
from typing import Any, Dict, List, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Configuration
AGENT_OS_URL = os.environ.get("AGENT_OS_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_OS_TOKEN", "mcp-agent-default")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("agent-os-mcp")

# Create MCP server
server = Server("agent-os")

# ─── Tool Definitions ─────────────────────────────────────────

TOOLS = [
    Tool(
        name="browser_navigate",
        description="Navigate to a URL. The browser has built-in anti-detection to bypass CAPTCHAs and bot protection.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"}
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="browser_fetch",
        description="Fetch a URL using Chrome-impersonating HTTP client. "
        "Bypasses TLS fingerprinting. Returns page title and text.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"}
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="browser_get_content",
        description="Get the current page's HTML content and text.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_get_dom",
        description="Get a structured DOM snapshot of the current page for analysis.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_screenshot",
        description="Take a screenshot of the current page (returns base64 PNG).",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_click",
        description="Click an element on the page using CSS selector. Includes human-like mouse movement.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element to click"}
            },
            "required": ["selector"]
        }
    ),
    Tool(
        name="browser_fill_form",
        description="Fill form fields with human-like typing. Keys are CSS selectors, values are text to type.",
        inputSchema={
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "Dictionary of {selector: value} pairs",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["fields"]
        }
    ),
    Tool(
        name="browser_scroll",
        description="Scroll the page up or down.",
        inputSchema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                "amount": {"type": "integer", "description": "Pixels to scroll", "default": 500}
            }
        }
    ),
    Tool(
        name="browser_evaluate_js",
        description="Execute JavaScript code in the current page context and return the result.",
        inputSchema={
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "JavaScript code to execute"}
            },
            "required": ["script"]
        }
    ),
    Tool(
        name="browser_scan_xss",
        description="Scan a URL for Cross-Site Scripting (XSS) vulnerabilities. Returns found vulnerabilities with payloads.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scan for XSS vulnerabilities"}
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="browser_scan_sqli",
        description="Scan a URL for SQL injection vulnerabilities. Tests URL parameters with various SQLi payloads.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scan for SQL injection"}
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="browser_transcribe",
        description="Transcribe audio/video from a URL using local Whisper. Supports YouTube and direct media URLs.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL of the video/audio to transcribe"},
                "language": {"type": "string", "description": "Language code (e.g., 'en', 'zh') or 'auto'", "default": "auto"}
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="browser_save_credentials",
        description="Save login credentials securely for a domain (AES-256 encrypted).",
        inputSchema={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain (e.g., 'github.com')"},
                "username": {"type": "string", "description": "Username or email"},
                "password": {"type": "string", "description": "Password"}
            },
            "required": ["domain", "username", "password"]
        }
    ),
    Tool(
        name="browser_auto_login",
        description="Automatically log in to a website using previously saved credentials.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Login page URL"},
                "domain": {"type": "string", "description": "Domain with saved credentials"}
            },
            "required": ["url", "domain"]
        }
    ),
    Tool(
        name="browser_tabs",
        description="Manage browser tabs: list, create new, or close tabs.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "new", "close"]},
                "tab_id": {"type": "string", "description": "Tab ID (required for 'close' and optional for 'new')"}
            },
            "required": ["action"]
        }
    ),
    Tool(
        name="browser_status",
        description="Get Agent-OS server status, uptime, and active sessions.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_type",
        description="Type text into the currently focused element with human-like delays.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"}
            },
            "required": ["text"]
        }
    ),
    Tool(
        name="browser_press",
        description="Press a keyboard key (Enter, Tab, Escape, Backspace, etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to press (e.g., 'Enter', 'Tab', 'Escape')"}
            },
            "required": ["key"]
        }
    ),
    Tool(
        name="browser_hover",
        description="Hover the mouse over an element.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element"}
            },
            "required": ["selector"]
        }
    ),
    Tool(
        name="browser_back",
        description="Go back in browser history.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_forward",
        description="Go forward in browser history.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_reload",
        description="Reload the current page.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_get_links",
        description="Get all links on the current page.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_get_images",
        description="Get all images on the current page with src, alt, width, height.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_wait",
        description="Wait for an element to appear on the page.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to wait for"},
                "timeout": {"type": "integer", "description": "Timeout in milliseconds", "default": 10000}
            },
            "required": ["selector"]
        }
    ),
    Tool(
        name="browser_scan_sensitive",
        description="Scan the current page for exposed sensitive data (API keys, tokens, emails, IPs).",
        inputSchema={"type": "object", "properties": {}}
    ),

    # Smart Element Finder
    Tool(
        name="browser_smart_find",
        description="Find an element by visible text or description. No CSS selector needed — works like a human looking at the page.",
        inputSchema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What to find — e.g. 'Sign In', 'email', 'Submit button'"},
                "tag": {"type": "string", "description": "Optional tag filter: 'button', 'input', 'a', etc."},
                "timeout": {"type": "integer", "description": "Max wait time in ms", "default": 5000}
            },
            "required": ["description"]
        }
    ),
    Tool(
        name="browser_smart_click",
        description="Click an element by its visible text. Finds the element automatically — no CSS selector needed.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Visible text of the element to click"},
                "tag": {"type": "string", "description": "Optional tag filter"},
                "timeout": {"type": "integer", "description": "Max wait time in ms", "default": 5000}
            },
            "required": ["text"]
        }
    ),
    Tool(
        name="browser_smart_fill",
        description="Find an input field by its label/placeholder text and fill it with a value.",
        inputSchema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Label or placeholder text of the input field"},
                "value": {"type": "string", "description": "Value to fill in"},
                "timeout": {"type": "integer", "description": "Max wait time in ms", "default": 5000}
            },
            "required": ["label", "value"]
        }
    ),

    # Workflow Engine
    Tool(
        name="browser_workflow",
        description="Execute a multi-step browser workflow in a single command. Supports variables, conditionals, retries.",
        inputSchema={
            "type": "object",
            "properties": {
                "steps": {"type": "array", "description": "Array of step objects, each with 'command' + params"},
                "variables": {"type": "object", "description": "Template variables for {{var}} substitution"},
                "on_error": {"type": "string", "enum": ["abort", "skip", "retry"], "default": "abort"},
                "retry_count": {"type": "integer", "description": "Retries per step on failure", "default": 0},
                "step_delay_ms": {"type": "integer", "description": "Delay between steps in ms", "default": 0}
            },
            "required": ["steps"]
        }
    ),

    # Network Capture
    Tool(
        name="browser_network_start",
        description="Start capturing all network requests on the current page. Filter by URL pattern, method, or resource type.",
        inputSchema={
            "type": "object",
            "properties": {
                "url_pattern": {"type": "string", "description": "Only capture URLs matching this regex"},
                "resource_types": {"type": "array", "items": {"type": "string"}, "description": "Filter: document, script, xhr, fetch, image, etc."},
                "methods": {"type": "array", "items": {"type": "string"}, "description": "Filter: GET, POST, PUT, DELETE"},
                "capture_body": {"type": "boolean", "description": "Capture response bodies (increases memory)", "default": False}
            }
        }
    ),
    Tool(
        name="browser_network_get",
        description="Get captured network requests with optional filters. Returns all requests with headers, status, timing.",
        inputSchema={
            "type": "object",
            "properties": {
                "url_pattern": {"type": "string", "description": "Filter URLs by regex"},
                "resource_type": {"type": "string", "description": "Filter by type: xhr, fetch, document, etc."},
                "method": {"type": "string", "description": "Filter by HTTP method"},
                "status_code": {"type": "integer", "description": "Filter by response status code"},
                "api_only": {"type": "boolean", "description": "Only return API calls (XHR/Fetch)", "default": False},
                "limit": {"type": "integer", "default": 100},
                "offset": {"type": "integer", "default": 0}
            }
        }
    ),
    Tool(
        name="browser_network_apis",
        description="Discover all API endpoints from captured network traffic. Groups by base URL with methods and status codes.",
        inputSchema={"type": "object", "properties": {}}
    ),

    # Page Analyzer
    Tool(
        name="browser_page_summary",
        description="Analyze the current page and return structured summary: title, headings, content, forms, links, detected technologies, readability.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_page_tables",
        description="Extract all HTML tables from the page as structured data (headers + rows).",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_page_seo",
        description="Run a basic SEO audit: title, meta description, H1, alt text, canonical, Open Graph, structured data. Returns score + issues.",
        inputSchema={"type": "object", "properties": {}}
    ),

    # Mobile Emulation
    Tool(
        name="browser_emulate_device",
        description="Emulate a mobile/tablet/desktop device. Changes viewport, user agent, touch support.",
        inputSchema={
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device preset: iphone_14, galaxy_s23, ipad, pixel_8, desktop_1080, etc."}
            },
            "required": ["device"]
        }
    ),

    # Proxy
    Tool(
        name="browser_set_proxy",
        description="Set proxy for the browser. Supports HTTP, HTTPS, SOCKS5. Requires browser restart.",
        inputSchema={
            "type": "object",
            "properties": {
                "proxy_url": {"type": "string", "description": "Proxy URL: http://user:pass@host:port or socks5://host:port"}
            },
            "required": ["proxy_url"]
        }
    ),

    # Session Save/Restore
    Tool(
        name="browser_save_session",
        description="Save full browser state: cookies, localStorage, sessionStorage, open tabs. Restore later with restore_session.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Session name for later retrieval", "default": "default"}
            }
        }
    ),
    Tool(
        name="browser_restore_session",
        description="Restore a previously saved browser session with all cookies, storage, and tabs.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Session name to restore", "default": "default"}
            }
        }
    ),
]


# ─── API Client ───────────────────────────────────────────────

async def agent_os_command(command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Send a command to Agent-OS via HTTP REST API."""
    data = {"token": AGENT_TOKEN, "command": command}
    if params:
        data.update(params)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(f"{AGENT_OS_URL}/command", json=data)
            return response.json()
        except httpx.ConnectError:
            return {"status": "error", "error": f"Cannot connect to Agent-OS at {AGENT_OS_URL}. Make sure it's running."}
        except Exception as e:
            return {"status": "error", "error": str(e)}


async def agent_os_status() -> Dict[str, Any]:
    """Get Agent-OS status."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{AGENT_OS_URL}/status")
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ─── MCP Handlers ─────────────────────────────────────────────

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available Agent-OS tools."""
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from the agent."""
    logger.info(f"Tool call: {name}({json.dumps(arguments)[:200]})")

    command_map = {
        "browser_navigate": ("navigate", ["url"]),
        "browser_fetch": ("fetch", ["url"]),
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
    }

    if name == "browser_status":
        result = await agent_os_status()
    elif name in command_map:
        cmd_name, param_keys = command_map[name]
        params = {k: arguments[k] for k in param_keys if k in arguments}
        result = await agent_os_command(cmd_name, params)
    else:
        result = {"status": "error", "error": f"Unknown tool: {name}"}

    # Format response
    output = json.dumps(result, indent=2)

    # Truncate large responses (screenshots, HTML)
    if len(output) > 10000:
        if "screenshot" in result:
            output = f"[Screenshot captured: {len(result['screenshot'])} bytes base64]"
        elif "html" in result:
            output = f"[HTML content: {len(result['html'])} chars]\n\nText preview:\n{result.get('text', '')[:2000]}"

    return [TextContent(type="text", text=output)]


# ─── Entry Point ──────────────────────────────────────────────

async def main():
    logger.info(f"Agent-OS MCP Server starting...")
    logger.info(f"Agent-OS URL: {AGENT_OS_URL}")
    logger.info(f"Agent Token: {AGENT_TOKEN[:10]}...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
