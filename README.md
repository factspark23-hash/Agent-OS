# Agent-OS

**Give any AI agent a real browser. Not a sandbox. Not a viewer. A real, persistent, undetectable browser it actually owns.**

Claude can peek at webpages. GPT can fetch URLs. But none of them can:
- Stay logged into your accounts across sessions
- Fill out forms like a human would
- Bypass bot detection without getting blocked
- Download files, manage tabs, run extensions
- Work across multiple sessions without losing state

Agent-OS fixes that. One local server. Any AI connects. Full browser access.

**Stack:** Python + Chromium (Playwright) — no GPU, no cloud, no API keys, no monthly fees.

---

## The Problem

| What AI agents need | What they actually get |
|---|---|
| Persistent login sessions | Sandbox that resets every time |
| Fill forms, click buttons, manage tabs | "Here's the page HTML, good luck" |
| Browse without getting blocked | Instantly flagged as a bot |
| Works with any AI platform | Locked into one provider's browser |
| Runs on your machine, your rules | Cloud service with your data on their servers |

**Claude MCP browser:** Sandboxed viewer. No cookies, no persistence, no real interaction.  
**OpenClaw browser:** Basic Playwright automation. No stealth, no credential management.  
**Browserbase/Browserless:** Cloud-hosted. Your data on their servers. $$$ per month.  
**Raw Playwright:** Build everything yourself. Good luck with bot detection.

**Agent-OS:** Real Chromium. Persistent sessions. Anti-detection. Credential vault. Self-hosted. Free. Works with any AI.

---

## What You Actually Get

### 🔒 Persistent Browser Sessions
Login once, stay logged in. Sessions survive across commands, restarts, and even machine reboots. Your AI agent remembers who it is on every site.

### 🛡️ Network-Level Anti-Detection
Agent-OS doesn't solve CAPTCHAs — it prevents them from loading. Detection scripts (reCAPTCHA, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Akamai) are intercepted and blocked before the browser executes them.

### 🧠 Human Behavior Simulation
Mouse movements follow Bezier curves. Typing has randomized delays. Scrolling feels natural. To bot detection systems, Agent-OS looks like a human — because it acts like one.

### 🔐 Encrypted Credential Vault
Save login credentials with AES-256 encryption. Auto-login to any site on command. Credentials never leave your machine.

### 🔌 Connect Any AI
Every connector exposes the same tools. Pick your platform:

- **MCP** → Claude Desktop, Codex
- **OpenAI API** → GPT-4, any OpenAI-compatible model
- **Claude API** → Anthropic models
- **OpenClaw** → OpenClaw agents
- **CLI** → Bash, Python, Node.js, anything that can run a shell command
- **HTTP/WebSocket** → Any language, any framework

### 🎬 Video Transcription
Local Whisper integration. Transcribe any video or audio. No cloud APIs, no data leaving your machine.

---

## Quick Start

### Docker (Recommended)

```bash
docker run -d \
  -p 8000:8000 \
  -p 8001:8001 \
  --name agent-os \
  agent-os

# Or with Docker Compose
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
docker compose up -d
```

### Manual Install

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
chmod +x setup.sh && ./setup.sh
python3 main.py --agent-token "my-agent-123"
```

### Verify It's Running

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token": "my-agent-123", "command": "navigate", "url": "https://github.com"}'
```

---

## Usage Examples

### Navigate and Extract Content
```bash
# Go to a page
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "navigate", "url": "https://news.ycombinator.com"}'

# Get everything on the page
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "get-content"}'

# Get all links
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "get-links"}'
```

### Save Login and Auto-Login Later
```bash
# Save credentials after manually logging in
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "save-creds", "site": "github.com"}'

# Auto-login on next session
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "auto-login", "site": "github.com"}'
```

### Fill Forms Automatically
```bash
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "fill-form", "fields": {"name": "John", "email": "john@example.com"}}'
```

