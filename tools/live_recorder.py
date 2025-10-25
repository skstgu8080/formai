#!/usr/bin/env python3
"""
Live Recording Session Manager
Manages real-time recording sessions with Chrome DevTools MCP integration
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse


class LiveRecorder:
    """Manages live recording sessions with Chrome DevTools MCP"""

    def __init__(self, recordings_dir: str = "recordings"):
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(exist_ok=True)

        # Active session state
        self.session_id = None
        self.is_recording = False
        self.start_url = None
        self.recorded_steps = []
        self.session_start_time = None
        self.detected_fields = {}

        # Field type patterns for smart detection
        self.field_patterns = {
            'firstName': ['first_name', 'fname', 'firstname', 'given_name', 'first-name', 'first name'],
            'lastName': ['last_name', 'lname', 'lastname', 'family_name', 'last-name', 'last name'],
            'email': ['email', 'e_mail', 'e-mail', 'email_address', 'emailaddress'],
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone_number'],
            'password': ['password', 'pass', 'pwd', 'passphrase'],
            'address': ['address', 'address1', 'street', 'address_line_1', 'street_address'],
            'city': ['city', 'town', 'locality'],
            'state': ['state', 'province', 'region'],
            'zip': ['zip', 'postal', 'postcode', 'postal_code', 'zipcode'],
            'country': ['country', 'nation'],
        }

    def start_session(self, url: str, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new live recording session

        Args:
            url: Starting URL to navigate to and record
            profile_id: Optional profile ID for testing with specific data

        Returns:
            Dict with session info
        """
        try:
            if self.is_recording:
                raise Exception("Recording session already active. Stop current session first.")

            self.session_id = str(uuid.uuid4())[:12]
            self.start_url = url
            self.recorded_steps = []
            self.detected_fields = {}
            self.is_recording = True
            self.session_start_time = datetime.now()

            # Add initial navigation step
            self._add_step({
                "type": "navigate",
                "url": url,
                "assertedEvents": [{
                    "type": "navigation",
                    "url": url,
                    "title": ""
                }]
            })

            return {
                "session_id": self.session_id,
                "status": "recording",
                "start_url": url,
                "start_time": self.session_start_time.isoformat(),
                "steps_recorded": 0,
                "message": "Recording started. Interact with the page via Chrome DevTools."
            }

        except Exception as e:
            raise Exception(f"Failed to start recording session: {e}")

    def record_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record an action performed via Chrome DevTools MCP

        Args:
            action_data: Action data with type and parameters
            {
                "type": "fill",  # or "click", "navigate", etc.
                "element": "First Name",
                "uid": "1_36",
                "value": "John",  # for fill actions
                "field_type": "textbox"
            }

        Returns:
            Dict with recording status
        """
        if not self.is_recording:
            raise Exception("No active recording session")

        action_type = action_data.get("type")

        # Convert Chrome DevTools action to recording format
        if action_type == "fill":
            step = self._create_fill_step(action_data)
            field_info = self._detect_field_type(action_data)
            if field_info:
                self.detected_fields[field_info['profile_field']] = field_info

        elif action_type == "click":
            step = self._create_click_step(action_data)

        elif action_type == "navigate":
            step = self._create_navigate_step(action_data)

        else:
            # Generic step for other actions
            step = action_data

        self._add_step(step)

        return {
            "session_id": self.session_id,
            "steps_recorded": len(self.recorded_steps),
            "last_action": action_type,
            "detected_fields": len(self.detected_fields)
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current recording session status"""
        if not self.is_recording:
            return {
                "status": "stopped",
                "session_id": None,
                "message": "No active recording session"
            }

        duration = (datetime.now() - self.session_start_time).total_seconds()

        return {
            "session_id": self.session_id,
            "status": "recording",
            "start_url": self.start_url,
            "start_time": self.session_start_time.isoformat(),
            "duration_seconds": int(duration),
            "steps_recorded": len(self.recorded_steps),
            "detected_fields": list(self.detected_fields.keys()),
            "field_count": len(self.detected_fields),
            "recent_steps": self._get_recent_steps(5)
        }

    def stop_session(self, recording_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop recording and save the session

        Args:
            recording_name: Optional custom name for the recording

        Returns:
            Dict with recording metadata and file path
        """
        try:
            if not self.is_recording:
                raise Exception("No active recording session")

            self.is_recording = False

            # Generate recording name if not provided
            if not recording_name:
                domain = urlparse(self.start_url).netloc or "unknown"
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                recording_name = f"Live Recording - {domain} - {timestamp}"

            # Generate field_mappings from recorded steps for replay compatibility
            field_mappings = []
            for step_index, step in enumerate(self.recorded_steps):
                if step.get("type") == "change" and "field_mapping" in step:
                    field_mapping_info = step["field_mapping"]
                    field_mappings.append({
                        "field_name": field_mapping_info["form_field"],
                        "field_selector": step.get("selectors", [[]])[0][0] if step.get("selectors") else "",
                        "field_type": field_mapping_info["field_type"],
                        "profile_mapping": field_mapping_info["profile_field"],
                        "sample_value": step.get("value", ""),
                        "step_index": step_index,
                        "original_step": step,
                        "confidence": 0.95
                    })

            # Create recording in FormAI format
            recording_data = {
                "recording_id": self.session_id,
                "recording_name": recording_name,
                "title": recording_name,
                "url": self.start_url,
                "created_at": datetime.now().isoformat(),
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "source": "chrome-devtools-live",
                "import_source": "chrome_devtools_live",
                "session_id": self.session_id,
                "steps": self.recorded_steps,
                "field_count": len(self.detected_fields),
                "total_fields_filled": len(field_mappings),
                "field_mappings": field_mappings,
                "detected_fields": self.detected_fields,
                "duration_seconds": int((datetime.now() - self.session_start_time).total_seconds()),
                "description": f"Live recording - {len(self.detected_fields)} fields detected",
                "notes": "Recorded via Chrome DevTools MCP live recording",
                "tags": ["live-recording", "chrome-devtools"]
            }

            # Save recording
            recording_file = self.recordings_dir / f"{self.session_id}.json"

            with open(recording_file, 'w', encoding='utf-8') as f:
                json.dump(recording_data, f, indent=2)

            result = {
                "recording_id": self.session_id,
                "recording_name": recording_name,
                "file_path": str(recording_file),
                "total_steps": len(self.recorded_steps),
                "detected_fields": len(self.detected_fields),
                "field_list": list(self.detected_fields.keys()),
                "start_url": self.start_url,
                "recording_data": recording_data
            }

            # Reset session
            self._reset_session()

            return result

        except Exception as e:
            raise Exception(f"Failed to stop recording session: {e}")

    def cancel_session(self) -> Dict[str, Any]:
        """Cancel recording without saving"""
        if not self.is_recording:
            return {"message": "No active recording session"}

        steps_count = len(self.recorded_steps)
        self._reset_session()

        return {
            "message": "Recording cancelled",
            "steps_discarded": steps_count
        }

    # Private helper methods

    def _add_step(self, step: Dict[str, Any]) -> None:
        """Add a step to the recording"""
        self.recorded_steps.append(step)

    def _reset_session(self) -> None:
        """Reset session state"""
        self.session_id = None
        self.is_recording = False
        self.start_url = None
        self.recorded_steps = []
        self.detected_fields = {}
        self.session_start_time = None

    def _create_fill_step(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fill/change step from Chrome DevTools action"""
        element_name = action_data.get("element", "unknown")
        value = action_data.get("value", "")
        uid = action_data.get("uid", "")

        # Detect profile field mapping
        profile_field = self._detect_profile_field(element_name)

        step = {
            "type": "change",
            "target": profile_field or element_name.lower().replace(" ", ""),
            "value": value,
            "selectors": [
                [f"aria/{element_name}"],
                [uid]
            ]
        }

        if profile_field:
            step["field_mapping"] = {
                "profile_field": profile_field,
                "form_field": element_name,
                "field_type": action_data.get("field_type", "textbox")
            }

        return step

    def _create_click_step(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a click step from Chrome DevTools action"""
        return {
            "type": "click",
            "target": action_data.get("element", "unknown"),
            "selectors": [
                [f"aria/{action_data.get('element')}"],
                [action_data.get("uid", "")]
            ]
        }

    def _create_navigate_step(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a navigation step"""
        url = action_data.get("url", "")
        return {
            "type": "navigate",
            "url": url,
            "assertedEvents": [{
                "type": "navigation",
                "url": url,
                "title": action_data.get("title", "")
            }]
        }

    def _detect_profile_field(self, element_name: str) -> Optional[str]:
        """Detect which profile field this form field maps to"""
        element_lower = element_name.lower().replace(" ", "").replace("_", "").replace("-", "")

        for profile_field, patterns in self.field_patterns.items():
            for pattern in patterns:
                pattern_clean = pattern.replace("_", "").replace("-", "").replace(" ", "")
                if pattern_clean in element_lower:
                    return profile_field

        return None

    def _detect_field_type(self, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect field type and mapping info"""
        element_name = action_data.get("element", "")
        profile_field = self._detect_profile_field(element_name)

        if not profile_field:
            return None

        return {
            "profile_field": profile_field,
            "form_field": element_name,
            "field_type": action_data.get("field_type", "textbox"),
            "found": True,
            "confidence": "high",
            "element_type": action_data.get("field_type", "textbox")
        }

    def _get_recent_steps(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most recent steps for status display"""
        recent = self.recorded_steps[-count:] if len(self.recorded_steps) > count else self.recorded_steps

        # Simplify steps for display
        display_steps = []
        for step in recent:
            step_type = step.get("type")
            if step_type == "change":
                display_steps.append({
                    "type": "fill",
                    "field": step.get("field_mapping", {}).get("form_field") or step.get("target"),
                    "value": step.get("value", "")[:20] + "..." if len(step.get("value", "")) > 20 else step.get("value", "")
                })
            elif step_type == "click":
                display_steps.append({
                    "type": "click",
                    "element": step.get("target", "unknown")
                })
            elif step_type == "navigate":
                display_steps.append({
                    "type": "navigate",
                    "url": step.get("url", "")
                })

        return display_steps
