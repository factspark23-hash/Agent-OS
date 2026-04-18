# MCP Passthrough Wrapper

Zero-API-key MCP server for Agent-OS. Works with Claude Desktop, Codex, and any MCP client.

## How It Works

```
MCP Client (Claude/GPT)  →  reasoning + tool selection (already paid for)
         ↓
MCP Passthrough          →  proxies tool calls, compresses results
         ↓
Agent-OS Server          →  executes browser actions
```

**No extra API key needed.** The MCP client's LLM handles reasoning. Agent-OS handles execution.

## Token Savings

Without compression, a single page visit returns 10,000-50,000 characters of HTML → burning 2,500-12,500 tokens in the MCP client's context.

SmartCompressor strips HTML boilerplate, deduplicates content, and caps output:

| Mode | Savings | Best For |
|------|---------|----------|
| `aggressive` (default) | ~85% | Most use cases |
| `normal` | ~50% | When you need more detail |
| `off` | 0% | Debugging |

**Example:** 3-page research task: 44,000 tokens → 5,600 tokens (87% saved).

## Setup

### 1. Start Agent-OS Server

```bash
python3 main.py --agent-token "my-secret-token"
```

### 2. Configure MCP Client

**Claude Desktop** — add to `claude_desktop_config.json`:

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

### 3. Restart Claude Desktop

199 browser tools appear automatically. No API key required.

## Or Use the Startup Script

```bash
./run_mcp.sh --token "my-secret-token"
```

This starts Agent-OS server + MCP wrapper and prints the Claude Desktop config.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_OS_URL` | `http://localhost:8001` | Agent-OS server URL |
| `AGENT_OS_TOKEN` | (auto-generated) | Auth token (must match server) |
| `AGENT_OS_COMPRESS` | `aggressive` | Compression: `aggressive`, `normal`, `off` |
| `AGENT_OS_MAX_OUTPUT` | `8000` | Max chars returned per tool call |

## Architecture

### BuiltinLLM (Rule-Based)

When LLM tools (`llm-complete`, `llm-classify`, `llm-extract`, `llm-summarize`) are called, they use a built-in rule-based engine instead of calling an external API:

- **classify**: Keyword + semantic category matching
- **extract**: Regex-based structured data extraction
- **summarize**: Extractive summarization (key sentence selection)
- **complete**: Intent detection + tool suggestion

Quality is lower than a real LLM but keeps all tools functional without any API dependency.

### SmartCompressor

Every tool result is compressed before being returned to the MCP client:

1. Strip HTML tags (script, style, nav, footer)
2. Remove boilerplate (cookie banners, copyright notices)
3. Deduplicate repeated lines
4. Cap output size per tool type
5. Replace base64 screenshots with placeholders
6. Hard cap at configurable max chars

## Troubleshooting

**"Cannot connect to Agent-OS server"**
→ Start the server: `python3 main.py --agent-token "your-token"`

**Tools not appearing in Claude Desktop**
→ Check the absolute path in config. Restart Claude Desktop.

**Results too compressed**
→ Set `AGENT_OS_COMPRESS=normal` or `AGENT_OS_MAX_OUTPUT=15000`

**Want full output (debugging)**
→ Set `AGENT_OS_COMPRESS=off` and `AGENT_OS_MAX_OUTPUT=50000`
