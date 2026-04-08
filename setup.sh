#!/usr/bin/env bash
# Agent-OS Setup Script
# Installs dependencies, Playwright, and verifies everything works.
set -e

echo "🤖 Agent-OS Setup"
echo "================="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Install Playwright Chromium
echo "🌐 Installing Playwright Chromium..."
playwright install chromium
echo "✅ Chromium installed"

# Verify installation
echo ""
echo "🔍 Verifying installation..."

# Check imports
python3 -c "
import playwright
import aiohttp
import websockets
import yaml
import cryptography
import psutil
import numpy
print('✅ All imports successful')
"

# Check Playwright browser
python3 -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
browser = p.chromium.launch(headless=True)
browser.close()
p.stop()
print('✅ Playwright Chromium works')
"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Quick start:"
echo "  python main.py --agent-token 'my-agent'"
echo ""
echo "Test with curl:"
echo "  curl -X POST http://localhost:8001/command -H 'Content-Type: application/json' -d '{\"token\":\"my-agent\",\"command\":\"navigate\",\"url\":\"https://example.com\"}'"
echo ""
