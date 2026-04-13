# Agent-OS

**Give any AI agent a real browser — persistent, stealthy, self-hosted.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Version](https://img.shields.io/badge/version-3.2.0-orange.svg)](https://github.com/factspark23-hash/Agent-OS)

---

## The Problem

Every AI agent needs to interact with the web, but existing tools fall short:

| What You Need | What You Get |
|---|---|
| Persistent login sessions | Sandboxes that reset every time |
| Fill forms, click buttons | "Here's some HTML, figure it out yourself" |
| Browse without getting blocked | Instant "Access Denied" or CAPTCHA |
| Access Netflix, Bloomberg, Glassdoor | "Bot detected" |
| Works with any AI platform | Locked to one provider's browser |

**Agent-OS solves this.** Real Chromium. Persistent sessions. Stealth mode. Self-hosted. Free. Works with any AI.

---

## Features

### Stealth Engine v4.0

Anti-detection system covering 20+ detection vectors:

```
DETECTION METHOD              STATUS       HOW
navigator.webdriver           REMOVED      Prototype-level override
CDP Detection                 BLOCKED      Property filter
DevTools Detection            BLOCKED      Timing randomization
Automation Artifacts          CLEANED      Global scan + removal
WebGL Fingerprint             SPOOFED      Real GPU data injection
Canvas Fingerprint            NOISED       Consistent noise
Audio Fingerprint             NOISED       Consistent noise
TLS Fingerprint (JA3/JA4)    BYPASSED     curl_cffi impersonation
HTTP/2 Fingerprint            MATCHED      Chrome 145/146 profiles
Fingerprinting Libraries      BLOCKED      40+ libs blocked
Anti-Bot Vendors              BLOCKED      15+ vendors blocked
Stack Traces                  SANITIZED    No Playwright references
```

### Browser Automation

```python
# Navigate with stealth
result = await browser.navigate("https://example.com")

# Fill forms with human-like typing
await browser.fill_form({"#email": "user@example.com", "#pass": "secret"})

# Click with realistic mouse movement (Bezier curves)
await browser.click("#submit-btn")

# Take a screenshot
img = await browser.screenshot()

# Get page content
content = await browser.get_content()

# Execute JavaScript
result = await browser.evaluate_js("document.title")
```

### Smart Navigation

Agent-OS automatically chooses the best strategy for each site:
- **HTTP-first** — Uses curl_cffi with Chrome TLS fingerprinting for fast, lightweight requests
- **Browser fallback** — Switches to full Chromium for JavaScript-heavy or heavily protected sites
- **Smart retry** — Retries with delays on rate limits, falls back to alternative URLs on blocks
- **Site-specific bypasses** — Built-in strategies for Reddit (old.reddit), Bloomberg (/markets), etc.

### REST API

```bash
# Health check
curl http://localhost:8001/health

# Navigate
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"YOUR_TOKEN","command":"navigate","url":"https://example.com"}'

# Click
curl -X POST http://localhost:8001/command \
  -d '{"token":"YOUR_TOKEN","command":"click","selector":"#button"}'

# Get page content
curl -X POST http://localhost:8001/command \
  -d '{"token":"YOUR_TOKEN","command":"get-content"}'
```

---

## Installation

### Option 1: One-Command Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

With options:

```bash
# With authentication token
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash -s -- --token my-secret-token

# Show browser window (for debugging)
curl -sSL ... | bash -s -- --headed

# Custom port
curl -sSL ... | bash -s -- --port 9000

# Install only, don't start
curl -sSL ... | bash -s -- --no-start

# Skip sudo steps
curl -sSL ... | bash -s -- --no-sudo
```

### Option 2: Docker

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
docker compose up -d

# Verify it's running
curl http://localhost:8001/health
```

### Option 3: Manual

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

# Generate JWT secret key
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# Start the server
python3 main.py --agent-token "your-token"
```

---

## AI Platform Connectors

Agent-OS connects to **any** AI platform. Five connectors are included out of the box:

### 1. Claude Desktop / Codex / MCP-Compatible Agents

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

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

**Works with:** Claude Desktop, Claude Code, OpenAI Codex, any MCP-compatible agent.

### 2. OpenAI / GPT-4 Function Calling

```python
from connectors.openai_connector import get_tools, call_tool

# Get tool definitions for OpenAI
tools = get_tools("openai")  # Returns OpenAI function-calling schema

# Or for Claude tool-use format
tools = get_tools("claude")

# Execute any tool
result = await call_tool("browser_navigate", {"url": "https://github.com"})
result = await call_tool("browser_screenshot", {})
result = await call_tool("browser_click", {"selector": "a[href='/login']"})
```

**Works with:** GPT-4, GPT-4o, any OpenAI-compatible API, Claude API (tool-use format).

### 3. OpenClaw

```python
from connectors.openclaw_connector import get_manifest, execute_tool

# Register tools with OpenClaw
manifest = get_manifest()

# Execute tools
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

The CLI tool supports **60+ commands** — run `./connectors/agent-os-tool.sh` without arguments to see all options.

**Works with:** Any agent that can execute shell commands — Python, Node.js, Go, Rust, etc.

### 5. Direct WebSocket / REST API

For custom integrations, connect directly to the WebSocket or REST API:

```python
import websockets
import json

async def agent():
    async with websockets.connect("ws://localhost:8000") as ws:
        await ws.send(json.dumps({
            "token": "your-token",
            "command": "navigate",
            "url": "https://example.com"
        }))
        result = json.loads(await ws.recv())
```

```bash
# REST API (port 8001 by default)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://example.com"}'
```

---

## Commands Reference

### Navigation
| Command | Description |
|---|---|
| `navigate` | Navigate to a URL |
| `back` | Go back in browser history |
| `forward` | Go forward in browser history |
| `reload` | Reload the current page |
| `smart-navigate` | Auto-select HTTP or browser strategy |

### Interaction
| Command | Description |
|---|---|
| `click` | Click an element (CSS selector) |
| `double-click` | Double-click an element |
| `right-click` | Right-click an element |
| `type` | Type text into focused element |
| `press` | Press a keyboard key (Enter, Tab, Escape, etc.) |
| `fill-form` | Fill multiple form fields |
| `hover` | Hover over an element |
| `scroll` | Scroll the page |
| `wait` | Wait for an element to appear |
| `select` | Select dropdown option |
| `upload` | Upload a file |
| `checkbox` | Set checkbox state |
| `drag-drop` | Drag and drop |

### Smart Finder (No CSS Selector Needed)
| Command | Description |
|---|---|
| `smart-find` | Find element by visible text or description |
| `smart-find-all` | Find all matching elements |
| `smart-click` | Click element by its visible text |
| `smart-fill` | Fill input by label/placeholder text |

### Content
| Command | Description |
|---|---|
| `get-content` | Get page HTML + extracted text |
| `get-dom` | Get structured DOM snapshot |
| `screenshot` | Take a screenshot (base64 PNG) |
| `get-links` | Extract all links |
| `get-images` | Extract all images |
| `evaluate-js` | Execute JavaScript in page context |

### Page Analysis
| Command | Description |
|---|---|
| `page-summary` | Analyze page: title, headings, content, tech stack |
| `page-tables` | Extract HTML tables as structured data |
| `page-seo` | SEO audit with score and issues |
| `page-structured` | Extract JSON-LD / Microdata |
| `page-emails` | Find all email addresses |
| `page-phones` | Find all phone numbers |
| `page-accessibility` | Basic accessibility audit |

### Network Capture
| Command | Description |
|---|---|
| `network-start` | Start capturing network requests |
| `network-stop` | Stop capturing |
| `network-get` | Get captured requests with filters |
| `network-apis` | Discover all API endpoints |
| `network-stats` | Capture statistics |
| `network-export` | Export to JSON or HAR format |

### Security Scanning
| Command | Description |
|---|---|
| `scan-xss` | Scan URL for XSS vulnerabilities |
| `scan-sqli` | Scan URL for SQL injection |
| `scan-sensitive` | Scan page for exposed sensitive data |

### Workflows
| Command | Description |
|---|---|
| `workflow` | Execute multi-step workflow |
| `workflow-save` | Save workflow as reusable template |
| `workflow-template` | Run a saved template |
| `workflow-list` | List all saved templates |

### Sessions & Auth
| Command | Description |
|---|---|
| `save-session` | Save full browser state (cookies, localStorage, tabs) |
| `restore-session` | Restore a saved session |
| `save-creds` | Save login credentials (AES-256 encrypted) |
| `auto-login` | Auto-login using saved credentials |
| `get-cookies` | Get all cookies |
| `set-cookie` | Set a cookie |

### Tabs
| Command | Description |
|---|---|
| `tabs list` | List all open tabs |
| `tabs new` | Create a new tab |
| `tabs switch` | Switch to a tab |
| `tabs close` | Close a tab |

### Proxy & Device
| Command | Description |
|---|---|
| `set-proxy` | Set proxy (HTTP, HTTPS, SOCKS5) |
| `emulate-device` | Emulate mobile/tablet/desktop device |

### Media
| Command | Description |
|---|---|
| `transcribe` | Transcribe audio/video from URL (Whisper) |

### Web Query Router (No LLM — Rule-Based)

The Web Query Router tells AI agents **when** to use the browser and **when not to** — without using any LLM. This is critical: if an agent doesn't know which tasks need web access, the tool is useless.

```bash
# Classify a query — full analysis
curl -X POST http://localhost:8001/command \
  -d '{"token":"TOKEN","command":"classify-query","query":"What is the weather in Delhi?"}'

# Quick yes/no — does this query need web?
curl -X POST http://localhost:8001/command \
  -d '{"token":"TOKEN","command":"needs-web","query":"What is 2+2?"}'

# Get recommended strategy
curl -X POST http://localhost:8001/command \
  -d '{"token":"TOKEN","command":"query-strategy","query":"Search for latest AI news"}'
```

| Command | Description |
|---|---|
| `classify-query` | Full classification: needs_web, confidence, category, reason, strategy |
| `needs-web` | Quick boolean: does this query need web access? |
| `query-strategy` | Recommended strategy: use_browser, try_http_first, no_web_needed |
| `router-stats` | Classification statistics |

**How it works:**
- 100+ weighted signal patterns across 20+ categories
- Strong web signals: URLs, real-time keywords, web actions, location-specific queries
- Strong no-web signals: math, code, historical facts, creative writing
- Override rules for edge cases (currency conversion, programming + updates)
- No LLM dependency — pure rule-based, instant, free

**Strategies returned:**
| Strategy | Meaning |
|---|---|
| `use_browser` | High confidence — use browser (confidence ≥ 0.7) |
| `try_http_first` | Medium confidence — try HTTP client first, fall back to browser |
| `no_web_needed` | High confidence — no web needed (confidence ≥ 0.7) |
| `probably_no_web` | Medium confidence — likely no web needed |
| `uncertain_consider_web` | Low confidence — agent should consider using web |

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (or set environment variables directly):

```bash
# REQUIRED: JWT secret key for authentication
JWT_SECRET_KEY=your-secret-key-here

# OPTIONAL: Database (PostgreSQL)
DATABASE_DSN=postgresql+asyncpg://user:pass@localhost/agentos

# OPTIONAL: Redis (for distributed rate limiting, sessions)
REDIS_URL=redis://localhost:6379/0

# OPTIONAL: Proxy
PROXY_URL=http://user:pass@proxy:8080
```

### CLI Arguments

```bash
python3 main.py \
  --agent-token "my-token" \     # Legacy authentication token
  --port 8000 \                  # WebSocket port (HTTP = port+1)
  --headed \                     # Show browser window (for debugging)
  --max-ram 500 \                # RAM limit in MB
  --proxy "http://proxy:8080" \  # HTTP/SOCKS5 proxy
  --device iphone_14 \           # Device preset to emulate
  --persistent \                 # Enable persistent Chromium (production)
  --database "postgresql+asyncpg://..." \  # PostgreSQL connection
  --redis "redis://localhost:6379/0" \     # Redis connection
  --json-logs \                  # JSON structured logging
  --log-level INFO \             # Log level: DEBUG, INFO, WARNING, ERROR
  --rate-limit 60 \              # Max requests per minute per token
  --debug                        # Enable debug UI server (port+2)
```

### Device Presets

| Preset | Device |
|---|---|
| `iphone_se` | iPhone SE |
| `iphone_14` | iPhone 14 |
| `iphone_14_pro_max` | iPhone 14 Pro Max |
| `ipad` | iPad |
| `ipad_pro` | iPad Pro |
| `galaxy_s23` | Samsung Galaxy S23 |
| `galaxy_tab_s9` | Samsung Galaxy Tab S9 |
| `pixel_8` | Google Pixel 8 |
| `desktop_1080` | Desktop 1920x1080 |
| `desktop_1440` | Desktop 2560x1440 |
| `desktop_4k` | Desktop 3840x2160 |

---

## Architecture

```
Agent-OS
├── src/
│   ├── core/                        # Core Engine
│   │   ├── browser.py               # Main browser engine (Playwright/Chromium)
│   │   ├── http_client.py           # TLS-spoofing HTTP client (curl_cffi)
│   │   ├── stealth.py               # Anti-detection JS + request blocking
│   │   ├── cdp_stealth.py           # CDP-level stealth injection
│   │   ├── stealth_god.py           # GOD MODE stealth system
│   │   ├── tls_spoof.py             # TLS fingerprint spoofing
│   │   ├── tls_proxy.py             # TLS proxy for real browser fingerprints
│   │   ├── smart_navigator.py       # Smart navigation strategy
│   │   ├── firefox_engine.py        # Firefox fallback engine
│   │   ├── config.py                # Configuration management
│   │   ├── session.py               # Session lifecycle management
│   │   └── persistent_browser.py    # Persistent Chromium engine
│   ├── auth/                        # Authentication
│   │   ├── jwt_handler.py           # JWT create/verify/refresh
│   │   ├── api_key_manager.py       # API key CRUD (prefix: aos_)
│   │   ├── user_manager.py          # User registration, login, bcrypt
│   │   └── middleware.py            # HTTP auth middleware chain
│   ├── security/                    # Security & Evasion
│   │   ├── evasion_engine.py        # Fingerprint generation + injection
│   │   ├── captcha_bypass.py        # CAPTCHA detection & bypass
│   │   ├── captcha_solver.py        # CAPTCHA solving
│   │   ├── cloudflare_bypass.py     # Cloudflare Turnstile bypass
│   │   ├── human_mimicry.py         # Bezier mouse, typing simulation
│   │   └── auth_handler.py          # Auto-login, credential vault (AES-256)
│   ├── tools/                       # Feature Tools (lazy-loaded)
│   │   ├── smart_finder.py          # Smart element finder
│   │   ├── smart_wait.py            # Intelligent wait strategies
│   │   ├── auto_heal.py             # Self-healing browser
│   │   ├── auto_retry.py            # Auto-retry with circuit breaker
│   │   ├── workflow.py              # Multi-step workflow engine
│   │   ├── network_capture.py       # Network request capture
│   │   ├── page_analyzer.py         # Page analysis & SEO audit
│   │   ├── scanner.py               # Security scanner (XSS, SQLi)
│   │   ├── form_filler.py           # Form filling engine
│   │   ├── proxy_rotation.py        # Proxy pool management
│   │   ├── auto_proxy.py            # Automatic proxy selection
│   │   ├── session_recording.py     # Session recording & replay
│   │   ├── multi_agent.py           # Multi-agent hub
│   │   ├── web_query_router.py      # Query classification (web vs no-web, no LLM)
│   │   └── transcriber.py           # Audio/video transcription
│   ├── agents/
│   │   └── server.py                # WebSocket + HTTP server (130+ handlers)
│   ├── infra/                       # Infrastructure
│   │   ├── database.py              # PostgreSQL (SQLAlchemy async)
│   │   ├── redis_client.py          # Redis client
│   │   ├── models.py                # Database models
│   │   └── logging.py               # Structured logging (structlog)
│   ├── validation/
│   │   └── schemas.py               # Input validation (Pydantic)
│   └── debug/                       # Debug UI
│       └── server.py                # Debug dashboard (port+2)
├── connectors/                      # AI Platform Connectors
│   ├── mcp_server.py                # Claude / Codex / MCP connector (38 tools)
│   ├── openai_connector.py          # OpenAI / Claude function-calling connector
│   ├── openclaw_connector.py        # OpenClaw connector
│   ├── agent-os-tool.sh             # Universal CLI connector (60+ commands)
│   └── mcp_config.json              # MCP config template
├── tests/
├── docker-compose.yml               # PostgreSQL + Redis + Agent-OS + Nginx
├── Dockerfile                       # Multi-stage Docker build
├── install.sh                       # One-command installer
└── main.py                          # Entry point
```

---

## Stealth Technology

### How It Works (Layered Defense)

```
Layer 1: Network Level
  ├── curl_cffi for real Chrome TLS fingerprint (JA3/JA4)
  ├── HTTP/2 fingerprint matching (Chrome 145/146)
  ├── HTTP/2 → HTTP/1.1 automatic fallback
  └── Request blocking (bot detection scripts, 40+ URLs)

Layer 2: CDP Level (Chrome DevTools Protocol)
  ├── Page.addScriptToEvaluateOnNewDocument
  ├── User-Agent metadata spoofing
  ├── Timezone override
  └── Locale override

Layer 3: JavaScript Level
  ├── navigator.webdriver removal (prototype level)
  ├── CDP property filtering
  ├── DevTools detection prevention
  ├── WebGL/Canvas/Audio fingerprint consistency
  ├── Chrome object completeness
  ├── Plugin simulation
  └── Stack trace sanitization

Layer 4: Behavior Level
  ├── Human-like mouse movement (Bezier curves)
  ├── Typing rhythm simulation
  ├── Scroll behavior mimicry
  └── Page interaction timing
```

### Blocked Detection Vendors

DataDome, PerimeterX, Imperva, Akamai, Cloudflare Bot Management,
Kasada, Shape Security, F5, Arkose Labs, ThreatMetrix, Iovation,
Sardine, SEON, IPQualityScore, FraudLabs, hCaptcha, reCAPTCHA

### Blocked Fingerprinting Libraries

FingerprintJS (v1-v3), ClientJS, ThumbmarkJS, CreepJS, BotD,
Sardine, Iovation, ThreatMetrix, Nethra, and 30+ more

### Known Limitations

Some sites with advanced JavaScript challenges (Cloudflare Turnstile managed challenges, PerimeterX) may still block headless browsers. For these sites, Agent-OS provides:
- **Site-specific bypass strategies** — Automatically tries alternative URLs (e.g., `old.reddit.com`, `bloomberg.com/markets`)
- **HTTP client fallback** — Uses curl_cffi with Chrome TLS fingerprint for fast, undetectable requests when full browser is blocked
- **Smart navigation** — Automatically selects the best strategy per domain

---

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_all.py::TestCaptchaBypass -v

# Lint check
pip install ruff && ruff check src/ main.py --select E,F,W --ignore E501
```

---

## Production Deployment

### Docker Compose (Recommended)

```bash
# Start full stack (PostgreSQL + Redis + Agent-OS + Nginx)
docker compose --profile with-nginx up -d

# Set environment variables
export JWT_SECRET_KEY="your-super-secret-key-here"
export POSTGRES_PASSWORD="strong-db-password"

# View logs
docker compose logs -f agent-os
```

### Authentication

For production, use JWT authentication instead of legacy tokens:

```bash
# Register a user
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "username": "admin", "password": "StrongPass123!"}'

# Login to get JWT tokens
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "StrongPass123!"}'

# Create an API key (using JWT token)
curl -X POST http://localhost:8001/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "my-app-key", "scopes": ["browser", "scanning"]}'
```

### Important Notes

1. **Run behind a firewall** — Agent-OS is designed for local/private network use. Use Nginx + SSL for public exposure.
2. **Use JWT authentication** — Legacy tokens are for development only. Enable JWT + API keys for production.
3. **CORS** — Cross-origin requests are blocked by default. Add your domain to `server.cors_allowed_origins`.
4. **RAM** — ~500MB idle, ~800MB under load. More tabs = more RAM. Use `--max-ram` to set limits.
5. **Set JWT_SECRET_KEY** — Without it, a new key is generated on every restart and sessions won't persist.

---

## License

MIT License — free for commercial and personal use.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

All tests must pass. Linter must be clean.
