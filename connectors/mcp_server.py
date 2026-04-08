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
