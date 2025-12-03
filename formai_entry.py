"""
FormAI Entry Point

Handles MODE environment variable to run as either:
- web: Full web server with dashboard (default)
- worker: Headless job processor

Also applies any pending updates before starting.
"""

import os
import sys


def apply_pending_updates():
    """Check for and apply any pending updates before starting."""
    try:
        from tools.auto_updater import apply_pending_update, updater
        if updater.has_pending_update():
            version = updater.get_pending_version()
            print(f"Applying pending update v{version}...")
            if apply_pending_update():
                print(f"Update v{version} applied successfully!")
                print("Restarting with new version...")
                # Restart the application
                os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"Update check skipped: {e}")


def main():
    # Apply any pending updates first
    apply_pending_updates()

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
