<!-- mcp-name: io.github.factspark23-hash/Agent-OS -->

<h1 align="center">
    <a href="https://github.com/factspark23-hash/Agent-OS">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcset="docs/cover_dark.svg">
          <img alt="Agent-OS" src="docs/cover_light.svg" width="700">
        </picture>
    </a>
    <br>
</h1>

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
    <img src="https://img.shields.io/badge/tools-203-brightgreen.svg" alt="203 Tools" />
    <img src="https://img.shields.io/badge/version-3.2.0-orange.svg" alt="Version 3.2.0" />
    <br/>
    <a href="https://github.com/factspark23-hash/Agent-OS/stargazers">
        <img src="https://img.shields.io/github/stars/factspark23-hash/Agent-OS?style=social" alt="Stars" />
    </a>
    <a href="https://github.com/factspark23-hash/Agent-OS/network/members">
        <img src="https://img.shields.io/github/forks/factspark23-hash/Agent-OS?style=social" alt="Forks" />
    </a>
</p>

<p align="center">
    <a href="#-quick-start"><strong>Quick Start</strong></a> &middot;
    <a href="#-connectors"><strong>Connectors</strong></a> &middot;
    <a href="#-stealth-engine"><strong>Stealth</strong></a> &middot;
    <a href="#-adaptive-scraper"><strong>Adaptive</strong></a> &middot;
    <a href="#-commands-reference"><strong>Commands</strong></a> &middot;
    <a href="#-architecture"><strong>Architecture</strong></a> &middot;
    <a href="#-deployment"><strong>Deployment</strong></a>
</p>

---

Agent-OS gives AI agents a **real browser** — persistent, stealthy, and self-hosted. It ships **203 tools** for navigation, form filling, data extraction, CAPTCHA bypass, adaptive scraping, and more. Works with **Claude, GPT-4, Codex, OpenClaw**, and any agent that can send an HTTP request.

One command to install. One config to connect. Zero API keys needed.

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

---

## Why Agent-OS?

| Problem | Agent-OS Solution |
|---------|-------------------|
| AI agents can't interact with websites | Real Chromium browser with 203 tools |
| Bot detection blocks automation | 26+ anti-detection vectors, Cloudflare bypass |
| Website changes break selectors | **Adaptive scraper** — learns element fingerprints, auto-relocates |
| Manual login required | Login handoff — pause AI, human logs in, resume |
| Single IP gets blocked | Proxy rotation with 4 strategies + health tracking |
| LLM token waste on browser output | SmartCompressor — 87% token savings |
| Need multiple AI platforms | 7 connectors — MCP, OpenAI, Claude, CLI, REST, OpenClaw |

---

## ⚡ Quick Start

### Option 1: One-Command Install

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

```bash
# With options
curl -sSL .../install.sh | bash -s -- --token my-secret-token
curl -sSL .../install.sh | bash -s -- --headed          # Show browser
curl -sSL .../install.sh | bash -s -- --port 9000       # Custom port
```

### Option 2: Manual Install

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m patchright install chromium

export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
python3 main.py --agent-token "your-token"
```

### Option 3: Docker

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
export POSTGRES_PASSWORD="strong-password"
docker compose up -d
```

### First Commands

```bash
# Health check
curl http://localhost:8001/health

# Navigate
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"navigate","url":"https://github.com"}'

# Screenshot
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"screenshot"}'

# Click by text (no CSS selector needed)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"your-token","command":"smart-click","text":"Sign in"}'
```

---

## 🔌 Connectors

All 203 tools available in every connector:

| Connector | Tools | Use With | API Key? |
|-----------|-------|----------|----------|
| **MCP Passthrough** ⭐ | 203 | Claude Desktop, Claude Code, Codex | ❌ No |
| MCP Server | 203 | Claude Desktop, Claude Code, Codex | Optional |
| OpenAI | 203 | GPT-4, GPT-4o, any OpenAI-compatible | Yes |
| Claude API | 203 | Claude API (tool-use format) | Yes |
| OpenClaw | 203 | OpenClaw agent framework | Optional |
| CLI (Bash) | 202 | Any language (Python, Node, Go...) | Token |
| HTTP REST | 202 | Direct API calls | Token |

### MCP Passthrough (Zero API Key) ⭐

```bash
./run_mcp.sh --token "my-secret-token"
```

**Claude Desktop config:**

```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python3",
      "args": ["/path/to/Agent-OS/connectors/mcp_passthrough.py"],
      "env": {
        "AGENT_OS_URL": "http://localhost:8001",
        "AGENT_OS_TOKEN": "my-secret-token",
        "AGENT_OS_COMPRESS": "aggressive"
      }
    }
  }
}
```

---

## 🛡️ Stealth Engine

