# Agent-OS MCP Passthrough Wrapper

<p align="center">
  <strong>Zero-API-key MCP server for Agent-OS. 199 browser tools + 87% token savings.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/API_Key-Not_Required-brightgreen.svg" alt="No API Key" />
  <img src="https://img.shields.io/badge/tools-199-brightgreen.svg" alt="199 Tools" />
  <img src="https://img.shields.io/badge/token_savings-87%25-blue.svg" alt="87% Token Savings" />
  <img src="https://img.shields.io/badge/MCP-1.0-purple.svg" alt="MCP 1.0" />
</p>

---

## What Is This?

A standalone MCP server that gives Claude Desktop, Claude Code, Codex, and any MCP client access to **199 browser automation tools** — without requiring any LLM API key.

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  MCP Client      │     │  MCP Passthrough │     │  Agent-OS Server │
│  (Claude/GPT)    │────▶│  (This wrapper)  │────▶│  (Browser engine)│
│                  │     │                  │     │                  │
│  • Reasoning     │     │  • 199 tools     │     │  • Chromium      │
│  • Tool selection│     │  • Compression   │     │  • Stealth       │
│  • Already paid  │     │  • LLM fallback  │     │  • Anti-detect   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

**Your MCP client's LLM handles reasoning. Agent-OS handles execution. No extra cost.**

---

## Why Use This?

| Problem | Solution |
|---------|----------|
| Agent-OS needs an API key for LLM tools | BuiltinLLM — rule-based, zero API calls |
| Browser results burn 10k+ tokens per page | SmartCompressor — 87% token savings |
| Setting up MCP is complicated | One command: `./run_mcp.sh` |
| Server down = everything crashes | Graceful errors, LLM tools work standalone |

---

## Quick Start

### Option A: Startup Script (Easiest)

```bash
cd Agent-OS

# Start everything
./run_mcp.sh --token "my-secret-token"
```

This starts both the Agent-OS server and the MCP wrapper, and prints your Claude Desktop config.

### Option B: Manual

```bash
# Terminal 1: Start Agent-OS server
cd Agent-OS
python3 main.py --agent-token "my-secret-token"

# Terminal 2: Start MCP wrapper
cd Agent-OS
AGENT_OS_TOKEN="my-secret-token" python3 connectors/mcp_passthrough.py
```

---

## Claude Desktop Configuration

Add to your config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-os": {
      "command": "python3",
      "args": ["/absolute/path/to/Agent-OS/connectors/mcp_passthrough.py"],
      "env": {
        "AGENT_OS_URL": "http://localhost:8001",
        "AGENT_OS_TOKEN": "my-secret-token"
      }
    }
  }
}
```

Restart Claude Desktop. **199 tools appear automatically.**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_OS_URL` | `http://localhost:8001` | Agent-OS server URL |
| `AGENT_OS_TOKEN` | (auto-generated) | Auth token (must match server) |
| `AGENT_OS_COMPRESS` | `aggressive` | Compression mode: `aggressive`, `normal`, `off` |
| `AGENT_OS_MAX_OUTPUT` | `8000` | Max chars returned per tool call |

### Compression Modes

| Mode | Token Savings | Best For |
|------|---------------|----------|
| `aggressive` | ~85% | Production — most use cases |
| `normal` | ~50% | When you need more detail |
| `off` | 0% | Debugging |

---

## How It Works

### Architecture

```
MCP Client (Claude/GPT)
    │
    │  1. Client asks: "Browse github.com and summarize trending repos"
    │
    ▼
MCP Passthrough
    │
    │  2. LLM tools → BuiltinLLM (rule-based, no API)
    │  3. Browser tools → proxy to Agent-OS server
    │  4. Results → SmartCompressor (strip HTML, dedupe, cap)
    │
    ▼
Agent-OS Server
    │
    │  5. Navigate, extract, screenshot
    │
    ▼
MCP Client
    │
    │  6. Compressed results (~2k tokens instead of ~50k)
    │
    ▼
User sees clean answer
```

### Token Savings — Real Numbers

```
Single page visit:
  Before:  50,000 chars HTML = ~12,500 tokens  💸
  After:    3,000 chars text = ~750 tokens     ✅
  Saved:   94%

3-page research task:
  Before:  44,361 tokens 💸
  After:    5,681 tokens ✅
  Saved:   87%
```

### BuiltinLLM — No API Key Needed

When LLM tools are called, they use a built-in rule-based engine:

| Tool | Method | Quality |
|------|--------|---------|
| `llm-classify` | Keyword + semantic matching | Good for common categories |
| `llm-extract` | Regex-based extraction | Works for emails, phones, URLs, dates |
| `llm-summarize` | Extractive summarization | Keeps key sentences |
| `llm-complete` | Intent detection + tool suggestion | Contextual analysis |

Quality is lower than a real LLM but keeps all tools functional without any API dependency.

### SmartCompressor — Token Saver

Every tool result is compressed before returning to the MCP client:

1. **Strip HTML tags** — removes `<script>`, `<style>`, `<nav>`, `<footer>`
2. **Remove boilerplate** — cookie banners, copyright notices, duplicate lines
3. **Deduplicate content** — removes repeated lines across page sections
4. **Cap output per tool** — different limits for different tool types
5. **Replace screenshots** — base64 data → placeholder text
6. **Hard cap** — configurable max chars (default 8000)

