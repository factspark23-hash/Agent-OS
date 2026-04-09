# Agent-OS — Browser for AI Agents

A browser automation server built **exclusively for AI agents** — not humans.

Connect any AI (Claude, GPT-4, Codex, OpenClaw, Qwen, local LLMs) and give them a real browser with anti-detection, human mimicry, and full control. Free, open-source, runs locally.

**Stack:** Python 3.10+ / Playwright (Chromium) — no GPU, no cloud, no monthly fees.

## Why Agent-OS?

| Problem | Agent-OS Solution |
|---------|-------------------|
| AI agents can't browse the web | Full browser control via API |
| Bot detection blocks automation | Blocks detection scripts **before they load** — no CAPTCHA ever appears |
| Browser services charge $$$ | Free, open-source, runs on your machine |
| Third-party browsers = no control | Your machine, your browser, your rules |
| APIs don't show what a user sees | Real browser = real user experience |

## Features

- 🛡️ **Anti-Detection** — Blocks reCAPTCHA, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Imperva, Akamai, Kasada at the network level
- 🤖 **74+ CLI Commands / 38 Connector Tools** — Navigate, click, fill forms, screenshot, scroll, tabs, DOM analysis, smart finder, workflows, network capture, page analysis, and more
- 🧠 **Human Mimicry** — Bezier mouse curves, realistic typing delays, natural scroll behavior, typo simulation
- 🔍 **Security Scanners** — XSS, SQL injection, sensitive data exposure detection
- 🔍 **Smart Element Finder** — Find elements by visible text — no CSS selector needed
- 🎯 **Multi-Step Workflows** — Chain actions with variables, retries, error handling, save/load templates
- 📊 **Network Capture** — Capture, filter, and export all HTTP requests. Discover API endpoints automatically
- 🧪 **Page Analysis** — Summarize pages, extract tables, SEO audit, accessibility check, find emails/phones
- 🌐 **Proxy Support** — HTTP, HTTPS, SOCKS5 with auth
- 📱 **Mobile Emulation** — 11 device presets (iPhone, Galaxy, iPad, Pixel, Desktop)
- 🔄 **Session Save/Restore** — Save full browser state (cookies, localStorage, tabs) and restore later
- 🎬 **Video Transcription** — Local Whisper integration (no cloud APIs)
- 🔒 **Privacy First** — Sessions auto-wipe, AES-256 credential vault, zero telemetry
- 🔌 **Connect Any Agent** — MCP (Claude/Codex), OpenAI, Claude API, OpenClaw, CLI — all tools on every connector
- 🍪 **Cookie Management** — Get/set cookies with full control (domain, path, secure, httpOnly, sameSite)
- 📋 **Console Log Capture** — Capture and retrieve browser console output (log, warn, error, pageerror)
- 🔄 **Persistent Chromium** — Long-running browser with per-user isolated contexts, auto-recovery, health monitoring, state survives restarts

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

### Option 3: Persistent Chromium (Production)

For production deployments serving multiple users, enable persistent mode:

```bash
# Via CLI flag
python3 main.py --persistent --agent-token "my-token"

# Via config (persistent.yaml or ~/.agent-os/config.yaml)
# persistent:
#   enabled: true
#   max_instances: 5
#   max_contexts_per_instance: 50
#   idle_timeout_minutes: 60
#   memory_cap_mb: 4000
#   auto_restart: true
```

**Persistent mode provides:**
- Long-running Chromium processes (no restart on every request)
- Per-user isolated browser contexts with dedicated profile directories
- State survives restarts (cookies, localStorage, open tabs auto-restore)
- Auto-recovery from browser crashes
- Health monitoring with configurable intervals
- LRU eviction of idle contexts
- Memory cap enforcement
- Horizontal scaling via multiple Chromium instances

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

All connectors expose the same tool set. Pick your platform:

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

manifest = get_manifest()  # Register with OpenClaw
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

## All Tools

### Navigation
| Tool | Description |
|------|-------------|
| `navigate` | Navigate to a URL with human-like timing |
| `back` | Go back in browser history |
| `forward` | Go forward in browser history |
| `reload` | Reload the current page |

### Interaction
| Tool | Description |
|------|-------------|
| `click` | Click an element (CSS selector) with Bezier mouse movement |
| `double-click` | Double-click an element |
| `right-click` | Right-click an element (opens context menu) |
| `context-action` | Right-click + select context menu option by text |
| `type` | Type text into focused element with human-like delays |
| `press` | Press keyboard key (Enter, Tab, Escape, etc.) |
| `hover` | Hover over an element |
| `fill-form` | Fill multiple form fields with human-like typing |
| `clear-input` | Clear an input field |
| `checkbox` | Set checkbox to checked/unchecked |
| `select` | Select a dropdown option |
| `upload` | Upload a file to a file input |
| `wait` | Wait for an element to appear |
| `drag-drop` | Drag element and drop on another |
| `drag-offset` | Drag element by pixel offset |

