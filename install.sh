#!/usr/bin/env bash
# Agent-OS One-Command Installer
# Usage: curl -sSL https://raw.githubusercontent.com/factspark23-hash/Agent-OS/main/install.sh | bash
#
# Or with options:
#   curl -sSL ... | bash -s -- --headed
#   curl -sSL ... | bash -s -- --token my-token
#   curl -sSL ... | bash -s -- --no-sudo
#   curl -sSL ... | bash -s -- --port 9000
set -e

# ─── Colors ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─── Defaults ────────────────────────────────────────────
INSTALL_DIR="$HOME/Agent-OS"
START_AFTER=true
NO_SUDO=false
AGENT_TOKEN=""
EXTRA_ARGS=""
REPO_URL="https://github.com/factspark23-hash/Agent-OS.git"

# ─── Parse Args ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)       INSTALL_DIR="$2"; shift 2 ;;
        --no-start)  START_AFTER=false; shift ;;
        --no-sudo)   NO_SUDO=true; shift ;;
        --token)     AGENT_TOKEN="$2"; shift 2 ;;
        --headed)    EXTRA_ARGS="$EXTRA_ARGS --headed"; shift ;;
        --port)      EXTRA_ARGS="$EXTRA_ARGS --port $2"; shift 2 ;;
        --max-ram)   EXTRA_ARGS="$EXTRA_ARGS --max-ram $2"; shift 2 ;;
        --help|-h)
            echo "Agent-OS One-Command Installer"
            echo ""
            echo "Usage: curl -sSL <url> | bash -s -- [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dir PATH       Install directory (default: ~/Agent-OS)"
            echo "  --token TOKEN    Set agent token"
            echo "  --headed         Show browser window"
            echo "  --port PORT      WebSocket port (default: 8000)"
            echo "  --max-ram MB     RAM limit in MB"
            echo "  --no-sudo        Skip sudo steps"
            echo "  --no-start       Install only, don't start server"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *) EXTRA_ARGS="$EXTRA_ARGS $1"; shift ;;
    esac
done

# ─── Helper ──────────────────────────────────────────────
run_privileged() {
    if $NO_SUDO; then
        return 0
    fi
    if command -v sudo > /dev/null 2>&1; then
        sudo "$@"
    else
        "$@"
    fi
}

step() {
    echo -e "${BLUE}▸${NC} $1"
}

ok() {
    echo -e "${GREEN}  ✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}  ⚠${NC} $1"
}

fail() {
    echo -e "${RED}  ✗${NC} $1"
    exit 1
}

# ─── Banner ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     ${GREEN}🤖 Agent-OS — One-Command Install${NC}     ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ─── Step 1: Check Python ────────────────────────────────
step "Checking Python..."
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v $cmd > /dev/null 2>&1; then
        VER=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        MAJOR=$(echo $VER | cut -d. -f1)
        MINOR=$(echo $VER | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON=$cmd
            ok "Found Python $VER"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    INSTALLED_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "not found")
    fail "Python 3.10+ required (found: $INSTALLED_VER). Install it first."
fi

# ─── Step 2: Check/Install Git ──────────────────────────
step "Checking Git..."
if ! command -v git > /dev/null 2>&1; then
    warn "Git not found. Installing..."
    if command -v apt-get > /dev/null 2>&1; then
        run_privileged apt-get update -qq && run_privileged apt-get install -y -qq git
    elif command -v yum > /dev/null 2>&1; then
        run_privileged yum install -y -q git
    elif command -v dnf > /dev/null 2>&1; then
        run_privileged dnf install -y -q git
    elif command -v pacman > /dev/null 2>&1; then
        run_privileged pacman -S --noconfirm git
    elif command -v brew > /dev/null 2>&1; then
        brew install git
    else
        fail "Cannot install Git. Install it manually: https://git-scm.com/downloads"
    fi
    ok "Git installed"
else
    ok "Git $(git --version | awk '{print $3}')"
fi

# ─── Step 3: Clone Repo ─────────────────────────────────
step "Cloning Agent-OS..."
if [ -d "$INSTALL_DIR" ]; then
    warn "Directory exists. Updating..."
    cd "$INSTALL_DIR"
    git pull --quiet 2>/dev/null || true
    ok "Updated to latest"
else
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    ok "Cloned to $INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ─── Step 4: Virtual Environment ────────────────────────
step "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    # Ensure venv module is available
    if ! $PYTHON -m venv --help > /dev/null 2>&1; then
        warn "python3-venv not found. Installing..."
        PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if command -v apt-get > /dev/null 2>&1; then
            run_privileged apt-get update -qq 2>/dev/null
            run_privileged apt-get install -y -qq "python${PY_VER}-venv" python3-pip python3-dev build-essential 2>/dev/null
        elif command -v dnf > /dev/null 2>&1; then
            run_privileged dnf install -y -q python3-venv python3-pip python3-devel gcc 2>/dev/null
        elif command -v yum > /dev/null 2>&1; then
            run_privileged yum install -y -q python3-venv python3-pip python3-devel gcc 2>/dev/null
        fi
    fi

    $PYTHON -m venv venv 2>/dev/null || {
        $PYTHON -m venv --without-pip venv
        source venv/bin/activate
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python /tmp/get-pip.py -q
        rm -f /tmp/get-pip.py
    }
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi
source venv/bin/activate
ok "Activated venv ($(which python))"

