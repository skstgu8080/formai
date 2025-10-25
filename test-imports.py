"""
Quick test to verify all imports work before building EXE
Run this to catch import errors early
"""
import sys
print("Python version:", sys.version)
print()
print("Testing imports...")
print()

try:
    print("✓ fastapi", end="... ")
    import fastapi
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ uvicorn", end="... ")
    import uvicorn
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ seleniumbase", end="... ")
    import seleniumbase
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ pyautogui", end="... ")
    import pyautogui
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ websockets", end="... ")
    import websockets
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ pyinstaller_utils", end="... ")
    from pyinstaller_utils import get_base_path, is_bundled
    print("OK")
    print(f"  - Base path: {get_base_path()}")
    print(f"  - Is bundled: {is_bundled()}")
except Exception as e:
    print(f"FAILED: {e}")

try:
    print("✓ selenium_automation", end="... ")
    import selenium_automation
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")

print()
print("If all tests passed, you're ready to build!")
print()
input("Press Enter to exit...")
