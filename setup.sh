#!/usr/bin/env bash
# Agent-OS Setup Script
# Installs dependencies, Playwright, and verifies everything works.
set -e

echo "🤖 Agent-OS Setup"
echo "================="
echo ""

# ─── Python Check ─────────────────────────────────────────────
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# ─── Virtual Environment (required) ──────────────────────────
VENV_DIR="$(dirname "$0")/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."

    # Check if python3-venv is available
    if ! python3 -m venv --help > /dev/null 2>&1; then
        echo "⚠️  python3-venv not found. Attempting to install..."
        if command -v apt-get > /dev/null 2>&1; then
            sudo apt-get update -qq && sudo apt-get install -y -qq "python${PYTHON_VERSION}-venv"
        else
            echo "❌ Cannot install python3-venv. Install it manually and re-run."
            exit 1
        fi
    fi

    # Try normal venv first, fall back to --without-pip + manual pip install
    python3 -m venv "$VENV_DIR" 2>/dev/null || {
        echo "  ⚠️  ensurepip not available, using --without-pip fallback..."
        python3 -m venv --without-pip "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python /tmp/get-pip.py -q
        rm -f /tmp/get-pip.py
    }
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

source "$VENV_DIR/bin/activate"
PIP_CMD="pip"
PYTHON_CMD="python"
echo "✅ Using virtual environment: $(which python)"

# ─── System Dependencies (for Playwright Chromium) ───────────
echo ""
echo "🔍 Checking system dependencies for Chromium..."

MISSING_DEPS=""
# Check both regular and t64 variants (Debian 12+ renames)
for lib in libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2; do
    if ! dpkg -l "$lib" 2>/dev/null | grep -q "^ii" && ! dpkg -l "${lib}t64" 2>/dev/null | grep -q "^ii"; then
        MISSING_DEPS="$MISSING_DEPS $lib"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    echo "⚠️  Missing system libraries:$MISSING_DEPS"
    echo "   Attempting to install..."
    if command -v apt-get > /dev/null 2>&1; then
        sudo apt-get update -qq 2>/dev/null || true
        sudo apt-get install -y -qq $MISSING_DEPS 2>/dev/null || {
            echo "⚠️  Could not install some system deps. Chromium may fail to launch."
            echo "   Try manually: sudo apt install$MISSING_DEPS"
        }
    fi
else
    echo "✅ All system dependencies present"
fi

# ─── Python Dependencies ─────────────────────────────────────
echo ""
echo "📦 Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "$(dirname "$0")/requirements.txt" -q
echo "✅ Python dependencies installed"

# ─── Playwright Chromium ─────────────────────────────────────
echo ""
echo "🌐 Installing Playwright Chromium..."
$PYTHON_CMD -m playwright install chromium
echo "✅ Chromium installed"

# ─── Verify Installation ─────────────────────────────────────
echo ""
echo "🔍 Verifying installation..."

$PYTHON_CMD -c "
import sys
errors = []

modules = [
    'playwright', 'websockets', 'aiohttp', 'httpx', 'cryptography',
    'bs4', 'lxml', 'yaml', 'psutil', 'numpy', 'mcp'
]

for mod in modules:
    try:
        __import__(mod)
    except ImportError as e:
        errors.append(f'  ❌ {mod}: {e}')

if errors:
    print('❌ Import failures:')
    for e in errors:
        print(e)
    sys.exit(1)
print('✅ All imports successful')
"

# Verify Playwright browser
$PYTHON_CMD -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=True)
browser.close()
p.stop()
print('✅ Playwright Chromium launches correctly')
"

# Run tests
echo ""
echo "🧪 Running test suite..."
$PYTHON_CMD -m pytest "$(dirname "$0")/tests/" -v --tb=short 2>&1 || {
    echo ""
    echo "⚠️  Some tests failed. Check output above."
}

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Quick start:"
echo "  source venv/bin/activate"
echo "  python main.py --agent-token 'my-agent'"
echo ""
echo "Test with curl:"
echo "  curl -X POST http://localhost:8001/command \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"token\":\"my-agent\",\"command\":\"navigate\",\"url\":\"https://example.com\"}'"
echo ""
