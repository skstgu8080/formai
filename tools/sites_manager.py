"""
Sites Manager - URL-based site management for auto-fill.

Stores URLs and their form fields with profile mappings in SQLite.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

# Import database
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import init_db, SiteRepository, ProfileRepository

SITES_DIR = Path(__file__).parent.parent / "sites"
PROFILES_DIR = Path(__file__).parent.parent / "profiles"


class SitesManager:
    """Manage sites for batch auto-fill using SQLite database."""

    def __init__(self):
        # Initialize database on first use
        init_db()

    def get_all_sites(self) -> List[Dict[str, Any]]:
        """Get all sites."""
        return SiteRepository.get_all()

    def get_enabled_sites(self) -> List[Dict[str, Any]]:
        """Get only enabled sites."""
        return SiteRepository.get_enabled()

    def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific site by ID (supports partial match)."""
        return SiteRepository.get_by_id(site_id)

    def add_site(self, url: str, name: str = None) -> Dict[str, Any]:
        """Add a new site."""
        # Generate ID
        site_id = str(uuid.uuid4())[:8]

        # Extract name from URL if not provided
        if not name:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            name = parsed.netloc.replace('www.', '')

        site = {
            "id": site_id,
            "url": url,
            "name": name,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "last_status": None,
            "fields_filled": 0
        }

        SiteRepository.create(site)
        return site

    def add_sites_bulk(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Add multiple sites at once."""
        added = []
        for url in urls:
            url = url.strip()
            if url and url.startswith('http'):
                added.append(self.add_site(url))
        return added

    def update_site(self, site_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a site."""
        site = SiteRepository.get_by_id(site_id)
        if not site:
            return None

        # Merge updates
        site.update(updates)
        SiteRepository.create(site)  # Uses INSERT OR REPLACE
        return site

    def update_site_status(self, site_id: str, status: str, fields_filled: int = 0):
        """Update site run status."""
        SiteRepository.update_status(site_id, status, fields_filled)

    def delete_site(self, site_id: str) -> bool:
        """Delete a site."""
        return SiteRepository.delete(site_id)

    def toggle_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Toggle site enabled/disabled."""
        SiteRepository.toggle(site_id)
        return SiteRepository.get_by_id(site_id)

    def import_from_recordings(self, recordings_dir: Path) -> int:
        """Import URLs from existing recordings."""
        count = 0
        recordings_index = recordings_dir / "recordings_index.json"

        if recordings_index.exists():
            try:
                with open(recordings_index, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                recordings = index.get("recordings", {})

                # Handle both dict and list formats
                if isinstance(recordings, dict):
                    items = recordings.values()
                else:
                    items = recordings

                for rec in items:
                    url = rec.get("url")
                    name = rec.get("recording_name") or rec.get("title")
                    if url:
                        self.add_site(url, name)
                        count += 1
            except Exception as e:
                print(f"Import error: {e}")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get site statistics."""
        return SiteRepository.get_stats()

    def update_site_fields(self, site_id: str, fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Store analyzed fields for a site."""
        return self.update_site(site_id, {
            "fields": fields,
            "analyzed_at": datetime.now().isoformat()
        })

    def get_site_fields(self, site_id: str) -> List[Dict[str, Any]]:
        """Get stored fields for a site."""
        site = self.get_site(site_id)
        return site.get("fields", []) if site else []

    def update_field_mapping(self, site_id: str, field_selector: str, profile_key: str, transform: str = "") -> bool:
        """Update mapping for a specific field."""
        site = self.get_site(site_id)
        if not site:
            return False

        fields = site.get("fields", [])
        for field in fields:
            if field.get("selector") == field_selector:
                field["profile_key"] = profile_key
                field["transform"] = transform
                self.update_site(site_id, {"fields": fields})
                return True
        return False

    def add_profile_field(self, profile_id: str, field_key: str, default_value: str = "") -> bool:
        """Add a new field to a profile if it doesn't exist."""
        profile = ProfileRepository.get_by_id(profile_id)
        if not profile:
            return False

        # Add field if not exists
        if field_key not in profile:
            profile[field_key] = default_value
            ProfileRepository.create(profile)
            return True
        return False  # Field already exists

    def get_missing_profile_fields(self, site_id: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get fields from site that don't have values in profile."""
        site = self.get_site(site_id)
        if not site:
            return []

        fields = site.get("fields", [])
        missing = []

        for field in fields:
            profile_key = field.get("profile_key", "")
            if profile_key and profile_key not in profile:
                missing.append({
                    "field": field,
                    "profile_key": profile_key
                })

        return missing

    def ensure_profile_has_fields(self, profile_id: str, site_id: str):
        """Ensure profile has all fields needed by site."""
        site = self.get_site(site_id)
        if not site:
            return

        for field in site.get("fields", []):
            profile_key = field.get("profile_key", "")
            if profile_key:
                self.add_profile_field(profile_id, profile_key, "")
