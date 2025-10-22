#!/usr/bin/env python3
"""
Recording Manager - Manage recording storage, retrieval, and metadata
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib
from tools.chrome_recorder_parser import ChromeRecorderParser

class RecordingManager:
    """Manages recording storage, metadata, and operations"""

    def __init__(self, recordings_dir: str = "recordings"):
        self.recordings_dir = Path(recordings_dir)
        self.recordings_index_file = self.recordings_dir / "recordings_index.json"
        self.templates_dir = self.recordings_dir / "templates"
        self.imports_dir = self.recordings_dir / "imports"

        # Ensure directories exist
        self.recordings_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.imports_dir.mkdir(exist_ok=True)

        self.chrome_parser = ChromeRecorderParser()
        self._initialize_index()

    def _initialize_index(self):
        """Initialize the recordings index file if it doesn't exist"""
        if not self.recordings_index_file.exists():
            self._save_index({
                "recordings": {},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_recordings": 0,
                    "version": "1.0"
                }
            })

    def _load_index(self) -> Dict[str, Any]:
        """Load the recordings index"""
        try:
            with open(self.recordings_index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # Return empty index if file is corrupted
            return {
                "recordings": {},
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_recordings": 0,
                    "version": "1.0"
                }
            }

    def _save_index(self, index_data: Dict[str, Any]):
        """Save the recordings index"""
        index_data["metadata"]["last_updated"] = datetime.now().isoformat()
        index_data["metadata"]["total_recordings"] = len(index_data["recordings"])

        with open(self.recordings_index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def import_chrome_recording(self, chrome_recording_path: str, recording_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Import a Chrome DevTools Recorder JSON file

        Args:
            chrome_recording_path: Path to Chrome Recorder JSON file
            recording_name: Optional custom name for the recording

        Returns:
            Dict containing the imported recording metadata
        """
        try:
            # Parse the Chrome recording
            formai_recording = self.chrome_parser.parse_chrome_recording(chrome_recording_path)

            # Override name if provided
            if recording_name:
                formai_recording["recording_name"] = recording_name

            # Save the recording
            recording_id = self.save_recording(formai_recording)

            # Copy original file to imports directory for reference
            original_filename = Path(chrome_recording_path).name
            import_path = self.imports_dir / f"{recording_id}_{original_filename}"
            shutil.copy2(chrome_recording_path, import_path)

            formai_recording["original_chrome_file"] = str(import_path)

            return formai_recording

        except Exception as e:
            raise Exception(f"Failed to import Chrome recording: {e}")

    def import_chrome_recording_data(self, chrome_data: Dict[str, Any], recording_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Import Chrome DevTools Recorder JSON data directly

        Args:
            chrome_data: Chrome Recorder JSON data as dict
            recording_name: Optional custom name for the recording

        Returns:
            Dict containing the imported recording metadata
        """
        try:
            # Validate the Chrome recording data
            is_valid, errors = self.chrome_parser.validate_chrome_recording(chrome_data)
            if not is_valid:
                raise Exception(f"Invalid Chrome recording data: {'; '.join(errors)}")

            # Parse the Chrome recording
            formai_recording = self.chrome_parser.parse_chrome_recording_data(chrome_data)

            # Override name if provided
            if recording_name:
                formai_recording["recording_name"] = recording_name

            # Save the recording
            recording_id = self.save_recording(formai_recording)

            # Save original Chrome data for reference
            chrome_file_path = self.imports_dir / f"{recording_id}_chrome_data.json"
            with open(chrome_file_path, 'w', encoding='utf-8') as f:
                json.dump(chrome_data, f, indent=2)

            formai_recording["original_chrome_file"] = str(chrome_file_path)

            return formai_recording

        except Exception as e:
            raise Exception(f"Failed to import Chrome recording data: {e}")

    def save_recording(self, recording_data: Dict[str, Any]) -> str:
        """
        Save a recording to the recordings directory

        Args:
            recording_data: Recording data in FormAI format

        Returns:
            Recording ID
        """
        try:
            recording_id = recording_data.get("recording_id")
            if not recording_id:
                recording_id = self._generate_recording_id(
                    recording_data.get("recording_name", "Recording"),
                    recording_data.get("url", "")
                )
                recording_data["recording_id"] = recording_id

            # Save recording file
            recording_file = self.recordings_dir / f"{recording_id}.json"
            with open(recording_file, 'w', encoding='utf-8') as f:
                json.dump(recording_data, f, indent=2, ensure_ascii=False)

            # Update index
            index = self._load_index()
            index["recordings"][recording_id] = {
                "recording_id": recording_id,
                "recording_name": recording_data.get("recording_name", "Unnamed Recording"),
                "url": recording_data.get("url", ""),
                "created_date": recording_data.get("created_date", datetime.now().strftime("%Y-%m-%d")),
                "created_timestamp": recording_data.get("created_timestamp", datetime.now().isoformat()),
                "total_fields": recording_data.get("total_fields_filled", 0),
                "import_source": recording_data.get("import_source", "manual"),
                "file_path": str(recording_file),
                "success_rate": recording_data.get("success_rate", "pending"),
                "description": recording_data.get("description", ""),
                "tags": recording_data.get("tags", [])
            }

            self._save_index(index)

            return recording_id

        except Exception as e:
            raise Exception(f"Failed to save recording: {e}")

    def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a recording by ID

        Args:
            recording_id: Recording ID

        Returns:
            Recording data or None if not found
        """
        try:
            recording_file = self.recordings_dir / f"{recording_id}.json"
            if not recording_file.exists():
                return None

            with open(recording_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception:
            return None

    def list_recordings(self, tags: Optional[List[str]] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all recordings with optional filtering

        Args:
            tags: Filter by tags
            source: Filter by import source

        Returns:
            List of recording metadata
        """
        index = self._load_index()
        recordings = list(index["recordings"].values())

        # Filter by tags
        if tags:
            recordings = [r for r in recordings if any(tag in r.get("tags", []) for tag in tags)]

        # Filter by source
        if source:
            recordings = [r for r in recordings if r.get("import_source") == source]

        # Sort by creation date (newest first)
        recordings.sort(key=lambda x: x.get("created_timestamp", ""), reverse=True)

        return recordings

    def delete_recording(self, recording_id: str) -> bool:
        """
        Delete a recording

        Args:
            recording_id: Recording ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Remove from index
            index = self._load_index()
            if recording_id not in index["recordings"]:
                return False

            del index["recordings"][recording_id]
            self._save_index(index)

            # Delete recording file
            recording_file = self.recordings_dir / f"{recording_id}.json"
            if recording_file.exists():
                recording_file.unlink()

            # Delete any associated import files
            for file_path in self.imports_dir.glob(f"{recording_id}_*"):
                file_path.unlink()

            return True

        except Exception:
            return False

    def update_recording_metadata(self, recording_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update recording metadata

        Args:
            recording_id: Recording ID
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            recording = self.get_recording(recording_id)
            if not recording:
                return False

            # Update recording data
            recording.update(updates)
            recording["last_modified"] = datetime.now().isoformat()

            # Save updated recording
            self.save_recording(recording)

            return True

        except Exception:
            return False

    def create_template(self, recording_id: str, template_name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a reusable template from a recording

        Args:
            recording_id: Source recording ID
            template_name: Name for the template
            description: Template description

        Returns:
            Template metadata
        """
        try:
            recording = self.get_recording(recording_id)
            if not recording:
                raise Exception("Recording not found")

            # Create template data
            template_data = {
                "template_id": self._generate_recording_id(template_name, recording.get("url", "")),
                "template_name": template_name,
                "description": description or f"Template created from {recording.get('recording_name', 'recording')}",
                "source_recording_id": recording_id,
                "url": recording.get("url", ""),
                "field_mappings": recording.get("field_mappings", []),
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "created_timestamp": datetime.now().isoformat(),
                "type": "template",
                "automation_method": recording.get("automation_method", "seleniumbase_cdp"),
                "total_fields": len(recording.get("field_mappings", []))
            }

            # Save template
            template_file = self.templates_dir / f"{template_data['template_id']}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)

            return template_data

        except Exception as e:
            raise Exception(f"Failed to create template: {e}")

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        templates = []

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    templates.append(template_data)
            except Exception:
                continue

        # Sort by creation date (newest first)
        templates.sort(key=lambda x: x.get("created_timestamp", ""), reverse=True)

        return templates

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID"""
        try:
            template_file = self.templates_dir / f"{template_id}.json"
            if not template_file.exists():
                return None

            with open(template_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception:
            return None

    def get_recording_stats(self) -> Dict[str, Any]:
        """Get recording statistics"""
        index = self._load_index()
        recordings = list(index["recordings"].values())
        templates = self.list_templates()

        # Calculate statistics
        total_recordings = len(recordings)
        total_templates = len(templates)

        # Group by source
        source_counts = {}
        for recording in recordings:
            source = recording.get("import_source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

        # Calculate total fields
        total_fields = sum(recording.get("total_fields", 0) for recording in recordings)

        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_recordings = [
            r for r in recordings
            if datetime.fromisoformat(r.get("created_timestamp", "1970-01-01T00:00:00"))
            > week_ago
        ]

        return {
            "total_recordings": total_recordings,
            "total_templates": total_templates,
            "total_fields_detected": total_fields,
            "source_breakdown": source_counts,
            "recent_recordings": len(recent_recordings),
            "average_fields_per_recording": total_fields / max(total_recordings, 1),
            "last_updated": index["metadata"]["last_updated"]
        }

    def _generate_recording_id(self, name: str, url: str) -> str:
        """Generate a unique recording ID"""
        content = f"{name}_{url}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def search_recordings(self, query: str) -> List[Dict[str, Any]]:
        """
        Search recordings by name, description, or URL

        Args:
            query: Search query

        Returns:
            List of matching recordings
        """
        index = self._load_index()
        recordings = list(index["recordings"].values())

        query_lower = query.lower()
        matches = []

        for recording in recordings:
            # Search in name, description, and URL
            searchable_text = " ".join([
                recording.get("recording_name", ""),
                recording.get("description", ""),
                recording.get("url", "")
            ]).lower()

            if query_lower in searchable_text:
                matches.append(recording)

        return matches

    def export_recording(self, recording_id: str, export_format: str = "json") -> str:
        """
        Export a recording to various formats

        Args:
            recording_id: Recording ID
            export_format: Export format (json, csv)

        Returns:
            Path to exported file
        """
        recording = self.get_recording(recording_id)
        if not recording:
            raise Exception("Recording not found")

        export_dir = self.recordings_dir / "exports"
        export_dir.mkdir(exist_ok=True)

        if export_format == "json":
            export_file = export_dir / f"{recording_id}_export.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(recording, f, indent=2, ensure_ascii=False)

        elif export_format == "csv":
            import csv
            export_file = export_dir / f"{recording_id}_fields.csv"

            with open(export_file, 'w', newline='', encoding='utf-8') as f:
                if recording.get("field_mappings"):
                    fieldnames = recording["field_mappings"][0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(recording["field_mappings"])

        else:
            raise Exception(f"Unsupported export format: {export_format}")

        return str(export_file)

def main():
    """Test the Recording Manager"""
    manager = RecordingManager()

    # Test with sample data
    sample_recording = {
        "recording_name": "Test Recording",
        "url": "https://example.com/form",
        "description": "Test recording for development",
        "field_mappings": [
            {
                "field_name": "First Name",
                "field_selector": "input[name='first_name']",
                "field_type": "textbox",
                "profile_mapping": "firstName",
                "sample_value": "John"
            }
        ]
    }

    # Save recording
    recording_id = manager.save_recording(sample_recording)
    print(f"Saved recording: {recording_id}")

    # List recordings
    recordings = manager.list_recordings()
    print(f"Total recordings: {len(recordings)}")

    # Get stats
    stats = manager.get_recording_stats()
    print(f"Stats: {stats}")

if __name__ == "__main__":
    main()