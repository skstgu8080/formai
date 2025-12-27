#!/usr/bin/env python3
"""
Ollama Model Checker and Auto-Installer

Terminal-friendly plug-and-play Ollama setup.
Runs entirely in the terminal - no popups, no user interaction needed.
"""
import os
import sys
import time
import shutil
import subprocess
import tempfile
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    # Also try to set console mode
    try:
        subprocess.run(["chcp", "65001"], capture_output=True, shell=True)
    except Exception:
        pass

# ANSI colors for terminal output (Windows 10+ supports these)
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Use ASCII-safe icons that work on all consoles
class Icons:
    CHECK = '[OK]'
    CROSS = '[X]'
    ARROW = '[>]'
    WARN = '[!]'
    INFO = '[i]'


def print_status(icon: str, message: str, color: str = Colors.RESET):
    """Print a formatted status message"""
    print(f"     {color}{icon}{Colors.RESET} {message}")


def print_progress(message: str, progress: int, total: int = 100):
    """Print a progress bar"""
    bar_width = 30
    filled = int(bar_width * progress / total)
    bar = '#' * filled + '-' * (bar_width - filled)
    # Write directly to avoid encoding issues
    try:
        sys.stdout.write(f'\r     [{bar}] {progress}% - {message}')
        sys.stdout.flush()
    except Exception:
        print(f"     [{bar}] {progress}% - {message}")
    if progress >= total:
        print()


def check_ollama_installed() -> tuple[bool, str]:
    """Check if Ollama is installed and return (installed, path)"""
    # Check common installation paths
    possible_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
    ]

    for path in possible_paths:
        if path.exists():
            return True, str(path)

    # Check if in PATH
    ollama_path = shutil.which("ollama")
    if ollama_path:
        return True, ollama_path

    return False, ""


