# Agent-OS — Browser for AI Agents

A browser automation server built **exclusively for AI agents** — not humans.

Connect any AI (Claude, GPT-4, Codex, OpenClaw, Qwen, local LLMs) and give them a real browser with anti-detection, human mimicry, and full control. Free, open-source, runs locally.

**Stack:** Python + Playwright (Chromium) — no GPU, no cloud, no monthly fees.

## Why Agent-OS?

| Problem | Agent-OS Solution |
|---------|-------------------|
| AI agents can't browse the web | Full browser control via API |
| Bot detection blocks automation | Blocks detection scripts **before they load** — no CAPTCHA ever appears |
| Browser services charge $$$ | Free, open-source, runs on your machine |
| Third-party browsers = no control | Your machine, your browser, your rules |
| APIs don't show what a user sees | Real browser = real user experience |

## Features

- 🛡️ **Anti-Detection** — Blocks reCAPTCHA, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome at the network level (before scripts load)
- 🤖 **25 Browser Tools** — Navigate, click, fill forms, screenshot, scroll, tabs, DOM analysis, and more
- 🧠 **Human Mimicry** — Bezier mouse curves, realistic typing delays, natural scroll behavior
- 🔍 **Security Scanners** — XSS, SQL injection, sensitive data exposure detection
- 🎬 **Video Transcription** — Local Whisper integration (no cloud APIs)
- 🔒 **Privacy First** — Sessions auto-wipe, AES-256 credential vault, zero telemetry
- 🔌 **Connect Any Agent** — MCP (Claude/Codex), OpenAI, Claude API, OpenClaw, CLI — all 25 tools on every connector

## Quick Start

### Option 1: Docker (Recommended)

```bash
# One command. That's it.
docker run -d -p 8000:8000 -p 8001:8001 --name agent-os factspark23-hash/agent-os

# Or with Docker Compose
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
docker compose up -d

# Check it's running
curl http://localhost:8001/status
```

### Option 2: Manual Install

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
chmod +x setup.sh && ./setup.sh
source venv/bin/activate   # if venv was created
python3 main.py --agent-token "my-agent-123"
```

### Test It

```bash
# Navigate to a site
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"navigate","url":"https://github.com"}'

# Get page content
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"get-content"}'
```

## Connect Your AI Agent

All connectors expose the **same 25 tools**. Pick your platform:

### MCP (Claude Desktop / Codex)

Add to your MCP config:

```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python3",
      "args": ["/path/to/Agent-OS/connectors/mcp_server.py"],
      "env": {
        "AGENT_OS_URL": "http://localhost:8001",
        "AGENT_OS_TOKEN": "your-token"
      }
    }
  }
}
```

### OpenAI / Claude API

```python
from connectors.openai_connector import get_tools, call_tool

# Get tool definitions
tools = get_tools("openai")   # For OpenAI GPT-4
tools = get_tools("claude")   # For Anthropic Claude

# Call any tool
result = await call_tool("browser_navigate", {"url": "https://github.com"})
```

### OpenClaw

```python
from connectors.openclaw_connector import get_manifest, execute_tool

manifest = get_manifest()  # 25 tools, register with OpenClaw
result = await execute_tool("browser_click", {"selector": "button[type=submit]"})
```

### CLI (Any Language)

```bash
# Bash
./connectors/agent-os-tool.sh navigate "https://github.com"

# Python
subprocess.run(["./connectors/agent-os-tool.sh", "click", "button.submit"])

