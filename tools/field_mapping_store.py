"""
Field Mapping Store - Unified Storage for Learned Field Mappings

Stores and retrieves field mappings by domain using SQLite database,
enabling "Learn Once, Replay Many" - eliminating AI guessing for trained sites.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Add parent to path for database import
sys.path.insert(0, str(Path(__file__).parent.parent))
from database import DomainMappingRepository

logger = logging.getLogger("field-mapping-store")


class FieldMappingStore:
    """
    Unified storage for domain-specific field mappings.

    Uses SQLite database via DomainMappingRepository.
    """

    def __init__(self, mappings_dir: str = None):
        """
        Initialize the field mapping store.

        Args:
            mappings_dir: Deprecated - kept for compatibility, ignored
        """
        self._cache: Dict[str, Dict] = {}

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain name."""
        # Keep domain as-is for database lookup
        return domain

    def has_mappings(self, domain: str) -> bool:
        """
        Check if mappings exist for a domain.

        Args:
            domain: Domain to check (e.g., "reebok.ph")

        Returns:
            True if mappings exist
        """
        # Check cache first
        if domain in self._cache:
            return True

        # Check database
        mapping = DomainMappingRepository.get_by_domain(domain)
        return mapping is not None

    def get_mappings(self, domain: str) -> Optional[List[Dict[str, str]]]:
        """
        Get saved mappings for a domain.

        Args:
            domain: Domain to get mappings for

        Returns:
            List of mappings or None if not found
        """
        # Check cache
        if domain in self._cache:
            return self._cache[domain].get("mappings")

        # Load from database
        data = DomainMappingRepository.get_by_domain(domain)
        if not data:
            logger.debug(f"No mappings found for {domain}")
            return None

        self._cache[domain] = data
        mappings = data.get("mappings", [])
        logger.info(f"Loaded {len(mappings)} mappings for {domain}")
        return mappings

    def get_full_data(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get full mapping data including metadata.

        Args:
            domain: Domain to get data for

        Returns:
            Full mapping data or None
        """
        # Check cache
        if domain in self._cache:
            return self._cache[domain]

        # Load from database
        data = DomainMappingRepository.get_by_domain(domain)
        if data:
            self._cache[domain] = data
        return data

    def save_mappings(
        self,
        domain: str,
        mappings: List[Dict[str, str]],
        url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        analyzer_version: Optional[str] = None
    ) -> bool:
        """
        Save field mappings for a domain.

        Supports both basic mappings {selector, profile_field} and
        enhanced mappings with fill_strategy for optimal replay.

        Args:
            domain: Domain to save mappings for
            mappings: List of mappings (basic or enhanced with fill_strategy)
            url: Optional URL for reference
            metadata: Optional additional metadata
            analyzer_version: Version of analyzer that generated mappings

        Returns:
            True if saved successfully
        """
        # Check if mappings are enhanced (have fill_strategy)
        is_enhanced = any(m.get('fill_strategy') for m in mappings)

        # Build fill_config from metadata
        fill_config = metadata.copy() if metadata else {}
        if analyzer_version:
            fill_config["analyzer_version"] = analyzer_version

        try:
            DomainMappingRepository.save(
                domain=domain,
                url=url or "",
                mappings=mappings,
                is_enhanced=is_enhanced,
                fill_config=fill_config if fill_config else None
            )

            # Update cache
            self._cache[domain] = {
                "domain": domain,
                "url": url,
                "mappings": mappings,
                "created_at": datetime.now().isoformat(),
                "fields_count": len(mappings),
                "is_enhanced": is_enhanced
            }

            logger.info(f"Saved {len(mappings)} mappings for {domain} to database")
            return True
        except Exception as e:
            logger.error(f"Error saving mappings for {domain}: {e}")
            return False

    def delete_mappings(self, domain: str) -> bool:
        """
        Delete mappings for a domain.

        Args:
            domain: Domain to delete mappings for

        Returns:
            True if deleted successfully
        """
        # Remove from cache
        if domain in self._cache:
            del self._cache[domain]

        # Delete from database
        try:
            result = DomainMappingRepository.delete(domain)
            if result:
                logger.info(f"Deleted mappings for {domain}")
            return result
        except Exception as e:
            logger.error(f"Error deleting mappings for {domain}: {e}")
            return False

    def list_domains(self) -> List[str]:
        """
        List all domains with saved mappings.

        Returns:
            List of domain names
        """
        all_mappings = DomainMappingRepository.get_all()
        return sorted([m.get("domain", "") for m in all_mappings if m.get("domain")])

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored mappings.

        Returns:
            Stats dict with counts and totals
        """
        all_mappings = DomainMappingRepository.get_all()

        domains = []
        total_fields = 0

        for data in all_mappings:
            domain = data.get("domain", "")
            field_count = data.get("fields_count", len(data.get("mappings", [])))
            domains.append({
                "domain": domain,
                "fields": field_count
            })
            total_fields += field_count

        return {
            "total_domains": len(domains),
            "total_fields": total_fields,
            "domains": sorted(domains, key=lambda x: x["fields"], reverse=True)
        }

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()

    def search_by_field(self, profile_field: str) -> List[Dict[str, Any]]:
        """
        Find all domains with mappings for a specific profile field.

        Args:
            profile_field: Profile field to search for (e.g., "email")

        Returns:
            List of {domain, selector} matches
        """
        matches = []
        all_mappings = DomainMappingRepository.get_all()

        for data in all_mappings:
            domain = data.get("domain", "")
            mappings = data.get("mappings", [])

            for mapping in mappings:
                if mapping.get("profile_field") == profile_field:
                    matches.append({
                        "domain": domain,
                        "selector": mapping.get("selector"),
                        "profile_field": profile_field
                    })
                    break  # One match per domain is enough

        return matches


# CLI testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    store = FieldMappingStore()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            print("Domains with saved mappings:")
            for domain in store.list_domains():
                print(f"  - {domain}")

        elif command == "stats":
            stats = store.get_stats()
            print(f"Total domains: {stats['total_domains']}")
            print(f"Total fields: {stats['total_fields']}")
            print("\nTop domains by field count:")
            for d in stats["domains"][:10]:
                print(f"  - {d['domain']}: {d['fields']} fields")

        elif command == "get" and len(sys.argv) > 2:
            domain = sys.argv[2]
            mappings = store.get_mappings(domain)
            if mappings:
                print(f"Mappings for {domain}:")
                for m in mappings:
                    print(f"  {m['selector']} -> {m['profile_field']}")
            else:
                print(f"No mappings found for {domain}")

        elif command == "search" and len(sys.argv) > 2:
            field = sys.argv[2]
            matches = store.search_by_field(field)
            print(f"Domains with '{field}' field:")
            for m in matches[:20]:
                print(f"  - {m['domain']}: {m['selector']}")

        elif command == "migrate":
            # Migration command to import JSON files
            print("Migration should be done via migrate_json_mappings.py")

        else:
            print("Usage:")
            print("  python field_mapping_store.py list")
            print("  python field_mapping_store.py stats")
            print("  python field_mapping_store.py get <domain>")
            print("  python field_mapping_store.py search <profile_field>")
    else:
        # Demo: save and retrieve
        print("Field Mapping Store Demo")
        print("=" * 40)

        # Save test mapping
        store.save_mappings(
            domain="test.example.com",
            mappings=[
                {"selector": "#email", "profile_field": "email"},
                {"selector": "#firstName", "profile_field": "firstName"},
            ],
            url="https://test.example.com/register"
        )

        # Retrieve it
        mappings = store.get_mappings("test.example.com")
        print(f"\nRetrieved mappings: {mappings}")

        # Check if exists
        print(f"Has mappings: {store.has_mappings('test.example.com')}")
        print(f"Has mappings for unknown: {store.has_mappings('unknown.com')}")

        # Clean up
        store.delete_mappings("test.example.com")
        print("\nCleaned up test data")
