# Agent-OS
**Give any AI agent a real browser. Not a sandbox. Not a viewer. A real, persistent, UNDETECTABLE browser it actually owns.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-1.49+-2EAD33.svg)](https://playwright.dev/)

---

## 🚨 Kya Problem Hai?

Har AI agent ko web se kaam karna padta hai, lekin:

| Chahiye | Milta hai |
|---|---|
| Persistent login sessions | Sandbox jo har baar reset ho jaata hai |
| Forms bharo, buttons click karo | "Yeh lo HTML, khud figure out karo" |
| Bina block hue browse karo | Turant "Access Denied" ya CAPTCHA |
| Netflix, Bloomberg, Glassdoor access | "Bot detected" |
| Kisi bhi AI platform ke saath kaam karo | Ek provider ke browser mein locked |

**Agent-OS:** Real Chromium. Persistent sessions. **Stealth Mode.** Self-hosted. Free. Kisi bhi AI ke saath kaam karta hai.

---

## ✨ Kya Milega

### 🛡️ Stealth Engine v4.0
**Anti-detection system jo 20+ detection vectors cover karta hai:**

```
DETECTION METHOD              STATUS       KAISE
navigator.webdriver           ✅ REMOVED    Prototype level
CDP Detection                 ✅ BLOCKED    Property filter
DevTools Detection            ✅ BLOCKED    Timing random
Automation Artifacts          ✅ CLEANED    Global scan
WebGL Fingerprint             ✅ SPOOFED    Real GPU data
Canvas Fingerprint            ✅ NOISED     Consistent
Audio Fingerprint             ✅ NOISED     Consistent
TLS Fingerprint               ✅ BYPASSED   curl_cffi
Fingerprinting Libraries      ✅ BLOCKED    40+ libs blocked
Anti-Bot Vendors              ✅ BLOCKED    15+ vendors blocked
Stack Traces                  ✅ SANITIZED  No Playwright refs
```

### 🌐 Kya Kya Kar Sakta Hai

```python
# Navigate — stealth ke saath
result = await browser.navigate("https://example.com")

# Form fill — human-like typing
await browser.fill_form({"#email": "user@example.com", "#pass": "secret"})

# Click — realistic mouse movement
await browser.click("#submit-btn")

# Screenshot
img = await browser.screenshot()

# Page content lo
content = await browser.get_content()

# JavaScript run karo
result = await browser.evaluate_js("document.title")
```

### 📡 REST API

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

# Page content lo
curl -X POST http://localhost:8001/command \
  -d '{"token":"YOUR_TOKEN","command":"get-content"}'
```

---

## 🚀 Setup Kaise Karein

### Option 1: One-Command Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
```

Options:
```bash
# Token ke saath
curl -sSL ... | bash -s -- --token my-secret-token

# Browser window dikhao
curl -sSL ... | bash -s -- --headed

# Custom port
curl -sSL ... | bash -s -- --port 9000
```

### Option 2: Docker

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
docker compose up -d
curl http://localhost:8001/health  # verify
```

### Option 3: Manual

```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Playwright browser
python3 -m playwright install chromium

# JWT key generate karo
export JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')

# Start
python3 main.py --agent-token "your-token"
```

---

## 🔌 AI Platform Connectors

### Claude Desktop (MCP)
```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python",
      "args": ["/path/to/Agent-OS/connectors/mcp_server.py"],
      "env": {"AGENT_OS_TOKEN": "your-token"}
    }
  }
}
```

### OpenAI Function Calling
```python
from connectors.openai_connector import AgentOSTools
tools = AgentOSTools(base_url="http://localhost:8001", token="your-token")
```

### OpenClaw
```bash
# Automatic — just point OpenClaw at the Agent-OS URL
```

---

## 📋 Commands Reference

| Command | Description |
|---|---|
| `navigate` | URL pe jao |
| `get-content` | Page ka HTML + text lo |
| `screenshot` | Screenshot lo |
| `click` | Element click karo |
| `fill` | Form fill karo |
| `type-text` | Type karo |
| `scroll` | Scroll karo |
| `go-back` | Back jao |
| `go-forward` | Forward jao |
| `new-tab` | Naya tab kholo |
| `close-tab` | Tab band karo |
| `evaluate-js` | JavaScript run karo |
| `get-cookies` | Cookies lo |
| `set-cookie` | Cookie set karo |
| `save-session` | Session save karo |
| `restore-session` | Session restore karo |
| `set-proxy` | Proxy set karo |
| `emulate-device` | Mobile/tablet emulate karo |

---

## ⚙️ Configuration

### Environment Variables (.env file)
```bash
# REQUIRED: JWT secret key
JWT_SECRET_KEY=your-secret-key-here

