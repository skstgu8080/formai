"""
Windows Startup Manager - Register FormAI to start with Windows.

Uses Windows Registry to add/remove startup entry.
"""

import os
import sys
import winreg
import logging
from pathlib import Path

logger = logging.getLogger("windows-startup")

# Registry path for current user startup
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FormAI"


def get_exe_path() -> str:
    """Get the path to the FormAI executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return sys.executable
    else:
        # Running as script - use pythonw to avoid console window
        python_path = sys.executable
        script_path = Path(__file__).parent.parent / "formai_entry.py"
        return f'"{python_path}" "{script_path}"'


def is_registered() -> bool:
    """Check if FormAI is registered to start with Windows."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        logger.error(f"Failed to check startup registration: {e}")
        return False


def register_startup(background: bool = True) -> bool:
    """
    Register FormAI to start with Windows.

    Args:
        background: If True, start in background mode (no browser popup)

    Returns:
        True if successful, False otherwise
    """
    try:
        exe_path = get_exe_path()

        # Add --background flag for silent startup
        if background:
            command = f'{exe_path} --background'
        else:
            command = exe_path

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE
        )

        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        logger.info(f"Registered startup: {command}")
        return True

    except Exception as e:
        logger.error(f"Failed to register startup: {e}")
        return False


def unregister_startup() -> bool:
    """
    Remove FormAI from Windows startup.

    Returns:
        True if successful, False otherwise
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE
        )

        try:
            winreg.DeleteValue(key, APP_NAME)
            logger.info("Unregistered from startup")
        except FileNotFoundError:
            # Already not registered
            pass

        winreg.CloseKey(key)
        return True

    except Exception as e:
        logger.error(f"Failed to unregister startup: {e}")
        return False


def get_startup_command() -> str:
    """Get the current startup command if registered."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return value
        except FileNotFoundError:
            winreg.CloseKey(key)
            return ""
    except Exception:
        return ""


# Quick test
if __name__ == "__main__":
    print(f"Exe path: {get_exe_path()}")
    print(f"Is registered: {is_registered()}")
    print(f"Current command: {get_startup_command()}")
