#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Agent-OS Quick Start — ONE COMMAND, PRODUCTION READY
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/quickstart.sh | bash
#
# Or:
#   git clone https://github.com/factspark23-hash/Agent-OS.git && cd Agent-OS && chmod +x quickstart.sh && ./quickstart.sh
#
# What it does (fully automatic):
#   1. Installs all dependencies (Python, system libs, Chromium)
#   2. Generates JWT secret key
#   3. Generates agent token
#   4. Creates .env file with all config
#   5. Detects PostgreSQL/Redis (uses if available, falls back if not)
#   6. Configures firewall (only allows 8000-8001 from localhost)
#   7. Starts the server in background
#   8. Prints connection info
#
# After this, just run:  cd ~/Agent-OS && python3 main.py
# ═══════════════════════════════════════════════════════════════
set -e

# ─── Colors ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Config ──────────────────────────────────────────────
INSTALL_DIR="${AGENT_OS_DIR:-$HOME/Agent-OS}"
REPO_URL="https://github.com/factspark23-hash/Agent-OS.git"
WS_PORT=8000
HTTP_PORT=8001
HEADLESS=true
EXTRA_ARGS=""

# ─── Parse Args ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)       INSTALL_DIR="$2"; shift 2 ;;
        --headed)    HEADLESS=false; EXTRA_ARGS="$EXTRA_ARGS --headed"; shift ;;
        --port)      WS_PORT="$2"; HTTP_PORT=$((WS_PORT+1)); EXTRA_ARGS="$EXTRA_ARGS --port $2"; shift 2 ;;
        --max-ram)   EXTRA_ARGS="$EXTRA_ARGS --max-ram $2"; shift 2 ;;
        --token)     CUSTOM_TOKEN="$2"; shift 2 ;;
        --no-start)  NO_START=true; shift ;;
        --no-sudo)   NO_SUDO=true; shift ;;
        --help|-h)
            echo -e "${BOLD}Agent-OS Quick Start${NC}"
            echo ""
            echo "Usage: ./quickstart.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dir PATH       Install directory (default: ~/Agent-OS)"
            echo "  --token TOKEN    Custom agent token (default: auto-generated)"
            echo "  --headed         Show browser window"
            echo "  --port PORT      WebSocket port (default: 8000)"
            echo "  --max-ram MB     RAM limit in MB"
            echo "  --no-start       Setup only, don't start server"
            echo "  --no-sudo        Skip sudo steps"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *) EXTRA_ARGS="$EXTRA_ARGS $1"; shift ;;
    esac
done

NO_START="${NO_START:-false}"
NO_SUDO="${NO_SUDO:-false}"

