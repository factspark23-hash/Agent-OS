# Agent-OS

**Give any AI agent a real browser. Not a sandbox. Not a viewer. A real, persistent, UNDETECTABLE browser it actually owns.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-1.49+-2EAD33.svg)](https://playwright.dev/)

---

## 🚨 The Problem

Every AI agent struggles with the web:

| What They Need | What They Get |
|---|---|
| Persistent login sessions | Sandbox that resets every time |
| Fill forms, click buttons, manage tabs | "Here's the page HTML, good luck" |
| Browse without getting blocked | Instantly flagged as a bot |
| Access Netflix, Bloomberg, Glassdoor | "Access Denied" or CAPTCHA hell |
| Works with any AI platform | Locked into one provider's browser |

**Claude MCP browser:** Sandboxed viewer. No cookies, no persistence.  
**OpenClaw browser:** Basic Playwright. No stealth. Gets blocked.  
**Browserbase/Browserless:** Cloud-hosted. Your data on their servers. $$$/month.  
**Raw Playwright:** Good luck with bot detection. Gets caught in seconds.

**Agent-OS:** Real Chromium. Persistent sessions. **GOD MODE Stealth.** Self-hosted. Free. Works with any AI.

---

## ✨ What You Get

### 🛡️ GOD MODE Stealth Engine v5.0
**The ultimate anti-detection system.** Covers 20 detection vectors that sites use to catch bots:

```
┌─────────────────────────────────────────────────────────────┐
│  DETECTION METHOD          │  STATUS       │  HOW           │
├─────────────────────────────────────────────────────────────┤
│  navigator.webdriver       │  ✅ REMOVED   │  CDP Prototype │
│  CDP Detection             │  ✅ BLOCKED   │  Property Filter│
│  DevTools Detection        │  ✅ BLOCKED   │  Timing Random │
│  Automation Artifacts      │  ✅ CLEANED   │  Global Scan   │
│  WebGL Fingerprint         │  ✅ SPOOFED   │  Real GPU Data │
│  Canvas Fingerprint        │  ✅ NOISED    │  Consistent    │
│  Audio Fingerprint         │  ✅ NOISED    │  Consistent    │
│  TLS Fingerprint           │  ✅ BYPASSED  │  curl_cffi     │
│  HTTP/2 Fingerprint        │  ✅ SPOOFED   │  Real Browser  │
│  IP Reputation             │  ✅ ROTATED   │  Residential   │
│  Error Stack Traces        │  ✅ SANITIZED │  CDP Override  │
│  Performance Timing        │  ✅ RANDOMIZED│  Seeded RNG    │
│  Permissions API           │  ✅ REALISTIC │  Override      │
│  Media Devices             │  ✅ SANITIZED │  Override      │
│  Chrome Object             │  ✅ COMPLETE  │  Full Structure│
│  Plugin List               │  ✅ REALISTIC │  Real Plugins  │
│  Screen Properties         │  ✅ MATCHED   │  Hardware Cons │
│  WebRTC IP Leak            │  ✅ BLOCKED   │  SDP Filter    │
│  Fingerprint Libraries     │  ✅ ALL BLOCKED│ Fetch/XHR Block│
│  BotD / Sardine / Kasada   │  ✅ BYPASSED  │  Multi-Layer   │
└─────────────────────────────────────────────────────────────┘
```

**Why it works:** All fingerprint values come from ONE seed. WebGL says Intel → Screen says 1920×1080 → Hardware says 8 cores → Canvas noise matches → Audio noise matches. Sites cross-check these values. Agent-OS makes them all consistent — just like a real computer.

### 🔐 TLS Fingerprint Bypass
**Sites detect Playwright's TLS signature.** Agent-OS uses `curl_cffi` to re-sign all requests with real Chrome TLS fingerprints.

```
Playwright → [TLS Proxy :8081] → curl_cffi (real Chrome TLS) → Target Site
```

**Bypasses:** JA3/JA4 fingerprinting, DataDome, PerimeterX, Imperva, Akamai TLS detection.

### 🌍 Smart Proxy Rotation with Geo-Targeting
**Datacenter IPs get blocked.** Agent-OS rotates residential proxies and auto-selects the right country for streaming sites.

| Site | Auto-Target |
|------|-------------|
| Netflix, Hulu, HBO, Disney+ | 🇺🇸 US |
| BBC, ITV, Channel 4 | 🇬🇧 GB |
| ZDF, Arte | 🇩🇪 DE / 🇫🇷 FR |
| Amazon.co.uk | 🇬🇧 GB |
| Crave, CTV | 🇨🇦 CA |

**8 Rotation Strategies:** `weighted`, `fastest`, `geo`, `sticky`, `per_domain`, `round_robin`, `random`, `least_used`

### 🔒 Persistent Browser Sessions
Login once, stay logged in. Sessions survive across commands, restarts, and machine reboots.

### 🧠 Human Behavior Simulation
Mouse movements follow Bezier curves. Typing has randomized delays. Scrolling feels natural. To bot detection systems, Agent-OS looks like a human — because it acts like one.

### 🔐 Encrypted Credential Vault
Save login credentials with AES-256 encryption. Auto-login to any site on command. Credentials never leave your machine.

### 🔌 Connect Any AI
- **MCP** → Claude Desktop, Codex
- **OpenAI API** → GPT-4, any OpenAI-compatible model
- **Claude API** → Anthropic models
- **OpenClaw** → OpenClaw agents
- **CLI** → Bash, Python, Node.js
- **HTTP/WebSocket** → Any language, any framework

---

## 🚀 Quick Start

### ⚡ One Command

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

**With options:**
```bash
# Custom token
curl -sSL ... | bash -s -- --token my-secret-token

# Show browser window
curl -sSL ... | bash -s -- --headed

# Custom port + RAM limit
curl -sSL ... | bash -s -- --port 9000 --max-ram 1024

# Install without starting
curl -sSL ... | bash -s -- --no-start
```

### 🐳 Docker (Recommended)

```bash
docker run -d \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 8081:8081 \
  --name agent-os \
  agent-os
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

## 📖 Usage Examples

### Navigate Any Site (Even Bot-Protected)

```bash
# Netflix (auto-selects US residential proxy)
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "navigate", "url": "https://www.netflix.com"}'