### Smart Finder (No CSS Selectors Needed!)
| Tool | Description |
|------|-------------|
| `smart-find` | Find element by visible text, label, or description |
| `smart-find-all` | Find ALL matching elements, ranked by relevance |
| `smart-click` | Click element by its visible text |
| `smart-fill` | Find input by label/placeholder and fill it |

### Content Extraction
| Tool | Description |
|------|-------------|
| `get-content` | Get page HTML and text content |
| `get-dom` | Get structured DOM snapshot |
| `get-links` | Get all links on the page |
| `get-images` | Get all images with src, alt, dimensions |
| `get-text` | Get text content of a specific element |
| `get-attr` | Get attribute value from an element |
| `screenshot` | Take screenshot (base64 PNG, full-page option) |
| `evaluate-js` | Execute JavaScript in page context |
| `scroll` | Scroll page up/down with human-like behavior |
| `viewport` | Change browser viewport size |

### Browser Control
| Tool | Description |
|------|-------------|
| `tabs` | Manage tabs: list, new, switch, close |
| `console-logs` | Get captured browser console logs |
| `get-cookies` | Get all cookies |
| `set-cookie` | Set a cookie with full control |
| `add-extension` | Load Chrome extension (headed mode) |

### Page Analysis
| Tool | Description |
|------|-------------|
| `page-summary` | Full page analysis: title, headings, content, forms, links, tech stack, readability |
| `page-tables` | Extract all HTML tables as structured data |
| `page-structured` | Extract JSON-LD and Microdata structured data |
| `page-emails` | Find all email addresses on page |
| `page-phones` | Find all phone numbers on page |
| `page-accessibility` | Basic accessibility audit |
| `page-seo` | SEO audit with score and issues |

### Multi-Step Workflows
| Tool | Description |
|------|-------------|
| `workflow` | Execute multi-step workflow with variables, retries, error handling |
| `workflow-template` | Execute a saved or built-in workflow template |
| `workflow-json` | Execute workflow from JSON string |
| `workflow-save` | Save workflow as reusable template |
| `workflow-list` | List all workflow templates |
| `workflow-status` | Get status of a running workflow |

**Built-in templates:** `google_search`, `login`, `screenshot_full`

### Network Capture
| Tool | Description |
|------|-------------|
| `network-start` | Start capturing requests (filter by URL, type, method) |
| `network-stop` | Stop capturing and get summary |
| `network-get` | Get captured requests with filters and pagination |
| `network-apis` | Discover all API endpoints from captured traffic |
| `network-detail` | Get full details of a specific request |
| `network-stats` | Get capture statistics |
| `network-export` | Export captured requests (JSON or HAR format) |
| `network-clear` | Clear captured data |

### Security Scanners
| Tool | Description |
|------|-------------|
| `scan-xss` | Scan URL for Cross-Site Scripting vulnerabilities |
| `scan-sqli` | Scan URL for SQL injection vulnerabilities |
| `scan-sensitive` | Scan page for exposed sensitive data (API keys, tokens, IPs) |

### Authentication
| Tool | Description |
|------|-------------|
| `save-creds` | Save credentials with AES-256 encryption |
| `auto-login` | Auto-login using saved credentials |

### Media
| Tool | Description |
|------|-------------|
| `transcribe` | Transcribe video/audio from URL using local Whisper |

### Proxy
| Tool | Description |
|------|-------------|
| `set-proxy` | Set proxy (HTTP, HTTPS, SOCKS5) |
| `get-proxy` | Get current proxy configuration |

### Mobile Emulation
| Tool | Description |
|------|-------------|
| `emulate-device` | Emulate mobile/tablet/desktop device |
| `list-devices` | List all available device presets |

**Available devices:** `iphone_se`, `iphone_14`, `iphone_14_pro_max`, `ipad`, `ipad_pro`, `galaxy_s23`, `galaxy_tab_s9`, `pixel_8`, `desktop_1080`, `desktop_1440`, `desktop_4k`

### Sessions
| Tool | Description |
|------|-------------|
| `save-session` | Save full browser state (cookies, localStorage, sessionStorage, tabs) |
| `restore-session` | Restore previously saved browser state |
| `list-sessions` | List all saved sessions |
| `delete-session` | Delete a saved session |