---

## Tool Reference

### 199 Tools Across 28 Categories

| Category | Count | Example Tools |
|----------|-------|---------------|
| Hub (Multi-Agent) | 23 | `hub-register`, `hub-broadcast`, `hub-lock`, `hub-task-create` |
| Interaction | 17 | `click`, `type`, `fill-form`, `drag-drop`, `scroll` |
| Proxy Rotation | 16 | `proxy-add`, `proxy-rotate`, `proxy-check`, `proxy-stats` |
| Auto-Heal | 10 | `heal-click`, `heal-fill`, `heal-stats`, `heal-fingerprint` |
| Auto-Retry | 10 | `retry-navigate`, `retry-click`, `retry-circuit-breakers` |
| Replay | 10 | `replay-play`, `replay-step`, `replay-export-workflow` |
| Page Analysis | 9 | `page-summary`, `page-tables`, `page-seo`, `page-accessibility` |
| Network | 8 | `network-start`, `network-get`, `network-apis`, `network-export` |
| Session | 8 | `save-session`, `restore-session`, `save-creds`, `auto-login` |
| Recording | 8 | `record-start`, `record-stop`, `record-pause`, `record-annotate` |
| Login Handoff | 8 | `login-handoff-start`, `login-handoff-complete`, `detect-login-page` |
| Smart Wait | 7 | `smart-wait`, `smart-wait-element`, `smart-wait-network`, `smart-wait-js` |
| LLM | 7 | `llm-complete`, `llm-classify`, `llm-extract`, `llm-summarize` |
| AI Content | 6 | `ai-content`, `structured-extract`, `structured-deduplicate` |
| CAPTCHA | 6 | `captcha-assess`, `captcha-preflight`, `captcha-monitor-start` |
| Workflow | 6 | `workflow`, `workflow-save`, `workflow-template`, `workflow-json` |
| Router | 6 | `classify-query`, `needs-web`, `query-strategy` |
| Navigation | 6 | `navigate`, `smart-navigate`, `back`, `forward`, `reload`, `route` |
| Smart Finder | 4 | `smart-find`, `smart-click`, `smart-fill`, `smart-find-all` |
| HTTP/TLS | 4 | `fetch`, `tls-get`, `tls-post`, `tls-stats` |
| Tabs & Device | 4 | `tabs`, `add-extension`, `emulate-device`, `list-devices` |
| Security | 3 | `scan-xss`, `scan-sqli`, `scan-sensitive` |
| Hub Memory | 4 | `hub-memory-set`, `hub-memory-get`, `hub-memory-list` |
| Proxy | 2 | `set-proxy`, `get-proxy` |
| Transcription | 1 | `transcribe` |
| Status | 1 | `health` |
| Media | 1 | `transcribe` (Whisper) |
| Route | 1 | `route` |
| **Total** | **199** | |

---

## Startup Script Options

```bash
./run_mcp.sh [OPTIONS]

Options:
  --token TOKEN       Auth token (must match server)
  --port PORT         WebSocket port (default: 8000)
  --headed            Show browser window
  --mcp-only          Only start MCP wrapper (server already running)
  --server-only       Only start server (for external MCP)
  --compress MODE     Compression: aggressive|normal|off (default: aggressive)
  --max-output CHARS  Max chars per tool result (default: 8000)
```

---

## Troubleshooting

### "Cannot connect to Agent-OS server"

```bash
# Start the server
python3 main.py --agent-token "your-token"

# Check it's running
curl http://localhost:8001/health
```

### Tools not appearing in Claude Desktop

1. Check the absolute path in config (not relative)
2. Make sure `python3` is in your PATH
3. Restart Claude Desktop completely (quit + reopen)
4. Check Claude Desktop logs for errors

### Results too compressed

```json
{
  "env": {
    "AGENT_OS_COMPRESS": "normal",
    "AGENT_OS_MAX_OUTPUT": "15000"
  }
}
```

### Want full output (debugging)

```json
{
  "env": {
    "AGENT_OS_COMPRESS": "off",
    "AGENT_OS_MAX_OUTPUT": "50000"
  }
}
```

### Token mismatch

The token in `AGENT_OS_TOKEN` must match the token used to start Agent-OS server:

```bash
# Server
python3 main.py --agent-token "SAME-TOKEN"

# MCP wrapper
AGENT_OS_TOKEN="SAME-TOKEN" python3 connectors/mcp_passthrough.py
```

---

## Development

```bash
# Run tests
cd Agent-OS
python3 -c "
from connectors.mcp_passthrough import BuiltinLLM, SmartCompressor
from connectors._tool_registry import TOOLS
print(f'Tools: {len(TOOLS)}')

llm = BuiltinLLM()
r = llm.classify('browse github', ['web', 'email'])
print(f'Classify: {r[\"category\"]} ({r[\"confidence\"]:.2f})')

r = llm.extract('email: test@co.com', {'email': 'string'})
print(f'Extract: {r[\"data\"]}')
"
```

---

## License

[MIT License](LICENSE) — same as Agent-OS.
