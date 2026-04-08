#!/usr/bin/env bash
# agent-os-tool — Universal CLI connector for Agent-OS
# Any agent can call this from any language via subprocess/curl
#
# Usage:
#   agent-os-tool navigate "https://github.com"
#   agent-os-tool click "button[type=submit]"
#   agent-os-tool type "hello world"
#   agent-os-tool press "Enter"
#   agent-os-tool fill-form '{"#email":"test@test.com","#password":"pass"}'
#   agent-os-tool scan-xss "https://target.com/search?q=test"
#   agent-os-tool screenshot
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
    echo "Navigation:"
    echo "  navigate <url>              Navigate to a URL"
    echo "  back                        Go back in history"
    echo "  forward                     Go forward in history"
    echo "  reload                      Reload current page"
    echo ""
    echo "Interaction:"
    echo "  click <selector>            Click an element"
    echo "  type <text>                 Type text into focused element"
    echo "  press <key>                 Press a key (Enter, Tab, etc.)"
    echo "  fill-form <json-fields>     Fill form fields"
    echo "  hover <selector>            Hover over element"
    echo "  select <selector> <value>   Select dropdown option"
    echo "  upload <selector> <path>    Upload a file"
    echo "  wait <selector> [timeout]   Wait for element"
    echo ""
    echo "Content:"
    echo "  get-content                 Get page HTML + text"
    echo "  get-dom                     Get DOM snapshot"
    echo "  get-links                   Get all links"
    echo "  get-images                  Get all images"
    echo "  screenshot [full-page]      Take screenshot"
    echo "  evaluate-js <script>        Execute JavaScript"
    echo "  scroll <direction> <amount> Scroll page"
    echo ""
    echo "Security:"
    echo "  scan-xss <url>              Scan for XSS"
    echo "  scan-sqli <url>             Scan for SQLi"
    echo "  scan-sensitive              Scan page for sensitive data"
    echo ""
    echo "Media:"
    echo "  transcribe <url> [lang]     Transcribe video/audio"
    echo ""
    echo "Auth:"
    echo "  save-creds <domain> <user> <pass>  Save credentials"
    echo "  auto-login <url> <domain>   Auto-login"
    echo ""
    echo "Forms:"
    echo "  fill-job <url> <profile>    Auto-fill job application"
    echo ""
    echo "Tabs:"
    echo "  tabs list                   List tabs"
    echo "  tabs new [id]               Create new tab"
    echo "  tabs switch <id>            Switch to tab"
    echo "  tabs close <id>             Close tab"
    echo ""
    echo "Server:"
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
    back)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"back\"}"
        ;;
    forward)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"forward\"}"
        ;;
    reload)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"reload\"}"
        ;;
    get-content)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-content\"}"
        ;;
    get-dom)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-dom\"}"
        ;;
    get-links)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-links\"}"
        ;;
    get-images)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-images\"}"
        ;;
    screenshot)
        FULL="${1:-false}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"screenshot\",\"full_page\":$FULL}"
        ;;
    click)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"click\",\"selector\":\"$1\"}"
        ;;
    type)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"type\",\"text\":\"$1\"}"
        ;;
    press)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"press\",\"key\":\"$1\"}"
        ;;
    fill-form)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"fill-form\",\"fields\":$1}"
        ;;
    hover)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"hover\",\"selector\":\"$1\"}"
        ;;
    select)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"select\",\"selector\":\"$1\",\"value\":\"$2\"}"
        ;;
    upload)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"upload\",\"selector\":\"$1\",\"file_path\":\"$2\"}"
        ;;
    wait)
        TIMEOUT="${2:-10000}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"wait\",\"selector\":\"$1\",\"timeout\":$TIMEOUT}"
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
    scan-sensitive)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-sensitive\"}"
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
    fill-job)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"fill-job\",\"url\":\"$1\",\"profile\":$2}"
        ;;
    tabs)
        TAB_ACTION="$1"
        TAB_ID="${2:-}"
        if [ -n "$TAB_ID" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$TAB_ACTION\",\"tab_id\":\"$TAB_ID\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$TAB_ACTION\"}"
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
        echo "Run 'agent-os-tool' without arguments to see all commands."
        exit 1
        ;;
esac

curl -s -X POST "$AGENT_OS_URL/command" \
    -H "Content-Type: application/json" \
    -d "$DATA" | python3 -m json.tool
