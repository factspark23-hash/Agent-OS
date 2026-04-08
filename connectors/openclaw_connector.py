#!/usr/bin/env python3
"""
Agent-OS OpenClaw Integration
Adds Agent-OS browser tools to OpenClaw sessions.

Setup:
    1. Start Agent-OS: python main.py
    2. Configure in OpenClaw config to use this connector
    3. Any OpenClaw agent can now use browser_navigate, browser_click, etc.

This script wraps the Agent-OS REST API into OpenClaw-compatible tool calls.
"""
import os
import json
import httpx

AGENT_OS_URL = os.environ.get("AGENT_OS_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_OS_TOKEN", "openclaw-agent")

TOOLS_MANIFEST = {
    "name": "agent-os-browser",
    "version": "1.0.0",
    "description": "AI Agent Browser — anti-detection browser automation for agents",
    "tools": [
        {
            "name": "browser_navigate",
            "description": "Navigate to a URL with anti-detection (bypasses CAPTCHAs)",
            "parameters": {
                "url": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_get_content",
            "description": "Get page content (HTML + text)",
            "parameters": {}
        },
        {
            "name": "browser_click",
            "description": "Click an element (CSS selector)",
            "parameters": {
                "selector": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_fill_form",
            "description": "Fill form fields",
            "parameters": {
                "fields": {"type": "object", "required": True}
            }
        },
        {
            "name": "browser_screenshot",
            "description": "Take a screenshot",
            "parameters": {}
        },
        {
            "name": "browser_scroll",
            "description": "Scroll page",
            "parameters": {
                "direction": {"type": "string", "default": "down"},
                "amount": {"type": "integer", "default": 500}
            }
        },
        {
            "name": "browser_evaluate_js",
            "description": "Execute JavaScript",
            "parameters": {
                "script": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_scan_xss",
            "description": "Scan for XSS vulnerabilities",
            "parameters": {
                "url": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_scan_sqli",
            "description": "Scan for SQL injection",
            "parameters": {
                "url": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_transcribe",
            "description": "Transcribe video/audio from URL",
            "parameters": {
                "url": {"type": "string", "required": True},
                "language": {"type": "string", "default": "auto"}
            }
        },
        {
            "name": "browser_save_credentials",
            "description": "Save login credentials (encrypted)",
            "parameters": {
                "domain": {"type": "string", "required": True},
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            }
        },
        {
            "name": "browser_auto_login",
            "description": "Auto-login with saved credentials",
            "parameters": {
                "url": {"type": "string", "required": True},
                "domain": {"type": "string", "required": True}
            }
        },
    ]
}


async def execute_tool(tool_name: str, params: dict = None) -> dict:
    """Execute an Agent-OS tool via REST API."""
    cmd = tool_name.replace("browser_", "").replace("_", "-")
    data = {"token": AGENT_TOKEN, "command": cmd}
    if params:
        data.update(params)

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{AGENT_OS_URL}/command", json=data)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}


def get_manifest() -> dict:
    """Return the tools manifest for registration with OpenClaw."""
    return TOOLS_MANIFEST


if __name__ == "__main__":
    print(json.dumps(TOOLS_MANIFEST, indent=2))
    print(f"\nTools ready. Agent-OS URL: {AGENT_OS_URL}")
    print(f"Token: {AGENT_TOKEN[:10]}...")
