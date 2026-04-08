#!/usr/bin/env python3
"""
Agent-OS Connector Tests
Tests MCP, OpenAI, Claude, OpenClaw, and CLI connectors against a live Agent-OS server.

Run:
    python test_connectors.py
"""
import asyncio
import json
import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "connectors"))

AGENT_OS_URL = "http://localhost:8001"
AGENT_TOKEN = "test-connector-token"

results = {"passed": 0, "failed": 0, "tests": []}


def log_test(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}" + (f" — {detail}" if detail else ""))
    results["tests"].append({"name": name, "passed": passed, "detail": detail})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1


async def test_mcp_tools():
    """Test MCP tool definitions load correctly."""
    print("\n📡 Testing MCP Server...")
    try:
        from connectors.mcp_server import TOOLS
        log_test("MCP tools loaded", len(TOOLS) > 0, f"{len(TOOLS)} tools")
        tool_names = [t.name for t in TOOLS]
        for expected in ["browser_navigate", "browser_click", "browser_fill_form", "browser_scan_xss"]:
            log_test(f"MCP tool '{expected}' exists", expected in tool_names)
    except Exception as e:
        log_test("MCP tools loaded", False, str(e))


async def test_openai_connector():
    """Test OpenAI function definitions."""
    print("\n🤖 Testing OpenAI Connector...")
    try:
        from connectors.openai_connector import get_tools, call_tool
        tools = get_tools("openai")
        log_test("OpenAI tools loaded", len(tools) > 0, f"{len(tools)} tools")

        # Verify format
        for tool in tools[:3]:
            has_type = tool.get("type") == "function"
            has_name = "name" in tool.get("function", {})
            log_test(f"OpenAI tool format valid", has_type and has_name, tool.get("function", {}).get("name", ""))

        # Test Claude format
        claude_tools = get_tools("claude")
        log_test("Claude tools loaded", len(claude_tools) > 0, f"{len(claude_tools)} tools")
        for tool in claude_tools[:3]:
            has_name = "name" in tool
            has_schema = "input_schema" in tool
            log_test(f"Claude tool format valid", has_name and has_schema, tool.get("name", ""))

    except Exception as e:
        log_test("OpenAI connector", False, str(e))


async def test_openclaw_connector():
    """Test OpenClaw connector manifest."""
    print("\n🐾 Testing OpenClaw Connector...")
    try:
        from connectors.openclaw_connector import get_manifest, execute_tool
        manifest = get_manifest()
        log_test("OpenClaw manifest loaded", "tools" in manifest)
        log_test("OpenClaw tools count", len(manifest["tools"]) > 0, f"{len(manifest['tools'])} tools")

        expected_tools = ["browser_navigate", "browser_click", "browser_fill_form", "browser_scan_xss"]
        tool_names = [t["name"] for t in manifest["tools"]]
        for name in expected_tools:
            log_test(f"OpenClaw tool '{name}'", name in tool_names)

    except Exception as e:
        log_test("OpenClaw connector", False, str(e))


async def test_cli_connector():
    """Test CLI connector script."""
    print("\n🔧 Testing CLI Connector...")
    try:
        script = "/root/.openclaw/workspace/Agent-OS/connectors/agent-os-tool.sh"
        log_test("CLI script exists", os.path.exists(script))
        log_test("CLI script executable", os.access(script, os.X_OK))

        # Test help output
        result = subprocess.run([script], capture_output=True, text=True, timeout=5)
        log_test("CLI help output", "Usage:" in result.stdout and "navigate" in result.stdout)

    except Exception as e:
        log_test("CLI connector", False, str(e))


async def test_live_rest_api():
    """Test live REST API connection."""
    print("\n🌐 Testing Live REST API...")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            # Test status endpoint
            resp = await client.get(f"{AGENT_OS_URL}/status")
            log_test("GET /status", resp.status_code == 200, resp.json().get("status", ""))

            # Test commands list
            resp = await client.get(f"{AGENT_OS_URL}/commands")
            cmds = resp.json()
            log_test("GET /commands", resp.status_code == 200 and len(cmds) > 0, f"{len(cmds)} commands")

            # Test navigate command
            resp = await client.post(f"{AGENT_OS_URL}/command", json={
                "token": AGENT_TOKEN, "command": "navigate", "url": "https://example.com"
            })
            result = resp.json()
            log_test("POST /command navigate", result.get("status") == "success", result.get("title", ""))

            # Test get-content
            resp = await client.post(f"{AGENT_OS_URL}/command", json={
                "token": AGENT_TOKEN, "command": "get-content"
            })
            result = resp.json()
            log_test("POST /command get-content", result.get("status") == "success", f"{len(result.get('text', ''))} chars")

            # Test evaluate-js
            resp = await client.post(f"{AGENT_OS_URL}/command", json={
                "token": AGENT_TOKEN, "command": "evaluate-js", "script": "document.title"
            })
            result = resp.json()
            log_test("POST /command evaluate-js", result.get("status") == "success", str(result.get("result", "")))

            # Test fill-form
            resp = await client.post(f"{AGENT_OS_URL}/command", json={
                "token": AGENT_TOKEN, "command": "fill-form",
                "fields": {"h1": "test"}
            })
            result = resp.json()
            log_test("POST /command fill-form", result.get("status") == "success")

    except httpx.ConnectError:
        log_test("Live REST API", False, f"Cannot connect to {AGENT_OS_URL} — start Agent-OS first")
    except Exception as e:
        log_test("Live REST API", False, str(e))


async def test_mcp_protocol():
    """Test MCP server can be imported and has correct handlers."""
    print("\n📋 Testing MCP Protocol...")
    try:
        from mcp.server import Server
        from connectors.mcp_server import server, handle_list_tools, handle_call_tool
        log_test("MCP Server created", server is not None)
        log_test("MCP list_tools handler", handle_list_tools is not None)
        log_test("MCP call_tool handler", handle_call_tool is not None)

        # Test list tools
        tools = await handle_list_tools()
        log_test("MCP list_tools returns tools", len(tools) > 0, f"{len(tools)} tools")

        # Test tool call (if server is running)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{AGENT_OS_URL}/status")
                if resp.status_code == 200:
                    result = await handle_call_tool("browser_status", {})
                    log_test("MCP call_tool browser_status", len(result) > 0)
        except:
            log_test("MCP call_tool (live)", False, "Server not running — skipped")

    except Exception as e:
        log_test("MCP protocol", False, str(e))


async def main():
    print("=" * 60)
    print("  🧪 Agent-OS Connector Test Suite")
    print("=" * 60)

    await test_mcp_tools()
    await test_openai_connector()
    await test_openclaw_connector()
    await test_cli_connector()
    await test_mcp_protocol()
    await test_live_rest_api()

    print("\n" + "=" * 60)
    print(f"  Results: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)

    if results["failed"] > 0:
        print("\n❌ Some tests failed!")
        for t in results["tests"]:
            if not t["passed"]:
                print(f"  - {t['name']}: {t['detail']}")
    else:
        print("\n✅ All connectors working!")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
