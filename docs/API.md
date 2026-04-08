# Agent-OS API Documentation

## Quick Start

```bash
# Install
pip install -r requirements.txt
playwright install chromium

# Run
python main.py --agent-token "my-agent"

# Connect
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent","command":"navigate","url":"https://github.com"}'
```

---

## Connection Methods

### WebSocket (Real-time)
```javascript
const ws = new WebSocket('ws://localhost:8000');
ws.onopen = () => {
  ws.send(JSON.stringify({
    token: "my-agent",
    command: "navigate",
    url: "https://example.com"
  }));
};
ws.onmessage = (msg) => console.log(JSON.parse(msg.data));
```

### HTTP REST (Simple)
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -d '{"token":"my-agent","command":"navigate","url":"https://example.com"}'
```

### Python
```python
import requests
r = requests.post("http://localhost:8001/command", json={
    "token": "my-agent",
    "command": "navigate",
    "url": "https://example.com"
})
print(r.json())
```

---

## Commands Reference

### navigate
Navigate to a URL.

```json
{"token":"my-agent","command":"navigate","url":"https://github.com/login"}
```
**Response:** `{"status":"success","url":"https://github.com/login","title":"Sign in · GitHub","status_code":200}`

### fill-form
Fill form fields with human-like typing.

```json
{"token":"my-agent","command":"fill-form","fields":{"#email":"user@example.com","#password":"secret123"}}
```
**Response:** `{"status":"success","filled":["#email","#password"],"total":2}`

### click
Click an element with human-like mouse movement.

```json
{"token":"my-agent","command":"click","selector":"button[type='submit']"}
```

### screenshot
Take a screenshot (base64 PNG).

```json
{"token":"my-agent","command":"screenshot"}
```

### get-content
Get page HTML and text.

```json
{"token":"my-agent","command":"get-content"}
```

### get-dom
Get structured DOM snapshot.

```json
{"token":"my-agent","command":"get-dom"}
```

### scroll
Scroll the page.

```json
{"token":"my-agent","command":"scroll","direction":"down","amount":500}
```

### evaluate-js
Execute JavaScript.

```json
{"token":"my-agent","command":"evaluate-js","script":"document.title"}
```

### scan-xss
Scan for XSS vulnerabilities.

```json
{"token":"my-agent","command":"scan-xss","url":"https://target.com/search?q=test"}
```
**Response:** `{"status":"success","scanner":"xss","vulnerabilities_found":1,"vulnerabilities":[...]}`

### scan-sqli
Scan for SQL injection.

```json
{"token":"my-agent","command":"scan-sqli","url":"https://target.com/page?id=1"}
```

### transcribe
Transcribe video/audio from URL.

```json
{"token":"my-agent","command":"transcribe","url":"https://youtube.com/watch?v=xxx"}
```

### save-creds
Save credentials for auto-login.

```json
{"token":"my-agent","command":"save-creds","domain":"github.com","username":"user@email.com","password":"secret"}
```

### auto-login
Auto-login using saved credentials.

```json
{"token":"my-agent","command":"auto-login","url":"https://github.com/login","domain":"github.com"}
```

### tabs
Manage browser tabs.

```json
{"token":"my-agent","command":"tabs","action":"list"}
{"token":"my-agent","command":"tabs","action":"new","tab_id":"research"}
{"token":"my-agent","command":"tabs","action":"close","tab_id":"research"}
```

---

## Status Endpoints

### GET /status
Server health check.

```bash
curl http://localhost:8001/status
```
**Response:** `{"status":"running","uptime_seconds":3600,"active_sessions":2,"browser_active":true}`

### GET /commands
List all available commands with parameters.

```bash
curl http://localhost:8001/commands
```

### GET /debug
Real-time debug info.

```bash
curl http://localhost:8001/debug
```

### GET /screenshot
Quick screenshot from command line.

```bash
curl http://localhost:8001/screenshot | base64 -d > screenshot.png
```

---

## Anti-Detection Features

Agent-OS automatically blocks these bot detection systems:
- Google reCAPTCHA v2/v3
- hCaptcha
- Cloudflare Turnstile
- PerimeterX
- DataDome
- Imperva/Incapsula
- Akamai Bot Manager
- Shape Security
- Kasada

### How it works:
1. **Request Interception**: Bot detection URLs are blocked at the network level
2. **Script Removal**: Detection JavaScript is removed before execution
3. **Fake Responses**: Blocked requests return fake "human verified" responses
4. **DOM Patching**: `navigator.webdriver`, plugins, hardware info are spoofed
5. **Human Mimicry**: Mouse movements use Bezier curves, typing has realistic delays

---

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
```

---

## Privacy & Security

- **Session Data**: Auto-wiped after timeout (default 15 min)
- **Credentials**: Encrypted with AES-256, stored at `~/.agent-os/vault.enc`
- **No Telemetry**: Zero data collection
- **Local Only**: All processing on-device, no external services
- **RAM Safe**: Built-in RAM monitor caps usage
