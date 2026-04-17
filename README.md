<p align="center">
  <img src="proof/demo_google_search.png" alt="Agent-OS" width="480" />
</p>

<h1 align="center">Agent-OS</h1>

<p align="center">
  <strong>Give any AI agent a real browser — persistent, stealthy, self-hosted.</strong>
</p>

<p align="center">
  Agent-OS is a production-grade stealth browser automation server that gives AI agents
  199 browser tools — navigate, click, fill forms, extract data, handle CAPTCHAs, and more.
  Works with Claude, GPT-4, Codex, OpenClaw, and any agent that can send an HTTP request.
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker Ready" />
  </a>
  <img src="https://img.shields.io/badge/tools-199-brightgreen.svg" alt="199 Tools" />
  <img src="https://img.shields.io/badge/version-3.2.0-orange.svg" alt="Version 3.2.0" />
</p>

---

## Table of Contents

- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [AI Platform Connectors](#ai-platform-connectors)
- [Commands Reference](#commands-reference)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Stealth and Anti-Detection](#stealth-and-anti-detection)
- [Architecture Overview](#architecture-overview)
- [Production Deployment](#production-deployment)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Key Features

### 🌐 Browser Automation — 199 Tools
- **Navigation** — `navigate`, `back`, `forward`, `reload`, `smart-navigate` (auto HTTP/browser strategy)
- **Interaction** — `click`, `double-click`, `right-click`, `hover`, `type`, `press`, `fill-form`, `drag-drop`, `scroll`, `select`, `upload`, `checkbox`
- **Smart Finder** — `smart-click`, `smart-find`, `smart-fill` — find elements by visible text, no CSS selectors needed
- **Content Extraction** — `get-content`, `get-dom`, `screenshot`, `get-links`, `get-images`, `get-text`, `evaluate-js`
- **Page Analysis** — `page-summary`, `page-tables`, `page-seo`, `page-structured`, `page-emails`, `page-phones`, `page-accessibility`
- **Network Capture** — `network-start`, `network-stop`, `network-get`, `network-apis`, `network-export` (HAR/JSON)
- **Security Scanning** — `scan-xss`, `scan-sqli`, `scan-sensitive`
- **Workflows** — `workflow`, `workflow-save`, `workflow-template` — multi-step automation with variables and error handling
- **Sessions** — `save-session`, `restore-session`, `save-creds`, `auto-login`, `get-cookies`, `set-cookie`
- **Tabs** — `tabs list/new/switch/close`, `add-extension`
- **Device Emulation** — 11 presets from iPhone SE to 4K desktop
- **Transcription** — `transcribe` audio/video via Whisper

### 🔧 Advanced Engines
- **Auto-Heal** — Self-healing selectors: if a CSS selector breaks, finds element by nearby text automatically
- **Auto-Retry** — Circuit breaker pattern with intelligent error classification and exponential backoff
- **Smart Wait** — 7 wait strategies: element, network idle, JS condition, DOM stable, page load, composed
- **Session Recording** — Record browser actions, replay them, export as workflows
- **Multi-Agent Hub** — Shared browser sessions, task queues, distributed locks, shared memory between agents
- **Login Handoff** — Pause AI, let human log in, resume with cookies. AI never sees passwords.
- **Proxy Rotation** — Pool management, health checks, geo-targeting, 6 rotation strategies
- **LLM Provider** — Built-in `llm-complete`, `llm-summarize`, `llm-classify`, `llm-extract`
- **AI Content Extraction** — Structured data extraction with schema.org, forms, metadata
- **Query Router** — Classify queries: does this need a browser? 3-tier routing (rules → LLM → conservative)

### 🛡️ Stealth Engine — 26+ Anti-Detection Vectors
- `navigator.webdriver` removal (prototype-level, not `defineProperty`)
- CDP detection blocking (property filtering + intercept)
- WebGL/Canvas/Audio fingerprint spoofing (deterministic, per-session)
- TLS fingerprint bypass (Chrome 145/146 impersonation via curl_cffi)
- HTTP/2 fingerprint matching
- WebRTC IP leak blocking
- 40+ fingerprinting libraries blocked (FingerprintJS, ClientJS, BotD, CreepJS...)
- 15+ bot detection vendors blocked (DataDome, PerimeterX, Cloudflare, Akamai, Kasada...)
- Human-like mouse movements (Bezier curves), typing rhythms, scroll behavior

### 🔌 Connectors — All 199 Tools in Every Connector
| Connector | Tools | Use With |
|-----------|-------|----------|
| MCP Server | 199 | Claude Desktop, Claude Code, Codex, any MCP agent |
| OpenAI | 199 | GPT-4, GPT-4o, any OpenAI-compatible API |
| Claude API | 199 | Claude API (tool-use format) |
| OpenClaw | 199 | OpenClaw agent framework |
| CLI (Bash) | 198 | Any language (Python, Node, Go, Rust...) |
| HTTP REST | 198 | Direct API calls |

---

## Quick Start

### Option 1: One-Command Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

With options:

```bash
# Custom token
curl -sSL .../install.sh | bash -s -- --token my-secret-token

# Show browser window (debugging)
curl -sSL .../install.sh | bash -s -- --headed

# Custom port
curl -sSL .../install.sh | bash -s -- --port 9000

# Install only, don't start
curl -sSL .../install.sh | bash -s -- --no-start
```

### Option 2: Quickstart (Auto-Connect Everything)

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/quickstart.sh | bash
```

This does everything install.sh does PLUS:
- Auto-detects Claude Code, Codex, OpenClaw
- Configures MCP connections automatically
- Prints ready-to-use connection info

### Option 3: Docker Compose

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
export POSTGRES_PASSWORD="strong-db-password"
docker compose up -d
curl http://localhost:8001/health
```

Full stack: PostgreSQL + Redis + Agent-OS + Nginx reverse proxy.

### Option 4: Manual Install

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m patchright install chromium

# Generate JWT secret
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# Start server
python3 main.py --agent-token "your-token"
```

### First Commands

```bash
# Check health
curl http://localhost:8001/health

# Navigate
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://github.com"}'

# Screenshot
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"screenshot"}'

# Click by text (no CSS selector)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"smart-click","text":"Sign in"}'
```

---

## AI Platform Connectors

### 1. Claude Desktop / Claude Code / Codex

Add to your config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Claude Code:** `~/.claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python3",
      "args": ["/absolute/path/to/Agent-OS/connectors/mcp_server.py"],
      "env": {
        "AGENT_OS_URL": "http://localhost:8001",
        "AGENT_OS_TOKEN": "your-token"
      }
    }
  }
}
```

Restart Claude Desktop / Claude Code — **199 browser tools** appear automatically.

### 2. OpenAI / GPT-4

```python
from connectors.openai_connector import get_tools, call_tool