def check_ollama_running() -> bool:
    """Check if Ollama service is responding"""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def get_installed_models() -> list:
    """Get list of installed Ollama models"""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def install_ollama_winget() -> bool:
    """Install Ollama using winget (silent, no popups)"""
    print_status(Icons.ARROW, "Installing Ollama via Windows Package Manager...", Colors.CYAN)

    try:
        # Check if winget is available
        result = subprocess.run(
            ["winget", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False

        # Install Ollama silently
        print_progress("Downloading and installing Ollama", 20)

        result = subprocess.run(
            ["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True,
            text=True,
            timeout=300
        )

        print_progress("Installing Ollama", 80)
        time.sleep(3)  # Wait for installation to finalize

        # Verify installation
        installed, _ = check_ollama_installed()
        if installed:
            print_progress("Ollama installed successfully", 100)
            return True

        return False

    except FileNotFoundError:
        # winget not available
        return False
    except subprocess.TimeoutExpired:
        print_status(Icons.CROSS, "Installation timed out", Colors.RED)
        return False
    except Exception as e:
        print_status(Icons.CROSS, f"Installation failed: {e}", Colors.RED)
        return False


def install_ollama_direct() -> bool:
    """Install Ollama by downloading installer directly (fallback)"""
    print_status(Icons.ARROW, "Downloading Ollama installer...", Colors.CYAN)

    try:
        import httpx

        # Download installer
        temp_dir = Path(tempfile.gettempdir())
        installer_path = temp_dir / "OllamaSetup.exe"

        url = "https://ollama.com/download/OllamaSetup.exe"

        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(installer_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = int(downloaded / total_size * 50)
                            print_progress(f"Downloading ({downloaded // 1024 // 1024}MB)", pct)

        print_progress("Download complete", 50)

        # Run silent installer
        print_progress("Installing Ollama (please wait)", 60)

        result = subprocess.run(
            [str(installer_path), "/S", "/VERYSILENT", "/NORESTART"],
            capture_output=True,
            timeout=300
        )

        print_progress("Finalizing installation", 90)
        time.sleep(5)  # Wait for installation to complete

        # Verify installation
        installed, _ = check_ollama_installed()
        if installed:
            print_progress("Ollama installed successfully", 100)
            # Clean up
            try:
                installer_path.unlink()
            except Exception:
                pass
            return True

        print_status(Icons.CROSS, "Installation verification failed", Colors.RED)
        return False

    except Exception as e:
        print_status(Icons.CROSS, f"Installation failed: {e}", Colors.RED)
        return False


def start_ollama_service(ollama_path: str) -> bool:
    """Start Ollama service"""
    print_status(Icons.ARROW, "Starting Ollama service...", Colors.CYAN)

    try:
        # Start Ollama serve in background (hidden window)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.Popen(
            [ollama_path, "serve"],
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Wait for service to start
        for i in range(15):
            time.sleep(1)
            if check_ollama_running():
                print_status(Icons.CHECK, "Ollama service started", Colors.GREEN)
                return True

        print_status(Icons.WARN, "Service slow to start, continuing anyway", Colors.YELLOW)
        return True

    except Exception as e:
        print_status(Icons.CROSS, f"Failed to start service: {e}", Colors.RED)
        return False


def pull_model(model_name: str, ollama_path: str) -> bool:
    """Pull an Ollama model with progress display"""
    print_status(Icons.ARROW, f"Downloading {model_name} model...", Colors.CYAN)
    print_status(Icons.INFO, "(This may take a few minutes on first run)", Colors.YELLOW)

    try:
        # Use binary mode and decode manually to avoid encoding issues
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            [ollama_path, "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        last_progress = 0
        while True:
            # Read raw bytes and decode with error handling
            raw_line = process.stdout.readline()
            if not raw_line:
                break

            try:
                line = raw_line.decode('utf-8', errors='replace').strip()
            except Exception:
                continue

            if not line:
                continue

            # Parse Ollama's progress output
            if "%" in line:
                try:
                    # Extract percentage from lines like "pulling manifest  50%"
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            pct = int(part.replace("%", ""))
                            if pct > last_progress:
                                last_progress = pct
                                print_progress(f"Pulling {model_name}", pct)
                except ValueError:
                    pass
            elif "success" in line.lower():
                print_progress(f"{model_name} ready", 100)

        process.wait(timeout=600)

        if process.returncode == 0:
            print_status(Icons.CHECK, f"Model {model_name} is ready", Colors.GREEN)
            return True
        else:
            print_status(Icons.CROSS, f"Failed to pull {model_name}", Colors.RED)
            return False

    except subprocess.TimeoutExpired:
        print_status(Icons.CROSS, "Model download timed out", Colors.RED)
        return False
    except Exception as e:
        print_status(Icons.CROSS, f"Model download failed: {e}", Colors.RED)
        return False


def main():
    """Main entry point for Ollama setup"""
    default_model = "llama3.2"

    print()
    print(f"{Colors.CYAN}     -----------------------------------------{Colors.RESET}")
    print(f"{Colors.BOLD}     Checking AI Model Setup (Ollama){Colors.RESET}")
    print(f"{Colors.CYAN}     -----------------------------------------{Colors.RESET}")
    print()

    # Step 1: Check if Ollama is installed
    installed, ollama_path = check_ollama_installed()

    if not installed:
        print_status(Icons.WARN, "Ollama not installed - installing now...", Colors.YELLOW)
        print()

        # Try winget first (truly silent)
        if install_ollama_winget():
            installed, ollama_path = check_ollama_installed()

        # Fall back to direct download
        if not installed:
            if install_ollama_direct():
                installed, ollama_path = check_ollama_installed()

        if not installed:
            print()
            print_status(Icons.CROSS, "Could not install Ollama automatically", Colors.RED)
            print_status(Icons.INFO, "Please install manually from: https://ollama.com/download", Colors.YELLOW)
            print()
            return 1

        print()
    else:
        print_status(Icons.CHECK, "Ollama is installed", Colors.GREEN)

    # Step 2: Check if service is running
    if not check_ollama_running():
        if not start_ollama_service(ollama_path):
            print()
            print_status(Icons.WARN, "Ollama service not running - AI features may be limited", Colors.YELLOW)
            print()
            return 1
    else:
        print_status(Icons.CHECK, "Ollama service is running", Colors.GREEN)

    # Step 3: Check if model is available
    models = get_installed_models()

    # Check for any variant of the model (llama3.2, llama3.2:latest, etc.)
    model_installed = any(default_model in m for m in models)

    if not model_installed:
        print()
        if not pull_model(default_model, ollama_path):
            print()
            print_status(Icons.WARN, f"Could not download {default_model} model", Colors.YELLOW)
            print_status(Icons.INFO, "AI features may be limited until model is available", Colors.YELLOW)
            print()
            return 1
        print()
    else:
        print_status(Icons.CHECK, f"Model {default_model} is ready", Colors.GREEN)

    print()
    print_status(Icons.CHECK, "AI setup complete - ready to use!", Colors.GREEN)
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_status(Icons.WARN, "Setup interrupted by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print()
        print_status(Icons.CROSS, f"Setup error: {e}", Colors.RED)
        sys.exit(1)
