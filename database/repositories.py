"""
FormAI Data Repositories - Clean data access layer.

Each repository handles CRUD operations for a specific entity type.
All methods are static for easy use without instantiation.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from .db import get_db, dict_from_row

logger = logging.getLogger("formai-repo")


class ProfileRepository:
    """Repository for user profiles."""

    @staticmethod
    def get_all() -> List[dict]:
        """Get all profiles."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, first_name, last_name, email, phone, password,
                       birthdate, gender, address1, address2, city, state, zip,
                       country, company, data, created_at, updated_at
                FROM profiles
                ORDER BY name, first_name
            """)
            rows = cursor.fetchall()

            profiles = []
            for row in rows:
                profile = dict_from_row(row)
                # Merge stored JSON data with column data
                if profile.get('data'):
                    extra = json.loads(profile['data'])
                    del profile['data']
                    profile.update(extra)
                profiles.append(profile)
            return profiles

    @staticmethod
    def get_by_id(profile_id: str) -> Optional[dict]:
        """Get profile by ID."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, first_name, last_name, email, phone, password,
                       birthdate, gender, address1, address2, city, state, zip,
                       country, company, data, created_at, updated_at
                FROM profiles WHERE id = ?
            """, (profile_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            profile = dict_from_row(row)
            if profile.get('data'):
                extra = json.loads(profile['data'])
                del profile['data']
                profile.update(extra)
            return profile

    @staticmethod
    def create(profile: dict) -> str:
        """Create new profile. Returns profile ID."""
        profile_id = profile.get('id') or str(uuid.uuid4())[:8]

        # Extract known columns
        columns = {
            'id': profile_id,
            'name': profile.get('name', ''),
            'first_name': profile.get('firstName', profile.get('first_name', '')),
            'last_name': profile.get('lastName', profile.get('last_name', '')),
            'email': profile.get('email', ''),
            'phone': profile.get('phone', ''),
            'password': profile.get('password', ''),
            'birthdate': profile.get('birthdate', profile.get('birthDate', '')),
            'gender': profile.get('gender', profile.get('sex', '')),
            'address1': profile.get('address1', profile.get('address', '')),
            'address2': profile.get('address2', ''),
            'city': profile.get('city', ''),
            'state': profile.get('state', ''),
            'zip': profile.get('zip', profile.get('zipCode', '')),
            'country': profile.get('country', ''),
            'company': profile.get('company', ''),
        }

        # Store full profile as JSON for any extra fields
        data_json = json.dumps(profile)

        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO profiles
                (id, name, first_name, last_name, email, phone, password,
                 birthdate, gender, address1, address2, city, state, zip,
                 country, company, data, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                columns['id'], columns['name'], columns['first_name'],
                columns['last_name'], columns['email'], columns['phone'],
                columns['password'], columns['birthdate'], columns['gender'],
                columns['address1'], columns['address2'], columns['city'],
                columns['state'], columns['zip'], columns['country'],
                columns['company'], data_json, datetime.now().isoformat()
            ))

        logger.debug(f"Created profile: {profile_id}")
        return profile_id

    @staticmethod
    def update(profile_id: str, updates: dict) -> bool:
        """Update profile. Returns True if updated."""
        existing = ProfileRepository.get_by_id(profile_id)
        if not existing:
            return False

        # Merge updates
        existing.update(updates)
        existing['id'] = profile_id  # Preserve ID
        ProfileRepository.create(existing)  # Uses INSERT OR REPLACE
        return True

    @staticmethod
    def delete(profile_id: str) -> bool:
        """Delete profile. Returns True if deleted."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            return cursor.rowcount > 0