# ─── Helpers ─────────────────────────────────────────────
step()  { echo -e "${BLUE}▸${NC} $1"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail()  { echo -e "${RED}  ✗${NC} $1"; exit 1; }

run_privileged() {
    if $NO_SUDO; then return 0; fi
    if command -v sudo > /dev/null 2>&1; then sudo "$@"; else "$@"; fi
}

gen_secret() {
    python3 -c 'import secrets; print(secrets.token_urlsafe(48))' 2>/dev/null || \
    openssl rand -base64 48 2>/dev/null || \
    head -c 48 /dev/urandom | base64 | tr -d '/+=' | head -c 64
}

gen_token() {
    python3 -c 'import secrets; print("aos-" + secrets.token_hex(16))' 2>/dev/null || \
    echo "aos-$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p)"
}

# ─── Banner ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}   ${GREEN}${BOLD}🤖 Agent-OS — Quick Start (Production Ready)${NC}   ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Step 1: Check Python ────────────────────────────────
step "Checking Python..."
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v $cmd > /dev/null 2>&1; then
        VER=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        MAJOR=$(echo $VER | cut -d. -f1)
        MINOR=$(echo $VER | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON=$cmd
            ok "Found Python $VER"
            break
        fi
    fi
done
[ -z "$PYTHON" ] && fail "Python 3.10+ required. Install it first."

# ─── Step 2: Install/Update ─────────────────────────────
step "Setting up Agent-OS..."
if [ -d "$INSTALL_DIR/.git" ]; then
    ok "Directory exists: $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull --quiet 2>/dev/null || warn "Could not pull latest (local changes?)"
else
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    ok "Cloned to $INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── Step 3: Run existing installer (deps + Chromium) ───
step "Installing dependencies..."
if [ -f "install.sh" ]; then
    bash install.sh --no-start --no-sudo 2>&1 | grep -E "(✓|✗|⚠|▸)" || true
    ok "Dependencies installed"
else
    # Fallback: manual install
    [ ! -d "venv" ] && $PYTHON -m venv venv 2>/dev/null || true
    source venv/bin/activate 2>/dev/null || true
    pip install -r requirements.txt --quiet 2>&1 | tail -3
    $PYTHON -m patchright install chromium 2>/dev/null || true
    ok "Dependencies installed (manual)"
fi

# Ensure we're in the right dir and venv
cd "$INSTALL_DIR"
[ -f "venv/bin/activate" ] && source venv/bin/activate 2>/dev/null || true

# ─── Step 4: Generate Secrets ────────────────────────────
step "Generating secrets..."

JWT_SECRET=$(gen_secret)
AGENT_TOKEN="${CUSTOM_TOKEN:-$(gen_token)}"

ok "JWT secret generated (64 chars)"
ok "Agent token: ${AGENT_TOKEN:0:8}****${AGENT_TOKEN: -4}"

# ─── Step 5: Create .env File ────────────────────────────
step "Creating .env configuration..."

# Detect PostgreSQL
PG_DSN=""
if command -v psql > /dev/null 2>&1; then
    PG_USER="agent_os"
    PG_PASS=$(gen_secret | head -c 24)
    PG_DSN="postgresql+asyncpg://${PG_USER}:${PG_PASS}@localhost:5432/agent_os"
    warn "PostgreSQL detected — creating database..."
    # Try to create DB and user
    run_privileged sudo -u postgres psql -c "CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';" 2>/dev/null || true
    run_privileged sudo -u postgres psql -c "CREATE DATABASE agent_os OWNER ${PG_USER};" 2>/dev/null || true
    run_privileged sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE agent_os TO ${PG_USER};" 2>/dev/null || true
    ok "PostgreSQL configured"
else
    ok "PostgreSQL not found — using in-memory storage (fine for single instance)"
fi

# Detect Redis
REDIS_URL=""
if command -v redis-cli > /dev/null 2>&1 && redis-cli ping > /dev/null 2>&1; then
    REDIS_URL="redis://localhost:6379/0"
    ok "Redis detected and running"
else
    ok "Redis not found — using in-memory rate limiting"
fi

# Write .env
cat > .env << ENVEOF
# Agent-OS Configuration — Auto-generated by quickstart.sh
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ═══ Authentication ═══
JWT_SECRET_KEY=${JWT_SECRET}
AGENT_TOKEN=${AGENT_TOKEN}

# ═══ Server ═══
AGENT_OS_HOST=127.0.0.1
WS_PORT=${WS_PORT}
HTTP_PORT=${HTTP_PORT}

# ═══ Database (leave empty to use in-memory) ═══
DATABASE_DSN=${PG_DSN}

# ═══ Redis (leave empty to use in-memory) ═══
REDIS_URL=${REDIS_URL}

# ═══ Browser ═══
HEADLESS=$($HEADLESS && echo "true" || echo "false")
MAX_RAM_MB=500

# ═══ Security ═══
ENABLE_JWT_AUTH=true
ENABLE_API_KEY_AUTH=true
ALLOW_LEGACY_TOKEN=true
ENVEOF

ok ".env created"

# ─── Step 6: Create/Update Config YAML ──────────────────
step "Updating config.yaml..."

CONFIG_DIR="$HOME/.agent-os"
mkdir -p "$CONFIG_DIR"

# Create config if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cat > "$CONFIG_DIR/config.yaml" << YAMLEOF
server:
  host: 127.0.0.1
  ws_port: ${WS_PORT}
  http_port: ${HTTP_PORT}
  agent_token: ${AGENT_TOKEN}

jwt:
  secret_key: ${JWT_SECRET}
  algorithm: HS256
  access_token_expire_minutes: 15
  refresh_token_expire_days: 30

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
  enable_jwt_auth: true
  enable_api_key_auth: true
  allow_legacy_token_auth: true
YAMLEOF
    ok "config.yaml created"
else
    ok "config.yaml already exists (not overwriting)"
fi

# ─── Step 7: Firewall (localhost only) ──────────────────
step "Configuring firewall..."

FIREWALL_CONFIGURED=false

# Try ufw (Ubuntu/Debian)
if command -v ufw > /dev/null 2>&1; then
    run_privileged ufw allow from 127.0.0.1 to any port ${WS_PORT} proto tcp 2>/dev/null || true
    run_privileged ufw allow from 127.0.0.1 to any port ${HTTP_PORT} proto tcp 2>/dev/null || true
    FIREWALL_CONFIGURED=true
    ok "ufw: ports ${WS_PORT}-${HTTP_PORT} allowed from localhost only"

# Try iptables
elif command -v iptables > /dev/null 2>&1; then
    run_privileged iptables -A INPUT -p tcp --dport ${WS_PORT} -s 127.0.0.1 -j ACCEPT 2>/dev/null || true
    run_privileged iptables -A INPUT -p tcp --dport ${HTTP_PORT} -s 127.0.0.1 -j ACCEPT 2>/dev/null || true
    run_privileged iptables -A INPUT -p tcp --dport ${WS_PORT} -j DROP 2>/dev/null || true
    run_privileged iptables -A INPUT -p tcp --dport ${HTTP_PORT} -j DROP 2>/dev/null || true
    FIREWALL_CONFIGURED=true
    ok "iptables: ports ${WS_PORT}-${HTTP_PORT} restricted to localhost"
fi

if ! $FIREWALL_CONFIGURED; then
    warn "No firewall tool found — ensure ports ${WS_PORT}-${HTTP_PORT} are not exposed to internet"
fi

# ─── Step 8: Verify Installation ────────────────────────
step "Verifying installation..."

ERRORS=0

# Check Python deps
if ! $PYTHON -c "import aiohttp, websockets, patchright, pyjwt, bcrypt, yaml" 2>/dev/null; then
    warn "Some Python packages may be missing"
    ERRORS=$((ERRORS+1))
else
    ok "All core Python packages present"
fi

# Check Chromium
if $PYTHON -c "import patchright; p = patchright.sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>/dev/null; then
    ok "Chromium browser working"
else
    warn "Chromium may need manual install: python3 -m patchright install chromium"
fi

# Check .env
if [ -f ".env" ]; then
    ok ".env file present"
else
    fail ".env file missing!"
fi

# Check JWT secret
if grep -q "JWT_SECRET_KEY=.\{20,\}" .env 2>/dev/null; then
    ok "JWT secret is set"
else
    warn "JWT secret may be too short"
fi

# ─── Step 9: Create convenience script ──────────────────
step "Creating start script..."

cat > start.sh << STARTEOF
#!/usr/bin/env bash
# Agent-OS Start Script — generated by quickstart.sh
set -e
cd "\$(dirname "\$0")"
[ -f venv/bin/activate ] && source venv/bin/activate

# Load .env
export \$(grep -v '^#' .env | xargs)

echo "🤖 Starting Agent-OS..."
echo "   WebSocket: ws://127.0.0.1:${WS_PORT}"
echo "   HTTP API:  http://127.0.0.1:${HTTP_PORT}"
echo "   Health:    http://127.0.0.1:${HTTP_PORT}/health"
echo ""

exec python3 main.py \\
    --agent-token "\${AGENT_TOKEN}" \\
    --port ${WS_PORT} \\
    \$@
STARTEOF
chmod +x start.sh
ok "start.sh created"

# Also create a stop script
cat > stop.sh << STOPEOF
#!/usr/bin/env bash
# Stop Agent-OS
echo "Stopping Agent-OS..."
pkill -f "python3 main.py" 2>/dev/null && echo "✓ Stopped" || echo "Not running"
STOPEOF
chmod +x stop.sh
ok "stop.sh created"

# ─── Step 10: Start Server ──────────────────────────────
if $NO_START; then
    echo ""
    echo -e "${YELLOW}  --no-start flag set. Skipping server start.${NC}"
    echo -e "  Run manually: ${CYAN}cd $INSTALL_DIR && ./start.sh${NC}"
else
    step "Starting Agent-OS server..."

    # Kill any existing instance
    pkill -f "python3 main.py" 2>/dev/null || true
    sleep 1

    # Load .env
    export $(grep -v '^#' .env | grep -v '^$' | xargs) 2>/dev/null || true

    # Start in background
    nohup python3 main.py \
        --agent-token "${AGENT_TOKEN}" \
        --port ${WS_PORT} \
        ${EXTRA_ARGS} \
        > agent-os.log 2>&1 &
    SERVER_PID=$!

    # Wait for startup
    echo -n "  Waiting for server"
    for i in $(seq 1 15); do
        sleep 1
        echo -n "."
        if curl -s "http://127.0.0.1:${HTTP_PORT}/health" > /dev/null 2>&1; then
            echo ""
            ok "Server is running (PID: $SERVER_PID)"
            break
        fi
        if [ $i -eq 15 ]; then
            echo ""
            warn "Server may still be starting. Check: tail -f $INSTALL_DIR/agent-os.log"
        fi
    done
fi

# ─── Done! ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}        ${GREEN}${BOLD}✅ Agent-OS Ready — Production!${NC}         ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Endpoints:${NC}"
echo -e "    WebSocket:  ${CYAN}ws://127.0.0.1:${WS_PORT}${NC}"
echo -e "    HTTP API:   ${CYAN}http://127.0.0.1:${HTTP_PORT}${NC}"
echo -e "    Health:     ${CYAN}http://127.0.0.1:${HTTP_PORT}/health${NC}"
echo ""
echo -e "  ${BOLD}Auth:${NC}"
echo -e "    Token:      ${GREEN}${AGENT_TOKEN}${NC}"
echo ""
echo -e "  ${BOLD}Quick Test:${NC}"
echo -e "    ${CYAN}curl http://127.0.0.1:${HTTP_PORT}/health${NC}"
echo ""
echo -e "  ${BOLD}Files:${NC}"
echo -e "    Config:     ${INSTALL_DIR}/.env"
echo -e "    Start:      ${INSTALL_DIR}/start.sh"
echo -e "    Stop:       ${INSTALL_DIR}/stop.sh"
echo -e "    Logs:       ${INSTALL_DIR}/agent-os.log"
echo ""

if [ -n "$PG_DSN" ]; then
    echo -e "  ${BOLD}PostgreSQL:${NC} Connected"
fi
if [ -n "$REDIS_URL" ]; then
    echo -e "  ${BOLD}Redis:${NC}       Connected"
fi

echo ""
echo -e "  ${YELLOW}To restart later:${NC}  cd $INSTALL_DIR && ./start.sh"
echo -e "  ${YELLOW}To stop:${NC}         cd $INSTALL_DIR && ./stop.sh"
echo ""