# Get tool definitions
tools = get_tools("openai")  # 199 tools

# Use with OpenAI API
result = await call_tool("browser_navigate", {"url": "https://github.com"})
result = await call_tool("browser_screenshot", {})
result = await call_tool("browser_smart_click", {"text": "Sign In"})
```

### 3. Claude API (Tool-Use)

```python
from connectors.openai_connector import get_tools, call_tool

# Get tools in Claude format
tools = get_tools("claude")  # 199 tools
```

### 4. OpenClaw

```python
from connectors.openclaw_connector import get_manifest, execute_tool

manifest = get_manifest()  # 199 tools
result = await execute_tool("browser_navigate", {"url": "https://example.com"})
```

### 5. CLI / Bash / Any Language

```bash
export AGENT_OS_TOKEN="your-token"

./connectors/agent-os-tool.sh navigate "https://github.com"
./connectors/agent-os-tool.sh screenshot
./connectors/agent-os-tool.sh smart-click "Sign In"
./connectors/agent-os-tool.sh status
```

Run without arguments to see all 198 commands.

### 6. Direct REST API

```bash
# WebSocket port: 8000
# HTTP port: 8001
# Debug UI: 8002 (with --debug)

curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://example.com"}'
```

---

## Commands Reference

All 198 server commands, organized by category:

| Category | Commands | Count |
|----------|----------|-------|
| **Navigation** | `navigate`, `smart-navigate`, `back`, `forward`, `reload`, `route` | 6 |
| **Interaction** | `click`, `double-click`, `right-click`, `context-action`, `hover`, `type`, `press`, `fill-form`, `clear-input`, `select`, `upload`, `checkbox`, `drag-drop`, `drag-offset`, `scroll`, `wait`, `viewport` | 17 |
| **Smart Finder** | `smart-find`, `smart-find-all`, `smart-click`, `smart-fill` | 4 |
| **Content** | `get-content`, `get-dom`, `screenshot`, `get-links`, `get-images`, `get-text`, `get-attr`, `evaluate-js`, `console-logs` | 9 |
| **Page Analysis** | `page-summary`, `page-tables`, `page-seo`, `page-structured`, `page-emails`, `page-phones`, `page-accessibility`, `analyze`, `analyze-search` | 9 |
| **Network** | `network-start`, `network-stop`, `network-get`, `network-apis`, `network-detail`, `network-stats`, `network-export`, `network-clear` | 8 |
| **Security** | `scan-xss`, `scan-sqli`, `scan-sensitive` | 3 |
| **Workflows** | `workflow`, `workflow-save`, `workflow-template`, `workflow-list`, `workflow-status`, `workflow-json` | 6 |
| **Sessions** | `save-session`, `restore-session`, `list-sessions`, `delete-session`, `save-creds`, `auto-login`, `get-cookies`, `set-cookie` | 8 |
| **Tabs & Device** | `tabs`, `add-extension`, `emulate-device`, `list-devices` | 4 |
| **Proxy** | `set-proxy`, `get-proxy` | 2 |
| **Proxy Rotation** | `proxy-add/remove/list/check/check-all/rotate/stats/enable/disable/strategy/save/load/load-file/load-api/record/get` | 16 |
| **Smart Wait** | `smart-wait`, `smart-wait-element/network/js/dom/page/compose` | 7 |
| **Auto-Heal** | `heal-click/fill/hover/double-click/wait/selector/stats/clear/fingerprint/fingerprint-page` | 10 |
| **Auto-Retry** | `retry-navigate/click/fill/execute/api-call/stats/health/circuit-breakers/reset-circuit/reset-all-circuits` | 10 |
| **Recording** | `record-start/stop/pause/resume/status/list/delete/annotate` | 8 |
| **Replay** | `replay-play/stop/pause/resume/step/jump/position/events/load/export-workflow` | 10 |
| **Multi-Agent Hub** | `hub-register/unregister/agents/status/broadcast/handoff/heartbeat/lock/unlock/locks/events/audit` | 12 |
| **Hub Tasks** | `hub-task-create/claim/start/complete/fail/cancel/tasks` | 7 |
| **Hub Memory** | `hub-memory-set/get/list/delete` | 4 |
| **Login Handoff** | `login-handoff-start/status/complete/cancel/list/stats/history`, `detect-login-page` | 8 |
| **TLS HTTP** | `fetch`, `tls-get`, `tls-post`, `tls-stats` | 4 |
| **LLM** | `llm-complete/summarize/classify/extract/provider-set/token-usage/cache-clear` | 7 |
| **AI Content** | `ai-content`, `fill-job`, `structured-extract/format/schema/deduplicate` | 6 |
| **CAPTCHA** | `captcha-assess/preflight/health/monitor-start/monitor-stop/shutdown` | 6 |
| **Query Router** | `classify-query`, `needs-web`, `query-strategy`, `router-stats`, `nav-stats` | 5 |
| **Transcription** | `transcribe` | 1 |
| **Status** | `health` | 1 |
| **Total** | | **198** |

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Production | Auto-generated | JWT signing key. Set for persistent sessions. |
| `POSTGRES_PASSWORD` | Docker | — | PostgreSQL password. |
| `AGENT_TOKEN` | Optional | Auto-generated | Legacy auth token. |
| `DATABASE_DSN` | Optional | — | PostgreSQL connection string. |
| `REDIS_URL` | Optional | — | Redis URL for distributed rate limiting. |
| `PROXY_URL` | Optional | — | HTTP/SOCKS5 proxy URL. |
| `SWARM_PROVIDER_API_KEY` | Optional | — | API key for LLM-based query routing. |

### CLI Arguments

```bash
python3 main.py \
  --agent-token "my-token" \       # Auth token
  --port 8000 \                     # WebSocket port (HTTP = port+1)
  --headed \                        # Show browser window
  --max-ram 500 \                   # RAM limit in MB
  --proxy "http://proxy:8080" \     # Proxy
  --device iphone_14 \              # Device preset
  --persistent \                    # Production mode (persistent Chromium)
  --database "postgresql+asyncpg://..." \
  --redis "redis://localhost:6379/0" \
  --json-logs \                     # JSON structured logging
  --debug \                         # Debug UI (port+2)
  --swarm \                         # Enable query routing
  --create-tables                   # Create DB tables on startup