class SiteRepository:
    """Repository for sites to fill."""

    @staticmethod
    def get_all() -> List[dict]:
        """Get all sites."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, url, name, enabled, last_run, last_status,
                       fields_filled, fields, created_at, analyzed_at
                FROM sites
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()

            sites = []
            for row in rows:
                site = dict_from_row(row)
                site['enabled'] = bool(site.get('enabled', 1))
                if site.get('fields'):
                    site['fields'] = json.loads(site['fields'])
                sites.append(site)
            return sites

    @staticmethod
    def get_enabled() -> List[dict]:
        """Get only enabled sites."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, url, name, enabled, last_run, last_status,
                       fields_filled, fields, created_at, analyzed_at
                FROM sites
                WHERE enabled = 1
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()

            sites = []
            for row in rows:
                site = dict_from_row(row)
                site['enabled'] = True
                if site.get('fields'):
                    site['fields'] = json.loads(site['fields'])
                sites.append(site)
            return sites

    @staticmethod
    def get_by_id(site_id: str) -> Optional[dict]:
        """Get site by ID (supports partial match)."""
        with get_db() as conn:
            # Try exact match first
            cursor = conn.execute("""
                SELECT id, url, name, enabled, last_run, last_status,
                       fields_filled, fields, created_at, analyzed_at
                FROM sites WHERE id = ?
            """, (site_id,))
            row = cursor.fetchone()

            # Try partial match
            if row is None:
                cursor = conn.execute("""
                    SELECT id, url, name, enabled, last_run, last_status,
                           fields_filled, fields, created_at, analyzed_at
                    FROM sites WHERE id LIKE ?
                    LIMIT 1
                """, (f"{site_id}%",))
                row = cursor.fetchone()

            if row is None:
                return None

            site = dict_from_row(row)
            site['enabled'] = bool(site.get('enabled', 1))
            if site.get('fields'):
                site['fields'] = json.loads(site['fields'])
            return site

    @staticmethod
    def create(site: dict) -> str:
        """Create new site. Returns site ID."""
        site_id = site.get('id') or str(uuid.uuid4())[:8]
        fields_json = json.dumps(site.get('fields', [])) if site.get('fields') else None

        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sites
                (id, url, name, enabled, last_run, last_status, fields_filled,
                 fields, created_at, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                site_id,
                site.get('url', ''),
                site.get('name', ''),
                1 if site.get('enabled', True) else 0,
                site.get('last_run'),
                site.get('last_status'),
                site.get('fields_filled', 0),
                fields_json,
                site.get('created_at', datetime.now().isoformat()),
                site.get('analyzed_at')
            ))

        return site_id

    @staticmethod
    def add(url: str, name: str = None) -> str:
        """Add new site by URL. Returns site ID."""
        site_id = str(uuid.uuid4())[:8]
        site_name = name or url

        with get_db() as conn:
            conn.execute("""
                INSERT INTO sites (id, url, name, enabled, created_at)
                VALUES (?, ?, ?, 1, ?)
            """, (site_id, url, site_name, datetime.now().isoformat()))

        return site_id

    @staticmethod
    def update_status(site_id: str, status: str, fields_filled: int) -> bool:
        """Update site fill status."""
        with get_db() as conn:
            cursor = conn.execute("""
                UPDATE sites
                SET last_status = ?, fields_filled = ?, last_run = ?
                WHERE id = ? OR id LIKE ?
            """, (status, fields_filled, datetime.now().isoformat(),
                  site_id, f"{site_id}%"))
            return cursor.rowcount > 0

    @staticmethod
    def toggle(site_id: str) -> bool:
        """Toggle site enabled status."""
        with get_db() as conn:
            cursor = conn.execute("""
                UPDATE sites SET enabled = NOT enabled
                WHERE id = ? OR id LIKE ?
            """, (site_id, f"{site_id}%"))
            return cursor.rowcount > 0

    @staticmethod
    def delete(site_id: str) -> bool:
        """Delete site."""
        with get_db() as conn:
            cursor = conn.execute("""
                DELETE FROM sites WHERE id = ? OR id LIKE ?
            """, (site_id, f"{site_id}%"))
            return cursor.rowcount > 0

    @staticmethod
    def get_stats() -> dict:
        """Get site statistics."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled,
                    SUM(CASE WHEN last_status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN last_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM sites
            """)
            row = cursor.fetchone()
            return {
                'total': row['total'] or 0,
                'enabled': row['enabled'] or 0,
                'success': row['success'] or 0,
                'failed': row['failed'] or 0,
            }


class LearnedFieldRepository:
    """Repository for learned field mappings (selector -> profile_key)."""

    @staticmethod
    def get(selector: str) -> Optional[str]:
        """Get profile_key for selector."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT profile_key FROM learned_fields WHERE selector = ?
            """, (selector,))
            row = cursor.fetchone()
            return row['profile_key'] if row else None

    @staticmethod
    def save(selector: str, profile_key: str, domain: str = None) -> None:
        """Save or update field mapping."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO learned_fields (selector, profile_key, domain, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(selector) DO UPDATE SET
                    profile_key = excluded.profile_key,
                    hit_count = hit_count + 1,
                    updated_at = excluded.updated_at
            """, (selector, profile_key, domain, datetime.now().isoformat()))

    @staticmethod
    def get_all_mappings() -> Dict[str, str]:
        """Get all mappings as dict."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT selector, profile_key FROM learned_fields
            """)
            return {row['selector']: row['profile_key'] for row in cursor.fetchall()}

    @staticmethod
    def get_by_domain(domain: str) -> Dict[str, str]:
        """Get mappings for specific domain."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT selector, profile_key FROM learned_fields
                WHERE domain = ? OR domain IS NULL
            """, (domain,))
            return {row['selector']: row['profile_key'] for row in cursor.fetchall()}

    @staticmethod
    def increment_hit(selector: str) -> None:
        """Increment hit count for selector."""
        with get_db() as conn:
            conn.execute("""
                UPDATE learned_fields SET hit_count = hit_count + 1
                WHERE selector = ?
            """, (selector,))

    @staticmethod
    def count() -> int:
        """Get total number of learned mappings."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM learned_fields")
            return cursor.fetchone()['cnt']


class FieldMappingRepository:
    """Repository for URL-specific field mappings."""

    @staticmethod
    def get_for_url(url: str) -> List[dict]:
        """Get all mappings for a URL."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT selector, profile_key, transform
                FROM field_mappings WHERE url = ?
            """, (url,))
            return [dict_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def save(url: str, selector: str, profile_key: str, transform: str = None) -> None:
        """Save field mapping for URL."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO field_mappings (url, selector, profile_key, transform)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url, selector) DO UPDATE SET
                    profile_key = excluded.profile_key,
                    transform = excluded.transform
            """, (url, selector, profile_key, transform))

    @staticmethod
    def delete_for_url(url: str) -> int:
        """Delete all mappings for URL. Returns count deleted."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM field_mappings WHERE url = ?", (url,))
            return cursor.rowcount


