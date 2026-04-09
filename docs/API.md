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

## New Commands (v2.1)

### find-element
Find an element by text, ARIA role, aria-label, or natural language description.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| description | string | Yes | Element description: text, role name, aria-label, or natural language |
| method | string | No | Search strategy: `smart` (default), `text`, `role`, `aria-label` |
| exact | bool | No | Exact text match (text method only, default false) |

```json
{"token":"my-agent","command":"find-element","description":"the login button","method":"smart"}
```
**Response:**
```json
{"status":"success","selector":"#login-btn","type":"button","keyword":"login"}
```
**Error:** `{"status":"error","error":"No button found matching: login"}`

### find-all-interactive
Find all interactive elements (buttons, inputs, links, selects) on the page.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"find-all-interactive"}
```
**Response:**
```json
{
  "status": "success",
  "elements": [
    {"tag":"button","id":"login-btn","name":null,"type":"submit","role":null,"aria_label":"Log in","placeholder":null,"text":"Log in","href":null,"selector":"#login-btn","visible":true}
  ],
  "count": 42
}
```

### extract
Extract structured data from the page.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| type | string | No | Extraction type: `tables`, `lists`, `articles`, `jsonld`, `metadata`, `links`, `all` (default: `all`) |
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"extract","type":"tables"}
```
**Response (tables):**
```json
{
  "status": "success",
  "tables": [
    {"index":0,"id":"data-table","headers":["Name","Email","Role"],"rows":[["Alice","alice@x.com","Admin"]],"row_count":1,"col_count":3}
  ],
  "count": 1
}
```

**Response (articles):**
```json
{
  "status": "success",
  "article": {
    "title": "How to Build a Browser Agent",
    "body": "...full text...",
    "author": "Jane Doe",
    "date": "2026-04-01",
    "description": "A comprehensive guide...",
    "found": true
  }
}
```

**Response (jsonld):**
```json
{
  "status": "success",
  "jsonld": [{"@type":"Article","headline":"..."}],
  "count": 1
}
```

**Response (metadata):**
```json
{
  "status": "success",
  "metadata": {
    "title": "Page Title",
    "meta": {"description": "...", "keywords": "..."},
    "open_graph": {"title": "...", "image": "..."},
    "twitter": {"card": "summary_large_image"},
    "links": {"canonical": "https://example.com/page"}
  }
}
```

**Response (links):**
```json
{
  "status": "success",
  "links": [
    {"text":"Click here","href":"https://example.com/target","title":"Go to target","target":"_blank","rel":"noopener"}
  ],
  "count": 1
}
```

**Response (all):**
```json
{
  "status": "success",
  "tables": [...],"table_count": 2,
  "lists": [...],"list_count": 3,
  "article": {...},
  "jsonld": [...],"jsonld_count": 1,
  "metadata": {...}
}
```

### get-markdown
Convert the current page to clean Markdown. Strips ads, navigation, footer, scripts, and styles.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"get-markdown"}
```
**Response:**
```json
{
  "status": "success",
  "markdown": "# Page Title\n\nArticle content in **Markdown**...\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |",
  "length": 4096,
  "page_id": "main"
}
```

### generate-pdf
Generate a PDF from the current page. Saves to `~/.agent-os/downloads/`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |
| format | string | No | Page format: `A4`, `Letter`, etc. (default: `A4`) |
| landscape | bool | No | Landscape orientation |
| margins | dict | No | `{top, bottom, left, right}` in CSS units |
| scale | float | No | Scale factor (0.1–2.0) |

```json
{"token":"my-agent","command":"generate-pdf","format":"Letter","landscape":true}
```
**Response:**
```json
{
  "status": "success",
  "path": "/home/user/.agent-os/downloads/Page_Title_1712678400.pdf",
  "filename": "Page_Title_1712678400.pdf",
  "size_bytes": 245760
}
```

---

### har-start
Start HAR (HTTP Archive) recording for a page. Captures all network requests.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"har-start"}
```
**Response:**
```json
{"status":"success","message":"HAR recording started for page 'main'","page_id":"main"}
```
**Error:** `{"status":"error","error":"HAR recording already active for page 'main'"}`

