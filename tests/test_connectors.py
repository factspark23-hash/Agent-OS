#!/usr/bin/env python3
"""
Agent-OS Connector Tests
Tests MCP, OpenAI, Claude, OpenClaw, and CLI connectors.
Enforces that ALL connectors expose the same 40 tools.

Run:
    python -m pytest tests/test_connectors.py -v
"""
import asyncio
import json
import sys
import os
import subprocess
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "connectors"))

AGENT_OS_URL = "http://localhost:8001"
AGENT_TOKEN = "test-connector-token"

# Canonical 40 tool names — every connector must match this exactly
EXPECTED_TOOLS = sorted([
    "browser_auto_login",
    "browser_back",
    "browser_click",
    "browser_evaluate_js",
    "browser_extract",
    "browser_fill_form",
    "browser_filter_network",
    "browser_find_element",
    "browser_forward",
    "browser_generate_pdf",
    "browser_get_content",
    "browser_get_dom",
    "browser_get_images",
    "browser_get_links",
    "browser_get_markdown",
    "browser_get_network_logs",
    "browser_har_save",
    "browser_har_start",
    "browser_har_stop",
    "browser_hover",
    "browser_navigate",
    "browser_press",
    "browser_proxy",
    "browser_proxy_rotate",
    "browser_reload",
    "browser_save_credentials",
    "browser_scan_sensitive",
    "browser_scan_sqli",
    "browser_scan_xss",
    "browser_screenshot",
    "browser_scroll",
    "browser_set_profile",
    "browser_status",
    "browser_tabs",
    "browser_transcribe",
    "browser_type",
    "browser_wait",
    "browser_webhook_list",
    "browser_webhook_register",
    "browser_webhook_remove",
])


# ─── MCP Connector ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_tools():
    """Test MCP has all 40 tools with correct names."""
    from connectors.mcp_server import TOOLS
    tool_names = sorted([t.name for t in TOOLS])
    assert tool_names == EXPECTED_TOOLS, (
        f"MCP tools mismatch.\n"
        f"  Missing: {set(EXPECTED_TOOLS) - set(tool_names)}\n"
        f"  Extra: {set(tool_names) - set(EXPECTED_TOOLS)}"
    )


# ─── OpenAI Connector ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_openai_connector():
    """Test OpenAI connector has all 40 tools in correct format."""
    from connectors.openai_connector import get_tools, get_all_tool_names

    # Check tool count
    tool_names = sorted(get_all_tool_names())
    assert tool_names == EXPECTED_TOOLS, (
        f"OpenAI tools mismatch.\n"
        f"  Missing: {set(EXPECTED_TOOLS) - set(tool_names)}\n"
        f"  Extra: {set(tool_names) - set(EXPECTED_TOOLS)}"
    )

    # Verify OpenAI format
    openai_tools = get_tools("openai")
    assert len(openai_tools) == 40
    for tool in openai_tools:
        assert tool.get("type") == "function", f"Tool missing type=function: {tool}"
        func = tool.get("function", {})
        assert "name" in func, f"Tool missing function.name: {tool}"
        assert "description" in func, f"Tool missing function.description: {tool}"
        assert "parameters" in func, f"Tool missing function.parameters: {tool}"


@pytest.mark.asyncio
async def test_claude_connector():
    """Test Claude connector has all 40 tools in correct format."""
    from connectors.openai_connector import get_tools

    claude_tools = get_tools("claude")
    assert len(claude_tools) == 40
    tool_names = sorted([t["name"] for t in claude_tools])
    assert tool_names == EXPECTED_TOOLS, (
        f"Claude tools mismatch.\n"
        f"  Missing: {set(EXPECTED_TOOLS) - set(tool_names)}\n"
        f"  Extra: {set(tool_names) - set(EXPECTED_TOOLS)}"
    )

    # Verify Claude format
    for tool in claude_tools:
        assert "name" in tool, f"Claude tool missing name: {tool}"
        assert "description" in tool, f"Claude tool missing description: {tool}"
        assert "input_schema" in tool, f"Claude tool missing input_schema: {tool}"