# Bloomberg (GOD MODE stealth bypasses their bot detection)
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "navigate", "url": "https://www.bloomberg.com"}'

# Force specific country
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "navigate", "url": "https://www.bbc.com", "country": "GB"}'
```

### Extract Content

```bash
# Get page text
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "get-content"}'

# Get all links
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "get-links"}'

# Take screenshot
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "screenshot"}'
```

### TLS Requests (No Browser Needed)

```bash
# Direct HTTP with real browser TLS fingerprint
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "tls-get", "url": "https://protected-site.com"}'

# POST with TLS
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "tls-post", "url": "https://api.site.com", "json": {"key": "value"}}'
```

### Proxy Management

```bash
# Add residential proxy
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "proxy-add", "url": "http://user:pass@proxy.com:8080", "country": "US"}'

# List all proxies
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "proxy-list"}'

# Change rotation strategy
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "proxy-strategy", "strategy": "fastest"}'

# Health check all proxies
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "proxy-check"}'
```

### Save Login & Auto-Login

```bash
# Save credentials after manually logging in
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "save-creds", "site": "github.com"}'

# Auto-login on next session
curl -X POST http://localhost:8001/command \
  -d '{"token": "my-agent", "command": "auto-login", "site": "github.com"}'
```

---

## 🛠️ All Commands

### Navigation & Content

| Command | Description |
|---------|-------------|
| `navigate` | Navigate to URL (with proxy rotation + stealth) |
| `back` / `forward` / `reload` | Browser navigation |
| `get-content` | Get page HTML and text |
| `get-dom` | Get structured DOM snapshot |
| `get-links` | Get all page links |
| `get-images` | Get all page images |
| `get-text` | Get element text |
| `get-attr` | Get element attribute |
| `screenshot` | Take screenshot |

### Interaction

| Command | Description |
|---------|-------------|
| `click` / `double-click` / `right-click` | Click elements |
| `type` / `press` | Type text / press keys |
| `hover` | Hover over element |
| `fill-form` | Fill form fields |
| `fill-job` | Fill job application forms |
| `select` / `checkbox` / `clear-input` | Form controls |
| `drag-drop` / `drag-offset` | Drag and drop |
| `upload` | Upload files |
| `wait` | Wait for element |
| `scroll` | Scroll page |

### Stealth & Anti-Detection

| Command | Description |
|---------|-------------|
| `tls-get` | HTTP GET with real browser TLS |
| `tls-post` | HTTP POST with real browser TLS |
| `tls-stats` | TLS proxy statistics |

### Proxy Rotation

| Command | Description |
|---------|-------------|
| `proxy-add` | Add proxy to pool |
| `proxy-remove` | Remove proxy |
| `proxy-list` | List all proxies |
| `proxy-get` | Get proxy for domain/geo |
| `proxy-rotate` | Manual rotation |
| `proxy-check` | Health check proxies |
| `proxy-stats` | Rotation statistics |
| `proxy-strategy` | Change strategy |

### Tabs & Sessions

| Command | Description |
|---------|-------------|
| `tabs` | List/manage tabs |
| `save-session` | Save browser session |
| `restore-session` | Restore session |
| `list-sessions` | List saved sessions |
| `delete-session` | Delete session |

### Auth & Credentials

| Command | Description |
|---------|-------------|
| `save-creds` | Save login credentials |
| `auto-login` | Auto-login to site |
| `get-cookies` | Get cookies |
| `set-cookie` | Set cookie |

### Media & Analysis

| Command | Description |
|---------|-------------|
| `transcribe` | Transcribe video/audio |
| `page-summary` | Summarize page content |
| `page-tables` | Extract tables |
| `page-seo` | SEO analysis |
| `page-accessibility` | Accessibility check |
| `console-logs` | Get browser console logs |

### Device Emulation

| Command | Description |
|---------|-------------|
| `emulate-device` | Emulate mobile/tablet/desktop |
| `list-devices` | List available devices |

---

## 🔌 Connect Your Agent

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
result = await call_tool("browser_navigate", {"url": "https://github.com"})
```

