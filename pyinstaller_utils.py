"""
PyInstaller Path Utilities
Helps locate resources correctly in both development and bundled executable modes
"""
import sys
import os
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for the application.

    Works correctly in both:
    - Development mode (running from Python)
    - Bundled mode (running from PyInstaller executable)

    Returns:
        Path object pointing to the application's base directory
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        # sys._MEIPASS is the temporary folder where PyInstaller extracts files
        return Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        return Path(__file__).parent.resolve()


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to a resource file.

    Args:
        relative_path: Path relative to application root (e.g., "static/css/style.css")

    Returns:
        Absolute Path object to the resource

    Example:
        >>> get_resource_path("web/index.html")
        Path("C:/Users/.../web/index.html")  # in dev mode
        Path("C:/Temp/_MEI.../web/index.html")  # in bundled mode
    """
    base = get_base_path()
    return base / relative_path


def is_bundled() -> bool:
    """
    Check if running as a PyInstaller bundle.

    Returns:
        True if running from bundled executable, False if running from Python
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


if __name__ == "__main__":
    # Quick test
    print(f"Running as bundle: {is_bundled()}")
    print(f"Base path: {get_base_path()}")
    print(f"Static path: {get_resource_path('static')}")
    print(f"Web path: {get_resource_path('web')}")
