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

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import Config
from src.core.browser import AgentBrowser
from src.core.session import SessionManager
from src.agents.server import AgentServer

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
        self.server = AgentServer(self.config, self.browser, self.session_manager)
        self._running = False
        self._ram_monitor_task = None

        # Apply CLI overrides
        if args.headed:
            self.config.set("browser.headless", False)
        if args.port:
            self.config.set("server.ws_port", args.port)
            self.config.set("server.http_port", args.port + 1)
        if args.max_ram:
            self.config.set("browser.max_ram_mb", args.max_ram)

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

        # Start agent server
        logger.info("Starting agent server...")
        await self.server.start()

        # Start RAM monitor
        self._ram_monitor_task = asyncio.create_task(self._ram_monitor())

        ws_port = self.config.get("server.ws_port", 8000)
        http_port = self.config.get("server.http_port", 8001)

        # Register the CLI token
        if args.agent_token:
            default_token = args.agent_token
        else:
            default_token = self.config.generate_agent_token("agent")
        self.config.register_token(default_token, "cli")

        logger.info("")
        logger.info("  ✅ Agent-OS is READY!")
        logger.info("  ─────────────────────────────────────────")
        logger.info(f"  WebSocket: ws://127.0.0.1:{ws_port}")
        logger.info(f"  HTTP API:  http://127.0.0.1:{http_port}")
        logger.info(f"  Agent Token: {default_token}")
        logger.info("")
        logger.info("  Quick test:")
        logger.info(f'  curl -X POST http://127.0.0.1:{http_port}/command \\')
        logger.info(f"    -H 'Content-Type: application/json' \\")
        logger.info(f"    -d '{{\"token\": \"{default_token}\", \"command\": \"navigate\", \"url\": \"https://example.com\"}}'")
        logger.info("")
        logger.info("  Press Ctrl+C to stop")
        logger.info("  ─────────────────────────────────────────")

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
            try:
                await self._ram_monitor_task
            except asyncio.CancelledError:
                pass

        await self.server.stop()
        await self.session_manager.stop()
        await self.browser.stop()

        logger.info("Agent-OS stopped. Goodbye! 👋")

    async def _ram_monitor(self):
        """Monitor RAM usage. Enforce cap by closing idle tabs."""
        max_ram = self.config.get("browser.max_ram_mb", 500)
        last_warning = 0
        while self._running:
            try:
                process = psutil.Process(os.getpid())
                ram_mb = process.memory_info().rss / 1024 / 1024
                now = asyncio.get_event_loop().time()

                if ram_mb > max_ram:
                    # Only warn every 60s to avoid spam
                    if now - last_warning > 60:
                        logger.warning(
                            f"⚠️  RAM usage ({ram_mb:.0f}MB) exceeds limit ({max_ram}MB). "
                            f"Closing idle tabs..."
                        )
                        last_warning = now

                    # Close non-main tabs to free memory
                    tabs_closed = 0
                    for tab_id in list(self.browser._pages.keys()):
                        if tab_id != "main":
                            try:
                                await self.browser.close_tab(tab_id)
                                tabs_closed += 1
                            except Exception:
                                pass

                    if tabs_closed:
                        logger.info(f"Freed memory by closing {tabs_closed} tab(s)")

                    # If still over limit after closing tabs, warn harder
                    process = psutil.Process(os.getpid())
                    ram_mb = process.memory_info().rss / 1024 / 1024
                    if ram_mb > max_ram * 1.5 and now - last_warning > 60:
                        logger.error(
                            f"🚨 RAM critically high ({ram_mb:.0f}MB / {max_ram}MB limit). "
                            f"Consider restarting Agent-OS."
                        )

                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"RAM monitor error: {e}")
                await asyncio.sleep(10)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agent-OS — AI Agent Browser"
    )
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--agent-token", type=str, help="Set agent authentication token")
    parser.add_argument("--port", type=int, help="WebSocket server port (HTTP = port+1)")
    parser.add_argument("--max-ram", type=int, help="Max RAM in MB")
    parser.add_argument("--config", type=str, help="Config file path")
    return parser.parse_args()


async def main():
    args = parse_args()
    app = AgentOS(args)

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
