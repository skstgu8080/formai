"""
FormAI Entry Point

Handles MODE environment variable to run as either:
- web: Full web server with dashboard (default)
- worker: Headless job processor

Command line arguments:
- --background: Start in background mode (no browser popup, tray icon only)

Also applies any pending updates before starting.
"""

import os
import sys
import argparse
import webbrowser
import threading
import logging

logger = logging.getLogger("formai-entry")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="FormAI - Form Automation")
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Start in background mode (no browser popup, tray icon only)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5511,
        help="Port to run server on (default: 5511)"
    )
    return parser.parse_args()


def ensure_ollama_running():
    """Ensure Ollama is installed and running for AI features."""
    try:
        from tools.ollama_installer import OllamaInstaller

        installer = OllamaInstaller()
        status = installer.check_installation()

        if not status["installed"]:
            result = installer.install_complete()
            if not result["success"]:
                return False

        if not status["running"]:
            if not installer.start_service():
                return False

        # Check if default model is installed
        if status["running"] and "llama3.2" not in status.get("models_available", []):
            installer.pull_model("llama3.2")

        return True
    except Exception:
        return False


def apply_pending_updates():
    """Check for and apply any pending updates before starting."""
    try:
        from tools.auto_updater import apply_pending_update, updater
        if updater.has_pending_update():
            if apply_pending_update():
                # Restart the application
                os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception:
        pass


def auto_register_startup():
    """Auto-register Windows startup on first run."""
    if sys.platform != "win32":
        return

    try:
        from tools.windows_startup import is_registered, register_startup

        # Check if already registered
        if not is_registered():
            register_startup(background=True)
    except Exception:
        pass  # Silently fail


def start_tray_icon(port: int, on_exit=None):
    """Start the system tray icon (Windows only)."""
    try:
        if sys.platform == "win32":
            from tools.windows_tray import start_tray, is_tray_available
            if is_tray_available():
                start_tray(port=port, on_exit=on_exit)
    except Exception:
        pass  # Silently fail


def main():
    args = parse_args()

    # Apply any pending updates first
    apply_pending_updates()

    # Auto-register Windows startup on first run
    auto_register_startup()

    # Ensure Ollama is running for AI features
    ensure_ollama_running()

    mode = os.environ.get("MODE", "web").lower()

    if mode == "worker":
        from core.worker import run_worker
        run_worker()
    else:
        import uvicorn
        from formai_server import app

        port = args.port
        background = args.background

        
        # Define shutdown handler for tray exit
        server = None
        def on_tray_exit():
            if server:
                server.should_exit = True
            os._exit(0)

        # Start system tray icon (Windows)
        if sys.platform == "win32":
            start_tray_icon(port=port, on_exit=on_tray_exit)

        # Open browser unless in background mode
        if not background:
            def open_browser():
                import time
                time.sleep(1.5)  # Wait for server to start
                webbrowser.open(f"http://localhost:{port}")
            threading.Thread(target=open_browser, daemon=True).start()

        # Configure uvicorn - bind to localhost only to avoid firewall prompt
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning"
        )
        server = uvicorn.Server(config)

        
        server.run()


if __name__ == "__main__":
    main()