### Forms
| Tool | Description |
|------|-------------|
| `fill-job` | Auto-fill job application forms with profile data |

## How Anti-Detection Works

Agent-OS doesn't solve CAPTCHAs — it **prevents them from loading**:

1. **Network-level blocking** — Detection scripts (reCAPTCHA, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Imperva, Akamai, Kasada) are intercepted and blocked before the browser executes them
2. **DOM patching** — `navigator.webdriver`, plugin lists, hardware fingerprints, WebGL, canvas, audio, and WebRTC are all spoofed
3. **Human mimicry** — Mouse movements use Bezier curves, typing has realistic random delays, typo simulation, natural scroll behavior
4. **Script injection** — Anti-detection JavaScript runs before any page scripts

**What's blocked:** Google reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, PerimeterX, DataDome, Imperva, Akamai Bot Manager, Kasada, Shape Security

**Honest limitations:** Advanced TLS fingerprinting can still detect Playwright. Some sophisticated bot protection (BotD) may still work. Effectiveness varies by site — test on your specific targets.

## Architecture

```
Agent-OS/
├── main.py                    # Entry point & CLI
├── Dockerfile                 # Docker build (multi-stage, ~350MB)
├── docker-compose.yml         # Docker Compose config
├── setup.sh                   # One-click installer
├── requirements.txt           # Python dependencies
├── qwen_bridge.py             # Qwen model bridge
├── src/
│   ├── core/
│   │   ├── browser.py         # Playwright browser with stealth patches
│   │   ├── config.py          # Configuration management
│   │   └── session.py         # Session lifecycle & auto-wipe
│   ├── agents/
│   │   └── server.py          # WebSocket + REST API server (74 commands)
│   ├── security/
│   │   ├── captcha_bypass.py  # Detection script blocking engine
│   │   ├── human_mimicry.py   # Bezier mouse, typing simulation
│   │   └── auth_handler.py    # AES-256 encrypted credential vault
│   └── tools/
│       ├── scanner.py         # XSS, SQLi, sensitive data scanners
│       ├── transcriber.py     # Video/audio transcription (Whisper)
│       ├── form_filler.py     # Smart form detection & filling
│       ├── smart_finder.py    # Find elements by visible text
│       ├── workflow.py        # Multi-step workflow engine
│       ├── network_capture.py # HTTP request capture & analysis
│       └── page_analyzer.py   # Page summary, SEO, accessibility
├── connectors/
│   ├── mcp_server.py          # MCP connector (38 tools)
│   ├── openai_connector.py    # OpenAI + Claude connector (38 tools)
│   ├── openclaw_connector.py  # OpenClaw connector (38 tools)
│   └── agent-os-tool.sh       # CLI connector (74 commands)
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

## CLI Arguments

```bash
python3 main.py [options]

Options:
  --headed              Show browser window
  --agent-token TOKEN   Set agent authentication token
  --port PORT           WebSocket port (HTTP = port+1)
  --max-ram MB          Cap RAM usage in MB
  --config PATH         Config file path
  --proxy URL           Proxy URL (http://user:pass@host:port)
  --device PRESET       Device preset (iphone_14, galaxy_s23, etc.)
  --persistent          Enable persistent Chromium (production mode)
```

## API Endpoints

### Standard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/command` | POST | Execute any tool command |
| `/status` | GET | Server status, uptime, sessions |
| `/commands` | GET | List all available commands with params |
| `/debug` | GET | Debug info (sessions, tabs, blocked requests) |
| `/screenshot` | GET | Quick screenshot (base64 text) |

### Persistent Browser (when `--persistent` enabled)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/persistent/health` | GET | Health of all browser instances, memory, contexts |
| `/persistent/users` | GET | List all active user contexts |
| `/persistent/command` | POST | Execute command for a specific user (needs `user_id`) |

## HTTP API Example

```bash
# Check status
curl http://localhost:8001/status

# Navigate
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"navigate","url":"https://example.com"}'

# Smart click (no selector needed)
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"smart-click","text":"Sign In"}'

# Execute workflow
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent-123","command":"workflow","steps":[{"command":"navigate","url":"https://google.com"},{"command":"fill-form","fields":{"input[name=q]":"hello"}},{"command":"press","key":"Enter"}]}'
```

## WebSocket API

```javascript
const ws = new WebSocket('ws://localhost:8000');
ws.onopen = () => {
  ws.send(JSON.stringify({
    token: 'my-agent-123',
    command: 'navigate',
    url: 'https://example.com'
  }));
};
ws.onmessage = (e) => console.log(JSON.parse(e.data));
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
