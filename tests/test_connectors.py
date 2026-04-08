#!/usr/bin/env python3
"""
Agent-OS Connector Tests
Tests MCP, OpenAI, Claude, OpenClaw, and CLI connectors.

Run:
    python -m pytest tests/test_connectors.py -v
"""
import asyncio
import json
import sys
import os
import subprocess
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "connectors"))

AGENT_OS_URL = "http://localhost:8001"
AGENT_TOKEN = "test-connector-token"


@pytest.mark.asyncio
async def test_mcp_tools():
    """Test MCP tool definitions load correctly."""
    from connectors.mcp_server import TOOLS
    assert len(TOOLS) > 0, f"Expected MCP tools, got {len(TOOLS)}"
    tool_names = [t.name for t in TOOLS]
    for expected in ["browser_navigate", "browser_click", "browser_fill_form", "browser_scan_xss"]:
        assert expected in tool_names, f"MCP tool '{expected}' missing"


@pytest.mark.asyncio
async def test_openai_connector():
    """Test OpenAI function definitions."""
    from connectors.openai_connector import get_tools
    tools = get_tools("openai")
    assert len(tools) > 0, "Expected OpenAI tools"

    # Verify format
    for tool in tools[:3]:
        assert tool.get("type") == "function", f"Tool missing type=function: {tool}"
        assert "name" in tool.get("function", {}), f"Tool missing function.name: {tool}"

    # Test Claude format
    claude_tools = get_tools("claude")
    assert len(claude_tools) > 0, "Expected Claude tools"
    for tool in claude_tools[:3]:
        assert "name" in tool, f"Claude tool missing name: {tool}"
        assert "input_schema" in tool, f"Claude tool missing input_schema: {tool}"


@pytest.mark.asyncio
async def test_openclaw_connector():
    """Test OpenClaw connector manifest."""
    from connectors.openclaw_connector import get_manifest
    manifest = get_manifest()
    assert "tools" in manifest, "Manifest missing 'tools' key"
    assert len(manifest["tools"]) > 0, "Expected tools in manifest"

    expected_tools = ["browser_navigate", "browser_click", "browser_fill_form", "browser_scan_xss"]
    tool_names = [t["name"] for t in manifest["tools"]]
    for name in expected_tools:
        assert name in tool_names, f"OpenClaw tool '{name}' missing from manifest"


@pytest.mark.asyncio
async def test_cli_connector():
    """Test CLI connector script exists and is valid."""
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "connectors", "agent-os-tool.sh")
    assert os.path.exists(script), f"CLI script not found at {script}"
    assert os.access(script, os.X_OK), "CLI script not executable"

    # Test help output
    result = subprocess.run([script], capture_output=True, text=True, timeout=5)
    assert "Usage:" in result.stdout, "CLI help missing 'Usage:'"
    assert "navigate" in result.stdout, "CLI help missing 'navigate' command"


@pytest.mark.asyncio
async def test_mcp_protocol():
    """Test MCP server can be imported and has correct handlers."""
    from mcp.server import Server
    from connectors.mcp_server import server, handle_list_tools, handle_call_tool
    assert server is not None, "MCP Server not created"
    assert handle_list_tools is not None, "MCP list_tools handler missing"
    assert handle_call_tool is not None, "MCP call_tool handler missing"

    # Test list tools
    tools = await handle_list_tools()
    assert len(tools) > 0, "MCP list_tools returned empty"


@pytest.mark.asyncio
async def test_live_rest_api():
    """Test live REST API connection (requires Agent-OS running)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{AGENT_OS_URL}/status")
            assert resp.status_code == 200, f"GET /status returned {resp.status_code}"
            data = resp.json()
            assert data.get("status") == "running", f"Server not running: {data}"

            # Test commands list
            resp = await client.get(f"{AGENT_OS_URL}/commands")
            assert resp.status_code == 200, f"GET /commands returned {resp.status_code}"
            cmds = resp.json()
            assert len(cmds) > 0, "No commands available"
    except httpx.ConnectError:
        pytest.skip(f"Cannot connect to {AGENT_OS_URL} — start Agent-OS first")