### Take a Screenshot
```bash
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "screenshot"}'
```

---

## All Tools

| Category | Tools |
|----------|-------|
| **Navigation** | `navigate`, `back`, `forward`, `reload` |
| **Interaction** | `click`, `type`, `press`, `hover`, `fill-form`, `wait`, `double-click`, `right-click`, `drag-drop` |
| **Content** | `get-content`, `get-dom`, `get-links`, `get-images`, `get-text`, `get-attr`, `screenshot` |
| **Control** | `scroll`, `evaluate-js`, `tabs`, `viewport`, `console-logs` |
| **Forms** | `fill-form`, `fill-job`, `select`, `checkbox`, `upload`, `clear-input` |
| **Auth** | `save-creds`, `auto-login`, `get-cookies`, `set-cookie` |
| **Media** | `transcribe` |

---

## Connect Your Agent

### MCP (Claude Desktop / Codex)

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

tools = get_tools("openai")   # Tool definitions for GPT-4
tools = get_tools("claude")   # Tool definitions for Claude

result = await call_tool("browser_navigate", {"url": "https://github.com"})
```

### OpenClaw

```python
from connectors.openclaw_connector import get_manifest, execute_tool

manifest = get_manifest()
result = await execute_tool("browser_click", {"selector": "button[type=submit]"})
```

### CLI (Any Language)

```bash
./connectors/agent-os-tool.sh navigate "https://github.com"
./connectors/agent-os-tool.sh screenshot
./connectors/agent-os-tool.sh get-content
```

---

## How Anti-Detection Works

Agent-OS uses Playwright's route interception to block detection scripts **before they execute**:

1. **Route interception** — Requests to known detection domains (google.com/recaptcha, hcaptcha.com, challenges.cloudflare.com, etc.) are blocked at the network level
2. **DOM patching** — `navigator.webdriver`, plugin lists, hardware fingerprints are spoofed before any page script runs
3. **Human mimicry** — Mouse movements use Bezier curves, typing has realistic random delays, scroll behavior matches human patterns

**What's blocked:** Google reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Imperva, Akamai Bot Manager, Kasada

**Honest limitations:** Advanced TLS fingerprinting can detect Playwright. Some sophisticated bot protection (BotD) may still work. Effectiveness varies by site.

---

## Architecture

```
Agent-OS/
├── main.py                    # Entry point
├── Dockerfile                 # Docker build (multi-stage, ~350MB)
├── docker-compose.yml         # One-command deploy
├── setup.sh                   # Auto-installer
├── src/
│   ├── core/
│   │   ├── browser.py         # Playwright + anti-detection
│   │   ├── config.py          # YAML config management
│   │   └── session.py         # Session lifecycle + auto-wipe
│   ├── agents/
│   │   └── server.py          # WebSocket + REST API
│   ├── security/
│   │   ├── captcha_bypass.py  # Detection script blocking
│   │   ├── human_mimicry.py   # Bezier mouse, typing simulation
│   │   └── auth_handler.py    # AES-256 credential vault
│   └── tools/
│       ├── scanner.py         # Security scanners
│       ├── transcriber.py     # Whisper transcription
│       └── form_filler.py     # Smart form detection
├── connectors/
│   ├── mcp_server.py          # MCP connector
│   ├── openai_connector.py    # OpenAI + Claude
│   ├── openclaw_connector.py  # OpenClaw
│   └── agent-os-tool.sh       # CLI
└── tests/                     # 29 tests, all passing
```

---

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

---

## Requirements

- **Python 3.10+** (or just Docker)
- **~500MB RAM** idle, ~800MB under load
- **No GPU required**
- **No external API keys needed**

---

## Privacy & Security

- **Local only** — everything runs on your machine
- **Zero telemetry** — no data leaves your server
- **Session auto-wipe** — data destroyed after timeout
- **AES-256 vault** — credentials encrypted at rest
- **Token auth** — all commands require valid agent token

---

## License

MIT
