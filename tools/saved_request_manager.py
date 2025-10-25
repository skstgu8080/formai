"""
Saved Request Template Manager

Manages saved HTTP request templates for reusable form submissions.
Templates store URL, headers, form data, and field mappings for batch execution.
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SavedRequestTemplate:
    """HTTP request template with field mappings for profile integration"""

    id: str
    name: str
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    form_data_template: Dict[str, str] = field(default_factory=dict)
    field_mappings: Dict[str, str] = field(default_factory=dict)
    detect_csrf: bool = True
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def __post_init__(self):
        """Set timestamps if not provided"""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SavedRequestTemplate':
        """Create from dictionary"""
        return cls(**data)

    def merge_with_profile(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """
        Merge profile data with form data template using field mappings.

        Args:
            profile: Profile data dictionary

        Returns:
            Form data with profile values inserted
        """
        merged_data = self.form_data_template.copy()

        for form_field, profile_path in self.field_mappings.items():
            # Handle nested paths (e.g., "address.street")
            value = self._get_nested_value(profile, profile_path)
            if value is not None:
                merged_data[form_field] = str(value)

        return merged_data

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """
        Get value from nested dictionary using dot notation.

        Examples:
            _get_nested_value({"address": {"street": "123 Main"}}, "address.street") -> "123 Main"
            _get_nested_value({"email": "test@example.com"}, "email") -> "test@example.com"
        """
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class SavedRequestManager:
    """Manages saved HTTP request templates"""

    def __init__(self, storage_dir: str = "saved_requests"):
        """
        Initialize manager with storage directory.

        Args:
            storage_dir: Directory to store template JSON files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"SavedRequestManager initialized: {self.storage_dir}")

    def save(self, template: SavedRequestTemplate) -> SavedRequestTemplate:
        """
        Save template to disk.

        Args:
            template: Template to save

        Returns:
            Saved template with updated timestamp
        """
        template.updated_at = datetime.utcnow().isoformat()

        file_path = self.storage_dir / f"{template.id}.json"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Saved template: {template.name} ({template.id})")
            return template

        except Exception as e:
            logger.error(f"Failed to save template {template.id}: {e}")
            raise

    def get(self, template_id: str) -> Optional[SavedRequestTemplate]:
        """
        Get template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template if found, None otherwise
        """
        file_path = self.storage_dir / f"{template_id}.json"

        if not file_path.exists():
            logger.warning(f"Template not found: {template_id}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return SavedRequestTemplate.from_dict(data)

        except Exception as e:
            logger.error(f"Failed to load template {template_id}: {e}")
            return None

    def list_all(self) -> List[SavedRequestTemplate]:
        """
        List all saved templates.

        Returns:
            List of all templates, sorted by updated_at descending
        """
        templates = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                template = SavedRequestTemplate.from_dict(data)
                templates.append(template)

            except Exception as e:
                logger.error(f"Failed to load template from {file_path}: {e}")
                continue

        # Sort by updated_at descending (newest first)
        templates.sort(key=lambda t: t.updated_at, reverse=True)

        return templates

    def delete(self, template_id: str) -> bool:
        """
        Delete template by ID.

        Args:
            template_id: Template ID

        Returns:
            True if deleted, False if not found
        """
        file_path = self.storage_dir / f"{template_id}.json"

        if not file_path.exists():
            logger.warning(f"Cannot delete - template not found: {template_id}")
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted template: {template_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete template {template_id}: {e}")
            raise

    def update(self, template_id: str, updates: Dict[str, Any]) -> Optional[SavedRequestTemplate]:
        """
        Update template fields.

        Args:
            template_id: Template ID
            updates: Dictionary of fields to update

        Returns:
            Updated template if found, None otherwise
        """
        template = self.get(template_id)

        if not template:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        # Save and return
        return self.save(template)

    def create_from_parsed_request(
        self,
        name: str,
        url: str,
        method: str,
        headers: Dict[str, str],
        form_data: Dict[str, str],
        field_mappings: Dict[str, str],
        detect_csrf: bool = True,
        description: str = "",
        tags: List[str] = None
    ) -> SavedRequestTemplate:
        """
        Create template from parsed request data.

        Args:
            name: Template name
            url: Request URL
            method: HTTP method
            headers: Request headers
            form_data: Form data template
            field_mappings: Field mappings (form field -> profile path)
            detect_csrf: Whether to detect and include CSRF tokens
            description: Optional description
            tags: Optional tags

        Returns:
            Created template
        """
        template = SavedRequestTemplate(
            id=str(uuid.uuid4()),
            name=name,
            url=url,
            method=method,
            headers=headers,
            form_data_template=form_data,
            field_mappings=field_mappings,
            detect_csrf=detect_csrf,
            description=description,
            tags=tags or []
        )

        return self.save(template)

    def search(self, query: str) -> List[SavedRequestTemplate]:
        """
        Search templates by name, URL, or tags.

        Args:
            query: Search query

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        templates = self.list_all()

        matching = []
        for template in templates:
            # Search in name, URL, description, and tags
            if (query_lower in template.name.lower() or
                query_lower in template.url.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                matching.append(template)

        return matching

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about saved templates.

        Returns:
            Statistics dictionary
        """
        templates = self.list_all()

        return {
            "total_templates": len(templates),
            "templates_by_method": self._count_by_field(templates, "method"),
            "templates_by_tag": self._count_by_tags(templates),
            "templates_with_csrf": sum(1 for t in templates if t.detect_csrf),
            "total_field_mappings": sum(len(t.field_mappings) for t in templates)
        }

    def _count_by_field(self, templates: List[SavedRequestTemplate], field: str) -> Dict[str, int]:
        """Count templates by field value"""
        counts = {}
        for template in templates:
            value = getattr(template, field, None)
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts

    def _count_by_tags(self, templates: List[SavedRequestTemplate]) -> Dict[str, int]:
        """Count templates by tag"""
        counts = {}
        for template in templates:
            for tag in template.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts
