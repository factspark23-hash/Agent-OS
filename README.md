# Agent OS — AI Agent Browser

A browser automation server built **for AI agents** — not humans. Connects via WebSocket/REST API to let any AI agent browse, fill forms, take screenshots, scan for vulnerabilities, and transcribe videos.

**Stack:** Python + Playwright (Chromium) — no Rust, no GPU needed.

## Features

- 🛡️ **Anti-Detection** — Blocks common bot detection scripts (reCAPTCHA, hCaptcha, PerimeterX, Cloudflare Turnstile) at the network level
- 🤖 **Universal Agent Connector** — Any AI connects via WebSocket, REST, MCP, or CLI
- 🧠 **Human Mimicry** — Bezier mouse curves, realistic typing delays, mistake simulation
- 🔍 **Bug Bounty Tools** — XSS scanner, SQL injection detector, sensitive data finder
- 🎬 **Video Transcription** — Local Whisper integration (no cloud APIs)
- 📝 **Form Automation** — Auto-detect and fill form fields with human-like timing
- 🔒 **Privacy First** — Sessions auto-wipe, AES-256 credential vault, no telemetry
- 🔌 **Multi-Connector** — MCP Server, OpenAI function calling, OpenClaw manifest, CLI tool

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Launch
python main.py --agent-token "my-agent-123"

# 4. Connect any AI (from another terminal)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"navigate","url":"https://github.com/login"}'
```

## Architecture

```
Agent-OS/
├── main.py                    # Entry point & CLI
├── src/
│   ├── core/
│   │   ├── browser.py         # Playwright browser with anti-detection
│   │   ├── config.py          # YAML configuration management
│   │   └── session.py         # Session lifecycle & auto-wipe
│   ├── agents/
│   │   └── server.py          # WebSocket + REST API server
│   ├── security/
│   │   ├── captcha_bypass.py  # Bot detection URL blocking
│   │   ├── human_mimicry.py   # Bezier mouse curves, typing simulation
│   │   └── auth_handler.py    # Encrypted credential vault & auto-login
│   └── tools/
│       ├── scanner.py         # XSS, SQLi, sensitive data scanners
│       ├── transcriber.py     # Video/audio transcription (Whisper)
│       └── form_filler.py     # Smart form field detection & filling
├── connectors/
│   ├── mcp_server.py          # MCP protocol (Claude Desktop / Codex)
│   ├── openai_connector.py    # OpenAI / Claude function calling
│   ├── openclaw_connector.py  # OpenClaw agent integration
│   └── agent-os-tool.sh       # CLI tool (any language via subprocess)
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

## API Commands

| Command | Parameters | Description |
|---------|-----------|-------------|
| `navigate` | `url` | Navigate to a URL |
| `fill-form` | `fields` (dict) | Fill form fields with human typing |
| `click` | `selector` | Click element (CSS selector) |
| `screenshot` | — | Take base64 PNG screenshot |
| `get-content` | — | Get HTML + text content |
| `get-dom` | — | Get structured DOM snapshot |
| `scroll` | `direction`, `amount` | Scroll the page |
| `evaluate-js` | `script` | Execute JavaScript |
| `scan-xss` | `url` | Scan for XSS vulnerabilities |
| `scan-sqli` | `url` | Scan for SQL injection |
| `transcribe` | `url`, `language` | Transcribe video/audio |
| `save-creds` | `domain`, `username`, `password` | Save encrypted credentials |
| `auto-login` | `url`, `domain` | Login with saved credentials |
| `tabs` | `action`, `tab_id` | Manage browser tabs |

## How Anti-Detection Works

Agent-OS intercepts requests at the network level:

1. **Request Blocking** — URLs matching bot detection patterns (recaptcha, hcaptcha, perimeterx, cloudflare-challenge) are intercepted and return fake "human verified" responses
2. **Script Blocking** — Bot detection JavaScript is removed before execution
3. **DOM Patching** — `navigator.webdriver`, plugins, hardware info are spoofed
4. **Human Mimicry** — Mouse movements use Bezier curves, typing has realistic delays

### What's Blocked
- Google reCAPTCHA v2/v3
- hCaptcha
- Cloudflare Turnstile
- PerimeterX
- DataDome
- Imperva/Incapsula
- Akamai Bot Manager
- Kasada

### Honest Limitations
- Advanced TLS fingerprinting can still detect Playwright
- Some sophisticated bot protection (like BotD fingerprinting) may still detect automation
- Anti-detection effectiveness varies by site — test on your specific targets

## Configuration

Default config at `~/.agent-os/config.yaml`:

```yaml
server:
  host: 127.0.0.1
  ws_port: 8000
  http_port: 8001
  max_connections: 10

browser:
  headless: true
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
  viewport: {width: 1920, height: 1080}
  max_ram_mb: 500
  page_timeout_ms: 30000

session:
  timeout_minutes: 15
  auto_wipe: true
  max_concurrent: 3

security:
  captcha_bypass: true
  human_mimicry: true
  block_bot_queries: true
  session_encryption: true
```

## Running Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

## Requirements

- Python 3.10+
- ~500MB RAM (idle), ~800MB under load
- No GPU required
- No external API keys needed (unless using transcription, which needs yt-dlp + whisper)

## Privacy & Security

- **Session Data**: Auto-wiped after timeout (default 15 min)
- **Credentials**: Encrypted with Fernet (AES-128-CBC), stored at `~/.agent-os/vault.enc`
- **No Telemetry**: Zero data collection
- **Local Only**: All processing on-device
- **Token Auth**: All commands require a valid agent token

## License

MIT
