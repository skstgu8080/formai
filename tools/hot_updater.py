"""
FormAI Hot Updater - Update tools and data without new exe

Updates these components independently:
1. tools/*.py - Automation scripts (from GitHub)
2. sites/sites.json - Sites database (from your server)
3. web/* - UI files (from your server)

The exe stays the same - only the dynamic parts update.
"""

import asyncio
import hashlib
import httpx
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("hot-updater")

# Configuration - Change these to your server
UPDATE_SERVER = os.environ.get("FORMAI_UPDATE_SERVER", "https://raw.githubusercontent.com/skstgu8080/formai/main")
MANIFEST_URL = f"{UPDATE_SERVER}/update-manifest.json"

# Local paths
if getattr(sys, 'frozen', False):
    # Running as exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as script
    BASE_DIR = Path(__file__).parent.parent

TOOLS_DIR = BASE_DIR / "tools"
SITES_DIR = BASE_DIR / "sites"
WEB_DIR = BASE_DIR / "web"
UPDATE_CACHE = BASE_DIR / "data" / "update_cache.json"


class HotUpdater:
    """Updates tools and data without requiring a new exe."""

    def __init__(self):
        self.last_check: Optional[datetime] = None
        self.updates_available: Dict[str, List[str]] = {}
        self.updates_applied: Dict[str, List[str]] = {}
        self.error: Optional[str] = None
        self._load_cache()

    def _load_cache(self):
        """Load cached file hashes to detect changes."""
        self.file_hashes: Dict[str, str] = {}
        if UPDATE_CACHE.exists():
            try:
                self.file_hashes = json.loads(UPDATE_CACHE.read_text())
            except:
                pass

    def _save_cache(self):
        """Save file hashes for future comparison."""
        UPDATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CACHE.write_text(json.dumps(self.file_hashes, indent=2))

    def _hash_content(self, content: bytes) -> str:
        """Generate hash of content."""
        return hashlib.sha256(content).hexdigest()[:16]

    async def check_for_updates(self) -> Dict[str, List[str]]:
        """
        Check remote server for available updates.

        Returns dict of {category: [list of files to update]}
        """
        self.updates_available = {"tools": [], "sites": [], "web": []}
        self.error = None

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Try to fetch manifest
                resp = await client.get(MANIFEST_URL)

                if resp.status_code == 200:
                    manifest = resp.json()

                    # Check each category
                    for category, files in manifest.get("files", {}).items():
                        for file_info in files:
                            filename = file_info.get("name")
                            remote_hash = file_info.get("hash")

                            # Compare with local hash
                            local_hash = self.file_hashes.get(f"{category}/{filename}")

                            if local_hash != remote_hash:
                                self.updates_available[category].append(filename)

                    self.last_check = datetime.now()

                elif resp.status_code == 404:
                    # No manifest yet - check individual files
                    logger.debug("No manifest found, checking files directly")
                    await self._check_files_directly(client)
                else:
                    self.error = f"Server returned {resp.status_code}"

        except httpx.TimeoutException:
            self.error = "Update check timed out"
        except Exception as e:
            self.error = str(e)
            logger.error(f"Update check failed: {e}")

        return self.updates_available

    async def _check_files_directly(self, client: httpx.AsyncClient):
        """Check for updates by comparing file hashes directly."""
        # Key files to check
        files_to_check = {
            "tools": ["seleniumbase_agent.py", "autofill_engine.py", "captcha_solver.py"],
            "sites": ["sites.json"],
        }

        for category, files in files_to_check.items():
            for filename in files:
                try:
                    url = f"{UPDATE_SERVER}/{category}/{filename}"
                    resp = await client.get(url)

                    if resp.status_code == 200:
                        remote_hash = self._hash_content(resp.content)
                        local_hash = self.file_hashes.get(f"{category}/{filename}")

                        if local_hash != remote_hash:
                            self.updates_available[category].append(filename)
                except:
                    continue

    async def apply_updates(self, categories: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Download and apply available updates.

        Args:
            categories: List of categories to update, or None for all

        Returns:
            Dict of {category: [list of updated files]}
        """
        if categories is None:
            categories = ["tools", "sites", "web"]

        self.updates_applied = {cat: [] for cat in categories}

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            for category in categories:
                files = self.updates_available.get(category, [])

                for filename in files:
                    success = await self._update_file(client, category, filename)
                    if success:
                        self.updates_applied[category].append(filename)

        self._save_cache()
        return self.updates_applied

    async def _update_file(self, client: httpx.AsyncClient, category: str, filename: str) -> bool:
        """Download and save a single file."""
        try:
            url = f"{UPDATE_SERVER}/{category}/{filename}"
            resp = await client.get(url)

            if resp.status_code != 200:
                logger.warning(f"Failed to download {category}/{filename}: {resp.status_code}")
                return False

            # Determine local path
            if category == "tools":
                local_path = TOOLS_DIR / filename
            elif category == "sites":
                local_path = SITES_DIR / filename
            elif category == "web":
                local_path = WEB_DIR / filename
            else:
                return False

            # Backup existing file
            if local_path.exists():
                backup_path = local_path.with_suffix(local_path.suffix + ".bak")
                shutil.copy2(local_path, backup_path)

            # Write new file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(resp.content)

            # Update hash cache
            self.file_hashes[f"{category}/{filename}"] = self._hash_content(resp.content)

            logger.info(f"Updated {category}/{filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to update {category}/{filename}: {e}")
            return False

    async def update_sites_database(self, url: Optional[str] = None) -> bool:
        """
        Update the sites database from remote server.

        Args:
            url: Optional custom URL for sites.json
        """
        if url is None:
            url = f"{UPDATE_SERVER}/sites/sites.json"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)

                if resp.status_code == 200:
                    # Validate JSON
                    sites_data = resp.json()

                    # Backup existing
                    sites_file = SITES_DIR / "sites.json"
                    if sites_file.exists():
                        backup = SITES_DIR / "sites.json.bak"
                        shutil.copy2(sites_file, backup)

                    # Save new data
                    sites_file.parent.mkdir(parents=True, exist_ok=True)
                    sites_file.write_text(json.dumps(sites_data, indent=2))

                    logger.info(f"Sites database updated: {len(sites_data.get('sites', []))} sites")
                    return True

        except Exception as e:
            logger.error(f"Failed to update sites database: {e}")

        return False

    def get_status(self) -> dict:
        """Get current update status for API."""
        return {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "updates_available": self.updates_available,
            "updates_applied": self.updates_applied,
            "error": self.error,
            "update_server": UPDATE_SERVER,
        }


# Global instance
hot_updater = HotUpdater()


async def check_and_apply_updates():
    """
    Background task to check and apply updates.
    Called on startup.
    """
    # Wait for server to start
    await asyncio.sleep(10)

    # Check for updates
    updates = await hot_updater.check_for_updates()

    # Count total updates
    total = sum(len(files) for files in updates.values())

    if total > 0:
        logger.info(f"Found {total} updates available")

        # Auto-apply tool updates
        await hot_updater.apply_updates(["tools", "sites"])

        applied = sum(len(files) for files in hot_updater.updates_applied.values())
        logger.info(f"Applied {applied} updates")


# API endpoints to add to formai_server.py:
"""
@app.get("/api/updates/check")
async def check_updates():
    updates = await hot_updater.check_for_updates()
    return {"updates": updates, "status": hot_updater.get_status()}

@app.post("/api/updates/apply")
async def apply_updates(categories: List[str] = None):
    applied = await hot_updater.apply_updates(categories)
    return {"applied": applied, "status": hot_updater.get_status()}

@app.get("/api/updates/status")
async def update_status():
    return hot_updater.get_status()
"""
