#!/usr/bin/env bash
# agent-os-tool — Universal CLI connector for Agent-OS
# Any agent can call this from any language via subprocess/curl
#
# Usage:
#   agent-os-tool navigate "https://github.com"
#   agent-os-tool click "button[type=submit]"
#   agent-os-tool fill-form '{"#email":"test@test.com","#password":"pass"}'
#   agent-os-tool scan-xss "https://target.com/search?q=test"
#   agent-os-tool status
#
# Environment:
#   AGENT_OS_URL   — Agent-OS HTTP endpoint (default: http://localhost:8001)
#   AGENT_OS_TOKEN — Agent authentication token (default: cli-agent-default)

set -e

AGENT_OS_URL="${AGENT_OS_URL:-http://localhost:8001}"
AGENT_OS_TOKEN="${AGENT_OS_TOKEN:-cli-agent-default}"

if [ -z "$1" ]; then
    echo "Usage: agent-os-tool <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  navigate <url>              Navigate to a URL"
    echo "  get-content                 Get page content"
    echo "  get-dom                     Get DOM snapshot"
    echo "  screenshot                  Take screenshot"
    echo "  click <selector>            Click an element"
    echo "  fill-form <json-fields>     Fill form fields"
    echo "  scroll <direction> <amount> Scroll page"
    echo "  evaluate-js <script>        Execute JavaScript"
    echo "  scan-xss <url>              Scan for XSS"
    echo "  scan-sqli <url>             Scan for SQLi"
    echo "  transcribe <url>            Transcribe video/audio"
    echo "  save-creds <domain> <user> <pass>  Save credentials"
    echo "  auto-login <url> <domain>   Auto-login"
    echo "  tabs <action> [tab_id]      Manage tabs"
    echo "  status                      Server status"
    echo "  commands                    List all commands"
    echo "  debug                       Debug info"
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    navigate)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"navigate\",\"url\":\"$1\"}"
        ;;
    get-content)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-content\"}"
        ;;
    get-dom)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-dom\"}"
        ;;
    screenshot)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"screenshot\"}"
        ;;
    click)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"click\",\"selector\":\"$1\"}"
        ;;
    fill-form)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"fill-form\",\"fields\":$1}"
        ;;
    scroll)
        DIR="${1:-down}"
        AMT="${2:-500}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scroll\",\"direction\":\"$DIR\",\"amount\":$AMT}"
        ;;
    evaluate-js)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"evaluate-js\",\"script\":\"$1\"}"
        ;;
    scan-xss)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-xss\",\"url\":\"$1\"}"
        ;;
    scan-sqli)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-sqli\",\"url\":\"$1\"}"
        ;;
    transcribe)
        LANG="${2:-auto}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"transcribe\",\"url\":\"$1\",\"language\":\"$LANG\"}"
        ;;
    save-creds)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"save-creds\",\"domain\":\"$1\",\"username\":\"$2\",\"password\":\"$3\"}"
        ;;
    auto-login)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"auto-login\",\"url\":\"$1\",\"domain\":\"$2\"}"
        ;;
    tabs)
        TAB_ID="${2:-}"
        if [ -n "$TAB_ID" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$1\",\"tab_id\":\"$TAB_ID\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$1\"}"
        fi
        ;;
    status)
        curl -s "$AGENT_OS_URL/status" | python3 -m json.tool
        exit 0
        ;;
    commands)
        curl -s "$AGENT_OS_URL/commands" | python3 -m json.tool
        exit 0
        ;;
    debug)
        curl -s "$AGENT_OS_URL/debug" | python3 -m json.tool
        exit 0
        ;;
    *)
        echo "Unknown command: $COMMAND"
        exit 1
        ;;
esac

curl -s -X POST "$AGENT_OS_URL/command" \
    -H "Content-Type: application/json" \
    -d "$DATA" | python3 -m json.tool