# Optional: Database
DATABASE_DSN=postgresql+asyncpg://user:pass@localhost/agentos

# Optional: Redis
REDIS_URL=redis://localhost:6379/0

# Optional: Proxy
PROXY_URL=http://user:pass@proxy:8080
```

### CLI Arguments
```bash
python3 main.py \
  --agent-token "my-token" \
  --port 8000 \
  --headed \
  --max-ram 500 \
  --proxy "http://proxy:8080" \
  --device iphone_14 \
  --persistent
```

---

## 🏗️ Architecture

```
Agent-OS
├── src/
│   ├── core/
│   │   ├── browser.py          # Main browser engine
│   │   ├── stealth.py          # Anti-detection JS + request blocking
│   │   ├── cdp_stealth.py      # CDP-level stealth injection
│   │   ├── stealth_god.py      # GOD MODE stealth system
│   │   ├── tls_spoof.py        # TLS fingerprint spoofing
│   │   ├── tls_proxy.py        # TLS proxy for real browser fingerprints
│   │   ├── config.py           # Configuration management
│   │   ├── session.py          # Session management
│   │   └── persistent_browser.py # Persistent Chromium engine
│   ├── security/
│   │   ├── evasion_engine.py   # Fingerprint generation + injection
│   │   ├── captcha_bypass.py   # CAPTCHA prevention (block, don't solve)
│   │   ├── human_mimicry.py    # Human behavior simulation
│   │   └── auth_handler.py     # Authentication
│   ├── tools/
│   │   ├── proxy_rotation.py   # Proxy pool management
│   │   ├── smart_finder.py     # Smart element finder
│   │   ├── form_filler.py      # Form filling engine
│   │   └── ...
│   ├── agents/
│   │   └── server.py           # WebSocket + HTTP server
│   └── infra/
│       ├── database.py         # PostgreSQL integration
│       ├── redis_client.py     # Redis integration
│       └── logging.py          # Structured logging
├── connectors/
│   ├── mcp_server.py           # Claude MCP connector
│   ├── openai_connector.py     # OpenAI connector
│   └── openclaw_connector.py   # OpenClaw connector
├── tests/
├── docker-compose.yml
├── Dockerfile
└── main.py                     # Entry point
```

---

## 🛡️ Stealth Technology

### Kaise Kaam Karta Hai (Layered Approach)

```
Layer 1: Network Level
  ├── curl_cffi for real TLS fingerprint
  ├── HTTP/2 fingerprint matching
  └── Request blocking (bot detection scripts)

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
  ├── Scroll behavior
  └── Page interaction timing
```

### Blocked Detection Vendors
DataDome, PerimeterX, Imperva, Akamai, Cloudflare Bot Management,
Kasada, Shape Security, F5, Arkose Labs, ThreatMetrix, Iovation,
Sardine, SEON, IPQualityScore, FraudLabs, hCaptcha, reCAPTCHA

### Blocked Fingerprinting Libraries
FingerprintJS (v1-v3), ClientJS, ThumbmarkJS, CreepJS, BotD,
Sardine, Iovation, ThreatMetrix, Nethra, and 30+ more

---

## 🧪 Testing

```bash
# All tests
python3 -m pytest tests/ -v

# Specific test
python3 -m pytest tests/test_all.py::TestCaptchaBypass -v

# Linter check
pip install ruff && ruff check src/ main.py --select E,F,W --ignore E501
```

---

## 📄 License

MIT License — free for commercial and personal use.

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m "feat: my feature"`
4. Push: `git push origin feature/my-feature`
5. Open PR

All tests must pass. Linter must be clean.
