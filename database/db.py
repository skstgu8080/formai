"""
FormAI Database - SQLite connection and schema management.

Single file database at data/formai.db with all application data.
"""

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

# Get data path for PyInstaller compatibility (user data next to exe)
try:
    from pyinstaller_utils import get_data_path
    DATA_BASE_PATH = get_data_path()
except ImportError:
    DATA_BASE_PATH = Path(".")

logger = logging.getLogger("formai-db")

# Database location - use data path for PyInstaller compatibility
DB_PATH = DATA_BASE_PATH / "data" / "formai.db"

# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles table
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    password TEXT,
    birthdate TEXT,
    gender TEXT,
    address1 TEXT,
    address2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    company TEXT,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sites table
CREATE TABLE IF NOT EXISTS sites (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    name TEXT,
    enabled INTEGER DEFAULT 1,
    last_run TIMESTAMP,
    last_status TEXT,
    fields_filled INTEGER DEFAULT 0,
    fields JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP
);

-- Learned field mappings (selector -> profile_key)
CREATE TABLE IF NOT EXISTS learned_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    selector TEXT UNIQUE NOT NULL,
    profile_key TEXT NOT NULL,
    domain TEXT,
    confidence REAL DEFAULT 1.0,
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_learned_selector ON learned_fields(selector);
CREATE INDEX IF NOT EXISTS idx_learned_domain ON learned_fields(domain);

-- Field mappings per URL
CREATE TABLE IF NOT EXISTS field_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    selector TEXT NOT NULL,
    profile_key TEXT NOT NULL,
    transform TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(url, selector)
);
CREATE INDEX IF NOT EXISTS idx_field_mappings_url ON field_mappings(url);

-- Domain field mappings (full mapping document per domain)
CREATE TABLE IF NOT EXISTS domain_mappings (
    domain TEXT PRIMARY KEY,
    url TEXT,
    mappings JSON NOT NULL,
    fields_count INTEGER DEFAULT 0,
    is_enhanced INTEGER DEFAULT 0,
    fill_config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_domain_mappings_url ON domain_mappings(url);

-- Fill results history
CREATE TABLE IF NOT EXISTS fill_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id TEXT,
    profile_id TEXT,
    url TEXT,
    success INTEGER,
    fields_filled INTEGER,
    error TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_fill_history_site ON fill_history(site_id);
CREATE INDEX IF NOT EXISTS idx_fill_history_date ON fill_history(created_at);

-- Admin: Registered clients
CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    hostname TEXT,
    local_ip TEXT,
    platform TEXT,
    version TEXT,
    license_key TEXT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    heartbeat_count INTEGER DEFAULT 0
);

-- Admin: License keys
CREATE TABLE IF NOT EXISTS licenses (
    key TEXT PRIMARY KEY,
    customer_name TEXT,
    customer_email TEXT,
    tier TEXT DEFAULT 'free',
    max_machines INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);
"""


def init_db() -> None:
    """Initialize database with schema. Safe to call multiple times."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Execute schema (IF NOT EXISTS makes it safe)
        conn.executescript(SCHEMA)

        # Track schema version
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")
    finally:
        conn.close()


@contextmanager
def get_db():
    """
    Context manager for database connections.

    Usage:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM profiles")
            rows = cursor.fetchall()
    """
    # Ensure DB exists
    if not DB_PATH.exists():
        init_db()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Return dict-like rows
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_from_row(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dict."""
    if row is None:
        return None
    return dict(row)


def migrate_json_to_sqlite() -> dict:
    """
    One-time migration from JSON files to SQLite.

    Returns:
        Migration stats: {"profiles": 5, "sites": 100, ...}
    """
    from .repositories import (
        ProfileRepository,
        SiteRepository,
        LearnedFieldRepository
    )

    stats = {
        "profiles": 0,
        "sites": 0,
        "learned_fields": 0,
        "errors": []
    }

    # Migrate profiles
    profiles_dir = Path("profiles")
    if profiles_dir.exists():
        for file in profiles_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                ProfileRepository.create(profile)
                stats["profiles"] += 1
            except Exception as e:
                stats["errors"].append(f"Profile {file.name}: {e}")

    # Migrate sites
    sites_file = Path("sites/sites.json")
    if sites_file.exists():
        try:
            with open(sites_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for site in data.get("sites", []):
                SiteRepository.create(site)
                stats["sites"] += 1
        except Exception as e:
            stats["errors"].append(f"Sites: {e}")

    # Migrate learned fields
    learned_file = DATA_BASE_PATH / "data" / "learned_fields.json"
    if learned_file.exists():
        try:
            with open(learned_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for selector, profile_key in data.get("mappings", {}).items():
                LearnedFieldRepository.save(selector, profile_key)
                stats["learned_fields"] += 1
        except Exception as e:
            stats["errors"].append(f"Learned fields: {e}")

    logger.info(f"Migration complete: {stats}")
    return stats


def export_to_json(output_dir: str = "backup") -> dict:
    """
    Export all database data to JSON files for backup.

    Args:
        output_dir: Directory to write JSON files

    Returns:
        Export stats
    """
    from .repositories import ProfileRepository, SiteRepository, LearnedFieldRepository

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = {"profiles": 0, "sites": 0, "learned_fields": 0}

    # Export profiles
    profiles = ProfileRepository.get_all()
    for p in profiles:
        file_path = output_path / f"profile_{p['id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(p, f, indent=2)
        stats["profiles"] += 1

    # Export sites
    sites = SiteRepository.get_all()
    sites_data = {"sites": sites}
    with open(output_path / "sites.json", 'w', encoding='utf-8') as f:
        json.dump(sites_data, f, indent=2)
    stats["sites"] = len(sites)

    # Export learned fields
    mappings = LearnedFieldRepository.get_all_mappings()
    learned_data = {"mappings": mappings, "exported_at": datetime.now().isoformat()}
    with open(output_path / "learned_fields.json", 'w', encoding='utf-8') as f:
        json.dump(learned_data, f, indent=2)
    stats["learned_fields"] = len(mappings)

    logger.info(f"Export complete to {output_dir}: {stats}")
    return stats
