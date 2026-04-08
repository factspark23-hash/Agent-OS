# 🤖 Agent OS — AI Agent Browser

A browser built **exclusively for AI agents** — not humans. Zero CAPTCHAs, zero auth walls, zero external services. Runs on 4GB RAM.

## Features

- 🚫 **CAPTCHA Bypass** — Blocks bot-detection queries at the network level before they trigger
- 🤖 **Universal Agent Connector** — Any AI (Claude, Qwen, Kimi, Llama) connects via WebSocket/cURL in 1 command
- 🧠 **Human Mimicry Engine** — Realistic mouse movements, typing rhythms, scroll patterns
- 🔍 **Bug Bounty Scanner** — XSS, SQL injection, sensitive data detection built-in
- 🎬 **Video Transcription** — Watch → extract audio → transcribe locally (Whisper.cpp)
- 📝 **Job Application Automation** — Auto-fill forms, upload resumes, submit applications
- 🔒 **Privacy First** — Sessions auto-wipe after timeout, no telemetry, no disk traces
- ⚡ **4GB RAM Safe** — RAM monitor built-in, CPU-only inference, no GPU needed

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
playwright install chromium

# 2. Launch
python main.py --agent-token "my-agent-123"

# 3. Connect any AI
curl -X POST http://localhost:8000/command -d '{
  "token": "my-agent-123",
  "command": "navigate",
  "url": "https://github.com/login"
}'
```

## Architecture

```
Agent-OS/
├── main.py                    # Entry point & CLI
├── src/
│   ├── core/
│   │   ├── browser.py         # Browser engine with anti-detection
│   │   ├── config.py          # Configuration management
│   │   └── session.py         # Session management & sandboxing
│   ├── agents/
│   │   ├── server.py          # WebSocket/REST agent server
│   │   └── connectors/        # Pre-built connectors for Claude/Qwen/Kimi
│   ├── security/
│   │   ├── captcha_bypass.py  # Query-level CAPTCHA prevention
│   │   ├── human_mimicry.py   # Human behavior simulation
│   │   └── auth_handler.py    # Auto-login & session injection
│   └── tools/
│       ├── scanner.py         # Bug bounty scanner (XSS/SQLi)
│       ├── transcriber.py     # Video transcription
│       └── form_filler.py     # Job application automation
├── tests/
│   └── test_all.py            # Full test suite
└── docs/
    └── API.md                 # Complete API documentation
```

## Connectors (Connect Any AI Agent)

| Connector | Format | Tools | Usage |
|-----------|--------|-------|-------|
| **MCP Server** | Model Context Protocol | 15 | Claude, Codex, any MCP client |
| **OpenAI** | Function Calling | 9 | GPT-4, any OpenAI-compatible API |
| **Claude** | Tool Use | 10 | Anthropic Claude API |
| **OpenClaw** | Manifest | 12 | OpenClaw agent framework |
| **CLI Tool** | Shell script | 14 | Any language via `subprocess` |

### MCP Setup (for Claude Desktop / Codex)
Add to your MCP config:
```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python3",
      "args": ["/path/to/Agent-OS/connectors/mcp_server.py"],
      "env": {
        "AGENT_OS_URL": "http://localhost:8001",
        "AGENT_OS_TOKEN": "your-token-here"
      }
    }
  }
}
```

### OpenAI / Claude API Usage
```python
from connectors.openai_connector import get_tools, call_tool

# For OpenAI
tools = get_tools("openai")  # Pass to OpenAI API

# For Claude
tools = get_tools("claude")  # Pass to Anthropic API

# Call any tool
result = await call_tool("browser_navigate", {"url": "https://github.com"})
```

### CLI Usage (from any language)
```bash
# From bash
./connectors/agent-os-tool.sh navigate "https://github.com"

# From Python
subprocess.run(["./connectors/agent-os-tool.sh", "scan-xss", "https://target.com"])

# From Node.js
execSync("./connectors/agent-os-tool.sh click 'button[type=submit]'")
```

## Requirements

- Python 3.8+
- 4GB RAM minimum
- No GPU required
- No external API keys needed

## License

MIT