```

### Device Presets

| Preset | Type | Viewport |
|--------|------|----------|
| `iphone_se` | Mobile | 375×667 |
| `iphone_14` | Mobile | 390×844 |
| `iphone_14_pro_max` | Mobile | 430×932 |
| `galaxy_s23` | Mobile | 360×780 |
| `pixel_8` | Mobile | 412×915 |
| `ipad` | Tablet | 768×1024 |
| `ipad_pro` | Tablet | 1024×1366 |
| `desktop_1080` | Desktop | 1920×1080 |
| `desktop_1440` | Desktop | 2560×1440 |
| `desktop_4k` | Desktop | 3840×2160 |

### Ports

| Port | Service |
|------|---------|
| 8000 | WebSocket (agent connections) |
| 8001 | HTTP REST API |
| 8002 | Debug UI (only with `--debug`) |

---

## Authentication

3-layer auth system, checked in order:

### Layer 1: JWT Tokens (Recommended)

```bash
# Register
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","username":"admin","password":"StrongPass123!"}'

# Login
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPass123!"}'

# Use JWT
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"command":"navigate","url":"https://example.com"}'
```

### Layer 2: API Keys

```bash
# Create key (via JWT)
curl -X POST http://localhost:8001/auth/api-keys \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-key","scopes":["browser"]}'