### CLI (Any Language)

```bash
./connectors/agent-os-tool.sh navigate "https://github.com"
./connectors/agent-os-tool.sh screenshot
./connectors/agent-os-tool.sh get-content
```

---

## 🏗️ Architecture

```
Agent-OS/
├── main.py                          # Entry point
├── Dockerfile                       # Docker build
├── docker-compose.yml               # One-command deploy
├── setup.sh                         # Auto-installer
├── src/
│   ├── core/
│   │   ├── browser.py               # Browser engine + stealth integration
│   │   ├── stealth_god.py           # GOD MODE v5.0 (20 detection vectors)
│   │   ├── cdp_stealth.py           # CDP-level stealth injection
│   │   ├── tls_proxy.py             # TLS fingerprint bypass (curl_cffi)
│   │   ├── tls_spoof.py             # TLS header spoofing
│   │   ├── stealth.py               # Base stealth constants
│   │   ├── config.py                # Configuration management
│   │   ├── session.py               # Session lifecycle
│   │   └── persistent_browser.py    # Persistent browser contexts
│   ├── agents/
│   │   └── server.py                # WebSocket + REST API (163 commands)
│   ├── security/
│   │   ├── evasion_engine.py        # Fingerprint generation
│   │   ├── captcha_bypass.py        # Detection script blocking
│   │   ├── human_mimicry.py         # Human behavior simulation
│   │   └── auth_handler.py          # AES-256 credential vault
│   ├── tools/
│   │   ├── proxy_rotation.py        # Proxy pool + rotation engine
│   │   ├── scanner.py               # Security scanners
│   │   ├── transcriber.py           # Whisper transcription
│   │   ├── form_filler.py           # Smart form detection
│   │   ├── page_analyzer.py         # Page analysis tools
│   │   ├── smart_finder.py          # Smart element finder
│   │   ├── auto_heal.py             # Self-healing selectors
│   │   └── workflow.py              # Workflow automation
│   └── connectors/
│       ├── mcp_server.py            # MCP connector
│       ├── openai_connector.py      # OpenAI + Claude
│       ├── openclaw_connector.py    # OpenClaw
│       └── agent-os-tool.sh         # CLI
└── tests/                           # Test suite
```

