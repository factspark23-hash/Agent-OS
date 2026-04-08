#!/usr/bin/env python3
"""
Agent-OS OpenAI / Claude Tool-Use Connector
Converts Agent-OS commands into OpenAI function-calling / Claude tool-use schemas.

Usage:
    from openai_connector import get_tools, call_tool
    
    # For OpenAI
    tools = get_tools("openai")   # Returns OpenAI function definitions
    result = await call_tool("browser_navigate", {"url": "https://example.com"})
    
    # For Claude
    tools = get_tools("claude")   # Returns Claude tool definitions
"""
import json
import os
import httpx
from typing import Dict, List, Any, Optional

AGENT_OS_URL = os.environ.get("AGENT_OS_URL", "http://localhost:8001")
AGENT_TOKEN = os.environ.get("AGENT_OS_TOKEN", "openai-connector-default")


# ─── OpenAI Function Definitions ─────────────────────────────

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Navigate to a URL. Anti-detection built-in to bypass CAPTCHAs and bot protection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_content",
            "description": "Get current page HTML content and text.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element with human-like mouse movement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill_form",
            "description": "Fill form fields with human-like typing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "object",
                        "description": "{selector: value} pairs",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "required": ["fields"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current page.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_evaluate_js",
            "description": "Execute JavaScript in page context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript code"}
                },
                "required": ["script"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_scan_xss",
            "description": "Scan URL for XSS vulnerabilities.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_scan_sqli",
            "description": "Scan URL for SQL injection vulnerabilities.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_transcribe",
            "description": "Transcribe video/audio from URL (YouTube, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "language": {"type": "string", "default": "auto"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Type text into the currently focused element.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_press",
            "description": "Press a keyboard key (Enter, Tab, Escape, etc.).",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_hover",
            "description": "Hover over an element.",
            "parameters": {
                "type": "object",
                "properties": {"selector": {"type": "string"}},
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_back",
            "description": "Go back in browser history.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_forward",
            "description": "Go forward in browser history.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_links",
            "description": "Get all links on the current page.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_wait",
            "description": "Wait for an element to appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "timeout": {"type": "integer", "default": 10000}
                },
                "required": ["selector"]
            }
        }
    },
]

# ─── Claude Tool Definitions ─────────────────────────────────

CLAUDE_TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL. Anti-detection bypasses CAPTCHAs and bot protection.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to navigate to"}},
            "required": ["url"]
        }
    },
    {
        "name": "browser_get_content",
        "description": "Get current page HTML content and extracted text.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_click",
        "description": "Click an element using CSS selector. Simulates human mouse movement.",
        "input_schema": {
            "type": "object",
            "properties": {"selector": {"type": "string", "description": "CSS selector"}},
            "required": ["selector"]
        }
    },
    {
        "name": "browser_fill_form",
        "description": "Fill form fields with human-like typing rhythm.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Dictionary mapping CSS selectors to values"
                }
            },
            "required": ["fields"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot (returns base64 PNG image).",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"]},
                "amount": {"type": "integer"}
            }
        }
    },
    {
        "name": "browser_evaluate_js",
        "description": "Execute JavaScript and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {"script": {"type": "string"}},
            "required": ["script"]
        }
    },
    {
        "name": "browser_scan_xss",
        "description": "Find XSS vulnerabilities on a URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    },
    {
        "name": "browser_scan_sqli",
        "description": "Find SQL injection vulnerabilities on a URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    },
    {
        "name": "browser_transcribe",
        "description": "Transcribe video/audio using local Whisper.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "language": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into the focused element with human-like delays.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to type"}},
            "required": ["text"]
        }
    },
    {
        "name": "browser_press",
        "description": "Press a keyboard key (Enter, Tab, Escape, Backspace, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string", "description": "Key to press"}},
            "required": ["key"]
        }
    },
    {
        "name": "browser_hover",
        "description": "Hover over an element.",
        "input_schema": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"]
        }
    },
    {
        "name": "browser_back",
        "description": "Go back in browser history.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_forward",
        "description": "Go forward in browser history.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_get_links",
        "description": "Get all links on the current page.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "browser_wait",
        "description": "Wait for an element to appear on the page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "timeout": {"type": "integer"}
            },
            "required": ["selector"]
        }
    },
]


def get_tools(format: str = "openai") -> List[Dict]:
    """Get tool definitions in the specified format."""
    if format == "openai":
        return OPENAI_TOOLS
    elif format == "claude":
        return CLAUDE_TOOLS
    else:
        raise ValueError(f"Unknown format: {format}. Use 'openai' or 'claude'")


async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call an Agent-OS tool."""
    command_map = {
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
    }

    command = command_map.get(tool_name)
    if not command:
        return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    data = {"token": AGENT_TOKEN, "command": command, **arguments}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(f"{AGENT_OS_URL}/command", json=data)
            return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ─── Example Usage ────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def demo():
        print("=== Agent-OS OpenAI Tools ===")
        print(json.dumps(OPENAI_TOOLS[:2], indent=2))
        print(f"\nTotal OpenAI tools: {len(OPENAI_TOOLS)}")
        print(f"Total Claude tools: {len(CLAUDE_TOOLS)}")
        print("\nTo use: AGENT_OS_URL=http://localhost:8001 python openai_connector.py")

    asyncio.run(demo())