### har-stop
Stop HAR recording for a page.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"har-stop"}
```
**Response:**
```json
{"status":"success","message":"HAR recording stopped","page_id":"main","request_count":156,"duration_seconds":42.3}
```

### har-save
Save recorded HAR data to a HAR 1.2 JSON file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |
| path | string | No | Output file path (auto-generated in `~/.agent-os/downloads/` if omitted) |

```json
{"token":"my-agent","command":"har-save","path":"/tmp/my_capture.har"}
```
**Response:**
```json
{"status":"success","path":"/tmp/my_capture.har","entries":156}
```
**Error:** `{"status":"error","error":"No HAR recording active for page 'main'. Start one first with har-start."}`

### har-status
Get HAR recording status.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"har-status"}
```
**Response (recording active):**
```json
{"status":"success","recording":true,"page_id":"main","requests_captured":156,"started_at":1712678400.0,"duration_seconds":42.3}
```
**Response (not recording):**
```json
{"status":"success","recording":false,"page_id":"main"}
```

---

### set-profile
Apply a stealth browser profile to mimic a specific OS/browser combination. Requires browser restart to fully apply.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| profile | string | Yes | Profile name |

**Available profiles:**
| Profile | Description |
|---------|-------------|
| `windows-chrome` | Windows 10, Chrome 120, US locale |
| `mac-safari` | macOS Sonoma, Safari 17, US locale |
| `linux-firefox` | Ubuntu Linux, Firefox 120, US locale |
| `mobile-chrome-android` | Android 14, Chrome Mobile, US locale |
| `mobile-safari-ios` | iOS 17, Safari Mobile, US locale |

```json
{"token":"my-agent","command":"set-profile","profile":"mac-safari"}
```
**Response:**
```json
{
  "status": "success",
  "profile": "mac-safari",
  "message": "Profile stored. Restart browser to fully apply.",
  "details": {
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "viewport": {"width": 1440, "height": 900},
    "platform": "MacIntel"
  }
}
```
**Error:** `{"status":"error","error":"Unknown profile: xyz. Available: [windows-chrome, mac-safari, ...]"}`

### list-profiles
List all available stealth profiles with descriptions.

```json
{"token":"my-agent","command":"list-profiles"}
```
**Response:**
```json
{
  "status": "success",
  "profiles": {
    "windows-chrome": "Windows 10, Chrome 120, US locale — most common fingerprint",
    "mac-safari": "macOS Sonoma, Safari 17, US locale",
    "linux-firefox": "Ubuntu Linux, Firefox 120, US locale",
    "mobile-chrome-android": "Android 14, Chrome Mobile, US locale",
    "mobile-safari-ios": "iOS 17, Safari Mobile, US locale"
  },
  "count": 5
}
```

---

### get-network-logs
Get network request logs, optionally filtered.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |
| url_pattern | string | No | Filter by URL substring |
| status_code | int | No | Filter by HTTP status code |
| resource_type | string | No | Filter by resource type (`document`, `xhr`, `fetch`, `script`, `stylesheet`, `image`, etc.) |

```json
{"token":"my-agent","command":"get-network-logs","url_pattern":"api","resource_type":"xhr"}
```
**Response:**
```json
{
  "status": "success",
  "page_id": "main",
  "logs": [
    {
      "url": "https://api.example.com/data",
      "method": "GET",
      "resource_type": "xhr",
      "headers": {"accept": "application/json"},
      "timestamp": 1712678400.0,
      "status": 200,
      "response_headers": {"content-type": "application/json"},
      "response_size": 4096,
      "timing": null
    }
  ],
  "total": 23,
  "total_captured": 312
}
```

### clear-network-logs
Clear captured network request logs for a page.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |

```json
{"token":"my-agent","command":"clear-network-logs"}
```
**Response:** `{"status":"success","cleared":312,"page_id":"main"}`

### get-api-calls
Get XHR/Fetch API calls from the network log. Convenience filter for `resource_type=xhr|fetch`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page_id | string | No | Tab ID (default: `main`) |
| url_pattern | string | No | Filter by URL substring |

```json
{"token":"my-agent","command":"get-api-calls","url_pattern":"graphql"}
```
**Response:**
```json
{
  "status": "success",
  "api_calls": [
    {"method":"POST","url":"https://api.example.com/graphql","status":200,"resource_type":"fetch","timestamp":1712678400.0}
  ],
  "count": 5,
  "page_id": "main"
}
```

---

### proxy-rotate
Rotate to the next proxy in the configured list. Requires browser restart to apply.

```json
{"token":"my-agent","command":"proxy-rotate"}
```
**Response:**
```json
{"status":"success","message":"Proxy rotated. Restart browser to apply.","proxy":"http://proxy2.example.com:8080","index":1}
```
**Error:** `{"status":"error","error":"No proxies configured. Set browser.proxies first."}`

### proxy-status
Get current proxy configuration.

