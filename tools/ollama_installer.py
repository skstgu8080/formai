#!/usr/bin/env python3
"""
Ollama Installer - Automatic installation and setup for Windows
"""
import os
import sys
import subprocess
import time
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import httpx


class OllamaInstaller:
    """Manages Ollama installation and configuration"""

    OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/OllamaSetup.exe"
    OLLAMA_SERVICE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, progress_callback=None):
        """
        Initialize Ollama installer

        Args:
            progress_callback: Optional function to report progress (status, percentage, message)
        """
        self.progress_callback = progress_callback
        self.installation_dir = None

    def _report_progress(self, status: str, percentage: int, message: str):
        """Report installation progress"""
        if self.progress_callback:
            self.progress_callback(status, percentage, message)
        else:
            print(f"[{percentage}%] {status}: {message}")

    def check_installation(self) -> Dict[str, Any]:
        """
        Check if Ollama is installed and running

        Returns:
            Dict with installation status information
        """
        result = {
            "installed": False,
            "running": False,
            "executable_path": None,
            "version": None,
            "models_available": []
        }

        # Check for Ollama executable
        possible_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Ollama" / "ollama.exe"
        ]

        for path in possible_paths:
            if path.exists():
                result["installed"] = True
                result["executable_path"] = str(path)
                self.installation_dir = path.parent
                break

        # Check if Ollama is in PATH
        if not result["installed"]:
            ollama_path = shutil.which("ollama")
            if ollama_path:
                result["installed"] = True
                result["executable_path"] = ollama_path
                self.installation_dir = Path(ollama_path).parent

        # Check if service is running
        if result["installed"]:
            try:
                response = httpx.get(f"{self.OLLAMA_SERVICE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    result["running"] = True
                    data = response.json()
                    result["models_available"] = [m["name"] for m in data.get("models", [])]
            except Exception:
                result["running"] = False

        # Get version if installed
        if result["installed"] and result["executable_path"]:
            try:
                version_output = subprocess.run(
                    [result["executable_path"], "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if version_output.returncode == 0:
                    result["version"] = version_output.stdout.strip()
            except Exception:
                pass

        return result

    def install_via_winget(self) -> bool:
        """
        Install Ollama using Windows Package Manager (winget).
        This is truly silent with no GUI popups.

        Returns:
            True if installation successful
        """
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

            self._report_progress("installing", 20, "Installing Ollama via Windows Package Manager...")

            # Install Ollama silently via winget
            result = subprocess.run(
                ["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements"],
                capture_output=True,
                text=True,
                timeout=300
            )

            self._report_progress("installing", 55, "Verifying installation...")
            time.sleep(3)

            # Verify installation
            status = self.check_installation()
            if status["installed"]:
                self._report_progress("installing", 60, "Ollama installed via winget")
                return True

            return False

        except FileNotFoundError:
            # winget not available
            return False
        except subprocess.TimeoutExpired:
            self._report_progress("error", 0, "Winget installation timed out")
            return False
        except Exception:
            return False

    def download_installer(self, download_path: Path) -> bool:
        """
        Download Ollama installer

        Args:
            download_path: Path where to save the installer

        Returns:
            True if download successful
        """
        try:
            self._report_progress("downloading", 10, "Downloading Ollama installer...")

            with httpx.stream("GET", self.OLLAMA_DOWNLOAD_URL, follow_redirects=True, timeout=300) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(download_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                percentage = 10 + int((downloaded / total_size) * 30)  # 10-40%
                                self._report_progress(
                                    "downloading",
                                    percentage,
                                    f"Downloaded {downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB"
                                )

            self._report_progress("downloading", 40, "Download complete")
            return True

        except Exception as e:
            self._report_progress("error", 0, f"Download failed: {str(e)}")
            return False

    def install_ollama(self, installer_path: Path) -> bool:
        """
        Run Ollama installer silently

        Args:
            installer_path: Path to the downloaded installer

        Returns:
            True if installation successful
        """
        try:
            self._report_progress("installing", 45, "Running Ollama installer (silent mode)...")

            # Run silent installation with multiple silent flags for compatibility
            # Hide the window completely
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                [str(installer_path), "/S", "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"],
                capture_output=True,
                text=True,
                timeout=300,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self._report_progress("installing", 55, "Finalizing installation...")

            # Wait for installation to complete
            time.sleep(5)

            # Verify installation
            status = self.check_installation()
            if status["installed"]:
                self._report_progress("installing", 60, "Ollama installed successfully")
                return True
            else:
                self._report_progress("error", 0, "Installation verification failed")
                return False

        except subprocess.TimeoutExpired:
            self._report_progress("error", 0, "Installation timed out")
            return False
        except Exception as e:
            self._report_progress("error", 0, f"Installation failed: {str(e)}")
            return False

    def start_service(self) -> bool:
        """
        Start Ollama service

        Returns:
            True if service started successfully
        """
        try:
            self._report_progress("starting", 65, "Starting Ollama service...")

            status = self.check_installation()
            if not status["installed"]:
                self._report_progress("error", 0, "Ollama not installed")
                return False

            # Start Ollama serve in background
            if sys.platform == "win32":
                # On Windows, Ollama typically starts automatically as a service
                # Just wait and check if it's running
                for i in range(5):
                    time.sleep(2)
                    status = self.check_installation()
                    if status["running"]:
                        self._report_progress("starting", 70, "Ollama service is running")
                        return True

                # If not running, try to start manually with hidden window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                subprocess.Popen(
                    [status["executable_path"], "serve"],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Wait for service to start
                for i in range(10):
                    time.sleep(2)
                    status = self.check_installation()
                    if status["running"]:
                        self._report_progress("starting", 70, "Ollama service started")
                        return True

            self._report_progress("error", 0, "Failed to start Ollama service")
            return False

        except Exception as e:
            self._report_progress("error", 0, f"Failed to start service: {str(e)}")
            return False

    def pull_model(self, model_name: Optional[str] = None) -> bool:
        """
        Pull (download) an Ollama model

        Args:
            model_name: Name of model to pull (default: llama3.2)

        Returns:
            True if model pulled successfully
        """
        if model_name is None:
            model_name = self.DEFAULT_MODEL

        try:
            self._report_progress("downloading_model", 75, f"Downloading {model_name} model...")

            status = self.check_installation()
            if not status["installed"]:
                self._report_progress("error", 0, "Ollama not installed")
                return False

            # Pull model using Ollama CLI (hidden window)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # Check if model already exists
            if model_name in status.get("models_available", []):
                self._report_progress("downloading_model", 100, f"Model {model_name} already installed")
                return True

            process = subprocess.Popen(
                [status["executable_path"], "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Monitor progress (read as bytes to avoid encoding issues)
            while True:
                chunk = process.stdout.read(1024)
                if not chunk:
                    break
                try:
                    line = chunk.decode('utf-8', errors='replace')
                    if "pulling" in line.lower():
                        self._report_progress("downloading_model", 80, f"Pulling {model_name}...")
                    elif "success" in line.lower():
                        self._report_progress("downloading_model", 95, f"Model {model_name} downloaded")
                except Exception:
                    pass

            process.wait(timeout=600)  # 10 minute timeout for model download

            if process.returncode == 0:
                self._report_progress("downloading_model", 100, f"Model {model_name} ready")
                return True
            else:
                self._report_progress("error", 0, f"Failed to pull model {model_name}")
                return False

        except subprocess.TimeoutExpired:
            self._report_progress("error", 0, "Model download timed out")
            return False
        except Exception as e:
            self._report_progress("error", 0, f"Model download failed: {str(e)}")
            return False

    def install_complete(self) -> Dict[str, Any]:
        """
        Perform complete Ollama installation

        Returns:
            Dict with installation result
        """
        result = {
            "success": False,
            "status": None,
            "message": None
        }

        try:
            # Check if already installed
            self._report_progress("checking", 0, "Checking Ollama installation...")
            status = self.check_installation()

            if status["installed"] and status["running"] and self.DEFAULT_MODEL in status["models_available"]:
                result["success"] = True
                result["status"] = "already_installed"
                result["message"] = "Ollama is already installed and configured"
                self._report_progress("complete", 100, "Ollama ready to use")
                return result

            # If not installed, try winget first (truly silent, no popups)
            if not status["installed"]:
                self._report_progress("installing", 10, "Attempting silent installation via winget...")
                if self.install_via_winget():
                    status = self.check_installation()

            # Fall back to direct installer download if winget failed
            if not status["installed"]:
                temp_dir = Path(tempfile.gettempdir())
                installer_path = temp_dir / "OllamaSetup.exe"

                if not self.download_installer(installer_path):
                    result["status"] = "download_failed"
                    result["message"] = "Failed to download Ollama installer"
                    return result

                # Install Ollama
                if not self.install_ollama(installer_path):
                    result["status"] = "install_failed"
                    result["message"] = "Failed to install Ollama"
                    return result

            # Start service
            if not self.start_service():
                result["status"] = "service_failed"
                result["message"] = "Failed to start Ollama service"
                return result

            # Pull default model
            if not self.pull_model():
                result["status"] = "model_failed"
                result["message"] = f"Failed to download {self.DEFAULT_MODEL} model"
                return result

            # Clean up installer
            try:
                installer_path.unlink()
            except:
                pass

            result["success"] = True
            result["status"] = "installed"
            result["message"] = "Ollama installed and configured successfully"
            self._report_progress("complete", 100, "Installation complete!")

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Installation error: {str(e)}"
            self._report_progress("error", 0, str(e))

        return result


# Singleton instance for shared state
_installer = None

def get_installer(progress_callback=None) -> OllamaInstaller:
    """Get or create Ollama installer instance"""
    global _installer
    if _installer is None or progress_callback is not None:
        _installer = OllamaInstaller(progress_callback)
    return _installer