# ─── OpenClaw Connector ───────────────────────────────────────

@pytest.mark.asyncio
async def test_openclaw_connector():
    """Test OpenClaw connector has all 40 tools."""
    from connectors.openclaw_connector import get_manifest, get_tool_names

    manifest = get_manifest()
    assert "tools" in manifest, "Manifest missing 'tools' key"

    tool_names = sorted(get_tool_names())
    assert len(tool_names) == 40, f"Expected 40 tools, got {len(tool_names)}"
    assert tool_names == EXPECTED_TOOLS, (
        f"OpenClaw tools mismatch.\n"
        f"  Missing: {set(EXPECTED_TOOLS) - set(tool_names)}\n"
        f"  Extra: {set(tool_names) - set(EXPECTED_TOOLS)}"
    )


# ─── CLI Connector ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cli_connector():
    """Test CLI connector script exists and is valid."""
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "connectors", "agent-os-tool.sh")
    assert os.path.exists(script), f"CLI script not found at {script}"
    assert os.access(script, os.X_OK), "CLI script not executable"

    # Test help output contains key commands
    result = subprocess.run([script], capture_output=True, text=True, timeout=5)
    assert "Usage:" in result.stdout, "CLI help missing 'Usage:'"

    expected_commands = [
        "navigate", "click", "type", "press", "fill-form", "hover",
        "scroll", "screenshot", "get-content", "get-dom", "get-links",
        "get-images", "evaluate-js", "scan-xss", "scan-sqli",
        "scan-sensitive", "transcribe", "save-creds", "auto-login",
        "tabs", "back", "forward", "reload", "wait", "status",
    ]
    for cmd in expected_commands:
        assert cmd in result.stdout, f"CLI help missing '{cmd}' command"


# ─── MCP Protocol ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_protocol():
    """Test MCP server can be imported and has correct handlers."""
    from mcp.server import Server
    from connectors.mcp_server import server, handle_list_tools, handle_call_tool
    assert server is not None, "MCP Server not created"
    assert handle_list_tools is not None, "MCP list_tools handler missing"
    assert handle_call_tool is not None, "MCP call_tool handler missing"

    # Test list tools returns all 40
    tools = await handle_list_tools()
    tool_names = sorted([t.name for t in tools])
    assert tool_names == EXPECTED_TOOLS, (
        f"MCP list_tools mismatch.\n"
        f"  Missing: {set(EXPECTED_TOOLS) - set(tool_names)}\n"
        f"  Extra: {set(tool_names) - set(EXPECTED_TOOLS)}"
    )


# ─── Cross-Connector Consistency ──────────────────────────────

def test_all_connectors_match():
    """Verify all connectors expose the exact same set of tools."""
    from connectors.mcp_server import TOOLS as mcp_tools
    from connectors.openai_connector import OPENAI_TOOLS, CLAUDE_TOOLS, get_all_tool_names
    from connectors.openclaw_connector import get_tool_names

    mcp_names = set(t.name for t in mcp_tools)
    openai_names = set(get_all_tool_names())
    claude_names = set(t["name"] for t in CLAUDE_TOOLS)
    openclaw_names = set(get_tool_names())

    assert mcp_names == openai_names == claude_names == openclaw_names, (
        f"Connector tool sets don't match!\n"
        f"  MCP:      {len(mcp_names)} tools\n"
        f"  OpenAI:   {len(openai_names)} tools\n"
        f"  Claude:   {len(claude_names)} tools\n"
        f"  OpenClaw: {len(openclaw_names)} tools\n"
        f"  MCP only:      {mcp_names - openai_names}\n"
        f"  OpenAI only:   {openai_names - mcp_names}\n"
        f"  Claude only:   {claude_names - mcp_names}\n"
        f"  OpenClaw only: {openclaw_names - mcp_names}"
    )


# ─── Live REST API ────────────────────────────────────────────

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