```json
{"token":"my-agent","command":"proxy-status"}
```
**Response:**
```json
{
  "status": "success",
  "current_proxy": "http://proxy1.example.com:8080",
  "available_proxies": 3,
  "proxy_list": [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "socks5://proxy3.example.com:1080"
  ],
  "active_index": 0
}
```

---

### webhook-register
Register a webhook endpoint to receive real-time browser events via HTTP POST.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | string | Yes | HTTP(S) URL to receive POST events |
| events | array of strings | Yes | Event types to subscribe to |
| secret | string | No | Optional HMAC-SHA256 secret for payload signing |

**Supported event types:**
`navigation`, `click`, `form_submit`, `form_fill`, `screenshot`, `error`, `session_start`, `session_end`, `download`, `alert`, `page_load`, `network_error`, `scan_complete`, `transcription_complete`

```json
{
  "token": "my-agent",
  "command": "webhook-register",
  "url": "https://hooks.example.com/agent-os",
  "events": ["navigation", "click", "error"],
  "secret": "my-hmac-secret"
}
```
**Response:**
```json
{
  "status": "success",
  "webhook_id": "a1b2c3d4",
  "events": ["navigation", "click", "error"],
  "url": "https://hooks.example.com/agent-os"
}
```
**Errors:**
- `{"status":"error","error":"URL must start with http:// or https://"}`
- `{"status":"error","error":"Maximum 10 webhooks allowed"}`
- `{"status":"error","error":"Webhook already registered for URL: ..."}`
- `{"status":"error","error":"Unknown event type(s): [bad_event]. Supported: [...]"}`

**Webhook POST body format:**
```json
{
  "event": "click",
  "timestamp": "2026-04-09T04:20:00+00:00",
  "data": {
    "selector": "#submit-btn",
    "session_id": "sess-abc123"
  },
  "webhook_id": "a1b2c3d4"
}
```

**HMAC Signature:** If `secret` is set, the `X-Agent-OS-Signature` header contains `sha256=<hmac-hex>` of the request body.

### webhook-list
List all registered webhooks (secrets are not returned).

```json
{"token":"my-agent","command":"webhook-list"}
```
**Response:**
```json
{
  "status": "success",
  "webhooks": [
    {
      "webhook_id": "a1b2c3d4",
      "url": "https://hooks.example.com/agent-os",
      "events": ["navigation", "click", "error"],
      "active": true,
      "created_at": 1712678400.0,
      "last_triggered": 1712678500.0,
      "trigger_count": 42,
      "failures": 0,
      "has_secret": true
    }
  ],
  "count": 1
}
```

### webhook-remove
Remove a registered webhook.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| webhook_id | string | Yes | Webhook ID to remove |

```json
{"token":"my-agent","command":"webhook-remove","webhook_id":"a1b2c3d4"}
```
**Response:** `{"status":"success","webhook_id":"a1b2c3d4","url":"https://hooks.example.com/agent-os"}`
**Error:** `{"status":"error","error":"Webhook not found: a1b2c3d4"}`

### webhook-test
Send a test `ping` event to verify a webhook is reachable.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| webhook_id | string | Yes | Webhook ID to test |

```json
{"token":"my-agent","command":"webhook-test","webhook_id":"a1b2c3d4"}
```
**Response:** `{"status":"success","webhook_id":"a1b2c3d4","message":"Test ping delivered successfully"}`
**Error:** `{"status":"error","error":"Webhook not found: a1b2c3d4"}`

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

### Stealth Profiles
Apply predefined browser fingerprints to mimic specific environments:
- `windows-chrome` — Most common fingerprint (Chrome 120 on Windows 10)
- `mac-safari` — macOS Sonoma with Safari 17
- `linux-firefox` — Ubuntu with Firefox 120
- `mobile-chrome-android` — Pixel 8 with Chrome Mobile
- `mobile-safari-ios` — iPhone with Safari Mobile

Use `set-profile` to apply, then restart the browser.

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
  proxy: null
  proxies: []

session:
  timeout_minutes: 15
  auto_wipe: true
  max_concurrent: 3

security:
  captcha_bypass: true
  human_mimicry: true
  block_bot_queries: true

retry:
  max_retries: 3
  base_delay: 0.5
  max_delay: 10.0
  backoff_factor: 2.0

webhooks:
  endpoints: []
```

---

## Privacy & Security

- **Session Data**: Auto-wiped after timeout (default 15 min)
- **Credentials**: Encrypted with AES-256, stored at `~/.agent-os/vault.enc`
- **No Telemetry**: Zero data collection
- **Local Only**: All processing on-device, no external services
- **RAM Safe**: Built-in RAM monitor caps usage
- **Webhook Signing**: Optional HMAC-SHA256 payload verification