# Node.js
execSync("./connectors/agent-os-tool.sh screenshot")
```

## All 42 Tools

| Category | Tools |
|----------|-------|
| **Navigation** | `navigate`, `back`, `forward`, `reload` |
| **Interaction** | `click`, `type`, `press`, `hover`, `fill-form`, `wait`, `double-click`, `right-click`, `context-action` |
| **Content** | `get-content`, `get-dom`, `get-links`, `get-images`, `screenshot` |
| **Control** | `scroll`, `evaluate-js`, `tabs`, `status`, `viewport` |
| **Drag & Drop** | `drag-drop`, `drag-offset` |
| **Forms** | `fill-form`, `clear-input`, `checkbox`, `select`, `upload` |
| **Cookies** | `get-cookies`, `set-cookie`, `console-logs` |
| **Smart Finder** | `smart-find`, `smart-find-all`, `smart-click`, `smart-fill` |
| **Workflows** | `workflow`, `workflow-template`, `workflow-json`, `workflow-save`, `workflow-list`, `workflow-status` |
| **Network** | `network-start`, `network-stop`, `network-get`, `network-apis`, `network-detail`, `network-stats`, `network-export`, `network-clear` |
| **Page Analysis** | `page-summary`, `page-tables`, `page-structured`, `page-emails`, `page-phones`, `page-accessibility`, `page-seo` |
| **Security** | `scan-xss`, `scan-sqli`, `scan-sensitive` |
| **Auth** | `save-credentials`, `auto-login` |
| **Media** | `transcribe` |
| **Proxy** | `set-proxy`, `get-proxy` |
| **Mobile** | `emulate-device`, `list-devices` |
| **Sessions** | `save-session`, `restore-session`, `list-sessions`, `delete-session` |

## How Anti-Detection Works

Agent-OS doesn't solve CAPTCHAs — it **prevents them from loading**:

1. **Network-level blocking** — Detection scripts (reCAPTCHA, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome) are intercepted and blocked before the browser executes them
2. **DOM patching** — `navigator.webdriver`, plugin lists, hardware fingerprints are spoofed
3. **Human mimicry** — Mouse movements use Bezier curves, typing has realistic random delays
4. **Script injection** — Anti-detection JavaScript runs before any page scripts

**What's blocked:** Google reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Imperva, Akamai Bot Manager, Kasada

**Honest limitations:** Advanced TLS fingerprinting can still detect Playwright. Some sophisticated bot protection (BotD) may still work. Effectiveness varies by site — test on your specific targets.

## Architecture

```
Agent-OS/
├── main.py                    # Entry point & CLI
├── Dockerfile                 # Docker build
├── docker-compose.yml         # Docker Compose config
├── setup.sh                   # One-click installer
├── src/
│   ├── core/
│   │   ├── browser.py         # Playwright browser with anti-detection
│   │   ├── config.py          # Configuration management
│   │   └── session.py         # Session lifecycle & auto-wipe
│   ├── agents/
│   │   └── server.py          # WebSocket + REST API server
│   ├── security/
│   │   ├── captcha_bypass.py  # Detection script blocking
│   │   ├── human_mimicry.py   # Bezier mouse, typing simulation
│   │   └── auth_handler.py    # Encrypted credential vault
│   └── tools/
│       ├── scanner.py         # XSS, SQLi, sensitive data scanners
│       ├── transcriber.py     # Video/audio transcription (Whisper)
│       └── form_filler.py     # Smart form detection & filling
├── connectors/
│   ├── mcp_server.py          # MCP (25 tools)
│   ├── openai_connector.py    # OpenAI + Claude (25 tools)
│   ├── openclaw_connector.py  # OpenClaw (25 tools)
│   └── agent-os-tool.sh       # CLI (25+ commands)
├── tests/
│   ├── test_all.py            # Core tests
│   └── test_connectors.py     # Connector consistency tests
└── docs/
    └── API.md                 # Complete API documentation
```

## Configuration

Default config at `~/.agent-os/config.yaml`:

```yaml
server:
  host: 127.0.0.1
  ws_port: 8000
  http_port: 8001

browser:
  headless: true
  viewport: {width: 1920, height: 1080}
  max_ram_mb: 500

session:
  timeout_minutes: 15
  auto_wipe: true

security:
  captcha_bypass: true
  human_mimicry: true
```

## Requirements

- **Python 3.10+** (or just Docker)
- **~500MB RAM** idle, ~800MB under load
- **No GPU required**
- **No external API keys needed**

## Privacy & Security

- **Local only** — all processing on your machine
- **Zero telemetry** — no data leaves your server
- **Session auto-wipe** — data destroyed after timeout
- **Encrypted vault** — credentials stored with AES-256
- **Token auth** — all commands require valid agent token

## License

MIT
