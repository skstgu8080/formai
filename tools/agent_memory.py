"""
Agent Memory - Local SQLite database for AI learning.

Stores successful field mappings, site patterns, and action history
so the AI gets smarter over time.
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("agent-memory")

# Default database path
DB_PATH = Path(__file__).parent.parent / "data" / "agent_memory.db"


class AgentMemory:
    """
    SQLite-based memory for AI agent learning.

    Stores:
    - Field mappings: selector → profile field associations
    - Site patterns: domain-specific form patterns
    - Action history: what actions worked/failed
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Field mappings: learned associations between selectors and profile fields
                CREATE TABLE IF NOT EXISTS field_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    selector TEXT NOT NULL,
                    field_name TEXT,
                    field_type TEXT,
                    profile_field TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    fail_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(domain, selector, profile_field)
                );

                -- Site patterns: learned form structures per domain
                CREATE TABLE IF NOT EXISTS site_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL UNIQUE,
                    form_type TEXT,
                    field_order TEXT,
                    submit_selector TEXT,
                    success_rate REAL DEFAULT 0.0,
                    attempts INTEGER DEFAULT 0,
                    last_success TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Action history: detailed log of actions taken
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    url TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    selector TEXT,
                    value TEXT,
                    success INTEGER NOT NULL,
                    error TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for fast lookups
                CREATE INDEX IF NOT EXISTS idx_mappings_domain ON field_mappings(domain);
                CREATE INDEX IF NOT EXISTS idx_mappings_selector ON field_mappings(selector);
                CREATE INDEX IF NOT EXISTS idx_history_domain ON action_history(domain);
                CREATE INDEX IF NOT EXISTS idx_patterns_domain ON site_patterns(domain);
            """)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return url

    def learn_field_mapping(
        self,
        url: str,
        selector: str,
        profile_field: str,
        field_name: Optional[str] = None,
        field_type: Optional[str] = None,
        success: bool = True
    ):
        """
        Learn a field mapping from successful/failed fill.

        Args:
            url: Page URL
            selector: CSS selector used
            profile_field: Profile field that was mapped
            field_name: Form field name attribute
            field_type: Input type (text, email, etc.)
            success: Whether the fill succeeded
        """
        domain = self._get_domain(url)
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Try to update existing mapping
            cursor = conn.execute("""
                SELECT id, success_count, fail_count FROM field_mappings
                WHERE domain = ? AND selector = ? AND profile_field = ?
            """, (domain, selector, profile_field))
            row = cursor.fetchone()

            if row:
                mapping_id, success_count, fail_count = row
                if success:
                    conn.execute("""
                        UPDATE field_mappings
                        SET success_count = ?, last_used = ?
                        WHERE id = ?
                    """, (success_count + 1, now, mapping_id))
                else:
                    conn.execute("""
                        UPDATE field_mappings
                        SET fail_count = ?
                        WHERE id = ?
                    """, (fail_count + 1, mapping_id))
            else:
                # Insert new mapping
                conn.execute("""
                    INSERT INTO field_mappings
                    (domain, selector, field_name, field_type, profile_field, success_count, fail_count, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain, selector, field_name, field_type, profile_field,
                    1 if success else 0,
                    0 if success else 1,
                    now
                ))

    def get_field_mappings(self, url: str) -> List[Dict[str, Any]]:
        """
        Get learned field mappings for a domain.

        Returns mappings sorted by success rate.
        """
        domain = self._get_domain(url)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT selector, profile_field, field_name, field_type,
                       success_count, fail_count,
                       CAST(success_count AS REAL) / (success_count + fail_count + 0.1) as score
                FROM field_mappings
                WHERE domain = ?
                ORDER BY score DESC, success_count DESC
            """, (domain,))

            return [dict(row) for row in cursor.fetchall()]

    def learn_site_pattern(
        self,
        url: str,
        success: bool,
        field_order: Optional[List[str]] = None,
        submit_selector: Optional[str] = None,
        form_type: Optional[str] = None
    ):
        """
        Learn site-level patterns from fill attempt.

        Args:
            url: Site URL
            success: Whether form was filled successfully
            field_order: Order of fields filled
            submit_selector: Selector used for submit
            form_type: Type of form (signup, contact, etc.)
        """
        domain = self._get_domain(url)
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, attempts, success_rate FROM site_patterns
                WHERE domain = ?
            """, (domain,))
            row = cursor.fetchone()

            if row:
                pattern_id, attempts, old_rate = row
                # Update running average
                new_attempts = attempts + 1
                new_rate = ((old_rate * attempts) + (1.0 if success else 0.0)) / new_attempts

                updates = ["attempts = ?", "success_rate = ?"]
                values = [new_attempts, new_rate]

                if success:
                    updates.append("last_success = ?")
                    values.append(now)
                if field_order:
                    updates.append("field_order = ?")
                    values.append(json.dumps(field_order))
                if submit_selector:
                    updates.append("submit_selector = ?")
                    values.append(submit_selector)
                if form_type:
                    updates.append("form_type = ?")
                    values.append(form_type)

                values.append(pattern_id)
                conn.execute(f"""
                    UPDATE site_patterns
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
            else:
                # Insert new pattern
                conn.execute("""
                    INSERT INTO site_patterns
                    (domain, form_type, field_order, submit_selector, success_rate, attempts, last_success)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (
                    domain,
                    form_type,
                    json.dumps(field_order) if field_order else None,
                    submit_selector,
                    1.0 if success else 0.0,
                    now if success else None
                ))

    def get_site_pattern(self, url: str) -> Optional[Dict[str, Any]]:
        """Get learned pattern for a site."""
        domain = self._get_domain(url)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM site_patterns WHERE domain = ?
            """, (domain,))
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("field_order"):
                    result["field_order"] = json.loads(result["field_order"])
                return result
            return None

    def log_action(
        self,
        url: str,
        action_type: str,
        success: bool,
        selector: Optional[str] = None,
        value: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log an action for history/debugging."""
        domain = self._get_domain(url)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO action_history
                (domain, url, action_type, selector, value, success, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (domain, url, action_type, selector, value, 1 if success else 0, error))

    def get_action_history(
        self,
        url: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent action history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if url:
                domain = self._get_domain(url)
                cursor = conn.execute("""
                    SELECT * FROM action_history
                    WHERE domain = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (domain, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM action_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Total mappings
            cursor = conn.execute("SELECT COUNT(*) FROM field_mappings")
            stats["total_mappings"] = cursor.fetchone()[0]

            # Total sites learned
            cursor = conn.execute("SELECT COUNT(*) FROM site_patterns")
            stats["sites_learned"] = cursor.fetchone()[0]

            # Success rate
            cursor = conn.execute("""
                SELECT AVG(success_rate) FROM site_patterns WHERE attempts > 0
            """)
            avg = cursor.fetchone()[0]
            stats["average_success_rate"] = round(avg * 100, 1) if avg else 0

            # Total actions
            cursor = conn.execute("SELECT COUNT(*) FROM action_history")
            stats["total_actions"] = cursor.fetchone()[0]

            # Top domains
            cursor = conn.execute("""
                SELECT domain, success_rate, attempts
                FROM site_patterns
                ORDER BY attempts DESC
                LIMIT 10
            """)
            stats["top_domains"] = [
                {"domain": row[0], "success_rate": round(row[1] * 100, 1), "attempts": row[2]}
                for row in cursor.fetchall()
            ]

            return stats

    def export_learning(self) -> Dict[str, Any]:
        """Export all learned data for backup/sharing."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            data = {
                "exported_at": datetime.now().isoformat(),
                "field_mappings": [],
                "site_patterns": []
            }

            # Export mappings (only successful ones)
            cursor = conn.execute("""
                SELECT domain, selector, profile_field, field_name, field_type, success_count
                FROM field_mappings
                WHERE success_count > fail_count
            """)
            data["field_mappings"] = [dict(row) for row in cursor.fetchall()]

            # Export patterns
            cursor = conn.execute("SELECT * FROM site_patterns")
            for row in cursor.fetchall():
                pattern = dict(row)
                if pattern.get("field_order"):
                    pattern["field_order"] = json.loads(pattern["field_order"])
                data["site_patterns"].append(pattern)

            return data

    def import_learning(self, data: Dict[str, Any]):
        """Import learned data from export."""
        with sqlite3.connect(self.db_path) as conn:
            # Import field mappings
            for mapping in data.get("field_mappings", []):
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO field_mappings
                        (domain, selector, profile_field, field_name, field_type, success_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        mapping["domain"],
                        mapping["selector"],
                        mapping["profile_field"],
                        mapping.get("field_name"),
                        mapping.get("field_type"),
                        mapping.get("success_count", 1)
                    ))
                except Exception:
                    pass

            # Import site patterns
            for pattern in data.get("site_patterns", []):
                try:
                    field_order = pattern.get("field_order")
                    if isinstance(field_order, list):
                        field_order = json.dumps(field_order)

                    conn.execute("""
                        INSERT OR IGNORE INTO site_patterns
                        (domain, form_type, field_order, submit_selector, success_rate, attempts)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        pattern["domain"],
                        pattern.get("form_type"),
                        field_order,
                        pattern.get("submit_selector"),
                        pattern.get("success_rate", 0),
                        pattern.get("attempts", 1)
                    ))
                except Exception:
                    pass


# Global instance
memory = AgentMemory()
