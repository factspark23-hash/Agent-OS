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
    exit 1
fi

COMMAND="$1"
shift

# Use python3 to build JSON safely — prevents shell injection
build_json() {
    python3 -c "
import json, sys
data = {'token': sys.argv[1], 'command': sys.argv[2]}
args = sys.argv[3:]
for i in range(0, len(args), 2):
    key = args[i]
    val = args[i+1] if i+1 < len(args) else ''
    # Try to parse val as JSON (for objects/arrays), otherwise use as string
    try:
        data[key] = json.loads(val)
    except (json.JSONDecodeError, ValueError):
        data[key] = val
print(json.dumps(data))
" "$AGENT_OS_TOKEN" "$COMMAND" "$@"
}

case "$COMMAND" in
    navigate)
        DATA=$(build_json url "$1")
        ;;
    back|forward|reload|get-content|get-dom|get-links|get-images)
        DATA=$(build_json)
        ;;
    screenshot)
        FULL="${1:-false}"
        DATA=$(build_json full_page "$FULL")
        ;;
    click|hover)
        DATA=$(build_json selector "$1")
        ;;
    type)
        DATA=$(build_json text "$1")
        ;;
    press)
        DATA=$(build_json key "$1")
        ;;
    fill-form)
        DATA=$(build_json fields "$1")
        ;;
    select)
        DATA=$(build_json selector "$1" value "$2")
        ;;
    upload)
        DATA=$(build_json selector "$1" file_path "$2")
        ;;
    wait)
        TIMEOUT="${2:-10000}"
        DATA=$(build_json selector "$1" timeout "$TIMEOUT")
        ;;
    scroll)
        DIR="${1:-down}"
        AMT="${2:-500}"
        DATA=$(build_json direction "$DIR" amount "$AMT")
        ;;
    evaluate-js)
        DATA=$(build_json script "$1")
        ;;
    scan-xss|scan-sqli)
        DATA=$(build_json url "$1")
        ;;
    scan-sensitive)
        DATA=$(build_json)
        ;;
    transcribe)
        LANG="${2:-auto}"
        DATA=$(build_json url "$1" language "$LANG")
        ;;
    save-creds)
        DATA=$(build_json domain "$1" username "$2" password "$3")
        ;;
    auto-login)
        DATA=$(build_json url "$1" domain "$2")
        ;;
    fill-job)
        DATA=$(build_json url "$1" profile "$2")
        ;;
    tabs)
        TAB_ACTION="$1"
        TAB_ID="${2:-}"
        if [ -n "$TAB_ID" ]; then
            DATA=$(build_json action "$TAB_ACTION" tab_id "$TAB_ID")
        else
            DATA=$(build_json action "$TAB_ACTION")
        fi
        ;;
    status)
        curl -s -H "Authorization: Bearer $AGENT_OS_TOKEN" "$AGENT_OS_URL/status" | python3 -m json.tool
        exit 0
        ;;
    commands)
        curl -s "$AGENT_OS_URL/commands" | python3 -m json.tool
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
