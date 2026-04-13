#!/usr/bin/env bash
# agent-os-tool — Universal CLI connector for Agent-OS (42 tools)
# Any agent can call this from any language via subprocess/curl
#
# Usage:
#   agent-os-tool navigate "https://github.com"
#   agent-os-tool smart-click "Sign In"
#   agent-os-tool workflow '{"steps":[{"command":"navigate","url":"https://example.com"}]}'
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
    echo "  click <selector>            Click an element (CSS selector)"
    echo "  double-click <selector>     Double-click an element"
    echo "  right-click <selector>      Right-click an element"
    echo "  type <text>                 Type text into focused element"
    echo "  press <key>                 Press a key (Enter, Tab, etc.)"
    echo "  fill-form <json-fields>     Fill form fields"
    echo "  hover <selector>            Hover over element"
    echo "  select <selector> <value>   Select dropdown option"
    echo "  upload <selector> <path>    Upload a file"
    echo "  wait <selector> [timeout]   Wait for element"
    echo "  clear-input <selector>      Clear an input field"
    echo "  checkbox <selector> <bool>  Set checkbox state"
    echo "  drag-drop <src> <tgt>       Drag and drop"
    echo "  drag-offset <sel> <x> <y>   Drag by pixel offset"
    echo "  context-action <sel> <txt>  Right-click + select menu item"
    echo ""
    echo "Smart Finder (no CSS selector needed!):"
    echo "  smart-find <description>    Find element by visible text"
    echo "  smart-find-all <desc>       Find ALL matching elements"
    echo "  smart-click <text>          Click element by its text"
    echo "  smart-fill <label> <value>  Fill input by its label/placeholder"
    echo ""
    echo "Content:"
    echo "  get-content                 Get page HTML + text"
    echo "  get-dom                     Get DOM snapshot"
    echo "  get-links                   Get all links"
    echo "  get-images                  Get all images"
    echo "  get-text <selector>         Get text of element"
    echo "  get-attr <sel> <attr>       Get element attribute"
    echo "  screenshot [full-page]      Take screenshot"
    echo "  evaluate-js <script>        Execute JavaScript"
    echo "  scroll <direction> <amount> Scroll page"
    echo "  viewport <w> <h>            Set viewport size"
    echo ""
    echo "Page Analysis:"
    echo "  page-summary                Analyze page (title, headings, content, tech)"
    echo "  page-tables                 Extract all tables as structured data"
    echo "  page-structured             Extract JSON-LD / Microdata"
    echo "  page-emails                 Find all email addresses"
    echo "  page-phones                 Find all phone numbers"
    echo "  page-accessibility          Basic accessibility audit"
    echo "  page-seo                    SEO audit with score"
    echo ""
    echo "Network Capture:"
    echo "  network-start [pattern]     Start capturing requests"
    echo "  network-stop                Stop capturing"
    echo "  network-get [filters]       Get captured requests"
    echo "  network-apis                Discover API endpoints"
    echo "  network-stats               Capture statistics"
    echo "  network-export <fmt> [fn]   Export to json/har"
    echo "  network-clear               Clear captured data"
    echo ""
    echo "Workflows:"
    echo "  workflow <json>             Execute multi-step workflow"
    echo "  workflow-template <name>    Run saved template"
    echo "  workflow-save <name> <json> Save workflow as template"
    echo "  workflow-list               List all templates"
    echo ""
    echo "Security:"
    echo "  scan-xss <url>              Scan for XSS"
    echo "  scan-sqli <url>             Scan for SQLi"
    echo "  scan-sensitive              Scan page for sensitive data"
    echo ""
    echo "Media:"
    echo "  transcribe <url> [lang]     Transcribe video/audio"
    echo ""
    echo "Auth & Cookies:"
    echo "  save-creds <domain> <user> <pass>  Save credentials"
    echo "  auto-login <url> <domain>   Auto-login"
    echo "  get-cookies                 Get all cookies"
    echo "  set-cookie <name> <val>     Set a cookie"
    echo "  console-logs                Get browser console logs"
    echo ""
    echo "Proxy:"
    echo "  set-proxy <url>             Set proxy (http/socks5)"
    echo "  get-proxy                   Get current proxy"
    echo ""
    echo "Mobile Emulation:"
    echo "  emulate-device <name>       Emulate device (iphone_14, galaxy_s23, etc.)"
    echo "  list-devices                List available devices"
    echo ""
    echo "Sessions:"
    echo "  save-session [name]         Save browser state"
    echo "  restore-session [name]      Restore saved state"
    echo "  list-sessions               List saved sessions"
    echo "  delete-session <name>       Delete a session"
    echo ""
    echo "Tabs:"
    echo "  tabs list                   List tabs"
    echo "  tabs new [id]               Create new tab"
    echo "  tabs switch <id>            Switch to tab"
    echo "  tabs close <id>             Close tab"
    echo ""
    echo "Forms:"
    echo "  fill-job <url> <profile>    Auto-fill job application"
    echo ""
    echo "Server:"
    echo "  status                      Server status"
    echo "  commands                    List all commands"
    echo "  debug                       Debug info"
    echo ""
    echo "Web Query Router (No LLM — Rule-Based):"
    echo "  classify-query <query>      Classify if query needs web access"
    echo "  needs-web <query>           Quick yes/no: does query need web?"
    echo "  query-strategy <query>      Get recommended strategy for query"
    echo "  router-stats                Router classification statistics"
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    # ─── Navigation ─────────────────────────────────
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

    # ─── Interaction ────────────────────────────────
    click)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"click\",\"selector\":\"$1\"}"
        ;;
    double-click)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"double-click\",\"selector\":\"$1\"}"
        ;;
    right-click)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"right-click\",\"selector\":\"$1\"}"
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
    clear-input)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"clear-input\",\"selector\":\"$1\"}"
        ;;
    checkbox)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"checkbox\",\"selector\":\"$1\",\"checked\":$2}"
        ;;
    drag-drop)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"drag-drop\",\"source\":\"$1\",\"target\":\"$2\"}"
        ;;
    drag-offset)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"drag-offset\",\"selector\":\"$1\",\"x\":$2,\"y\":$3}"
        ;;
    context-action)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"context-action\",\"selector\":\"$1\",\"action_text\":\"$2\"}"
        ;;

    # ─── Smart Finder ───────────────────────────────
    smart-find)
        TAG="${2:-}"
        TIMEOUT="${3:-5000}"
        if [ -n "$TAG" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-find\",\"description\":\"$1\",\"tag\":\"$TAG\",\"timeout\":$TIMEOUT}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-find\",\"description\":\"$1\",\"timeout\":$TIMEOUT}"
        fi
        ;;
    smart-find-all)
        TAG="${2:-}"
        if [ -n "$TAG" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-find-all\",\"description\":\"$1\",\"tag\":\"$TAG\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-find-all\",\"description\":\"$1\"}"
        fi
        ;;
    smart-click)
        TAG="${2:-}"
        TIMEOUT="${3:-5000}"
        if [ -n "$TAG" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-click\",\"text\":\"$1\",\"tag\":\"$TAG\",\"timeout\":$TIMEOUT}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-click\",\"text\":\"$1\",\"timeout\":$TIMEOUT}"
        fi
        ;;
    smart-fill)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"smart-fill\",\"label\":\"$1\",\"value\":\"$2\"}"
        ;;

    # ─── Content ────────────────────────────────────
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
    get-text)
        SELECTOR="${1:?Missing selector}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-text\",\"selector\":\"$SELECTOR\"}"
        ;;
    get-attr)
        SELECTOR="${1:?Missing selector}"
        ATTR="${2:?Missing attribute}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-attr\",\"selector\":\"$SELECTOR\",\"attribute\":\"$ATTR\"}"
        ;;
    screenshot)
        FULL="${1:-false}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"screenshot\",\"full_page\":$FULL}"
        ;;
    evaluate-js)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"evaluate-js\",\"script\":\"$1\"}"
        ;;
    scroll)
        DIR="${1:-down}"
        AMT="${2:-500}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scroll\",\"direction\":\"$DIR\",\"amount\":$AMT}"
        ;;
    viewport)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"viewport\",\"width\":$1,\"height\":$2}"
        ;;

    # ─── Page Analysis ─────────────────────────────
    page-summary)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-summary\"}"
        ;;
    page-tables)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-tables\"}"
        ;;
    page-structured)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-structured\"}"
        ;;
    page-emails)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-emails\"}"
        ;;
    page-phones)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-phones\"}"
        ;;
    page-accessibility)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-accessibility\"}"
        ;;
    page-seo)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"page-seo\"}"
        ;;

    # ─── Network Capture ───────────────────────────
    network-start)
        PATTERN="${1:-}"
        if [ -n "$PATTERN" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-start\",\"url_pattern\":\"$PATTERN\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-start\"}"
        fi
        ;;
    network-stop)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-stop\"}"
        ;;
    network-get)
        PATTERN="${1:-}"
        API_ONLY="${2:-false}"
        if [ -n "$PATTERN" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-get\",\"url_pattern\":\"$PATTERN\",\"api_only\":$API_ONLY}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-get\"}"
        fi
        ;;
    network-apis)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-apis\"}"
        ;;
    network-stats)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-stats\"}"
        ;;
    network-export)
        FMT="${1:-json}"
        FN="${2:-}"
        if [ -n "$FN" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-export\",\"format\":\"$FMT\",\"filename\":\"$FN\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-export\",\"format\":\"$FMT\"}"
        fi
        ;;
    network-clear)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"network-clear\"}"
        ;;

    # ─── Workflows ─────────────────────────────────
    workflow)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"workflow\",\"steps\":$1}"
        ;;
    workflow-template)
        VARS="${2:-{}}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"workflow-template\",\"template_name\":\"$1\",\"variables\":$VARS}"
        ;;
    workflow-save)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"workflow-save\",\"name\":\"$1\",\"steps\":$2}"
        ;;
    workflow-list)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"workflow-list\"}"
        ;;

    # ─── Security ──────────────────────────────────
    scan-xss)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-xss\",\"url\":\"$1\"}"
        ;;
    scan-sqli)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-sqli\",\"url\":\"$1\"}"
        ;;
    scan-sensitive)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"scan-sensitive\"}"
        ;;

    # ─── Media ─────────────────────────────────────
    transcribe)
        LANG="${2:-auto}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"transcribe\",\"url\":\"$1\",\"language\":\"$LANG\"}"
        ;;

    # ─── Auth & Cookies ────────────────────────────
    save-creds)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"save-creds\",\"domain\":\"$1\",\"username\":\"$2\",\"password\":\"$3\"}"
        ;;
    auto-login)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"auto-login\",\"url\":\"$1\",\"domain\":\"$2\"}"
        ;;
    get-cookies)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-cookies\"}"
        ;;
    set-cookie)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"set-cookie\",\"name\":\"$1\",\"value\":\"$2\"}"
        ;;
    console-logs)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"console-logs\"}"
        ;;

    # ─── Proxy ─────────────────────────────────────
    set-proxy)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"set-proxy\",\"proxy_url\":\"$1\"}"
        ;;
    get-proxy)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"get-proxy\"}"
        ;;

    # ─── Mobile Emulation ──────────────────────────
    emulate-device)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"emulate-device\",\"device\":\"$1\"}"
        ;;
    list-devices)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"list-devices\"}"
        ;;

    # ─── Sessions ──────────────────────────────────
    save-session)
        NAME="${1:-default}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"save-session\",\"name\":\"$NAME\"}"
        ;;
    restore-session)
        NAME="${1:-default}"
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"restore-session\",\"name\":\"$NAME\"}"
        ;;
    list-sessions)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"list-sessions\"}"
        ;;
    delete-session)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"delete-session\",\"name\":\"$1\"}"
        ;;

    # ─── Tabs ──────────────────────────────────────
    tabs)
        TAB_ACTION="$1"
        TAB_ID="${2:-}"
        if [ -n "$TAB_ID" ]; then
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$TAB_ACTION\",\"tab_id\":\"$TAB_ID\"}"
        else
            DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"tabs\",\"action\":\"$TAB_ACTION\"}"
        fi
        ;;

    # ─── Forms ─────────────────────────────────────
    fill-job)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"fill-job\",\"url\":\"$1\",\"profile\":$2}"
        ;;

    # ─── Server ────────────────────────────────────
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

    # ─── Web Query Router ─────────────────────────
    classify-query)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"classify-query\",\"query\":\"$1\"}"
        ;;
    needs-web)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"needs-web\",\"query\":\"$1\"}"
        ;;
    query-strategy)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"query-strategy\",\"query\":\"$1\"}"
        ;;
    router-stats)
        DATA="{\"token\":\"$AGENT_OS_TOKEN\",\"command\":\"router-stats\"}"
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
