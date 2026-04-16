<p align="center">
  <img src="proof/demo_google_search.png" alt="Agent-OS" width="480" />
</p>

<h1 align="center">Agent-OS</h1>

<p align="center">
  <strong>Give any AI agent a real browser — persistent, stealthy, self-hosted.</strong>
</p>

<p align="center">
  Agent-OS is a Python stealth browser automation server that lets AI agents browse the web
  like a human: clicking, typing, filling forms, and extracting data across persistent sessions
  — all while defeating 26+ anti-detection vectors. Works with Claude, GPT-4, Codex, and any agent
  that can send an HTTP request.
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
  <img src="https://img.shields.io/badge/version-3.2.0-orange.svg" alt="Version 3.2.0" />
</p>

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Stealth and Anti-Detection](#stealth-and-anti-detection)
- [Agent Swarm and Query Routing](#agent-swarm-and-query-routing)
- [AI Platform Connectors](#ai-platform-connectors)
- [Web UI](#web-ui)
- [Commands Reference](#commands-reference)
- [Production Deployment](#production-deployment)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Key Features

### Browser Automation
- **60+ Commands** — Navigate, click, type, screenshot, scan, extract data, manage sessions, and more
- **Smart Navigation** — Automatically picks HTTP-first or full browser strategy per site
- **Persistent Sessions** — Login once, stay logged in across restarts (AES-256 encrypted credentials)
- **11 Device Presets** — iPhone SE to 4K desktop, with accurate viewport, touch, and user agent
- **Multi-Tab Support** — Create, switch, and close browser tabs dynamically
- **Smart Element Finder** — Click and fill elements by visible text — no CSS selectors needed

### Stealth Engine
- **26+ Anti-Detection Layers** — Covers navigator, CDP, WebGL, Canvas, Audio, TLS, HTTP/2, and more
- **Blocks 15+ Bot-Detection Vendors** — DataDome, PerimeterX, Cloudflare, Imperva, Akamai, Kasada, and others
- **Blocks 40+ Fingerprinting Libraries** — FingerprintJS, ClientJS, ThumbmarkJS, CreepJS, BotD, and more
- **Human Mimicry** — Bezier-curve mouse movements, realistic typing rhythms, natural scroll behavior
- **Consistent Fingerprints** — Cross-vector consistency ensures WebGL, Canvas, and hardware profiles match

### Intelligence
- **3-Tier Query Router** — Determines when an AI agent should use the browser, at zero extra LLM cost
- **6 Query Categories** — `needs_web`, `needs_calculation`, `needs_security`, `needs_code`, `needs_knowledge`, `ambiguous`
- **100+ Weighted Patterns** — Rule-based classification with anti-false-positive override guards
- **Agent Swarm** — Search/routing module with specialized agent profiles for different query types

### Connectors
- **MCP Server** — Claude Desktop, Claude Code, OpenAI Codex, any MCP-compatible agent
- **OpenAI Function Calling** — GPT-4, GPT-4o, any OpenAI-compatible API
- **OpenClaw** — OpenClaw agent framework
- **CLI / Bash** — Universal shell connector for any language (Python, Node, Go, Rust, etc.)
- **REST + WebSocket** — Direct HTTP and WebSocket APIs for custom integrations

### Web UI
- **React 18 + Vite 6 + TypeScript + TailwindCSS + Zustand** — Modern, responsive dashboard
- **Live Browser View** — Real-time browser viewport and command execution
- **API Key Management** — Create, revoke, and scope API keys from the UI
- **Swarm Control** — Monitor and manage agent swarm activity
- **Settings Panel** — Configure server, browser, and security options

### Infrastructure
- **PostgreSQL + Redis** — Production-grade data persistence and distributed rate limiting
- **3-Layer Authentication** — JWT (HS256) + API Keys (`aos_` prefix) + Legacy tokens
- **Docker Compose** — Full stack with PostgreSQL, Redis, Agent-OS, and Nginx reverse proxy
- **Structured Logging** — JSON or human-readable output via structlog
- **Pydantic v2 Validation** — Input validation on all commands

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Clients                             │
│   Claude Desktop  │  GPT-4  │  Codex  │  CLI  │  Custom HTTP/WS   │
└────────┬──────────┴────┬─────┴────┬─────┴───┬───┴────────┬─────────┘
         │               │          │         │            │
         ▼               ▼          ▼         ▼            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Connectors                                 │
│   MCP Server  │  OpenAI FC  │  OpenClaw  │  CLI  │  REST + WebSocket│
└────────┬──────┴──────┬──────┴──────┬─────┴───┬───┴────────┬────────┘
         │             │             │         │            │
         └─────────────┴──────┬──────┴─────────┴────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Agent Server (aiohttp)                         │
│  ┌──────────┐  ┌───────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │   Auth   │  │  Rate Limiter  │  │ Validator │  │  Command    │  │
│  │  Layer   │  │  (Redis/Mem)   │  │ (Pydantic)│  │  Router     │  │
│  └──────────┘  └───────────────┘  └───────────┘  └──────┬──────┘  │
└─────────────────────────────────────────────────────────┼──────────┘
                                                          │
                              ┌───────────────────────────┤
                              │                           │
                              ▼                           ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────┐
│           Core Engine Layer          │  │        Tools Layer             │
│  ┌──────────┐ ┌──────────┐          │  │ ┌────────────┐ ┌────────────┐ │
│  │ Browser  │ │ Stealth  │          │  │ │ Smart      │ │ Workflow   │ │
│  │(Patchright│ │ Engine   │          │  │ │ Finder     │ │ Engine     │ │
│  │/Chromium)│ │(26+ vec) │          │  │ └────────────┘ └────────────┘ │
│  └──────────┘ └──────────┘          │  │ ┌────────────┐ ┌────────────┐ │
│  ┌──────────┐ ┌──────────┐          │  │ │ Network    │ │ Security   │ │
│  │ Session  │ │Persistent│          │  │ │ Capture    │ │ Scanner    │ │
│  │ Manager  │ │ Browser  │          │  │ └────────────┘ └────────────┘ │
│  └──────────┘ └──────────┘          │  │ ┌────────────┐ ┌────────────┐ │
│  ┌──────────┐ ┌──────────┐          │  │ │ Page       │ │ Agent      │ │
│  │ HTTP     │ │ TLS      │          │  │ │ Analyzer   │ │ Swarm      │ │
│  │ Client   │ │ Spoof    │          │  │ └────────────┘ └────────────┘ │
│  └──────────┘ └──────────┘          │  └───────────────────────────────┘
└──────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│       Infrastructure Layer           │
│  ┌──────────┐  ┌───────┐  ┌───────┐ │
│  │PostgreSQL│  │ Redis │  │Config │ │
│  │(SQLAsync)│  │(Cache)│  │(YAML) │ │
│  └──────────┘  └───────┘  └───────┘ │
│  ┌──────────┐  ┌───────────────────┐ │
│  │ Logging  │  │   Web UI          │ │
│  │(structlog)│  │(React + Vite)    │ │
│  └──────────┘  └───────────────────┘ │
└──────────────────────────────────────┘
```

### Request Flow

```
Agent (AI) ──► WebSocket/HTTP ──► Auth Check ──► Rate Limit ──► Validate
                                                                     │
                                                                     ▼
                                                             Command Router
                                                                     │
                                       ┌───────────┬─────────────────┤
                                       ▼           ▼                 ▼
                                  Browser       Tools            Infra
                                  (navigate,   (workflow,       (DB/Redis)
                                   click,      scanner,
                                   screenshot  etc.)
                                   etc.)
```

---

## Quick Start

### Option 1: One-Command Install (Recommended)

```bash
# Install and start — token and URL are printed at the end
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash

# Test it
curl http://localhost:8001/health
```

With options:

```bash
# Custom authentication token
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash -s -- --token my-secret-token

# Show browser window (debugging)
curl -sSL ... | bash -s -- --headed

# Custom port
curl -sSL ... | bash -s -- --port 9000

# Install only, do not start
curl -sSL ... | bash -s -- --no-start
```

### Option 2: Docker Compose

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS

# Set required environment variable
export POSTGRES_PASSWORD="strong-db-password"

# Start the full stack (PostgreSQL + Redis + Agent-OS + Nginx)
docker compose up -d

# Verify
curl http://localhost:8001/health
```

The Docker stack includes PostgreSQL, Redis, Agent-OS, and an Nginx reverse proxy — all isolated in a Docker network with resource limits and health checks.

### Option 3: Manual Install

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Chromium browser
python3 -m patchright install chromium

# Generate a JWT secret key (required for production)
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# Start the server
python3 main.py --agent-token "your-token"
```

### First Commands

```bash
# Check server health
curl http://localhost:8001/health

# Navigate to a website
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://github.com"}'

# Take a screenshot
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"screenshot"}'

# Get page content
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"get-content"}'

# Click by visible text (no CSS selector needed)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"smart-click","text":"Sign in"}'
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root or set environment variables directly:

| Variable | Required | Default | Description |
|---|---|---|---|
| `JWT_SECRET_KEY` | Production | Auto-generated | Secret key for JWT signing. Must be set for persistent sessions. |
| `POSTGRES_PASSWORD` | Docker | — | PostgreSQL password. Required for Docker deployments. |
| `AGENT_TOKEN` | Optional | Auto-generated | Legacy authentication token for development. |
| `DATABASE_DSN` | Optional | — | PostgreSQL connection string (`postgresql+asyncpg://user:pass@host/db`). |
| `REDIS_URL` | Optional | — | Redis URL for distributed rate limiting (`redis://localhost:6379/0`). |
| `PROXY_URL` | Optional | — | HTTP/SOCKS5 proxy URL (`http://user:pass@proxy:8080`). |
| `PROXY_PROVIDER` | Optional | — | Proxy provider type (`rotating`, `static`). |
| `SWARM_PROVIDER_API_KEY` | Optional | — | API key for Tier 2 ProviderRouter (your existing LLM provider). |
| `SWARM_PROVIDER_BASE_URL` | Optional | `https://api.openai.com/v1` | Base URL for Tier 2 provider. |
| `SWARM_PROVIDER_MODEL` | Optional | `gpt-4o` | Model for Tier 2 provider. |

### CLI Arguments

```bash
python3 main.py \
  --agent-token "my-token" \          # Legacy authentication token
  --port 8000 \                       # WebSocket port (HTTP = port+1, Debug = port+2)
  --headed \                          # Show browser window (for debugging)
  --max-ram 500 \                     # RAM limit in MB
  --proxy "http://proxy:8080" \       # HTTP/SOCKS5 proxy
  --device iphone_14 \                # Device preset to emulate
  --persistent \                      # Enable persistent Chromium (production)
  --database "postgresql+asyncpg://..." \  # PostgreSQL connection
  --redis "redis://localhost:6379/0" \     # Redis connection
  --json-logs \                       # JSON structured logging
  --log-level INFO \                  # Log level: DEBUG, INFO, WARNING, ERROR
  --rate-limit 60 \                   # Max requests per minute per token
  --debug \                           # Enable debug UI server (port+2)
  --swarm \                           # Enable Agent Swarm (search) module
  --swarm-api-key "key" \             # API key for swarm endpoints
  --create-tables                     # Create database tables on startup
```

### Config File

Agent-OS auto-creates `~/.agent-os/config.yaml` with sensible defaults on first run. Key sections:

```yaml
server:          # Host, ports (WS:8000, HTTP:8001, Debug:8002), CORS, rate limits
browser:         # Headless, viewport, user agent, proxy, device, timeout
session:         # Timeout (15min), auto-wipe, max concurrent (3)
security:        # Captcha bypass, human mimicry, JWT, API key auth
database:        # PostgreSQL DSN, pool size (disabled by default)
redis:           # Redis URL (disabled by default, has in-memory fallback)
jwt:             # Secret key, HS256, token expiry
persistent:      # Long-running Chromium settings
scanner:         # Rate limits for security scans
transcription:   # Whisper model selection
logging:         # Level, JSON format, service name
```

Access config programmatically:

```python
config.get("browser.max_ram_mb")     # Dotted key access
config.set("server.ws_port", 9000)   # Set value
config.set("x.y", val, save=True)    # Set and persist to YAML
```

### Device Presets

| Preset | Device | Viewport | Type |
|---|---|---|---|
| `iphone_se` | iPhone SE | 375 x 667 | Mobile |
| `iphone_14` | iPhone 14 | 390 x 844 | Mobile |
| `iphone_14_pro_max` | iPhone 14 Pro Max | 430 x 932 | Mobile |
| `galaxy_s23` | Samsung Galaxy S23 | 360 x 780 | Mobile |
| `pixel_8` | Google Pixel 8 | 412 x 915 | Mobile |
| `ipad` | iPad | 768 x 1024 | Tablet |
| `ipad_pro` | iPad Pro | 1024 x 1366 | Tablet |
| `galaxy_tab_s9` | Samsung Galaxy Tab S9 | 800 x 1280 | Tablet |
| `desktop_1080` | Desktop | 1920 x 1080 | Desktop |
| `desktop_1440` | Desktop | 2560 x 1440 | Desktop |
| `desktop_4k` | Desktop | 3840 x 2160 | Desktop |

### Ports

| Port | Service |
|---|---|
| 8000 | WebSocket (agent connections) |
| 8001 | HTTP REST API |
| 8002 | Debug UI dashboard (only with `--debug`) |

---

## API Reference

### Core Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/command` | POST | Required | Execute any tool command |
| `/health` | GET | None | Server health check — uptime, active sessions, browser state |
| `/status` | GET | None | Server status with details |
| `/commands` | GET | None | List all available commands with parameters |
| `/screenshot` | GET | Required | Quick screenshot (returns base64 PNG) |

### Authentication Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/auth/register` | POST | None | Register a new user |
| `/auth/login` | POST | None | Login and receive JWT tokens |
| `/auth/refresh` | POST | JWT | Refresh an expired access token |
| `/auth/api-keys` | POST | JWT | Create a new API key |
| `/auth/api-keys` | GET | JWT | List your API keys |
| `/auth/api-keys/{id}` | DELETE | JWT | Revoke an API key |

### Persistent Browser Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/persistent/health` | GET | Required | Full health report of all browser instances |
| `/persistent/users` | GET | Required | List all active user contexts |
| `/persistent/command` | POST | Required | Execute a command for a specific user |

### Examples

**Navigate to a URL:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://github.com/login"}'
```

Response:
```json
{
  "status": "success",
  "url": "https://github.com/login",
  "title": "Sign in to GitHub",
  "status_code": 200,
  "blocked_requests": 5
}
```

**Fill a login form:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"fill-form","fields":{"#login_field":"user@example.com","#password":"secret123"}}'
```

**Smart click by visible text:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"smart-click","text":"Sign in"}'
```

**Take a full-page screenshot:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"screenshot","full_page":true}'
```

**Execute a multi-step workflow:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{
    "token":"your-token",
    "command":"workflow",
    "steps":[
      {"command":"navigate","url":"https://google.com"},
      {"command":"fill-form","fields":{"input[name=q]":"{{query}}"}},
      {"command":"press","key":"Enter"},
      {"command":"wait","selector":"#search"},
      {"command":"get-content"}
    ],
    "variables":{"query":"Agent-OS"},
    "on_error":"abort",
    "retry_count":1
  }'
```

**Classify a query with the router:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"classify-query","query":"What is the weather in Tokyo?"}'
```

Response:
```json
{
  "status": "success",
  "category": "needs_web",
  "confidence": 0.94,
  "reason": "pattern_matched:weather forecast",
  "strategy": "use_browser",
  "suggested_agents": ["generalist"]
}
```

**Execute JavaScript in page context:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"evaluate-js","script":"document.querySelectorAll(\"a\").length"}'
```

---

## Authentication

Agent-OS uses a 3-layer authentication system. The middleware attempts each method in order and uses the first one that succeeds.

### Layer 1: JWT Tokens (Recommended for Production)

JWT tokens use HS256 signing with configurable expiry. Access tokens are short-lived; refresh tokens allow re-authentication without credentials.

**Register a user:**

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","username":"admin","password":"StrongPass123!"}'
```

**Login to get tokens:**

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPass123!"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Use JWT in requests:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"command":"navigate","url":"https://example.com"}'
```

**Refresh an expired token:**

```bash
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"eyJhbGciOiJIUzI1NiIs..."}'
```

### Layer 2: API Keys

API keys use the `aos_` prefix and are stored as salted hashes. They support scoped permissions and are ideal for programmatic access.

**Create an API key:**

```bash
curl -X POST http://localhost:8001/auth/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-app-key","scopes":["browser","scanning"]}'
```

**Use API key in requests (header):**

```bash
curl -X POST http://localhost:8001/command \
  -H "X-API-Key: aos_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"command":"navigate","url":"https://example.com"}'
```

**Use API key in requests (body):**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"aos_your_api_key_here","command":"navigate","url":"https://example.com"}'
```

### Layer 3: Legacy Tokens

Legacy tokens are simple shared secrets for development and testing. They are **not recommended for production**.

```bash
# Set via CLI
python3 main.py --agent-token "my-dev-token"

# Or via environment
export AGENT_TOKEN="my-dev-token"
```

**Use in requests:**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-dev-token","command":"navigate","url":"https://example.com"}'
```

### Authentication Flow Summary

```
Request arrives
     │
     ├─► Check Authorization: Bearer <token> ──► Validate as JWT ──► ✅ Authenticated
     │
     ├─► Check X-API-Key header ──► Validate as API key (aos_*) ──► ✅ Authenticated
     │
     ├─► Check token in JSON body
     │       │
     │       ├─► Starts with "aos_" ──► Validate as API key ──► ✅ Authenticated
     │       ├─► Valid JWT ──► ✅ Authenticated
     │       └─► Matches legacy token (HMAC) ──► ✅ Authenticated
     │
     └─► ❌ 401 Unauthorized
```

### Rate Limiting

Authenticated users are rate-limited per minute (default: 60 RPM). Rate limit headers are included in every response:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1710000000
```

Brute-force protection is applied to login endpoints: 5 failed attempts trigger a 15-minute lockout per IP address.

---

## Stealth and Anti-Detection

Agent-OS defeats bot detection using a 4-layer defense system covering 26+ detection vectors.

### Detection Vectors Blocked

| Detection Method | Status | Technique |
|---|---|---|
| `navigator.webdriver` | **REMOVED** | Prototype-level override (not `defineProperty`) |
| CDP Detection | **BLOCKED** | Property filter + intercept (`__executionContextId`, `cdc_*`) |
| DevTools Detection | **BLOCKED** | Timing randomization + debugger statement interception |
| Automation Artifacts | **CLEANED** | Global scan + removal (Playwright, Selenium, Phantom references) |
| `window.chrome` Object | **INJECTED** | Complete `chrome.runtime`, `chrome.app`, `chrome.csi`, `chrome.loadTimes` |
| `navigator.plugins` | **SPOOFED** | Cached realistic plugin list (Chrome PDF, Native Client) |
| `navigator.hardwareConcurrency` | **SPOOFED** | Matches selected hardware profile (6-10 cores) |
| `navigator.deviceMemory` | **SPOOFED** | Matches selected hardware profile (8-32 GB) |
| `navigator.languages` | **SPOOFED** | Consistent `['en-US', 'en']` |
| `navigator.connection` | **SPOOFED** | Realistic `rtt`, `downlink`, `effectiveType` |
| Screen Properties | **SPOOFED** | `width`, `height`, `availWidth`, `availHeight`, `colorDepth`, `pixelDepth` |
| WebGL Fingerprint | **SPOOFED** | Real GPU data injection (Intel UHD 630, NVIDIA RTX 3060, Apple M1 Pro, etc.) |
| Canvas Fingerprint | **NOISED** | Consistent deterministic noise per session (seeded RNG) |
| Audio Fingerprint | **NOISED** | Consistent deterministic noise per session (seeded RNG) |
| TLS Fingerprint (JA3/JA4) | **BYPASSED** | `curl_cffi` Chrome impersonation |
| HTTP/2 Fingerprint | **MATCHED** | Chrome 145/146 profiles |
| WebRTC IP Leak | **BLOCKED** | ICE server removal + host candidate stripping |
| Permissions API | **SPOOFED** | Realistic `notifications` and `geolocation` responses |
| Media Devices | **SPOOFED** | Realistic microphone, speaker, camera enumeration |
| Performance Timing | **RANDOMIZED** | Consistent offset per session |
| Notification Permission | **SPOOFED** | Returns `default` |
| Stack Traces | **SANITIZED** | No Playwright/Patchright references in error traces |
| Fingerprinting Libraries | **BLOCKED** | 40+ libraries blocked at network level |
| Bot Detection Scripts | **BLOCKED** | 15+ vendor scripts blocked, fake success responses returned |
| Property Descriptor Checks | **PROTECTED** | All overrides appear as native `[native code]` |
| `Object.getOwnPropertyNames` | **FILTERED** | CDP/Playwright properties hidden |

### Layered Defense Architecture

```
Layer 1: Network Level
  ├── curl_cffi for real Chrome TLS fingerprint (JA3/JA4)
  ├── HTTP/2 fingerprint matching (Chrome 145/146)
  ├── HTTP/2 → HTTP/1.1 automatic fallback
  ├── Request blocking (bot detection scripts, 40+ URLs)
  └── Fake success responses for reCAPTCHA (score: 0.9) and hCaptcha (pass)

Layer 2: CDP Level (Chrome DevTools Protocol)
  ├── Page.addScriptToEvaluateOnNewDocument (injected before any page JS)
  ├── User-Agent metadata spoofing
  ├── Timezone override
  └── Locale override

Layer 3: JavaScript Level (19 injection modules)
  ├── navigator.webdriver removal (prototype level, not defineProperty)
  ├── CDP property filtering (__executionContextId, cdc_*, __pw_*)
  ├── DevTools detection prevention (timing + debugger interception)
  ├── Chrome object completeness (runtime, app, csi, loadTimes, webstore)
  ├── Plugin simulation (cached, reference-stable)
  ├── Hardware profile consistency (cores, memory, screen, pixel ratio)
  ├── WebGL renderer/vendor spoofing (real GPU profiles)
  ├── Canvas fingerprint noise (seeded deterministic)
  ├── Audio fingerprint noise (seeded deterministic)
  ├── WebRTC IP leak prevention
  ├── Permissions API spoofing
  ├── Media device enumeration spoofing
  ├── Performance timing randomization
  ├── Notification permission spoofing
  ├── Function toString masking (all overrides appear as [native code])
  ├── Stack trace sanitization
  ├── Property descriptor protection
  └── Global cleanup (remove all automation artifacts)

Layer 4: Behavior Level
  ├── Human-like mouse movement (Bezier curves with micro-tremor)
  ├── Typing rhythm simulation (40-300ms per keystroke, WPM-based)
  ├── Word pause simulation (200-600ms)
  ├── Typo simulation with correction (3% rate)
  ├── Natural scroll behavior (multi-step with micro-variance)
  ├── Hesitation before actions
  └── Page interaction timing
```

### Consistent Fingerprint Engine

The stealth system generates a **consistent fingerprint** per session — all detection vectors cross-check each other. If WebGL says Intel but Canvas says NVIDIA, that is detectable. Agent-OS uses real hardware profiles from telemetry data:

| Profile | GPU | Cores | Memory | Resolution |
|---|---|---|---|---|
| Intel UHD 630 + i7-10700 | Intel UHD 630 | 8 | 16 GB | 1920 x 1080 |
| Intel Iris Xe + i7-1165G7 | Intel Iris Xe | 8 | 16 GB | 1920 x 1080 |
| NVIDIA GTX 1660 + Ryzen 5 | NVIDIA GTX 1660 | 6 | 16 GB | 1920 x 1080 |
| NVIDIA RTX 3060 + i5-12400 | NVIDIA RTX 3060 | 6 | 32 GB | 2560 x 1440 |
| AMD Radeon RX 580 + Ryzen 7 | AMD Radeon RX 580 | 8 | 16 GB | 1920 x 1080 |
| Apple M1 Pro | Apple M1 Pro | 10 | 16 GB | 2560 x 1600 |
| Apple M2 | Apple M2 | 8 | 8 GB | 2560 x 1600 |

Each fingerprint is generated from a seed and produces deterministic Canvas and Audio noise, ensuring the same session always returns the same fingerprint.

### Blocked Detection Vendors

DataDome, PerimeterX, Imperva, Akamai Bot Management, Cloudflare Bot Management, Cloudflare Turnstile, Kasada, Shape Security, F5, Arkose Labs, ThreatMetrix, Iovation, Sardine, SEON, IPQualityScore, FraudLabs, hCaptcha, reCAPTCHA

### Blocked Fingerprinting Libraries

FingerprintJS (v1-v3), ClientJS, ThumbmarkJS, CreepJS, BotD, Sardine, Iovation, ThreatMetrix, Nethra, OpenFingerprint, SEON, IPQualityScore, FraudLabs, BrowserLeaks, AmIUnique, and 30+ more

---

## Agent Swarm and Query Routing

When an AI agent receives a user query, it needs to know: **"Should I use the browser for this?"** Agent-OS answers this with a 3-tier routing system — no extra LLM cost required by default.

### 3-Tier Router Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│  Tier 1: RuleBasedRouter        │  Free, instant, 100+ weighted patterns
│  Pattern matching across        │  with anti-false-positive override guards
│  6 categories                   │
└────────────┬────────────────────┘
             │ Unsure? (confidence < 0.7)
             ▼
┌─────────────────────────────────┐
│  Tier 2: ProviderRouter         │  Uses YOUR existing LLM API
│  Sends query to your configured │  (OpenAI, Anthropic, Google, etc.)
│  provider for classification    │  Only activates if SWARM_LLM_API_KEY set
└────────────┬────────────────────┘
             │ Still unsure?
             ▼
┌─────────────────────────────────┐
│  Tier 3: ConservativeRouter     │  Safe default
│  Returns needs_web              │  "When in doubt, use the browser"
└─────────────────────────────────┘
```

### Tier 1 — RuleBasedRouter (Fast, Free)

Classifies queries across 6 categories using 100+ weighted patterns with priority ordering and anti-false-positive override guards:

| Category | Examples | Signal |
|---|---|---|
| `needs_web` | "What's the weather?", "Scrape product data", "Latest AI news" | Real-time data, URLs, web actions, scraping |
| `needs_knowledge` | "What is gravity?", "Who invented the telephone?" | Static knowledge, definitions, history |
| `needs_calculation` | "What is 2+2?", "Convert 5 miles to km" | Math/computation (no browser needed) |
| `needs_code` | "Write a Python function", "Debug this error" | Programming tasks (usually no browser) |
| `needs_security` | "Solve the captcha", "Bypass Cloudflare", "Fill login form" | Stealth/bypass tasks (needs browser) |
| `ambiguous` | "Tell me about Tesla" | Could be web or knowledge |

**Anti-false-positive guards** prevent miscategorization:
- "Solve the captcha" → `needs_security` (not `needs_calculation`)
- "Calculate stock price return" → `needs_web` (live data, not math)
- "Code a Fibonacci in Python" → `needs_code` (not `needs_calculation`)
- "Formula for area of circle" → `needs_knowledge` (reference, not computation)
- "Install latest Python" → `needs_web` (current version, not code generation)

**Strategies returned:**

| Strategy | Meaning |
|---|---|
| `use_browser` | High confidence — use browser (confidence >= 0.7) |
| `try_http_first` | Medium confidence — try HTTP client, fall back to browser |
| `no_web_needed` | High confidence — no web needed (confidence >= 0.7) |
| `probably_no_web` | Medium confidence — likely no web needed |
| `uncertain_consider_web` | Low confidence — agent should consider using web |

### Tier 2 — ProviderRouter (Your LLM, Your Cost)

If Tier 1 is uncertain, the query is sent to **your own** configured LLM provider (OpenAI, Anthropic, Google, etc.). This is NOT a separate LLM — it uses your existing API key. Only activates if `SWARM_PROVIDER_API_KEY` is configured.

### Tier 3 — ConservativeRouter (Safe Default)

When both tiers are uncertain, this always returns `needs_web`. The philosophy: it is better to use the browser unnecessarily than miss a web-requiring query.

### Router Commands

```bash
# Full classification with reasoning
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN","command":"classify-query","query":"What is the weather in Delhi?"}'

# Quick yes/no — does this need the browser?
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN","command":"needs-web","query":"What is 2+2?"}'

# Get recommended strategy
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN","command":"query-strategy","query":"Search for latest AI news"}'

# View classification statistics
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"TOKEN","command":"router-stats"}'
```

### Agent Profiles

The router maps categories to specialized agent profiles:

| Category | Sub-type | Agents |
|---|---|---|
| `needs_web` | news | news_hound, generalist |
| `needs_web` | price | price_checker, generalist |
| `needs_web` | finance | finance_analyst, news_hound |
| `needs_web` | social | social_media_tracker, generalist |
| `needs_web` | scraping | data_extractor, deep_researcher |
| `needs_security` | captcha | captcha_solver, security_agent |
| `needs_security` | cloudflare | cloudflare_bypasser, security_agent |
| `needs_security` | stealth | stealth_agent, security_agent |
| `needs_knowledge` | — | generalist, deep_researcher |
| `needs_calculation` | — | generalist |
| `needs_code` | — | tech_scanner |

---

## AI Platform Connectors

Agent-OS connects to **any** AI platform. Five connectors are included out of the box.

### 1. Claude Desktop / Codex / MCP-Compatible Agents

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

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

Works with: Claude Desktop, Claude Code, OpenAI Codex, any MCP-compatible agent.

### 2. OpenAI / GPT-4 Function Calling

```python
from connectors.openai_connector import get_tools, call_tool