---

## ⚙️ Configuration

Default config at `~/.agent-os/config.yaml`:

```yaml
server:
  host: 127.0.0.1
  ws_port: 8000                    # WebSocket port
  http_port: 8001                  # HTTP API port

browser:
  headless: true                   # Run headless
  viewport: {width: 1920, height: 1080}
  max_ram_mb: 500                  # RAM limit
  user_agent: "Mozilla/5.0 ..."    # Custom user agent
  proxy: null                      # Single proxy (optional)
  locale: "en-US"
  timezone_id: "America/New_York"
  
  # TLS Fingerprint Bypass
  tls_proxy_enabled: true          # Enable TLS proxy
  tls_proxy_port: 8081             # TLS proxy port
  
  # Proxy Rotation
  proxy_rotation_enabled: true     # Enable proxy rotation
  proxy_rotation_strategy: "weighted"  # Strategy: weighted|fastest|geo|sticky
  proxy_file: null                 # Path to proxy list file
  proxy_api_url: null              # Proxy provider API URL
  proxy_api_key: null              # Proxy provider API key

session:
  timeout_minutes: 15              # Session timeout
  auto_wipe: true                  # Auto-wipe on timeout
  max_concurrent: 3                # Max concurrent sessions

security:
  captcha_bypass: true             # Enable CAPTCHA bypass
  human_mimicry: true              # Enable human behavior simulation
  block_bot_queries: true          # Block bot detection requests
  session_encryption: true         # Encrypt session data
```

---

## 🔒 Stealth Technology Deep Dive

### GOD MODE v5.0 — How It Works

Agent-OS uses **3 layers of stealth** that work together:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: CDP STEALTH                         │
│  Injected BEFORE any page JavaScript via CDP protocol           │
│  - Deletes navigator.webdriver from prototype                   │
│  - Blocks CDP detection properties                              │
│  - Filters automation artifacts from Object.getOwnPropertyNames │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 2: FINGERPRINT CONSISTENCY              │
│  All values derived from ONE seed = consistent hardware profile │
│  - WebGL says Intel → Screen says 1920×1080 → 8 cores           │
│  - Canvas noise matches → Audio noise matches                   │
│  - Sites can't find inconsistencies                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: NETWORK STEALTH                     │
│  TLS + Proxy + Request interception                            │
│  - curl_cffi re-signs TLS with real Chrome fingerprint          │
│  - Residential proxy rotation (IP reputation clean)             │
│  - Bot detection scripts blocked before execution               │
└─────────────────────────────────────────────────────────────────┘
```

### What Gets Blocked (And How)

| Detection Library | How Agent-OS Bypasses It |
|-------------------|-------------------------|
| **FingerprintJS** | Fetch/XHR to fpjs blocked, returns fake response |
| **BotD** | CDP properties filtered, timing randomized |
| **PerimeterX** | Detection scripts blocked, TLS spoofed |
| **DataDome** | TLS fingerprint bypassed, JS challenges solved |
| **Cloudflare** | Turnstile blocked, CF bypass via cloudscraper |
| **Akamai** | TLS + HTTP/2 fingerprint spoofed |
| **Kasada** | Detection scripts blocked at network level |
| **Sardine/Iovation** | Canvas/WebGL/Audio consistency maintained |

### Consistency Engine — The Secret Sauce

```
Traditional bots:
  WebGL: NVIDIA RTX 3060    ← From spoofing
  Screen: 1366×768          ← From another spoofing
  Hardware: 4 cores         ← Random
  Canvas: Random noise      ← Different each time
  Result: INCONSISTENT → DETECTED

