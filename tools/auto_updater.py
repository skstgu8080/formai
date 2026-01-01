"""
FormAI Auto-Updater

Checks GitHub releases for updates and downloads them in the background.
Updates are applied on next restart.
"""

import asyncio
import httpx
import logging
import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("auto-updater")

GITHUB_REPO = "skstgu8080/formai"
UPDATE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "FormAI" / "updates"


class AutoUpdater:
    """Handles automatic update checking and downloading."""

    def __init__(self):
        self.current_version: str = "0.0.0"
        self.latest_version: Optional[str] = None
        self.update_available: bool = False
        self.update_ready: bool = False
        self.download_progress: int = 0
        self.update_error: Optional[str] = None
        self._download_url: Optional[str] = None

    def _load_current_version(self):
        """Load current version from version.py."""
        try:
            from version import __version__
            self.current_version = __version__
        except ImportError:
            self.current_version = "0.0.0"

    async def check_for_update(self) -> bool:
        """
        Check GitHub releases API for a newer version.

        Returns:
            True if update is available, False otherwise.
        """
        self._load_current_version()

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                    headers={"User-Agent": "FormAI-AutoUpdater"},
                    timeout=15
                )

                if resp.status_code == 200:
                    data = resp.json()
                    self.latest_version = data.get("tag_name", "").lstrip("v")

                    # Find download URL for current platform
                    self._download_url = self._get_download_url(data.get("assets", []))

                    # Compare versions
                    self.update_available = self._is_newer(
                        self.latest_version,
                        self.current_version
                    )

                    if self.update_available:
                        logger.info(
                            f"Update available: v{self.current_version} → v{self.latest_version}"
                        )
                    else:
                        logger.debug(f"Already on latest version: v{self.current_version}")

                    return self.update_available

                elif resp.status_code == 404:
                    logger.debug("No releases found")
                else:
                    logger.warning(f"GitHub API returned status {resp.status_code}")

        except httpx.TimeoutException:
            logger.debug("Update check timed out")
        except Exception as e:
            logger.debug(f"Update check failed: {e}")

        return False

    def _get_download_url(self, assets: list) -> Optional[str]:
        """Get the download URL for the current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Map platform to expected asset name
        if system == "windows":
            if "arm" in machine:
                target = "formai-windows-arm64.zip"
            elif "64" in machine or machine == "amd64":
                target = "formai-windows-x64.zip"
            else:
                target = "formai-windows-x86.zip"
        elif system == "darwin":
            if "arm" in machine:
                target = "formai-macos-arm64.zip"
            else:
                target = "formai-macos-x64.zip"
        else:  # Linux
            target = "formai-linux-x64.zip"

        for asset in assets:
            if asset.get("name") == target:
                return asset.get("browser_download_url")

        return None

    def _is_newer(self, latest: str, current: str) -> bool:
        """
        Compare semantic versions.

        Args:
            latest: Latest version string (e.g., "1.0.4")
            current: Current version string (e.g., "1.0.3")

        Returns:
            True if latest > current
        """
        try:
            latest_parts = [int(x) for x in latest.split(".")]
            current_parts = [int(x) for x in current.split(".")]

            # Pad shorter version with zeros
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)

            return latest_parts > current_parts
        except (ValueError, AttributeError):
            return False

    async def download_update(self) -> bool:
        """
        Download the latest release to the updates directory.

        Returns:
            True if download succeeded, False otherwise.
        """
        if not self.update_available or not self._download_url:
            return False

        try:
            # Create updates directory
            UPDATE_DIR.mkdir(parents=True, exist_ok=True)

            zip_path = UPDATE_DIR / f"formai-{self.latest_version}.zip"
            extract_path = UPDATE_DIR / "pending"

            # Clean up any previous pending update
            if extract_path.exists():
                shutil.rmtree(extract_path)

            logger.info(f"Downloading update v{self.latest_version}...")
            self.download_progress = 0

            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", self._download_url, timeout=300) as resp:
                    if resp.status_code != 200:
                        self.update_error = f"Download failed: HTTP {resp.status_code}"
                        return False

                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0

                    with open(zip_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self.download_progress = int(downloaded / total * 100)

            # Extract zip
            logger.info("Extracting update...")
            extract_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_path)

            # Clean up zip
            zip_path.unlink()

            # Mark update as ready
            self.update_ready = True
            self.download_progress = 100

            # Write version marker
            (extract_path / ".version").write_text(self.latest_version)

            logger.info(f"Update v{self.latest_version} ready - restart to apply")
            return True

        except Exception as e:
            self.update_error = str(e)
            logger.error(f"Download failed: {e}")
            return False

    def has_pending_update(self) -> bool:
        """Check if there's a pending update waiting to be applied."""
        pending_path = UPDATE_DIR / "pending"
        version_file = pending_path / ".version"
        return version_file.exists()

    def get_pending_version(self) -> Optional[str]:
        """Get the version of the pending update."""
        version_file = UPDATE_DIR / "pending" / ".version"
        if version_file.exists():
            return version_file.read_text().strip()
        return None

    def get_status(self) -> dict:
        """Get current update status for API."""
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "update_ready": self.update_ready or self.has_pending_update(),
            "pending_version": self.get_pending_version(),
            "download_progress": self.download_progress,
            "error": self.update_error
        }


# Global instance
updater = AutoUpdater()


async def check_and_download():
    """
    Check for updates and download if available.
    Called on startup as a background task.
    """
    # Wait a bit before checking (let server start first)
    await asyncio.sleep(5)

    if await updater.check_for_update():
        # Download in background
        await updater.download_update()


def apply_pending_update() -> bool:
    """
    Apply a pending update by replacing current files.
    Should be called at startup before the main app runs.

    Returns:
        True if update was applied, False otherwise.
    """
    pending_path = UPDATE_DIR / "pending"

    if not pending_path.exists():
        return False

    version_file = pending_path / ".version"
    if not version_file.exists():
        return False

    try:
        new_version = version_file.read_text().strip()
        logger.info(f"Applying update v{new_version}...")

        # Get current app directory
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller exe
            app_dir = Path(sys.executable).parent
        else:
            # Running as script
            app_dir = Path(__file__).parent.parent

        # Backup current version (optional)
        backup_dir = UPDATE_DIR / "backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        # Copy new files over current ones
        for item in pending_path.iterdir():
            if item.name == ".version":
                continue

            dest = app_dir / item.name

            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Update version.py
        version_py = app_dir / "version.py"
        version_py.write_text(f'"""FormAI Version - Single source of truth."""\n\n__version__ = "{new_version}"\n__author__ = "FormAI Team"\n')

        # Clean up pending update
        shutil.rmtree(pending_path)

        logger.info(f"Update v{new_version} applied successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to apply update: {e}")
        return False


# Import sys for frozen check
import sys