# Get tool definitions for OpenAI function calling
tools = get_tools("openai")

# Or for Claude tool-use format
tools = get_tools("claude")

# Execute any tool
result = await call_tool("browser_navigate", {"url": "https://github.com"})
result = await call_tool("browser_screenshot", {})
result = await call_tool("browser_click", {"selector": "a[href='/login']"})
```

Works with: GPT-4, GPT-4o, any OpenAI-compatible API, Claude API (tool-use format).

### 3. OpenClaw

```python
from connectors.openclaw_connector import get_manifest, execute_tool

manifest = get_manifest()
result = await execute_tool("browser_navigate", {"url": "https://example.com"})
```

### 4. CLI / Bash / Any Language

```bash
# Navigate
./connectors/agent-os-tool.sh navigate "https://github.com"

# Screenshot
./connectors/agent-os-tool.sh screenshot

# Smart click (no CSS selector needed)
./connectors/agent-os-tool.sh smart-click "Sign In"

# Multi-step workflow
./connectors/agent-os-tool.sh workflow '{"steps":[{"command":"navigate","url":"https://example.com"}]}'

# Check server status
./connectors/agent-os-tool.sh status
```

Run `./connectors/agent-os-tool.sh` without arguments to see all 60+ commands. Works with any agent that can execute shell commands — Python, Node.js, Go, Rust, etc.

### 5. Direct WebSocket / REST API

**WebSocket (Python):**

```python
import websockets, json, asyncio