class DomainMappingRepository:
    """Repository for domain-level field mappings (replaces JSON files)."""

    @staticmethod
    def get_all() -> List[dict]:
        """Get all domain mappings."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT domain, url, mappings, fields_count, is_enhanced,
                       fill_config, created_at, updated_at
                FROM domain_mappings
                ORDER BY domain
            """)
            results = []
            for row in cursor.fetchall():
                mapping = dict_from_row(row)
                mapping['mappings'] = json.loads(mapping['mappings']) if mapping.get('mappings') else []
                mapping['is_enhanced'] = bool(mapping.get('is_enhanced', 0))
                if mapping.get('fill_config'):
                    mapping['fill_config'] = json.loads(mapping['fill_config'])
                results.append(mapping)
            return results

    @staticmethod
    def get_by_domain(domain: str) -> Optional[dict]:
        """Get mapping for a specific domain."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT domain, url, mappings, fields_count, is_enhanced,
                       fill_config, created_at, updated_at
                FROM domain_mappings WHERE domain = ?
            """, (domain,))
            row = cursor.fetchone()
            if row is None:
                return None
            mapping = dict_from_row(row)
            mapping['mappings'] = json.loads(mapping['mappings']) if mapping.get('mappings') else []
            mapping['is_enhanced'] = bool(mapping.get('is_enhanced', 0))
            if mapping.get('fill_config'):
                mapping['fill_config'] = json.loads(mapping['fill_config'])
            return mapping

    @staticmethod
    def save(domain: str, url: str, mappings: List[dict],
             is_enhanced: bool = False, fill_config: dict = None) -> None:
        """Save or update domain mapping."""
        mappings_json = json.dumps(mappings)
        fill_config_json = json.dumps(fill_config) if fill_config else None

        with get_db() as conn:
            conn.execute("""
                INSERT INTO domain_mappings
                (domain, url, mappings, fields_count, is_enhanced, fill_config, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    url = excluded.url,
                    mappings = excluded.mappings,
                    fields_count = excluded.fields_count,
                    is_enhanced = excluded.is_enhanced,
                    fill_config = excluded.fill_config,
                    updated_at = excluded.updated_at
            """, (domain, url, mappings_json, len(mappings),
                  1 if is_enhanced else 0, fill_config_json,
                  datetime.now().isoformat()))

    @staticmethod
    def delete(domain: str) -> bool:
        """Delete domain mapping. Returns True if deleted."""
        with get_db() as conn:
            cursor = conn.execute(
                "DELETE FROM domain_mappings WHERE domain = ?", (domain,))
            return cursor.rowcount > 0

    @staticmethod
    def count() -> int:
        """Get total number of domain mappings."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM domain_mappings")
            return cursor.fetchone()['cnt']

    @staticmethod
    def search(query: str) -> List[dict]:
        """Search mappings by domain or URL."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT domain, url, mappings, fields_count, is_enhanced,
                       fill_config, created_at, updated_at
                FROM domain_mappings
                WHERE domain LIKE ? OR url LIKE ?
                ORDER BY domain
            """, (f"%{query}%", f"%{query}%"))
            results = []
            for row in cursor.fetchall():
                mapping = dict_from_row(row)
                mapping['mappings'] = json.loads(mapping['mappings']) if mapping.get('mappings') else []
                mapping['is_enhanced'] = bool(mapping.get('is_enhanced', 0))
                if mapping.get('fill_config'):
                    mapping['fill_config'] = json.loads(mapping['fill_config'])
                results.append(mapping)
            return results


class FillHistoryRepository:
    """Repository for fill operation history."""

    @staticmethod
    def record(site_id: str, profile_id: str, url: str, success: bool,
               fields_filled: int, error: str = None, duration_ms: int = None) -> int:
        """Record a fill operation. Returns history ID."""
        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO fill_history
                (site_id, profile_id, url, success, fields_filled, error, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (site_id, profile_id, url, 1 if success else 0,
                  fields_filled, error, duration_ms))
            return cursor.lastrowid

    @staticmethod
    def get_recent(limit: int = 100) -> List[dict]:
        """Get recent fill history."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT * FROM fill_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def get_stats() -> dict:
        """Get fill statistics."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_fills,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(fields_filled) as total_fields,
                    AVG(duration_ms) as avg_duration_ms
                FROM fill_history
            """)
            row = cursor.fetchone()
            return {
                'total_fills': row['total_fills'] or 0,
                'successful': row['successful'] or 0,
                'success_rate': (row['successful'] or 0) / max(row['total_fills'] or 1, 1) * 100,
                'total_fields': row['total_fields'] or 0,
                'avg_duration_ms': row['avg_duration_ms'] or 0,
            }
