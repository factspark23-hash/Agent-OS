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
    # Core browser automation
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
    # ── Element Finder ──
    Tool(
        name="browser_find_element",
        description="Find an element by text, ARIA role, aria-label, or natural language (e.g., 'the login button').",
        inputSchema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Element description: text, role, aria-label, or natural language"},
                "method": {"type": "string", "enum": ["smart", "text", "role", "aria-label"], "description": "Search strategy", "default": "smart"},
                "exact": {"type": "boolean", "description": "Exact text match (text method only)", "default": False},
            },
            "required": ["description"]
        }
    ),
    Tool(
        name="browser_find_all_interactive",
        description="Find all interactive elements (buttons, inputs, links, selects) on the page.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    # ── Data Extraction ──
    Tool(
        name="browser_extract",
        description="Extract structured data: tables, lists, articles, JSON-LD, metadata, links, or all.",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["tables", "lists", "articles", "jsonld", "metadata", "links", "all"], "description": "Extraction type", "default": "all"},
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    # ── Markdown ──
    Tool(
        name="browser_get_markdown",
        description="Convert the current page to clean Markdown (strips ads, nav, scripts, styles).",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    # ── PDF ──
    Tool(
        name="browser_generate_pdf",
        description="Generate a PDF from the current page. Saves to the downloads directory.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"},
                "format": {"type": "string", "description": "Page format (A4, Letter, etc.)", "default": "A4"},
                "landscape": {"type": "boolean", "description": "Landscape orientation"},
                "scale": {"type": "number", "description": "Scale factor (0.1-2.0)"}
            }
        }
    ),
    # ── HAR Recording ──
    Tool(
        name="browser_har_start",
        description="Start HAR (HTTP Archive) recording for a page.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    Tool(
        name="browser_har_stop",
        description="Stop HAR recording for a page.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    Tool(
        name="browser_har_save",
        description="Save recorded HAR data to a JSON file.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"},
                "path": {"type": "string", "description": "Output file path (auto-generated if omitted)"}
            }
        }
    ),
    Tool(
        name="browser_har_status",
        description="Get HAR recording status (active, request count, duration).",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Tab ID", "default": "main"}
            }
        }
    ),
    # ── Stealth Profiles ──
    Tool(
        name="browser_set_profile",
        description="Apply a stealth browser profile to mimic specific OS/browser. Requires restart.",
        inputSchema={
            "type": "object",
            "properties": {
                "profile": {"type": "string", "enum": ["windows-chrome", "mac-safari", "linux-firefox", "mobile-chrome-android", "mobile-safari-ios"], "description": "Profile name"}
            },
            "required": ["profile"]
        }
    ),
    Tool(
        name="browser_list_profiles",
        description="List all available stealth profiles with descriptions.",
        inputSchema={"type": "object", "properties": {}}
    ),
    # ── Network Logs ──
    Tool(
        name="browser_get_network_logs",
        description="Get network request logs, optionally filtered by URL pattern, status code, or resource type.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "default": "main"},
                "url_pattern": {"type": "string", "description": "Filter by URL substring"},
                "status_code": {"type": "integer", "description": "Filter by HTTP status code"},
                "resource_type": {"type": "string", "description": "Resource type (document, xhr, fetch, script, etc.)"}
            }
        }
    ),
    Tool(
        name="browser_clear_network_logs",
        description="Clear captured network request logs for a page.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "default": "main"}
            }
        }
    ),
    Tool(
        name="browser_get_api_calls",
        description="Get XHR/Fetch API calls from the network log.",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "default": "main"},
                "url_pattern": {"type": "string", "description": "Filter by URL substring"}
            }
        }
    ),
    # ── Proxy ──
    Tool(
        name="browser_proxy_rotate",
        description="Rotate to the next proxy in the configured list. Requires browser restart.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_proxy_status",
        description="Get current proxy configuration and status.",
        inputSchema={"type": "object", "properties": {}}
    ),
    # ── Webhooks ──
    Tool(
        name="browser_webhook_register",
        description="Register a webhook endpoint to receive real-time browser events.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP(S) URL to receive POST events"},
                "events": {"type": "array", "items": {"type": "string"}, "description": "Event types: navigation, click, form_submit, screenshot, error, session_start, session_end, etc."},
                "secret": {"type": "string", "description": "Optional HMAC-SHA256 secret for signing payloads"}
            },
            "required": ["url", "events"]
        }
    ),
    Tool(
        name="browser_webhook_list",
        description="List all registered webhooks.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="browser_webhook_remove",
        description="Remove a registered webhook by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_id": {"type": "string", "description": "Webhook ID to remove"}
            },
            "required": ["webhook_id"]
        }
    ),
    Tool(
        name="browser_webhook_test",
        description="Send a test ping to verify a webhook is working.",
        inputSchema={
            "type": "object",
            "properties": {
                "webhook_id": {"type": "string", "description": "Webhook ID to test"}
            },
            "required": ["webhook_id"]
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