Agent-OS defeats bot detection with a **4-layer defense system**:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Network                                         │
│ Chrome TLS fingerprint (JA3/JA4) via curl_cffi          │
│ HTTP/2 matching • Bot scripts blocked at network level   │
├─────────────────────────────────────────────────────────┤
│ Layer 2: CDP (Chrome DevTools Protocol)                  │
│ Page.addScriptToEvaluateOnNewDocument injection          │
│ User-Agent metadata spoofing • Timezone override         │
├─────────────────────────────────────────────────────────┤
│ Layer 3: JavaScript (19 injection modules)               │
│ navigator.webdriver removal • CDP property filtering     │
│ WebGL/Canvas/Audio fingerprint spoofing                  │
│ WebRTC IP leak prevention • Function toString masking    │
├─────────────────────────────────────────────────────────┤
│ Layer 4: Behavior                                        │
│ Bezier-curve mouse movements • Realistic typing rhythms  │
│ Word pause simulation • Typo + correction (3% rate)      │
└─────────────────────────────────────────────────────────┘
```

**Blocked vendors:** DataDome, PerimeterX, Imperva, Akamai, Cloudflare Bot Management, Turnstile, Kasada, Shape Security, F5, Arkose Labs, ThreatMetrix, hCaptcha, reCAPTCHA

---

## 🧠 Adaptive Scraper

When a website changes its DOM structure, traditional selectors break. Agent-OS **remembers** element fingerprints and **relocates** them automatically:

```
1. Find element with CSS selector → ✅ Found → Save fingerprint (tag, attrs, text, path, parent)
2. Website redesigns, selector breaks → ❌ Not found
3. Load stored fingerprint → Scan all page elements → Score similarity
4. Best match above 40% threshold → ✅ Element relocated!
```

**Fingerprint components:**
| Component | Weight | What it captures |
|-----------|--------|------------------|
| Tag name | 30% | `div`, `span`, `a`, etc. |
| Attributes | 30% | class, id, name, href |
| Text content | 20% | Inner text (survives minor changes) |
| DOM path | 10% | Tag chain from root |
| Parent context | 10% | Parent tag + attributes |

**Commands:**
```bash
# Find element adaptively
{"command": "adaptive-find", "selector": ".product-title", "identifier": "product-name"}

# Save element fingerprint manually
{"command": "adaptive-save", "selector": "#login-btn", "identifier": "login-button"}

# View stored fingerprints
{"command": "adaptive-stats"}

# Clean old fingerprints
{"command": "adaptive-cleanup", "max_age_days": 30}
```

---

## 🔄 Proxy Rotation

Thread-safe proxy rotator with **4 strategies**:

| Strategy | How it works | Best for |
|----------|-------------|----------|
| **Cyclic** | Sequential round-robin | General scraping |
| **Weighted** | Higher weight = more requests | Premium vs budget proxies |
| **Random** | Random selection | Anti-pattern detection |
| **Sticky** | Same proxy per domain | Session-based scraping |

**Health tracking:** Success rate, latency, consecutive failures. Unhealthy proxies auto-skipped with failover.

```python
from src.tools.proxy_rotator import ProxyRotator

rotator = ProxyRotator(
    proxies=["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"],
    strategy="weighted"
)

proxy = rotator.get_proxy()                    # Get next proxy
proxy = rotator.get_proxy(domain="google.com") # Sticky per domain
proxy = rotator.get_proxy(country="US")        # Geo-targeted

rotator.record_result(proxy_id, success=True, latency_ms=120)
```

---

## 🌐 Browser Automation

**203 tools** across 15 categories:

| Category | Tools | Highlights |
|----------|-------|------------|
| Navigation | 6 | `navigate`, `smart-navigate` (auto HTTP/browser) |
| Interaction | 17 | `click`, `fill-form`, `drag-drop`, `scroll` |
| Smart Finder | 4 | Find by visible text — no CSS selectors |
| Content | 9 | `screenshot`, `get-dom`, `evaluate-js` |
| Page Analysis | 9 | `page-seo`, `page-emails`, `page-accessibility` |
| Network | 8 | Capture XHR, export HAR |
| Security | 3 | `scan-xss`, `scan-sqli`, `scan-sensitive` |
| Workflows | 6 | Multi-step automation with variables |
| Sessions | 8 | Save/restore cookies, auto-login |
| Proxy | 18 | Pool management, health checks, rotation |
| Adaptive | 4 | Element fingerprinting + relocation |
| Smart Wait | 7 | 7 wait strategies |
| Auto-Heal | 10 | Self-healing selectors |
| Auto-Retry | 10 | Circuit breaker + exponential backoff |
| Recording | 18 | Record, replay, export workflows |
| Multi-Agent | 19 | Shared sessions, task queues, locks |
| Login Handoff | 8 | Pause AI → human logs in → resume |
| LLM | 7 | Built-in `llm-complete`, `llm-summarize` |
| AI Content | 6 | Structured extraction, schema.org |
| CAPTCHA | 6 | Preempt, solve, monitor |
| TLS HTTP | 4 | Chrome TLS fingerprint without browser |

---

## 🔐 Authentication

3-layer auth system:

```bash
# Layer 1: JWT (recommended)
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","username":"admin","password":"StrongPass123!"}'

curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPass123!"}'

# Layer 2: API Keys
curl -X POST http://localhost:8001/auth/api-keys \
  -H "Authorization: Bearer YOUR_JWT" \
  -d '{"name":"my-key","scopes":["browser"]}'

