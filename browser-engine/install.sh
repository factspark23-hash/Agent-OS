#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Browser Engine v2.1 — One-Command Installer
# Production Anti-Detection Browser with CDP, Smart Modes, State Persistence,
# Handoff Controller, Tab Manager, Stealth & Fingerprint, Platform Adapters
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

BROWSER_ENGINE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════════════"
echo "  Browser Engine v2.1 — Installer"
echo "  Production Anti-Detection Browser"
echo "═══════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# ─── Step 1: Check for Bun ─────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking for Bun runtime...${NC}"
if command -v bun &>/dev/null; then
    BUN_VERSION=$(bun --version)
    echo -e "${GREEN}  ✓ Bun v${BUN_VERSION} found${NC}"
else
    echo -e "${YELLOW}  Bun not found. Installing Bun...${NC}"
    curl -fsSL https://bun.sh/install | bash
    # Source bun into the current shell
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
    if command -v bun &>/dev/null; then
        BUN_VERSION=$(bun --version)
        echo -e "${GREEN}  ✓ Bun v${BUN_VERSION} installed${NC}"
    else
        echo -e "${RED}  ✗ Failed to install Bun. Please install manually:${NC}"
        echo -e "${RED}    curl -fsSL https://bun.sh/install | bash${NC}"
        exit 1
    fi
fi

# ─── Step 2: Install npm dependencies ──────────────────────────────────────
echo -e "${YELLOW}[2/5] Installing npm dependencies...${NC}"
cd "$BROWSER_ENGINE_DIR"
bun install
echo -e "${GREEN}  ✓ Dependencies installed${NC}"

# ─── Step 3: Install Playwright browsers ────────────────────────────────────
echo -e "${YELLOW}[3/5] Installing Playwright Chromium browser...${NC}"
bunx playwright install chromium
echo -e "${GREEN}  ✓ Playwright Chromium installed${NC}"

# ─── Step 4: Create .env.example if it doesn't exist ───────────────────────
echo -e "${YELLOW}[4/5] Setting up environment configuration...${NC}"

ENV_FILE="$BROWSER_ENGINE_DIR/.env"
ENV_EXAMPLE="$BROWSER_ENGINE_DIR/.env.example"

# Always create/update .env.example
cat > "$ENV_EXAMPLE" << 'EOF'
# ═══════════════════════════════════════════════════════════════════════════════
# Browser Engine v2.1 — Environment Configuration
# Copy this file to .env and fill in your values: cp .env.example .env
# ═══════════════════════════════════════════════════════════════════════════════

# Server port (default: 3003)
PORT=3003

# Directory for saved browser states (cookies, localStorage, IndexedDB)
# Defaults to ~/.agent-os/browser-states if not set
BROWSER_STATES_DIR=

# Twitter/X API bearer token (required for Twitter adapter endpoints)
# Obtain from Twitter Developer Portal: https://developer.twitter.com/
TWITTER_BEARER_TOKEN=

# Instagram App ID (used in upload/post/delete API headers)
# Default: 936619743392459 (Instagram web app ID)
IG_APP_ID=

# Instagram Create Post GraphQL doc_id (used in deletePost mutation)
# Default: 6511191288958346
IG_CREATE_POST_DOC_ID=
EOF

echo -e "${GREEN}  ✓ .env.example created${NC}"

# Create .env from example if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo -e "${GREEN}  ✓ .env created from .env.example (edit with your API keys)${NC}"
else
    echo -e "${GREEN}  ✓ .env already exists (skipped)${NC}"
fi

# ─── Step 5: Create start.sh ───────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Creating start script...${NC}"

START_SCRIPT="$BROWSER_ENGINE_DIR/start.sh"
cat > "$START_SCRIPT" << 'STARTSH'
#!/usr/bin/env bash
# Start Browser Engine v2.1 server
set -euo pipefail

ENGINE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ENGINE_DIR"

# Load .env if it exists
if [ -f "$ENGINE_DIR/.env" ]; then
    set -a
    source "$ENGINE_DIR/.env"
    set +a
fi

PORT="${PORT:-3003}"

echo "═══════════════════════════════════════════════════════════════════════"
echo "  Browser Engine v2.1 — Starting on port $PORT"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

exec bun run index.ts
STARTSH

chmod +x "$START_SCRIPT"
echo -e "${GREEN}  ✓ start.sh created and made executable${NC}"

# ─── Done! ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════"
echo -e "  ✓ Browser Engine v2.1 installed successfully!"
echo -e "═══════════════════════════════════════════════════════════════════════"
echo ""
echo -e "${CYAN}  Quick Start:${NC}"
echo -e "    ./start.sh                          # Start the server"
echo -e ""
echo -e "${CYAN}  Verify Installation:${NC}"
echo -e "    curl http://localhost:${PORT:-3003}/api/health"
echo -e ""
echo -e "${CYAN}  Configuration:${NC}"
echo -e "    Edit .env with your API keys (Twitter, Instagram, etc.)"
echo -e ""
echo -e "${CYAN}  Features:${NC}"
echo -e "    • CDP Connection Module (6 endpoints)"
echo -e "    • Smart Browser Modes (Full/Light/Ghost)"
echo -e "    • Dual-Layer State Persistence"
echo -e "    • Handoff Controller (2FA/CAPTCHA)"
echo -e "    • Auto Tab Management"
echo -e "    • 20-Point Stealth & Fingerprint"
echo -e "    • Platform Adapters (Instagram, Twitter, LinkedIn, Facebook)"
echo -e "    • Rate Limiting (100 req/IP/min)"
echo -e "    • Graceful Shutdown"
echo ""
echo -e "${CYAN}  Documentation:${NC}"
echo -e "    See README.md for full API reference and architecture"
echo ""