# Use key (header)
curl -X POST http://localhost:8001/command \
  -H "X-API-Key: aos_your_key" \
  -H "Content-Type: application/json" \
  -d '{"command":"navigate","url":"https://example.com"}'
```

### Layer 3: Legacy Tokens (Development Only)

```bash
python3 main.py --agent-token "my-dev-token"

# Use in requests
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-dev-token","command":"navigate","url":"https://example.com"}'
```

---

## Stealth and Anti-Detection

Agent-OS defeats bot detection with a 4-layer defense system:

### Layer 1: Network
- Chrome TLS fingerprint (JA3/JA4) via curl_cffi
- HTTP/2 fingerprint matching (Chrome 145/146)
- Bot detection scripts blocked at network level
- Fake success responses for reCAPTCHA/hCaptcha

### Layer 2: CDP (Chrome DevTools Protocol)
- Page.addScriptToEvaluateOnNewDocument injection
- User-Agent metadata spoofing
- Timezone and locale override

### Layer 3: JavaScript (19 injection modules)
- `navigator.webdriver` removal (prototype-level)
- CDP property filtering
- Chrome object completeness (runtime, app, csi, loadTimes)
- WebGL/Canvas/Audio fingerprint spoofing
- WebRTC IP leak prevention
- Function toString masking
- Stack trace sanitization

### Layer 4: Behavior
- Bezier-curve mouse movements with micro-tremor
- Realistic typing rhythms (40-300ms per keystroke)
- Word pause simulation (200-600ms)
- Typo simulation with correction (3% rate)
- Natural scroll with micro-variance

### Blocked Vendors
DataDome, PerimeterX, Imperva, Akamai, Cloudflare Bot Management, Cloudflare Turnstile, Kasada, Shape Security, F5, Arkose Labs, ThreatMetrix, hCaptcha, reCAPTCHA

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  External Clients                                            │
│  Claude Desktop │ GPT-4 │ Codex │ CLI │ HTTP/WS            │
└────────┬────────┴───┬─────┴───┬───┴──┬──┴──────┬────────────┘
         │            │         │      │         │
         ▼            ▼         ▼      ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│  Connectors (199 tools each)                                │
│  MCP │ OpenAI │ Claude │ OpenClaw │ CLI │ REST+WebSocket   │
└────────┬──────┴───┬─────┴────┬─────┴──┬──┴──────┬──────────┘
         │          │          │        │         │
         └──────────┴────┬─────┴────────┴─────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent Server (aiohttp)                                     │
│  Auth │ Rate Limiter │ Validator │ Command Router           │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Browser      │ │ Tools Layer  │ │ Infrastructure│
│ (Patchright  │ │ Smart Finder │ │ PostgreSQL   │
│  + Stealth)  │ │ Workflows    │ │ Redis        │
│ 26+ vectors  │ │ Auto-Heal    │ │ JWT Auth     │
│              │ │ Recording    │ │ Logging      │
│              │ │ LLM Provider │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## Production Deployment

### Docker Compose (Recommended)

```bash
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
export POSTGRES_PASSWORD="strong-db-password"
docker compose --profile with-nginx up -d
```

### Production Checklist

- [ ] Set `JWT_SECRET_KEY` (without it, sessions don't survive restarts)
- [ ] Use JWT + API keys (legacy tokens are dev-only)
- [ ] Run behind firewall (use Nginx + SSL for public exposure)
- [ ] Enable Redis for distributed rate limiting
- [ ] Set up PostgreSQL for multi-instance deployments
- [ ] Monitor RAM (~500MB idle, ~800MB under load)
- [ ] Configure CORS for your domain

### Scaling

| Config | Concurrent Users | Memory |
|--------|-----------------|--------|
| 1 instance × 50 contexts | 50 | ~800 MB |
| 3 instances × 50 contexts | 150 | ~2.4 GB |
| 5 instances × 50 contexts | 250 | ~4 GB |

---

## Project Structure

```
Agent-OS/
├── main.py                          # Entry point
├── install.sh                       # One-command installer
├── quickstart.sh                    # Install + auto-connect
├── docker-compose.yml               # Full Docker stack
├── Dockerfile                       # Multi-stage build
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # DB migrations
│
├── src/
│   ├── core/                        # Browser engine
│   │   ├── browser.py               #   Main browser (Patchright/Chromium)
│   │   ├── http_client.py           #   TLS HTTP client (curl_cffi)
│   │   ├── stealth.py               #   Anti-detection JS
│   │   ├── cdp_stealth.py           #   CDP-level stealth
│   │   ├── stealth_god.py           #   GOD MODE (26+ vectors)
│   │   ├── tls_spoof.py             #   TLS fingerprint spoofing
│   │   ├── tls_proxy.py             #   TLS proxy
│   │   ├── smart_navigator.py       #   Auto HTTP/browser strategy
│   │   ├── persistent_browser.py    #   Production persistent Chromium
│   │   ├── llm_provider.py          #   LLM integration
│   │   ├── config.py                #   Configuration (YAML)
│   │   └── session.py               #   Session management
│   │
│   ├── auth/                        # Authentication
│   │   ├── jwt_handler.py           #   JWT (HS256)
│   │   ├── api_key_manager.py       #   API keys (aos_ prefix)
│   │   ├── user_manager.py          #   User registration
│   │   └── middleware.py            #   3-layer auth middleware
│   │
│   ├── security/                    # Stealth & Evasion
│   │   ├── evasion_engine.py        #   Fingerprint generation
│   │   ├── captcha_bypass.py        #   CAPTCHA detection
│   │   ├── captcha_solver.py        #   CAPTCHA solving
│   │   ├── captcha_preempt.py       #   CAPTCHA preemption
│   │   ├── cloudflare_bypass.py     #   Cloudflare bypass
│   │   └── human_mimicry.py         #   Human behavior simulation
│   │
│   ├── tools/                       # Feature engines
│   │   ├── smart_finder.py          #   Find by visible text
│   │   ├── workflow.py              #   Multi-step workflows
│   │   ├── network_capture.py       #   Network request capture
│   │   ├── page_analyzer.py         #   Page analysis
│   │   ├── form_filler.py           #   Form filling
│   │   ├── auto_heal.py             #   Self-healing selectors
│   │   ├── auto_retry.py            #   Auto-retry + circuit breaker
│   │   ├── session_recording.py     #   Record & replay
│   │   ├── multi_agent.py           #   Multi-agent hub
│   │   ├── proxy_rotation.py        #   Proxy pool management
│   │   ├── login_handoff.py         #   Human-in-the-loop login
│   │   ├── ai_content.py            #   AI content extraction
│   │   ├── web_query_router.py      #   Query classification
│   │   └── transcriber.py           #   Audio/video transcription
│   │
│   ├── agents/
│   │   └── server.py                # WebSocket + HTTP server (198 commands)
│   │
│   ├── agent_swarm/                 # Query routing system
│   │   ├── router/                  #   3-tier router
│   │   ├── agents/                  #   Agent profiles
│   │   └── search/                  #   Search backends
│   │
│   ├── infra/                       # Infrastructure
│   │   ├── database.py              #   PostgreSQL (async)
│   │   ├── redis_client.py          #   Redis
│   │   └── logging.py               #   Structured logging
│   │
│   └── validation/
│       └── schemas.py               # Input validation (Pydantic v2)
│
├── connectors/                      # AI Platform Connectors
│   ├── _tool_registry.py            #   199 tool definitions (source of truth)
│   ├── mcp_server.py                #   MCP (Claude/Codex)
│   ├── openai_connector.py          #   OpenAI function-calling
│   ├── openclaw_connector.py        #   OpenClaw
│   ├── agent-os-tool.sh             #   CLI (198 commands)
│   └── mcp_config.json              #   MCP config template
│
├── web/                             # React Web UI
│   ├── src/                         #   React 18 + TypeScript + TailwindCSS
│   └── vite.config.ts               #   Vite 6
│
└── tests/                           # Test suite
```

---

## Development

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m patchright install chromium
python3 main.py --headed --debug --agent-token "dev-token"
```

### Testing

```bash
python3 -m pytest tests/ -v
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | `python3 main.py --port 9000` |
| Chromium not found | `python3 -m patchright install chromium` |
| JWT warning | `export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')` |
| Auth failed | Check token in startup logs or `.env` |
| Site detects bot | Try `--device iphone_14` or add `--proxy` |
| High RAM | `python3 main.py --max-ram 500` |
| DB connection error | Check `docker compose logs postgres` |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Browser | Patchright (stealth Playwright) + Chromium |
| HTTP Client | curl_cffi (Chrome TLS fingerprint) |
| Database | PostgreSQL (SQLAlchemy async) |
| Cache | Redis (with in-memory fallback) |
| Auth | JWT (HS256) + API keys + legacy tokens |
| Web UI | React 18 + Vite 6 + TypeScript + TailwindCSS |
| Validation | Pydantic v2 |
| Logging | structlog |
| Runtime | Python 3.10+ / asyncio |

---

## License

[MIT License](LICENSE) — free for commercial and personal use.