# ─── Step 5: System Dependencies ────────────────────────
step "Checking system dependencies..."
MISSING_DEPS=""
for lib in libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2; do
    if ! dpkg -l "$lib" 2>/dev/null | grep -q "^ii" && ! dpkg -l "${lib}t64" 2>/dev/null | grep -q "^ii"; then
        MISSING_DEPS="$MISSING_DEPS $lib"
    fi
done 2>/dev/null || true

if [ -n "$MISSING_DEPS" ] && command -v apt-get > /dev/null 2>&1; then
    warn "Installing missing libraries..."
    run_privileged apt-get update -qq 2>/dev/null || true
    run_privileged apt-get install -y -qq $MISSING_DEPS 2>/dev/null || true
    (run_privileged apt-get install -y -qq libasound2t64 2>/dev/null || run_privileged apt-get install -y -qq libasound2 2>/dev/null || true)
fi
ok "System dependencies ready"

# ─── Step 6: Python Dependencies ────────────────────────
step "Installing Python packages..."
pip install --upgrade pip -q 2>&1 | tail -1
REQ_FILE="requirements.lock"
[ ! -f "$REQ_FILE" ] && REQ_FILE="requirements.txt"
pip install -r "$REQ_FILE" --no-cache-dir 2>&1 | tail -5 || {
    warn "Some packages failed. Retrying with --no-build-isolation..."
    pip install -r "$REQ_FILE" --no-build-isolation 2>&1 | tail -5 || true
}
ok "Python packages installed"

# ─── Step 7: Playwright Chromium ────────────────────────
step "Installing Chromium browser..."
python -m playwright install chromium 2>&1 | tail -1
# Also install system deps if available
python -m playwright install-deps chromium 2>&1 | tail -1 || true
ok "Chromium ready"

# ─── Step 8: Environment File ───────────────────────────
step "Configuring environment..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        touch .env
    fi

    # Generate JWT key
    GENERATED_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')
    echo "JWT_SECRET_KEY=$GENERATED_KEY" >> .env
    ok "Generated JWT_SECRET_KEY"

    # Generate agent token if not provided
    if [ -z "$AGENT_TOKEN" ]; then
        AGENT_TOKEN="agent-$(python -c 'import secrets; print(secrets.token_hex(8))')"
    fi
    echo "AGENT_TOKEN=$AGENT_TOKEN" >> .env
    ok "Agent token: $AGENT_TOKEN"
else
    ok ".env already exists"
    if [ -z "$AGENT_TOKEN" ]; then
        AGENT_TOKEN=$(grep "^AGENT_TOKEN=" .env 2>/dev/null | cut -d= -f2)
        [ -z "$AGENT_TOKEN" ] && AGENT_TOKEN="agent-$(python -c 'import secrets; print(secrets.token_hex(8))')"
    fi
fi

# ─── Step 9: Verify ─────────────────────────────────────
step "Verifying installation..."
ERRORS=0
for pair in "playwright:playwright" "websockets:websockets" "aiohttp:aiohttp" "httpx:httpx" "cryptography:cryptography" "beautifulsoup4:bs4" "lxml:lxml" "PyYAML:yaml" "psutil:psutil" "numpy:numpy" "mcp:mcp" "curl_cffi:curl_cffi" "cloudscraper:cloudscraper" "redis:redis" "sqlalchemy:sqlalchemy" "pydantic:pydantic"; do
    PKG="${pair%%:*}"
    IMP="${pair##*:}"
    python -c "import $IMP" 2>/dev/null || { warn "Import failed: $PKG (as $IMP)"; ERRORS=$((ERRORS+1)); }
done

if [ $ERRORS -gt 0 ]; then
    warn "$ERRORS module(s) had import issues (may still work)"
else
    ok "All modules verified"
fi

# ─── Done ───────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}        ${GREEN}✅ Installation Complete!${NC}          ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Install dir:${NC}  $INSTALL_DIR"
echo -e "  ${BLUE}Agent token:${NC}  $AGENT_TOKEN"
echo -e "  ${BLUE}HTTP API:${NC}     http://localhost:8001"
echo -e "  ${BLUE}WebSocket:${NC}    ws://localhost:8000"
echo ""

# ─── Start Server ───────────────────────────────────────
if $START_AFTER; then
    echo -e "${GREEN}Starting Agent-OS...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    exec python main.py --agent-token "$AGENT_TOKEN" $EXTRA_ARGS
else
    echo "To start:"
    echo "  cd $INSTALL_DIR"
    echo "  source venv/bin/activate"
    echo "  python main.py --agent-token '$AGENT_TOKEN'"
    echo ""
fi