async def agent():
    async with websockets.connect("ws://localhost:8000") as ws:
        await ws.send(json.dumps({
            "token": "your-token",
            "command": "navigate",
            "url": "https://example.com"
        }))
        result = json.loads(await ws.recv())
        print(result)

asyncio.run(agent())
```

**REST API (curl):**

```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://example.com"}'
```

### Connector Tool Counts

| Connector | Tools | File |
|---|---|---|
| MCP (Claude/Codex) | 38 | `connectors/mcp_server.py` |
| OpenAI / Claude API | 38 | `connectors/openai_connector.py` |
| OpenClaw | 38 | `connectors/openclaw_connector.py` |
| CLI (Bash) | 74 commands | `connectors/agent-os-tool.sh` |
| HTTP API | 74 commands | Server at `/command` |
| Persistent API | 30+ commands | Server at `/persistent/command` |

---

## Web UI

Agent-OS includes a modern React dashboard for monitoring and control.

**Tech Stack:** React 18 + Vite 6 + TypeScript + TailwindCSS + Zustand

### Features

- **Dashboard** — Server status, active sessions, browser state at a glance
- **Browser Tab** — Live browser viewport and command execution
- **Command Tab** — Send commands directly from the UI with auto-complete
- **API Keys Tab** — Create, scope, and revoke API keys
- **Swarm Tab** — Monitor and manage agent swarm activity
- **Handoff Tab** — Login handoff management
- **Settings Tab** — Configure server, browser, and security options

### Running the Web UI

```bash
cd web
npm install
npm run dev     # Development server at http://localhost:5173
npm run build   # Production build
```

The Web UI connects to the Agent-OS server via the REST API.

---

## Commands Reference

Agent-OS includes 60+ commands organized into categories. All commands require a `token` and `command` field.

<details>
<summary><strong>Navigation</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `navigate` | Navigate to a URL | `url`, `wait_until` |
| `back` | Go back in browser history | — |
| `forward` | Go forward in browser history | — |
| `reload` | Reload the current page | — |
| `smart-navigate` | Auto-select HTTP or browser strategy | `url` |

</details>

<details>
<summary><strong>Interaction</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `click` | Click an element (CSS selector) | `selector` |
| `double-click` | Double-click an element | `selector` |
| `right-click` | Right-click an element | `selector` |
| `context-action` | Right-click and select context menu option | `selector`, `action_text` |
| `type` | Type text into focused element | `text` |
| `press` | Press a keyboard key | `key` (Enter, Tab, Escape, etc.) |
| `fill-form` | Fill multiple form fields at once | `fields` (selector → value map) |
| `clear-input` | Clear an input field | `selector` |
| `hover` | Hover over an element | `selector` |
| `scroll` | Scroll the page | `direction`, `amount` |
| `wait` | Wait for an element to appear | `selector`, `timeout` |
| `select` | Select dropdown option | `selector`, `value` |
| `upload` | Upload a file | `selector`, `file_path` |
| `checkbox` | Set checkbox state | `selector`, `checked` |
| `drag-drop` | Drag and drop | `source`, `target` |
| `drag-offset` | Drag by pixel offset | `selector`, `x`, `y` |

</details>

<details>
<summary><strong>Smart Finder (No CSS Selector Needed)</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `smart-find` | Find element by visible text or description | `description`, `tag`, `timeout` |
| `smart-find-all` | Find all matching elements | `description` |
| `smart-click` | Click element by its visible text | `text` |
| `smart-fill` | Fill input by label/placeholder text | `label`, `value` |

The Smart Finder searches across multiple strategies in priority order: exact text → aria-label → placeholder → title attribute → alt text → link text → button text → label text → fuzzy text → partial text → text nearby.

</details>

<details>
<summary><strong>Content Extraction</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `get-content` | Get page HTML + extracted text | — |
| `get-dom` | Get structured DOM snapshot | — |
| `screenshot` | Take a screenshot (base64 PNG) | `full_page` |
| `get-links` | Extract all links from the page | — |
| `get-images` | Extract all images from the page | — |
| `get-text` | Get text content of a specific element | `selector` |
| `get-attr` | Get an attribute value from an element | `selector`, `attribute` |
| `evaluate-js` | Execute JavaScript in page context | `script` |
| `scroll` | Scroll with human-like behavior | `direction`, `amount` |
| `viewport` | Change the browser viewport size | `width`, `height` |

</details>

<details>
<summary><strong>Page Analysis</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `page-summary` | Full page analysis: title, headings, content, tech stack | — |
| `page-tables` | Extract HTML tables as structured data | — |
| `page-seo` | SEO audit with score (0-100) and issues | — |
| `page-structured` | Extract JSON-LD / Microdata | — |
| `page-emails` | Find all email addresses on the page | — |
| `page-phones` | Find all phone numbers on the page | — |
| `page-accessibility` | Basic accessibility audit | — |

</details>

<details>
<summary><strong>Network Capture</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `network-start` | Start capturing network requests | `url_pattern`, `resource_types`, `capture_body` |
| `network-stop` | Stop capturing and get summary | — |
| `network-get` | Get captured requests with filters | `url_pattern`, `method`, `status_code`, `limit` |
| `network-apis` | Discover all API endpoints | — |
| `network-detail` | Get full details of a captured request | `request_id` |
| `network-stats` | Capture statistics | — |
| `network-export` | Export to JSON or HAR format | `format`, `filename` |
| `network-clear` | Clear captured requests | — |

</details>

<details>
<summary><strong>Security Scanning</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `scan-xss` | Scan URL for XSS vulnerabilities | `url` |
| `scan-sqli` | Scan URL for SQL injection | `url` |
| `scan-sensitive` | Scan page for exposed sensitive data | — |

</details>

<details>
<summary><strong>Workflows</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `workflow` | Execute a multi-step workflow | `steps`, `variables`, `on_error`, `retry_count` |
| `workflow-save` | Save workflow as reusable template | `name`, `steps`, `variables`, `description` |
| `workflow-template` | Run a saved template | `template_name`, `variables` |
| `workflow-list` | List all saved templates | — |
| `workflow-status` | Get status of a running workflow | `workflow_id` |
| `workflow-json` | Execute workflow from JSON string | `json` |

</details>

<details>
<summary><strong>Sessions and Auth</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `save-session` | Save full browser state (cookies, localStorage, tabs) | `name` |
| `restore-session` | Restore a saved session | `name` |
| `list-sessions` | List all saved sessions | — |
| `delete-session` | Delete a saved session | `name` |
| `save-creds` | Save login credentials (AES-256 encrypted) | `domain`, `username`, `password` |
| `auto-login` | Auto-login using saved credentials | `url`, `domain` |
| `get-cookies` | Get all cookies | — |
| `set-cookie` | Set a cookie | `name`, `value`, `domain`, `path`, `secure` |

</details>

<details>
<summary><strong>Tabs</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `tabs list` | List all open tabs | — |
| `tabs new` | Create a new tab | `tab_id` |
| `tabs switch` | Switch to a tab | `tab_id` |
| `tabs close` | Close a tab | `tab_id` |

</details>

<details>
<summary><strong>Proxy and Device</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `set-proxy` | Set proxy (HTTP, HTTPS, SOCKS5) | `proxy_url` |
| `get-proxy` | Get current proxy configuration | — |
| `emulate-device` | Emulate mobile/tablet/desktop device | `device` |
| `list-devices` | List all available device presets | — |

</details>

<details>
<summary><strong>Media</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `transcribe` | Transcribe audio/video from URL (Whisper) | `url`, `language` |

</details>

<details>
<summary><strong>Web Query Router</strong></summary>

| Command | Description | Key Parameters |
|---|---|---|
| `classify-query` | Full classification: category, confidence, reason, strategy | `query` |
| `needs-web` | Quick boolean: does this query need web access? | `query` |
| `query-strategy` | Recommended strategy | `query` |
| `router-stats` | Classification statistics | — |

</details>

---

## Production Deployment

### Docker Compose (Recommended)

```bash
# Set required environment variables
export JWT_SECRET_KEY="your-super-secret-key-here"
export POSTGRES_PASSWORD="strong-db-password"

