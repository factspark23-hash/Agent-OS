# Agent-OS — Kaise Use Karein 🚀

## Step 1: Install & Start

### Docker se (Recommended)
```bash
# Clone karo
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS

# Start karo (PostgreSQL + Redis + Agent-OS sab ek saath)
docker compose up -d

# Check karo sab chal raha hai ya nahi
curl http://localhost:8001/health
```

**Output:** `{"status": "healthy", "checks": {...}}`

### Bina Docker ke (Manual)
```bash
git clone https://github.com/factspark23-hash/Agent-OS.git
cd Agent-OS
chmod +x setup.sh && ./setup.sh
python3 main.py --agent-token "apna-token-yahan-dalo"
```

---

## Step 2: Verify Running

```bash
# Health check
curl http://localhost:8001/health

# Status check
curl http://localhost:8001/status
```

---

## Step 3: Use Karo! 

### 🔑 Auth Setup (Production ke liye)

```bash
# Register new user
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "username": "dude",
    "password": "StrongPass123!"
  }'

# Login — JWT token milega
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "dude",
    "password": "StrongPass123!"
  }'

# Response:
# {
#   "status": "success",
#   "access_token": "eyJhbGciOi...",
#   "refresh_token": "eyJhbGciOi...",
#   "user": {"id": "...", "username": "dude", "plan": "free"}
# }

# API Key banao (JWT token se)
curl -X POST http://localhost:8001/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOi..." \
  -d '{"name": "my-app-key", "scopes": ["browser", "scanning"]}'
```

---

### 🌐 Browser Commands (Sabse Important!)

#### Navigate to any website
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "navigate",
    "url": "https://google.com"
  }'
```

#### Screenshot lo
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"command": "screenshot"}'
```

#### Page ka content nikalo
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"command": "get-content"}'
```

#### Links nikalo
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"command": "get-links"}'
```

#### Click karo
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "click",
    "selector": "button[type=submit]"
  }'
```

#### Type karo (Form fill)
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "fill-form",
    "fields": {
      "q": "Agent-OS browser automation"
    }
  }'
```

#### Scroll karo
```bash
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "scroll",
    "direction": "down",
    "amount": 500
  }'
```

---

### 🤖 AI Agent ke saath use karna

#### OpenAI / GPT ke saath
```python
from connectors.openai_connector import get_tools, call_tool

# Tool definitions le lo
tools = get_tools("openai")  # GPT-4 function calling ke liye

# Tool call karo
result = await call_tool("browser_navigate", {"url": "https://github.com"})
result = await call_tool("browser_screenshot", {})
result = await call_tool("browser_click", {"selector": "a[href='/login']"})
```

#### Claude / MCP ke saath
```json
// Claude Desktop config mein add karo
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

#### CLI se (Bash/Python/Node kuch bhi)
```bash
./connectors/agent-os-tool.sh navigate "https://github.com"
./connectors/agent-os-tool.sh screenshot
./connectors/agent-os-tool.sh get-content
```

---

### 🔐 Login Save Karo (Auto-Login)

```bash
# Pehle manually login karo browser mein, phir credentials save karo
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "save-creds",
    "site": "github.com"
  }'

# Baad mein auto-login
curl -X POST http://localhost:8001/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "auto-login",
    "site": "github.com"
  }'
```

---

### 📋 Real-World Examples

#### Example 1: GitHub se repo list nikalo
```bash
# Navigate
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{"command": "navigate", "url": "https://github.com/factspark23-hash"}'

# Content lo
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{"command": "get-content"}'
```

#### Example 2: Amazon pe product search
```bash
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{"command": "navigate", "url": "https://amazon.com"}'

curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{"command": "fill-form", "fields": {"field-keywords": "MacBook Pro"}}'

curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{"command": "click", "selector": "input[type=submit]"}'
```

#### Example 3: Multi-step workflow
```bash
curl -X POST http://localhost:8001/command \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "command": "workflow",
    "steps": [
      {"command": "navigate", "url": "https://example.com/login"},
      {"command": "fill-form", "fields": {"email": "test@test.com", "password": "pass123"}},
      {"command": "click", "selector": "button[type=submit]"},
      {"command": "wait", "selector": ".dashboard"},
      {"command": "screenshot"}
    ]
  }'
```

---

## 📊 All Commands Reference

| Category | Commands |
|----------|----------|
| **Navigation** | `navigate`, `back`, `forward`, `reload` |
| **Click/Type** | `click`, `type`, `press`, `hover`, `double-click`, `right-click` |
| **Content** | `get-content`, `get-dom`, `get-links`, `get-images`, `get-text`, `screenshot` |
| **Forms** | `fill-form`, `fill-job`, `select`, `checkbox`, `upload`, `clear-input` |
| **Scroll** | `scroll` (up/down/left/right) |
| **Auth** | `save-creds`, `auto-login`, `get-cookies`, `set-cookie` |
| **Tabs** | `tabs` (list/new/switch/close) |
| **Smart** | `smart-click`, `smart-fill`, `smart-find`, `smart-wait` |
| **Workflow** | `workflow`, `workflow-save`, `workflow-list` |
| **Network** | `network-start`, `network-stop`, `network-get`, `network-apis` |
| **Security** | `scan-xss`, `scan-sqli`, `scan-sensitive` |
| **Recording** | `record-start`, `record-stop`, `replay-play` |
| **Multi-Agent** | `hub-register`, `hub-task-create`, `hub-broadcast` |
| **Proxy** | `proxy-add`, `proxy-get`, `proxy-list`, `proxy-stats` |
| **Media** | `transcribe` |

---

## 🐳 Production Deployment

```bash
# Full stack deploy (PostgreSQL + Redis + Agent-OS + Nginx)
docker compose --profile with-nginx up -d

# Environment variables set karo
export JWT_SECRET_KEY="your-super-secret-key-here"
export POSTGRES_PASSWORD="strong-db-password"

# Logs dekho
docker compose logs -f agent-os
```

---

## ⚠️ Important Notes

1. **Localhost pe chalao** — Ye local server hai, internet pe expose mat karo bina nginx/SSL ke
2. **Token safe rakho** — Legacy token browser-only access deta hai, production mein JWT use karo
3. **CORS** — Default mein cross-origin blocked hai, `server.cors_allowed_origins` mein apna domain add karo
4. **RAM** — ~500MB idle, ~800MB under load. Zyada tabs = zyada RAM

---

_Built with ❤️ by Agent-OS team_
