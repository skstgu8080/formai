"""
Windows System Tray - FormAI tray icon with menu.

Runs in background thread alongside the FastAPI server.
"""

import threading
import webbrowser
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("windows-tray")

# Try to import pystray
try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None
    Image = None


class FormAITray:
    """System tray icon for FormAI."""

    def __init__(self, port: int = 5511, on_exit=None):
        self.port = port
        self.on_exit = on_exit  # Callback to shutdown server
        self.icon = None
        self._thread = None

    def _create_icon_image(self):
        """Create tray icon image."""
        # Try to load favicon
        icon_paths = [
            Path(__file__).parent.parent / "static" / "favicon.ico",
            Path(__file__).parent.parent / "static" / "favicon.png",
            Path(__file__).parent.parent / "static" / "favicon.svg",
        ]

        for icon_path in icon_paths:
            if icon_path.exists():
                try:
                    return Image.open(icon_path)
                except:
                    pass

        # Create a simple colored icon if no file found
        img = Image.new('RGB', (64, 64), color=(59, 130, 246))  # Blue
        return img

    def _create_menu(self):
        """Create tray menu."""
        return pystray.Menu(
            pystray.MenuItem("Open FormAI", self._open_browser, default=True),
            pystray.MenuItem("Settings", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit)
        )

    def _open_browser(self, icon=None, item=None):
        """Open FormAI in browser."""
        webbrowser.open(f"http://localhost:{self.port}")

    def _open_settings(self, icon=None, item=None):
        """Open settings page."""
        webbrowser.open(f"http://localhost:{self.port}/settings")

    def _exit(self, icon=None, item=None):
        """Exit the application."""
        logger.info("Exit requested from tray")

        # Stop the tray icon
        if self.icon:
            self.icon.stop()

        # Call exit callback to shutdown server
        if self.on_exit:
            self.on_exit()
        else:
            # Force exit if no callback
            os._exit(0)

    def run(self):
        """Start tray icon in background thread."""
        if not TRAY_AVAILABLE:
            logger.warning("pystray not available, skipping tray icon")
            return

        def _run_tray():
            try:
                image = self._create_icon_image()
                menu = self._create_menu()

                self.icon = pystray.Icon(
                    name="FormAI",
                    icon=image,
                    title="FormAI - Form Automation",
                    menu=menu
                )

                logger.info("Starting system tray icon")
                self.icon.run()

            except Exception as e:
                logger.error(f"Failed to start tray icon: {e}")

        self._thread = threading.Thread(target=_run_tray, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the tray icon."""
        if self.icon:
            self.icon.stop()


# Global tray instance
_tray_instance = None


def start_tray(port: int = 5511, on_exit=None) -> FormAITray:
    """Start the system tray icon."""
    global _tray_instance

    if not TRAY_AVAILABLE:
        logger.warning("System tray not available (pystray not installed)")
        return None

    _tray_instance = FormAITray(port=port, on_exit=on_exit)
    _tray_instance.run()
    return _tray_instance


def stop_tray():
    """Stop the system tray icon."""
    global _tray_instance
    if _tray_instance:
        _tray_instance.stop()
        _tray_instance = None


def is_tray_available() -> bool:
    """Check if system tray is available."""
    return TRAY_AVAILABLE


# Quick test
if __name__ == "__main__":
    import time

    print(f"Tray available: {TRAY_AVAILABLE}")

    if TRAY_AVAILABLE:
        def on_exit():
            print("Exit callback triggered")
            sys.exit(0)

        tray = start_tray(port=5511, on_exit=on_exit)
        print("Tray started. Right-click the icon to see menu.")
        print("Press Ctrl+C to exit...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_tray()
            print("Stopped")
