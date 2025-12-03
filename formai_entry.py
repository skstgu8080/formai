"""
FormAI Entry Point

Handles MODE environment variable to run as either:
- web: Full web server with dashboard (default)
- worker: Headless job processor
"""

import os
import sys

def main():
    mode = os.environ.get("MODE", "web").lower()

    if mode == "worker":
        print("Starting FormAI in WORKER mode...")
        from worker import run_worker
        run_worker()
    else:
        print("Starting FormAI in WEB mode...")
        # Import and run the main server
        import formai_server
        # The server starts automatically on import via uvicorn

if __name__ == "__main__":
    main()