# Layer 3: Legacy Tokens (dev only)
python3 main.py --agent-token "dev-token"
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  External Clients                                             │
│  Claude Desktop │ GPT-4 │ Codex │ CLI │ HTTP/WS             │
└────────┬────────┴───┬─────┴───┬───┴──┬──┴──────┬─────────────┘
         │            │         │      │         │
         ▼            ▼         ▼      ▼         ▼
┌──────────────────────────────────────────────────────────────┐
│  Connectors (203 tools each)                                 │
│  MCP │ OpenAI │ Claude │ OpenClaw │ CLI │ REST+WebSocket    │
└────────┬──────┴───┬─────┴────┬─────┴──┬──┴──────┬───────────┘
         └──────────┴────┬─────┴────────┴─────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Server (aiohttp)                                      │
│  Auth │ Rate Limiter │ Validator │ Command Router            │
└────────────────────────┬─────────────────────────────────────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Browser      │ │ Tools Layer  │ │ Infrastructure│
│ (Patchright  │ │ Adaptive     │ │ PostgreSQL   │
│  + Stealth)  │ │ Auto-Heal    │ │ Redis        │
│ 26+ vectors  │ │ Workflows    │ │ JWT Auth     │
│              │ │ LLM Provider │ │ Logging      │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🚀 Deployment

### Production Checklist

```bash
# 1. Set JWT secret
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# 2. Start with production flags
python3 main.py \
  --agent-token "strong-random-token" \
  --port 8000 \
  --max-ram 500 \
  --json-logs

# 3. Verify
curl http://localhost:8001/health
```

### Docker Compose (Full Stack)

```bash
export POSTGRES_PASSWORD="strong-db-password"
docker compose --profile with-nginx up -d
```

### Scaling

| Config | Concurrent Users | Memory |
|--------|-----------------|--------|
| 1 instance × 50 contexts | 50 | ~800 MB |
| 3 instances × 50 contexts | 150 | ~2.4 GB |
| 5 instances × 50 contexts | 250 | ~4 GB |

---

## 📁 Project Structure

```
Agent-OS/
├── main.py                          # Entry point
├── install.sh                       # One-command installer
├── docker-compose.yml               # Full Docker stack
├── requirements.txt                 # Python dependencies
│
├── src/
│   ├── core/                        # Browser engine
│   │   ├── browser.py               #   Main browser (Patchright/Chromium)
│   │   ├── stealth.py               #   Anti-detection JS (1264 lines)
│   │   ├── cdp_stealth.py           #   CDP-level stealth
│   │   ├── stealth_god.py           #   GOD MODE (26+ vectors)
│   │   ├── llm_provider.py          #   12 LLM providers
│   │   └── config.py                #   YAML configuration
│   │
│   ├── tools/                       # Feature engines
│   │   ├── adaptive_scraper.py      #   ⭐ Adaptive element relocation
│   │   ├── proxy_rotator.py         #   ⭐ 4-strategy proxy rotation
│   │   ├── auto_heal.py             #   Self-healing selectors
│   │   ├── workflow.py              #   Multi-step workflows
│   │   ├── session_recording.py     #   Record & replay
│   │   └── ...                      #   15+ more tools
│   │
│   ├── security/                    # Stealth & evasion
│   │   ├── evasion_engine.py        #   Fingerprint generation
│   │   ├── captcha_solver.py        #   CAPTCHA solving
│   │   └── cloudflare_bypass.py     #   Cloudflare bypass
│   │
│   └── agents/
│       └── server.py                # WebSocket + HTTP (202 commands)
│
├── connectors/                      # AI Platform Connectors
│   ├── _tool_registry.py            #   203 tool definitions
│   ├── mcp_server.py                #   MCP (Claude/Codex)
│   └── openai_connector.py          #   OpenAI function-calling
│
└── tests/                           # Test suite
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Browser | Patchright (stealth Playwright) + Chromium |
| HTTP Client | curl_cffi (Chrome TLS fingerprint) |
| Database | PostgreSQL (SQLAlchemy async) |
| Cache | Redis (with in-memory fallback) |
| Auth | JWT (HS256) + API keys |
| Validation | Pydantic v2 |
| Logging | structlog |
| Runtime | Python 3.10+ / asyncio |

---

## 🤝 Contributing

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m patchright install chromium

# Run tests
python3 -m pytest tests/ -v

# Start dev server
python3 main.py --headed --debug --agent-token "dev-token"
```

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | `python3 main.py --port 9000` |
| Chromium not found | `python3 -m patchright install chromium` |
| JWT warning | `export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')` |
| Site detects bot | Try `--device iphone_14` or add `--proxy` |
| High RAM | `python3 main.py --max-ram 500` |

---

## 📄 License

[MIT License](LICENSE) — free for commercial and personal use.

### Third-Party Code

- **[Scrapling](https://github.com/D4Vinci/Scrapling)** by Karim Shoair — Adaptive scraping algorithm and proxy rotation engine. Used under [BSD 3-Clause License](THIRD_PARTY_LICENSES.md).