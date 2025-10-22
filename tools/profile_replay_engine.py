#!/usr/bin/env python3
"""
Profile-Based Replay Engine - Execute recordings with profile data substitution
"""
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from seleniumbase import SB
from tools.training_logger import TrainingLogger
from tools.recording_manager import RecordingManager

class ProfileReplayEngine:
    """Execute recorded form interactions with profile data substitution"""

    def __init__(self, use_stealth: bool = True, headless: bool = False):
        self.use_stealth = use_stealth
        self.headless = headless
        self.sb = None
        self.logger = None
        self.recording_manager = RecordingManager()

        # Progress callback for real-time updates
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        # Replay statistics
        self.replay_stats = {
            "start_time": None,
            "end_time": None,
            "total_fields": 0,
            "successful_fields": 0,
            "failed_fields": 0,
            "errors": [],
            "execution_times": []
        }

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def _send_progress_update(self, status: str, message: str, progress: float = 0, field_data: Dict = None):
        """Send progress update to callback if available"""
        if self.progress_callback:
            update = {
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                "field_data": field_data or {},
                "stats": self.replay_stats.copy()
            }
            self.progress_callback(update)

    def start_browser(self, url: str) -> bool:
        """Initialize SeleniumBase with CDP mode"""
        try:
            self._send_progress_update("initializing", "Starting browser...")

            # Initialize SeleniumBase with optimized settings
            self.sb = SB(
                uc=self.use_stealth,  # Undetected Chrome mode
                headed=not self.headless,  # Show browser window
                incognito=True,  # Use incognito mode
                block_images=False,  # Load images (more human-like)
                do_not_track=True,  # Enable do not track
                disable_gpu=False  # Keep GPU for performance
            )

            self.sb.__enter__()

            # Navigate to URL
            self._send_progress_update("navigating", f"Navigating to {url}...")

            if self.use_stealth:
                # Activate CDP mode for maximum stealth
                self.sb.activate_cdp_mode(url)
            else:
                self.sb.open(url)

            # Wait for page to fully load
            time.sleep(3)

            self._send_progress_update("ready", "Browser ready for form filling")
            return True

        except Exception as e:
            self._send_progress_update("error", f"Error starting browser: {e}")
            return False

    def load_profile(self, profile_path: str) -> Dict[str, Any]:
        """Load profile data from JSON file"""
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)

            self._send_progress_update("profile_loaded", f"Profile loaded: {profile_data.get('profileName', 'Unknown')}")
            return profile_data

        except Exception as e:
            raise Exception(f"Failed to load profile: {e}")

    def replay_recording(self, recording_id: str, profile_data: Dict[str, Any],
                        session_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Replay a recording with profile data substitution

        Args:
            recording_id: ID of the recording to replay
            profile_data: Profile data to use for field values
            session_name: Optional name for the replay session

        Returns:
            Dict containing replay results and statistics
        """
        try:
            # Initialize stats
            self.replay_stats = {
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "recording_id": recording_id,
                "profile_name": profile_data.get("profileName", "Unknown"),
                "session_name": session_name or f"replay_{int(time.time())}",
                "total_fields": 0,
                "successful_fields": 0,
                "failed_fields": 0,
                "errors": [],
                "execution_times": [],
                "field_results": []
            }

            # Load recording
            recording = self.recording_manager.get_recording(recording_id)
            if not recording:
                raise Exception(f"Recording not found: {recording_id}")

            self._send_progress_update("loading", f"Loaded recording: {recording['recording_name']}")

            # Initialize training logger
            self.logger = TrainingLogger(self.replay_stats["session_name"])

            # Start browser and navigate to URL
            if not self.start_browser(recording["url"]):
                raise Exception("Failed to start browser")

            # Get field mappings
            field_mappings = recording.get("field_mappings", [])
            self.replay_stats["total_fields"] = len(field_mappings)

            if not field_mappings:
                raise Exception("No field mappings found in recording")

            self._send_progress_update("starting", f"Starting form fill with {len(field_mappings)} fields")

            # Execute field fills
            for i, field_mapping in enumerate(field_mappings):
                progress = (i / len(field_mappings)) * 100
                field_result = self._fill_field(field_mapping, profile_data, progress)
                self.replay_stats["field_results"].append(field_result)

                if field_result["success"]:
                    self.replay_stats["successful_fields"] += 1
                else:
                    self.replay_stats["failed_fields"] += 1
                    self.replay_stats["errors"].append(field_result["error"])

                # Small delay between fields for human-like behavior
                time.sleep(0.3)

            # Take final screenshot
            self._take_screenshot(f"final_result_{self.replay_stats['session_name']}")

            # Finalize stats
            self.replay_stats["end_time"] = datetime.now().isoformat()
            success_rate = (self.replay_stats["successful_fields"] / max(self.replay_stats["total_fields"], 1)) * 100
            self.replay_stats["success_rate"] = f"{success_rate:.1f}%"

            # Update recording success rate
            self.recording_manager.update_recording_metadata(recording_id, {
                "success_rate": self.replay_stats["success_rate"],
                "last_replay": datetime.now().isoformat()
            })

            self._send_progress_update("completed",
                f"Replay completed: {self.replay_stats['successful_fields']}/{self.replay_stats['total_fields']} fields successful",
                100)

            return self.replay_stats

        except Exception as e:
            error_msg = f"Replay failed: {e}"
            self.replay_stats["errors"].append(error_msg)
            self.replay_stats["end_time"] = datetime.now().isoformat()

            self._send_progress_update("error", error_msg)

            return self.replay_stats

        finally:
            self.close_browser()

    def _fill_field(self, field_mapping: Dict[str, Any], profile_data: Dict[str, Any], progress: float) -> Dict[str, Any]:
        """Fill a single field using profile data"""
        start_time = time.time()
        field_name = field_mapping.get("field_name", "Unknown Field")
        selector = field_mapping.get("field_selector", "")
        field_type = field_mapping.get("field_type", "textbox")
        profile_mapping = field_mapping.get("profile_mapping", "")

        field_result = {
            "field_name": field_name,
            "selector": selector,
            "field_type": field_type,
            "profile_mapping": profile_mapping,
            "value_used": "",
            "success": False,
            "error": None,
            "execution_time_ms": 0
        }

        try:
            # Get value from profile data
            value = self._get_profile_value(profile_data, profile_mapping, field_mapping)
            field_result["value_used"] = value

            self._send_progress_update("filling", f"Filling {field_name}: {value}", progress, field_result)

            # Fill the field based on type
            if field_type in ["textbox", "textarea"]:
                success = self._fill_text_field(selector, value, field_name)
            elif field_type == "select":
                success = self._fill_select_field(selector, value, field_name)
            elif field_type == "checkbox":
                success = self._fill_checkbox_field(selector, value, field_name)
            elif field_type == "radio":
                success = self._fill_radio_field(selector, value, field_name)
            else:
                # Default to text field
                success = self._fill_text_field(selector, value, field_name)

            field_result["success"] = success
            execution_time = (time.time() - start_time) * 1000
            field_result["execution_time_ms"] = execution_time

            if success:
                # Log successful interaction
                self.logger.log_successful_fill(
                    url=self.sb.get_current_url() if self.sb else "unknown",
                    selector=selector,
                    field_type=field_type,
                    value=value,
                    method="profile_replay",
                    time_ms=execution_time,
                    auto_detected=True,
                    confidence=field_mapping.get("confidence", 1.0)
                )
            else:
                field_result["error"] = f"Failed to fill field {field_name}"

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            field_result["execution_time_ms"] = execution_time
            field_result["error"] = str(e)

            # Log failed interaction
            if self.logger:
                self.logger.log_failed_fill(
                    url=self.sb.get_current_url() if self.sb else "unknown",
                    selector=selector,
                    field_type=field_type,
                    error_msg=str(e),
                    method="profile_replay",
                    time_ms=execution_time
                )

        self.replay_stats["execution_times"].append(field_result["execution_time_ms"])
        return field_result

    def _get_profile_value(self, profile_data: Dict[str, Any], profile_mapping: str, field_mapping: Dict[str, Any]) -> str:
        """Get the appropriate value from profile data"""
        # Handle nested profile data structures
        if "data" in profile_data and isinstance(profile_data["data"], dict):
            # Handle business-profile.json format
            profile_values = profile_data["data"]
        else:
            # Handle direct profile format (chris.json, etc.)
            profile_values = profile_data

        # Get value from profile
        value = profile_values.get(profile_mapping, "")

        # If no value in profile, use sample value
        if not value:
            value = field_mapping.get("sample_value", "")

        # If still no value, generate default
        if not value:
            value = self._generate_default_value(profile_mapping, field_mapping.get("field_type", "textbox"))

        return str(value)

    def _generate_default_value(self, profile_mapping: str, field_type: str) -> str:
        """Generate default values for missing profile data"""
        defaults = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "(555) 123-4567",
            "company": "Example Corp",
            "address1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "USA"
        }

        return defaults.get(profile_mapping, "Default Value")

    def _fill_text_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a text field using CDP mode"""
        try:
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                if self.sb.cdp.is_element_present(selector):
                    self.sb.cdp.click(selector)
                    time.sleep(0.2)
                    self.sb.cdp.clear_input(selector)
                    time.sleep(0.1)
                    self.sb.cdp.type(selector, value)
                    return True
                else:
                    # Try fallback selector strategies
                    return self._try_fallback_selectors(selector, value, "text")
            else:
                # Standard Selenium fallback
                element = self.sb.find_element(selector)
                element.clear()
                element.send_keys(value)
                return True

        except Exception as e:
            print(f"Error filling text field {field_name}: {e}")
            return False

    def _fill_select_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a select dropdown field"""
        try:
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                if self.sb.cdp.is_element_present(selector):
                    self.sb.cdp.click(selector)
                    time.sleep(0.5)
                    self.sb.cdp.select_option_by_text(selector, value)
                    return True
                else:
                    return self._try_fallback_selectors(selector, value, "select")
            else:
                self.sb.select_option_by_text(selector, value)
                return True

        except Exception as e:
            print(f"Error filling select field {field_name}: {e}")
            return False

    def _fill_checkbox_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a checkbox field"""
        try:
            should_check = value.lower() in ['true', '1', 'yes', 'on', 'checked']

            if self.use_stealth and hasattr(self.sb, 'cdp'):
                if self.sb.cdp.is_element_present(selector):
                    # Check current state and click if needed
                    is_checked = self.sb.cdp.is_element_checked(selector) if hasattr(self.sb.cdp, 'is_element_checked') else False

                    if should_check and not is_checked:
                        self.sb.cdp.click(selector)
                    elif not should_check and is_checked:
                        self.sb.cdp.click(selector)

                    return True
            else:
                element = self.sb.find_element(selector)
                if should_check and not element.is_selected():
                    element.click()
                elif not should_check and element.is_selected():
                    element.click()
                return True

        except Exception as e:
            print(f"Error filling checkbox field {field_name}: {e}")
            return False

    def _fill_radio_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a radio button field"""
        try:
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                if self.sb.cdp.is_element_present(selector):
                    self.sb.cdp.click(selector)
                    return True
            else:
                element = self.sb.find_element(selector)
                element.click()
                return True

        except Exception as e:
            print(f"Error filling radio field {field_name}: {e}")
            return False

    def _try_fallback_selectors(self, original_selector: str, value: str, field_type: str) -> bool:
        """Try alternative selectors if the original fails"""
        # Generate fallback selectors
        fallback_selectors = self._generate_fallback_selectors(original_selector)

        for fallback_selector in fallback_selectors:
            try:
                if self.use_stealth and hasattr(self.sb, 'cdp'):
                    if self.sb.cdp.is_element_present(fallback_selector):
                        if field_type == "text":
                            self.sb.cdp.click(fallback_selector)
                            time.sleep(0.1)
                            self.sb.cdp.clear_input(fallback_selector)
                            self.sb.cdp.type(fallback_selector, value)
                        elif field_type == "select":
                            self.sb.cdp.click(fallback_selector)
                            time.sleep(0.3)
                            self.sb.cdp.select_option_by_text(fallback_selector, value)

                        return True
                else:
                    element = self.sb.find_element(fallback_selector)
                    if field_type == "text":
                        element.clear()
                        element.send_keys(value)
                    elif field_type == "select":
                        self.sb.select_option_by_text(fallback_selector, value)

                    return True

            except Exception:
                continue

        return False

    def _generate_fallback_selectors(self, original_selector: str) -> List[str]:
        """Generate alternative selectors based on the original"""
        fallbacks = []

        # Extract name attribute if present
        import re
        name_match = re.search(r'\[name=["\']([^"\']+)["\']', original_selector)
        if name_match:
            name = name_match.group(1)
            fallbacks.extend([
                f"input[name='{name}']",
                f"select[name='{name}']",
                f"textarea[name='{name}']",
                f"[name='{name}']"
            ])

        # Extract ID if present
        id_match = re.search(r'#([a-zA-Z0-9_-]+)', original_selector)
        if id_match:
            element_id = id_match.group(1)
            fallbacks.extend([
                f"#{element_id}",
                f"input#{element_id}",
                f"select#{element_id}"
            ])

        return fallbacks

    def _take_screenshot(self, filename: str):
        """Take a screenshot for documentation"""
        try:
            screenshot_dir = Path("training_data")
            screenshot_dir.mkdir(exist_ok=True)

            screenshot_path = screenshot_dir / f"{filename}.png"
            self.sb.save_screenshot(str(screenshot_path))

            self._send_progress_update("screenshot", f"Screenshot saved: {screenshot_path}")

        except Exception as e:
            print(f"Warning: Could not save screenshot: {e}")

    def close_browser(self):
        """Close browser and save training data"""
        try:
            if self.sb:
                self.sb.__exit__(None, None, None)

            if self.logger:
                self.logger.save_training_data()

            self._send_progress_update("cleanup", "Browser closed and data saved")

        except Exception as e:
            print(f"Warning: Error closing browser: {e}")

    def replay_template(self, template_id: str, profile_data: Dict[str, Any],
                       session_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Replay a template with profile data

        Args:
            template_id: ID of the template to replay
            profile_data: Profile data to use
            session_name: Optional session name

        Returns:
            Replay results
        """
        # Load template
        template = self.recording_manager.get_template(template_id)
        if not template:
            raise Exception(f"Template not found: {template_id}")

        # Create temporary recording from template
        temp_recording = {
            "recording_id": f"temp_{template_id}_{int(time.time())}",
            "recording_name": template["template_name"],
            "url": template["url"],
            "field_mappings": template["field_mappings"],
            "description": f"Template replay: {template['template_name']}"
        }

        # Save temporary recording
        temp_recording_id = self.recording_manager.save_recording(temp_recording)

        try:
            # Replay the temporary recording
            return self.replay_recording(temp_recording_id, profile_data, session_name)
        finally:
            # Clean up temporary recording
            self.recording_manager.delete_recording(temp_recording_id)

def main():
    """Test the Profile Replay Engine"""
    engine = ProfileReplayEngine(use_stealth=True, headless=False)

    # Test profile data
    test_profile = {
        "profileName": "test",
        "firstName": "John",
        "lastName": "Smith",
        "email": "john.smith@test.com",
        "phone": "(555) 123-4567"
    }

    # Set up progress callback
    def progress_callback(update):
        print(f"[{update['status'].upper()}] {update['message']} ({update['progress']:.1f}%)")

    engine.set_progress_callback(progress_callback)

    print("Profile Replay Engine test - Manual testing required")
    print("Use with actual recording IDs and profile data")

if __name__ == "__main__":
    main()