#!/usr/bin/env python3
"""
Agent-OS — AI Agent Browser
Entry point. Launches browser + agent server.

Usage:
    python main.py                              # Default: headless, port 8000
    python main.py --headed                     # Show browser window
    python main.py --agent-token "my-token"     # Set custom agent token
    python main.py --port 9000                  # Custom WebSocket port
    python main.py --max-ram 450                # Cap RAM at 450MB
"""
import asyncio
import argparse
import logging
import signal
import sys
import psutil
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
from src.core.browser import AgentBrowser
from src.core.session import SessionManager
from src.core.persistent_browser import PersistentBrowserManager
from src.agents.server import AgentServer
from src.debug.server import DebugServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("agent-os")


class AgentOS:
    """Main Agent-OS application."""

    def __init__(self, args):
        self.args = args
        self.config = Config(args.config)
        self.browser = AgentBrowser(self.config)
        self.session_manager = SessionManager(self.config)
        self.persistent_manager = PersistentBrowserManager(self.config) if (self.config.get("persistent.enabled", False) or args.persistent) else None
        self.server = AgentServer(self.config, self.browser, self.session_manager, self.persistent_manager)
        self.debug_server = None if args.no_debug else DebugServer(self.config, self.browser, self.session_manager, self.server, self.persistent_manager)
        self._running = False
        self._ram_monitor_task = None

        # Apply CLI overrides
        if args.headed:
            self.config.set("browser.headless", False)
        if args.port:
            self.config.set("server.ws_port", args.port)
            self.config.set("server.http_port", args.port + 1)
            self.config.set("server.debug_port", args.port + 2)
        if args.max_ram:
            self.config.set("browser.max_ram_mb", args.max_ram)
        if args.proxy:
            self.config.set("browser.proxy", args.proxy)
        if args.device:
            self.config.set("browser.device", args.device)

        # Store token in config for server validation
        if args.agent_token:
            self.config.set("server.agent_token", args.agent_token)

        # Rate limiting
        self.config.set("server.rate_limit_max", args.rate_limit)

    async def start(self):
        """Start all components."""
        self._running = True
        logger.info("=" * 60)
        logger.info("  🤖 Agent-OS — AI Agent Browser v2.1")
        logger.info("=" * 60)

        # Start browser
        logger.info("Starting browser engine...")
        await self.browser.start()

        # Start session manager
        logger.info("Starting session manager...")
        await self.session_manager.start()

        # Start persistent browser manager if enabled
        if self.persistent_manager:
            logger.info("Starting persistent browser manager...")
            await self.persistent_manager.start()

        # Start agent server
        logger.info("Starting agent server...")
        await self.server.start()

        # Start debug UI server
        if self.debug_server:
            logger.info("Starting debug UI server...")
            await self.debug_server.start()

        # Start RAM monitor
        self._ram_monitor_task = asyncio.create_task(self._ram_monitor())

        ws_port = self.config.get("server.ws_port", 8000)
        http_port = self.config.get("server.http_port", 8001)
        debug_port = self.config.get("server.debug_port", 8002)
        default_token = self.args.agent_token or self.config.generate_agent_token("agent")

        logger.info("")
        logger.info("  ✅ Agent-OS is READY!")
        logger.info("  ─────────────────────────────────────────")
        logger.info(f"  WebSocket: ws://127.0.0.1:{ws_port}")
        logger.info(f"  HTTP API:  http://127.0.0.1:{http_port}")
        if self.debug_server:
            logger.info(f"  Debug UI:  http://127.0.0.1:{debug_port}")
        logger.info(f"  Agent Token: {default_token}")
        logger.info("")
        logger.info("  Quick test:")
        logger.info(f'  curl -X POST http://127.0.0.1:{http_port}/command \\')
        logger.info(f"    -H 'Content-Type: application/json' \\")
        logger.info(f"    -d '{{\"token\": \"{default_token}\", \"command\": \"navigate\", \"url\": \"https://example.com\"}}'")
        logger.info("")
        logger.info("  Press Ctrl+C to stop")
        logger.info("  ─────────────────────────────────────────")

        # Wait for shutdown signal
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Graceful shutdown."""
        self._running = False
        logger.info("Shutting down Agent-OS...")

        if self._ram_monitor_task:
            self._ram_monitor_task.cancel()

        if self.debug_server:
            await self.debug_server.stop()

        if self.persistent_manager:
            await self.persistent_manager.stop()

        await self.server.stop()
        await self.session_manager.stop()
        await self.browser.stop()

        logger.info("Agent-OS stopped. Goodbye! 👋")

    async def _ram_monitor(self):
        """Monitor RAM usage and warn if exceeding limits."""
        max_ram = self.config.get("browser.max_ram_mb", 500)
        while self._running:
            try:
                process = psutil.Process(os.getpid())
                ram_mb = process.memory_info().rss / 1024 / 1024
                if ram_mb > max_ram:
                    logger.warning(f"⚠️  RAM usage ({ram_mb:.0f}MB) exceeds limit ({max_ram}MB)")
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(10)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agent-OS — AI Agent Browser"
    )
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--agent-token", type=str, help="Set agent authentication token")
    parser.add_argument("--port", type=int, help="WebSocket server port (HTTP = port+1, Debug = port+2)")
    parser.add_argument("--max-ram", type=int, help="Max RAM in MB")
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--proxy", type=str, help="Proxy URL (http://user:pass@host:port)")
    parser.add_argument("--device", type=str, help="Device preset (iphone_14, galaxy_s23, ipad, etc.)")
    parser.add_argument("--persistent", action="store_true", help="Enable persistent Chromium (production mode)")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug UI server")
    parser.add_argument("--rate-limit", type=int, default=60, help="Max requests per minute per token (default: 60)")
    return parser.parse_args()


async def main():
    args = parse_args()
    app = AgentOS(args)

    # Handle shutdown signals
    def signal_handler(sig, frame):
        asyncio.create_task(app.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await app.start()
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await app.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