# Start full stack (PostgreSQL + Redis + Agent-OS + Nginx)
docker compose --profile with-nginx up -d

# View logs
docker compose logs -f agent-os
```

### Docker Architecture

```
┌─────────────────────────────────────────────────┐
│  Docker Network (isolated)                      │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  Agent-OS    │  │  PostgreSQL  │             │
│  │  (2GB RAM)   │  │  (512MB RAM) │             │
│  │  Port 8000   │  │  Port 5432   │             │
│  │  Port 8001   │  │  (internal)  │             │
│  │  Non-root    │  │              │             │
│  │  no-new-priv │  │              │             │
│  └──────┬───────┘  └──────┬───────┘             │
│         │                  │                     │
│  ┌──────┴───────┐  ┌──────┴───────┐             │
│  │    Redis     │  │    Nginx     │             │
│  │  (300MB RAM) │  │  Port 8080   │             │
│  │  (internal)  │  │  (127.0.0.1) │             │
│  └──────────────┘  │  no-new-priv │             │
│                     └──────────────┘             │
│                                                  │
│  Volumes: postgres-data, redis-data,             │
│           agent-os-data (persistent)             │
│  Tmpfs:  /tmp (noexec, nosuid)                  │
└─────────────────────────────────────────────────┘
```

Key isolation features:
- **Non-root user** — Agent-OS runs as `agentos` user, never root
- **no-new-privileges** — Containers cannot escalate privileges
- **All ports bound to 127.0.0.1** by default (not exposed to the internet)
- **Resource limits** — Each service has memory and CPU caps
- **Health checks** — Automatic restart on failure
- **Named volumes** — Data persists across container restarts
- **Tmpfs /tmp** — Noexec, nosuid temporary filesystem
- **Nginx reverse proxy** — Optional SSL termination and request filtering

### Persistent Chromium (Production Mode)

For production deployments serving multiple concurrent users, enable persistent mode:

```bash
python3 main.py --persistent --agent-token "my-token"
```

**Architecture:**

```
PersistentBrowserManager (singleton)
├── BrowserInstance 1 (Chromium PID 1234)
│   ├── UserContext "user-abc" → ~/.agent-os/users/user-abc/
│   │   ├── main page (tab)
│   │   ├── tab-1 (tab)
│   │   ├── cookies.json
│   │   └── context_state.json
│   ├── UserContext "user-def" → ~/.agent-os/users/user-def/
│   └── ... (up to 50 contexts)
├── BrowserInstance 2 (Chromium PID 5678)
│   └── ... (next 50 users)
└── BrowserInstance N (up to 5 instances = 250 concurrent users)
```

**Scaling estimates:**

| Config | Concurrent Users | Memory (est.) |
|---|---|---|
| 1 instance x 50 contexts | 50 | ~800 MB |
| 3 instances x 50 contexts | 150 | ~2.4 GB |
| 5 instances x 50 contexts | 250 | ~4 GB |
| 5 instances x 100 contexts | 500 | ~8 GB |

### Production Checklist

- **Set `JWT_SECRET_KEY`** — Without it, a new key is generated on every restart and sessions will not persist
- **Run behind a firewall** — Agent-OS is designed for local/private network use. Use Nginx + SSL for public exposure
- **Use JWT + API keys** — Legacy tokens are for development only
- **Configure CORS** — Cross-origin requests are blocked by default. Add your domain to `server.cors_allowed_origins`
- **Monitor RAM** — ~500 MB idle, ~800 MB under load. Use `--max-ram` to set limits
- **Enable Redis** — In-memory rate limiting does not scale across instances. Use Redis for distributed deployments
- **Set up PostgreSQL** — File-based storage works for single instances but PostgreSQL is required for multi-instance deployments

---

## Project Structure

```
Agent-OS/
├── main.py                          # Entry point — AgentOS class, CLI, startup/shutdown
├── install.sh                       # One-command installer
├── docker-compose.yml               # Full stack: PostgreSQL + Redis + Agent-OS + Nginx
├── Dockerfile                       # Multi-stage Docker build
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Database migration config
│
├── src/
│   ├── core/                        # Core Engine
│   │   ├── browser.py               #   Main browser engine (Patchright/Chromium)
│   │   ├── http_client.py           #   TLS-spoofing HTTP client (curl_cffi)
│   │   ├── stealth.py               #   Anti-detection JS + request blocking
│   │   ├── cdp_stealth.py           #   CDP-level stealth injection
│   │   ├── stealth_god.py           #   GOD MODE stealth system (26+ vectors)
│   │   ├── tls_spoof.py             #   TLS fingerprint spoofing
│   │   ├── tls_proxy.py             #   TLS proxy for real browser fingerprints
│   │   ├── smart_navigator.py       #   Smart navigation strategy
│   │   ├── firefox_engine.py        #   Firefox fallback engine
│   │   ├── config.py                #   Configuration management (YAML + dotted keys)
│   │   ├── session.py               #   Session lifecycle management
│   │   └── persistent_browser.py    #   Persistent Chromium engine (production)
│   │
│   ├── auth/                        # Authentication
│   │   ├── jwt_handler.py           #   JWT create/verify/refresh (HS256)
│   │   ├── api_key_manager.py       #   API key CRUD (prefix: aos_)
│   │   ├── user_manager.py          #   User registration, login, bcrypt
│   │   └── middleware.py            #   HTTP auth middleware chain (3-layer)
│   │
│   ├── security/                    # Security and Evasion
│   │   ├── evasion_engine.py        #   Fingerprint generation + injection
│   │   ├── captcha_bypass.py        #   CAPTCHA detection and bypass
│   │   ├── captcha_solver.py        #   CAPTCHA solving
│   │   ├── cloudflare_bypass.py     #   Cloudflare Turnstile bypass
│   │   ├── human_mimicry.py         #   Bezier mouse, typing simulation
│   │   └── auth_handler.py          #   Auto-login, credential vault (AES-256)
│   │
│   ├── tools/                       # Feature Tools (lazy-loaded)
│   │   ├── smart_finder.py          #   Smart element finder
│   │   ├── smart_wait.py            #   Intelligent wait strategies
│   │   ├── auto_heal.py             #   Self-healing browser
│   │   ├── auto_retry.py            #   Auto-retry with circuit breaker
│   │   ├── workflow.py              #   Multi-step workflow engine
│   │   ├── network_capture.py       #   Network request capture
│   │   ├── page_analyzer.py         #   Page analysis and SEO audit
│   │   ├── scanner.py               #   Security scanner (XSS, SQLi)
│   │   ├── form_filler.py           #   Form filling engine
│   │   ├── proxy_rotation.py        #   Proxy pool management
│   │   ├── auto_proxy.py            #   Automatic proxy selection
│   │   ├── session_recording.py     #   Session recording and replay
│   │   ├── multi_agent.py           #   Multi-agent hub
│   │   ├── web_query_router.py      #   Query classification (rule-based + provider)
│   │   ├── login_handoff.py         #   Login handoff management
│   │   └── transcriber.py           #   Audio/video transcription (Whisper)
│   │
│   ├── agents/
│   │   └── server.py                #   WebSocket + HTTP server (130+ handlers)
│   │
│   ├── agent_swarm/                 # Agent Swarm Module
│   │   ├── router/                  #   3-Tier Router
│   │   │   ├── rule_based.py        #     Tier 1: Pattern matching (100+ patterns)
│   │   │   ├── orchestrator.py      #     Router orchestration
│   │   │   ├── provider_router.py   #     Tier 2: User's provider as brain
│   │   │   └── conservative.py      #     Tier 3: Conservative default
│   │   ├── agents/                  #   Agent profiles and pool
│   │   ├── search/                  #   Search backends (Agent-OS, HTTP)
│   │   └── output/                  #   Result aggregation and formatting
│   │
│   ├── infra/                       # Infrastructure
│   │   ├── database.py              #   PostgreSQL (SQLAlchemy async)
│   │   ├── redis_client.py          #   Redis client with fallback
│   │   ├── models.py                #   Database models
│   │   └── logging.py               #   Structured logging (structlog)
│   │
│   ├── validation/
│   │   └── schemas.py               #   Input validation (Pydantic v2)
│   │
│   └── debug/
│       └── server.py                #   Debug dashboard (port+2)
│
├── connectors/                      # AI Platform Connectors
│   ├── mcp_server.py                #   Claude / Codex / MCP connector
│   ├── openai_connector.py          #   OpenAI / Claude function-calling
│   ├── openclaw_connector.py        #   OpenClaw connector
│   ├── agent-os-tool.sh             #   Universal CLI connector (60+ commands)
│   └── mcp_config.json              #   MCP config template
│
├── web/                             # React Web UI
│   ├── src/                         #   React 18 + TypeScript + TailwindCSS
│   │   ├── components/              #   UI components (Dashboard, Browser, etc.)
│   │   ├── store/                   #   Zustand state management
│   │   └── services/                #   API client
│   ├── vite.config.ts               #   Vite 6 configuration
│   └── package.json                 #   Frontend dependencies
│
├── tests/                           # Test suite
└── docs/                            # Documentation
```

---

## Development

### Local Development Setup

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Chromium browser
python3 -m patchright install chromium

# Install system dependencies (Linux)
python3 -m patchright install-deps chromium

# Start in development mode
python3 main.py --headed --debug --agent-token "dev-token"
```