Agent-OS:
  WebGL: Intel UHD 630      ─┐
  Screen: 1920×1080         ─┤ All from ONE seed
  Hardware: 8 cores         ─┤ = Real hardware profile
  Canvas: Deterministic     ─┤ = CONSISTENT
  Audio: Deterministic      ─┘
  Result: UNDETECTABLE
```

---

## 📊 Tested Sites

### ✅ Successfully Bypasses

| Category | Sites |
|----------|-------|
| **Streaming** | Netflix, Hulu, HBO Max, Disney+, IMDb |
| **Finance** | Bloomberg, Yahoo Finance, Investing.com |
| **Social** | LinkedIn, Reddit, Twitter/X |
| **E-commerce** | Amazon, eBay, Walmart, Target |
| **News** | NYT, CNN, BBC, Reuters, Guardian |
| **Travel** | Booking.com, Expedia, TripAdvisor |
| **Bot Detection** | DataDome, PerimeterX, Imperva sites |
| **Cloudflare** | Any site using Cloudflare Bot Management |

### ⚠️ Limitations (Honest)

- **Residential proxies** required for streaming sites (datacenter IPs get blocked)
- **Some sites** with advanced behavioral analysis may require longer wait times
- **CAPTCHA challenges** are prevented, not solved (prevention > solving)

---

## 📦 Requirements

- **Python 3.10+**
- **~500MB RAM** idle, ~800MB under load
- **No GPU required**
- **No external API keys needed** (for basic usage)
- **curl_cffi** (for TLS fingerprint bypass)
- **cloudscraper** (for Cloudflare bypass)

### Optional Dependencies

```bash
# Full stealth stack
pip install curl_cffi cloudscraper

# For video transcription
pip install openai-whisper

# For proxy rotation (add your proxies)
# No extra packages needed — just add proxy URLs
```

---

## 🔐 Privacy & Security

- **Local only** — everything runs on your machine
- **Zero telemetry** — no data leaves your server
- **Session auto-wipe** — data destroyed after timeout
- **AES-256 vault** — credentials encrypted at rest
- **Token auth** — all commands require valid agent token
- **Cookie encryption** — browser cookies encrypted on disk

---

## 🤝 Contributing

We welcome contributions! Areas where help is needed:

- [ ] Mobile browser emulation improvements
- [ ] More proxy provider integrations
- [ ] Additional connector protocols
- [ ] Performance optimizations
- [ ] Documentation and examples

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with:
- [Playwright](https://playwright.dev/) — Browser automation
- [curl_cffi](https://github.com/yifeikong/curl_cffi) — TLS fingerprint impersonation
- [cloudscraper](https://github.com/VeNoMouS/cloudscraper) — Cloudflare bypass
- [aiohttp](https://docs.aiohttp.org/) — Async HTTP server
- [cryptography](https://cryptography.io/) — Encryption

---

<div align="center">

**⭐ Star this repo if Agent-OS helps your AI agent!**

[Report Bug](https://github.com/factspark23-hash/Agent-OS/issues) · 
[Request Feature](https://github.com/factspark23-hash/Agent-OS/issues) · 
[Documentation](https://github.com/factspark23-hash/Agent-OS#readme)

</div>