### Web UI Development

```bash
cd web
npm install
npm run dev      # Development server at http://localhost:5173
npm run build    # Production build
```

### Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test suite
python3 -m pytest tests/test_all.py -v

# Run connector tests
python3 -m pytest tests/test_connectors.py -v

# Run extended tests
python3 -m pytest tests/test_extended.py -v

# Run specific test class
python3 -m pytest tests/test_all.py::TestCaptchaBypass -v

# Lint check
pip install ruff && ruff check src/ main.py --select E,F,W --ignore E501
```

### Adding New Features

**New tool:**
1. Create the tool module in `src/tools/`
2. Add command handler in `src/agents/server.py` (`_execute_command` map + `_cmd_*` method)
3. Add lazy-init getter for the tool

**New connector:**
1. Create the connector in `connectors/`
2. Follow the existing pattern (MCP or OpenAI connector)

**New config option:**
1. Add to `DEFAULT_CONFIG` in `src/core/config.py`

**New browser method:**
1. Add to `AgentBrowser` in `src/core/browser.py`

### Common Patterns

- **Lazy loading** — Tools are `None` until first use, then imported and instantiated on demand
- **All commands return** — `{"status": "success/error", ...}` consistently
- **Sessions** — Auto-created per token, 15-minute timeout, auto-wipe
- **Error handling** — `_safe_execute()` wraps browser operations with crash recovery
- **Config** — YAML file at `~/.agent-os/config.yaml` with dotted-key access

---

## Troubleshooting

### Port Already in Use

```
OSError: [Errno 98] Address already in use
```

Another process is using port 8000 or 8001. Use a different port:

```bash
python3 main.py --port 9000
```

Or find and stop the existing process:

```bash
lsof -i :8000 -i :8001
```

### Chromium Not Found

```
Error: Browser closed unexpectedly
```

Install Chromium and its system dependencies:

```bash
python3 -m patchright install chromium
python3 -m patchright install-deps chromium   # Linux system dependencies
```

### JWT_SECRET_KEY Warning

```
WARNING: JWT_SECRET_KEY not set — auto-generated (sessions won't survive restarts)
```

Set the environment variable for production:

```bash
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
```

### Authentication Failed

```
{"status": "error", "message": "Authentication failed"}
```

- Verify your token is correct (check startup logs or `.env` file)
- For JWT auth, ensure the `Authorization: Bearer <token>` header is set correctly
- For API keys, ensure the key starts with `aos_` and has not been revoked
- Check that the key's scopes include the required permission for the endpoint

### Site Still Detects the Bot

Some sites with advanced JavaScript challenges may still block headless browsers. Try these fallback strategies:

- **Site-specific bypasses** — Smart navigation automatically tries alternatives (e.g., `old.reddit.com`)
- **HTTP client fallback** — Uses `curl_cffi` with Chrome TLS fingerprint for fast, undetectable requests
- **Try a different device preset** — Some sites are less strict with mobile user agents: `--device iphone_14`
- **Use a proxy** — Residential proxies reduce detection: `--proxy "http://user:pass@proxy:8080"`
- **Enable headed mode** — Some sites are harder to detect when the browser is visible: `--headed`

### Database Connection Failed

```
Error: Cannot connect to PostgreSQL
```

If using Docker:

```bash
docker compose ps
docker compose logs postgres
```

If running manually, verify the connection string:

```bash
python3 -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('postgresql://user:pass@localhost/agentos'))"
```

### Redis Connection Failed

```
WARNING: Redis connection failed — falling back to in-memory
```

Agent-OS gracefully falls back to in-memory storage if Redis is unavailable. For production, ensure Redis is running:

```bash
docker compose logs redis
redis-cli ping   # Should return PONG
```

### RAM Usage Too High

```bash
# Limit RAM usage
python3 main.py --max-ram 500

# Close unused tabs via the tabs close command
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Browser Engine | Patchright (Playwright fork with stealth patches) + Chromium |
| HTTP Client | `curl_cffi` (Chrome TLS fingerprint) |
| Anti-Bot | `cloudscraper` + custom bypass engine |
| Database | PostgreSQL (SQLAlchemy async + `asyncpg` + Alembic) |
| Cache | Redis (with in-memory fallback) |
| Auth | JWT (HS256) + API keys (`aos_` prefix) + legacy tokens |
| Web UI | React 18 + Vite 6 + TypeScript + TailwindCSS + Zustand |
| Validation | Pydantic v2 |
| Logging | structlog (JSON or human-readable) |
| Connectors | MCP server, OpenAI function calling, OpenClaw, CLI |
| Runtime | Python 3.10+ / asyncio |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

All tests must pass and the linter must be clean before merging.

---

## License

This project is licensed under the [MIT License](LICENSE) — free for commercial and personal use.
