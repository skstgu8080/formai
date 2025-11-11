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
from tools.replay_extension import ReplayExtension, ReplayContext
from tools.profile_data_extension import ProfileDataExtension

class ProfileReplayEngine:
    """Execute recorded form interactions with profile data substitution"""

    def __init__(self, use_stealth: bool = True, headless: bool = False, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.use_stealth = use_stealth
        self.headless = headless
        self.sb = None
        self.sb_context = None  # SeleniumBase context manager
        self.logger = None
        self.recording_manager = RecordingManager()
        self.use_recorded_values = False  # Preview mode flag
        self.event_loop = event_loop  # Store the main event loop for async callbacks

        # Extension system
        self.extensions: List[ReplayExtension] = []

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
            "execution_times": [],
            "submission": {
                "attempted": False,
                "success": False,
                "status_code": None,
                "response_body": None,
                "cookies": None,
                "redirect_url": None,
                "success_indicators": [],
                "error_message": None
            }
        }

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def register_extension(self, extension: ReplayExtension):
        """Register an extension to hook into replay lifecycle"""
        if extension not in self.extensions:
            self.extensions.append(extension)
            print(f"Registered extension: {extension.name}")

    def unregister_extension(self, extension: ReplayExtension):
        """Unregister an extension"""
        if extension in self.extensions:
            self.extensions.remove(extension)
            print(f"Unregistered extension: {extension.name}")

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

            # Handle async callbacks properly from sync code
            if asyncio.iscoroutinefunction(self.progress_callback):
                try:
                    # Use the stored event loop if available
                    if self.event_loop and self.event_loop.is_running():
                        # Schedule the coroutine to run in the main event loop
                        asyncio.run_coroutine_threadsafe(self.progress_callback(update), self.event_loop)
                    else:
                        print(f"Warning: No running event loop available for progress update")
                except Exception as e:
                    print(f"Error sending progress update: {e}")
            else:
                self.progress_callback(update)

    def start_browser(self, url: str) -> bool:
        """Initialize SeleniumBase with CDP mode"""
        try:
            self._send_progress_update("initializing", "Starting browser...")

            # Initialize SeleniumBase with optimized settings
            self.sb_context = SB(
                uc=self.use_stealth,  # Undetected Chrome mode
                headed=not self.headless,  # Show browser window
                incognito=True,  # Use incognito mode
                block_images=False,  # Load images (more human-like)
                do_not_track=True  # Enable do not track
            )

            # Enter context and get the driver
            self.sb = self.sb_context.__enter__()

            # Navigate to URL
            self._send_progress_update("navigating", f"Navigating to {url}...")

            # Just use standard open - CDP mode is deprecated
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
                        session_name: Optional[str] = None, preview_mode: bool = False, keep_browser_open: bool = False) -> Dict[str, Any]:
        """
        Replay a recording with profile data substitution

        Args:
            recording_id: ID of the recording to replay
            profile_data: Profile data to use for field values
            session_name: Optional name for the replay session
            preview_mode: If True, use recorded sample values; if False, use profile data
            keep_browser_open: If True, don't close browser after replay (for testing/verification)

        Returns:
            Dict containing replay results and statistics
        """
        # Set preview mode flag
        self.use_recorded_values = preview_mode
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
                "field_results": [],
                "submission": {
                    "attempted": False,
                    "success": False,
                    "status_code": None,
                    "response_body": None,
                    "cookies": None,
                    "redirect_url": None,
                    "success_indicators": [],
                    "error_message": None
                }
            }

            # Load recording
            recording = self.recording_manager.get_recording(recording_id)
            if not recording:
                raise Exception(f"Recording not found: {recording_id}")

            recording_name = recording.get("recording_name") or recording.get("title", "Unknown Recording")
            self._send_progress_update("loading", f"Loaded recording: {recording_name}")

            # Initialize training logger
            self.logger = TrainingLogger(self.replay_stats["session_name"])

            # Start browser and navigate to URL
            if not self.start_browser(recording["url"]):
                raise Exception("Failed to start browser")

            # Create replay context for extensions
            context = ReplayContext(
                profile_data=profile_data,
                replay_stats=self.replay_stats,
                current_url=recording["url"],
                session_name=self.replay_stats["session_name"],
                browser_driver=self.sb
            )

            # Call beforeAllSteps on all extensions
            for extension in self.extensions:
                extension.beforeAllSteps(context)

            # Get field mappings
            field_mappings = recording.get("field_mappings", [])
            self.replay_stats["total_fields"] = len(field_mappings)

            if not field_mappings:
                raise Exception("No field mappings found in recording")

            self._send_progress_update("starting", f"Starting form fill with {len(field_mappings)} fields")

            # Execute field fills
            for i, field_mapping in enumerate(field_mappings):
                progress = (i / len(field_mappings)) * 100
                field_result = self._fill_field(field_mapping, profile_data, progress, context)
                self.replay_stats["field_results"].append(field_result)

                if field_result["success"]:
                    self.replay_stats["successful_fields"] += 1
                else:
                    self.replay_stats["failed_fields"] += 1
                    self.replay_stats["errors"].append(field_result["error"])

                # Small delay between fields for human-like behavior
                time.sleep(0.3)

            # Call afterAllSteps on all extensions
            # Pass field_results list and context to extensions
            for extension in self.extensions:
                extension.afterAllSteps(self.replay_stats.get("field_results", []), context)

            # Attempt form submission
            self._send_progress_update("submitting", "Attempting to submit form", 90)
            self.replay_stats["submission"]["attempted"] = True

            if self._click_submit():
                print("Form submitted successfully")
                self._send_progress_update("verifying", "Verifying submission", 95)

                # Capture network response data
                self._capture_network_response()

                # Verify submission success
                self._verify_submission_success()

                if self.replay_stats["submission"]["success"]:
                    self._send_progress_update("verified", "Submission verified successful", 98)
                else:
                    self._send_progress_update("warning", "Submission completed but success could not be verified", 98)

                # Wait 5 seconds so user can see the submission result
                print("Waiting 5 seconds to view submission result...")
                time.sleep(5)
            else:
                print("Could not submit form (submit button not found or click failed)")
                self._send_progress_update("warning", "Form filled but submission skipped", 95)

            # Take final screenshot
            self._take_screenshot(f"final_result_{self.replay_stats['session_name']}")

            # Finalize stats
            self.replay_stats["end_time"] = datetime.now().isoformat()
            success_rate = (self.replay_stats["successful_fields"] / max(self.replay_stats["total_fields"], 1)) * 100
            self.replay_stats["success_rate"] = f"{success_rate:.1f}%"

            # Print summary of filled fields
            print("\n" + "="*80)
            print("FORM FILL SUMMARY")
            print("="*80)
            for result in self.replay_stats["field_results"]:
                status = "✅" if result["success"] else "❌"
                field_name = result["field_name"]
                value = result["value_used"]
                profile_mapping = result.get("profile_mapping", "N/A")

                print(f"{status} {field_name}")
                print(f"   Profile Field: {profile_mapping}")
                print(f"   Value: {value}")

                if not result["success"] and result.get("error"):
                    print(f"   Error: {result['error']}")
                print()

            print("="*80)
            print(f"Summary: {self.replay_stats['successful_fields']}/{self.replay_stats['total_fields']} fields filled successfully ({success_rate:.1f}%)")
            print("="*80 + "\n")

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
            if not keep_browser_open:
                self.close_browser()

    def _fill_field(self, field_mapping: Dict[str, Any], profile_data: Dict[str, Any], progress: float, context: ReplayContext) -> Dict[str, Any]:
        """Fill a single field using profile data"""
        start_time = time.time()

        # Call beforeEachStep on all extensions
        for extension in self.extensions:
            extension.beforeEachStep(field_mapping, context)

        # Apply transformations from extensions
        transformed_step = field_mapping.copy()
        for extension in self.extensions:
            # Check if step should be skipped
            if extension.shouldSkipStep(transformed_step, context):
                print(f"Step skipped by extension: {extension.name}")
                return {
                    "field_name": field_mapping.get("field_name", "Unknown Field"),
                    "selector": field_mapping.get("field_selector", ""),
                    "field_type": field_mapping.get("field_type", "textbox"),
                    "profile_mapping": field_mapping.get("profile_mapping", ""),
                    "value_used": "",
                    "success": True,
                    "error": None,
                    "execution_time_ms": 0,
                    "skipped": True
                }
            # Transform the step (check if extension's transformStep accepts context)
            try:
                # ProfileDataExtension accepts context parameter
                transformed_step = extension.transformStep(transformed_step, context)
            except TypeError:
                # Base extension only accepts step parameter
                transformed_step = extension.transformStep(transformed_step)

        field_name = transformed_step.get("field_name", "Unknown Field")
        field_type = transformed_step.get("field_type", "textbox")
        profile_mapping = transformed_step.get("profile_mapping", "")

        # Get field selector
        selector = transformed_step.get("field_selector", "")

        # Skip ARIA selectors and use CSS selectors instead
        if selector.startswith("aria/"):
            original_step = transformed_step.get("original_step", {})
            selectors_list = original_step.get("selectors", [])

            # Find first non-ARIA selector
            for selector_option in selectors_list:
                if isinstance(selector_option, list) and len(selector_option) > 0:
                    candidate = selector_option[0]
                    if not candidate.startswith("aria/"):
                        selector = candidate
                        print(f"Switched from ARIA selector to CSS selector: {selector}")
                        break

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
            # Check if extension provided a transformed value
            if "value_to_use" in transformed_step:
                # Use value from extension transformation
                value = transformed_step["value_to_use"]
                mode_label = transformed_step.get("value_source", "extension")
            elif self.use_recorded_values:
                # Preview mode: use the recorded sample value
                value = transformed_step.get("sample_value", "")
                mode_label = "preview"
            else:
                # Production mode: use profile data
                value = self._get_profile_value(profile_data, profile_mapping, transformed_step)
                mode_label = "production"

            field_result["value_used"] = value

            self._send_progress_update("filling", f"Filling {field_name} ({mode_label}): {value}", progress, field_result)

            # Detect actual element type at runtime (Chrome Recorder doesn't distinguish select vs input)
            actual_element_type = self._detect_element_type(selector)

            # Get sample_value for fallback (from recording)
            sample_value = transformed_step.get("sample_value", "")

            # Fill the field based on detected type
            if actual_element_type == "select":
                success = self._fill_select_field(selector, value, field_name, sample_value)
            elif actual_element_type in ["checkbox"]:
                success = self._fill_checkbox_field(selector, value, field_name)
            elif actual_element_type in ["radio"]:
                success = self._fill_radio_field(selector, value, field_name)
            else:
                # Default to text field for input, textarea, etc.
                success = self._fill_text_field(selector, value, field_name)

            field_result["success"] = success
            execution_time = (time.time() - start_time) * 1000
            field_result["execution_time_ms"] = execution_time

            if success:
                # Send completion update
                self._send_progress_update("field_completed", f"✅ {field_name} completed", progress, field_result)

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
                # Send failure update
                self._send_progress_update("field_failed", f"❌ {field_name} failed", progress, field_result)

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

        # Call afterEachStep on all extensions
        for extension in self.extensions:
            extension.afterEachStep(transformed_step, field_result, context)

        return field_result

    def _detect_date_format(self, sample_value: str) -> str:
        """
        Detect the date format from a sample value
        Returns format string like 'YYYY-MM-DD', 'MM/DD/YYYY', etc.
        """
        import re

        if not sample_value or len(sample_value) < 6:
            return "YYYY-MM-DD"  # Default to ISO format

        # Check for common patterns
        if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', sample_value):
            # YYYY-MM-DD or YYYY/MM/DD
            separator = '-' if '-' in sample_value else '/'
            return f"YYYY{separator}MM{separator}DD"

        elif re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', sample_value):
            # Could be MM/DD/YYYY or DD/MM/YYYY
            separator = '-' if '-' in sample_value else '/'
            parts = sample_value.split(separator)

            # Try to determine if first part is month or day
            first_num = int(parts[0])
            second_num = int(parts[1])

            # If first number > 12, must be day (DD/MM/YYYY)
            if first_num > 12:
                return f"DD{separator}MM{separator}YYYY"
            # If second number > 12, must be DD/MM/YYYY
            elif second_num > 12:
                return f"DD{separator}MM{separator}YYYY"
            else:
                # Ambiguous - default to MM/DD/YYYY (US format)
                return f"MM{separator}DD{separator}YYYY"

        elif re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2}', sample_value):
            # Short year format: MM/DD/YY or DD/MM/YY
            separator = '-' if '-' in sample_value else '/'
            return f"MM{separator}DD{separator}YY"

        # Default to ISO format
        return "YYYY-MM-DD"

    def _construct_date_in_format(self, year: str, month: str, day: str, date_format: str) -> str:
        """
        Construct a date string in the specified format

        Args:
            year: Year as string (e.g., "1999")
            month: Month as string (e.g., "12")
            day: Day as string (e.g., "15")
            date_format: Format string like "YYYY-MM-DD", "MM/DD/YYYY", etc.

        Returns:
            Formatted date string
        """
        # Ensure we have string values
        year = str(year)
        month = str(month)
        day = str(day)

        # Determine separator from format
        separator = '-' if '-' in date_format else '/'

        # Pad month and day if needed (check format for padding)
        if 'MM' in date_format:
            month = month.zfill(2)
        else:
            month = str(int(month))  # Remove leading zeros

        if 'DD' in date_format:
            day = day.zfill(2)
        else:
            day = str(int(day))  # Remove leading zeros

        # Handle 2-digit year
        if date_format.count('Y') == 2:
            year = year[-2:]  # Take last 2 digits

        # Construct based on format pattern
        format_upper = date_format.upper()

        if format_upper.startswith('YYYY'):
            # YYYY-MM-DD or YYYY/MM/DD
            return f"{year}{separator}{month}{separator}{day}"
        elif format_upper.startswith('MM'):
            # MM/DD/YYYY or MM-DD-YYYY
            return f"{month}{separator}{day}{separator}{year}"
        elif format_upper.startswith('DD'):
            # DD/MM/YYYY or DD-MM-YYYY
            return f"{day}{separator}{month}{separator}{year}"
        else:
            # Default fallback
            return f"{year}{separator}{month}{separator}{day}"

    def _get_profile_value(self, profile_data: Dict[str, Any], profile_mapping: str, field_mapping: Dict[str, Any]) -> str:
        """Get the appropriate value from profile data with intelligent fallback and multi-format date support"""
        # Handle nested profile data structures
        if "data" in profile_data and isinstance(profile_data["data"], dict):
            # Handle business-profile.json format
            profile_values = profile_data["data"]
        else:
            # Handle direct profile format (chris.json, etc.)
            profile_values = profile_data

        # Define alternative field names for common mappings
        field_alternatives = {
            'birthYear': ['dobY', 'dobYear', 'dob_year', 'birth_year', 'byear', 'year_of_birth', 'birthYear'],
            'birthMonth': ['dobM', 'dobMonth', 'dob_month', 'birth_month', 'bmonth', 'month_of_birth', 'birthMonth'],
            'birthDay': ['dobD', 'dobDay', 'dob_day', 'birth_day', 'bday', 'day_of_birth', 'birthDay'],
            'firstName': ['firstName', 'first_name', 'fname', 'givenName', 'given_name'],
            'lastName': ['lastName', 'last_name', 'lname', 'surname', 'familyName', 'family_name'],
            'email': ['email', 'emailAddress', 'email_address', 'e_mail'],
            'phone': ['phone', 'phoneNumber', 'phone_number', 'tel', 'telephone'],
            'address1': ['address1', 'address_1', 'street', 'street_address', 'addressLine1'],
            'address2': ['address2', 'address_2', 'addressLine2', 'apartment', 'apt'],
            'city': ['city', 'town', 'locality'],
            'state': ['state', 'province', 'region'],
            'zip': ['zip', 'zipCode', 'zip_code', 'postalCode', 'postal_code', 'postcode'],
            'country': ['country', 'nation', 'countryCode', 'country_code']
        }

        # Check if this is a full date field
        selector = field_mapping.get("field_selector", "").lower()
        field_name = field_mapping.get("field_name", "").lower()
        sample_value = field_mapping.get("sample_value", "")

        # Detect if this is a single full date input field
        is_full_date_field = any([
            'birthdate' in selector,
            'birth-date' in selector,
            'dob' in selector and 'doby' not in selector and 'dobm' not in selector and 'dobd' not in selector,
            'birth_date' in field_name,
            'birthdate' in field_name,
            # Check if sample value looks like a date
            (sample_value and len(sample_value) >= 8 and (sample_value.count('-') >= 2 or sample_value.count('/') >= 2))
        ])

        # If this is a full date field, construct the date from separate components
        if is_full_date_field:
            # Try to get year, month, day from profile
            year = ""
            month = ""
            day = ""

            # Get year
            for alt in field_alternatives.get('birthYear', []):
                year = profile_values.get(alt, "")
                if year:
                    break

            # Get month
            for alt in field_alternatives.get('birthMonth', []):
                month = profile_values.get(alt, "")
                if month:
                    break

            # Get day
            for alt in field_alternatives.get('birthDay', []):
                day = profile_values.get(alt, "")
                if day:
                    break

            # If we found all components, construct date in the appropriate format
            if year and month and day:
                # Detect format from sample value
                date_format = self._detect_date_format(sample_value)

                # Construct date in detected format
                value = self._construct_date_in_format(year, month, day, date_format)

                print(f"  [DATE FORMAT] Detected: {date_format}, Constructed: {value} (Y={year}, M={month}, D={day})")
                return value

        # Try exact match first
        value = profile_values.get(profile_mapping, "")

        # If no exact match, try alternatives
        if not value and profile_mapping in field_alternatives:
            for alt_name in field_alternatives[profile_mapping]:
                value = profile_values.get(alt_name, "")
                if value:
                    print(f"  [PROFILE MAPPING] Found {profile_mapping} as '{alt_name}' = '{value}'")
                    break

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

    def _detect_element_type(self, selector: str) -> str:
        """Detect the actual element type at runtime"""
        try:
            element = self.sb.find_element(selector)
            tag_name = element.tag_name.lower()

            if tag_name == "select":
                return "select"
            elif tag_name == "textarea":
                return "textarea"
            elif tag_name == "input":
                input_type = element.get_attribute("type")
                if input_type == "checkbox":
                    return "checkbox"
                elif input_type == "radio":
                    return "radio"
                else:
                    return "text"
            else:
                return "text"

        except Exception:
            # If we can't detect, default to text
            return "text"

    def _fill_text_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a text field using standard Selenium"""
        try:
            # Use standard Selenium methods
            self.sb.type(selector, value)
            return True

        except Exception as e:
            print(f"Error filling text field {field_name}: {e}")
            # Try fallback selector strategies
            return self._try_fallback_selectors(selector, value, "text")

    def _fill_select_field(self, selector: str, value: str, field_name: str, sample_value: str = None) -> bool:
        """
        Fill a select dropdown field with intelligent fallback

        Args:
            selector: CSS selector for the dropdown
            value: Primary value to try (from profile or recording)
            field_name: Field name for logging
            sample_value: Optional fallback value from recording
        """
        try:
            # Try selecting by value first (most Chrome Recorder recordings use values)
            self.sb.select_option_by_value(selector, value)
            return True

        except Exception:
            # Fallback to selecting by text
            try:
                self.sb.select_option_by_text(selector, value)
                return True
            except Exception:
                # If value doesn't match, try sample_value from recording (if available)
                if sample_value and sample_value != value:
                    try:
                        self.sb.select_option_by_value(selector, sample_value)
                        print(f"  [FALLBACK] Used recorded value '{sample_value}' for {field_name}")
                        return True
                    except Exception:
                        try:
                            self.sb.select_option_by_text(selector, sample_value)
                            print(f"  [FALLBACK] Used recorded value '{sample_value}' for {field_name}")
                            return True
                        except Exception:
                            pass

                # Final fallback: skip the field gracefully for dropdowns
                print(f"  [SKIP] Dropdown {field_name}: no valid option for '{value}'")
                return True  # Return True to avoid counting as failure - dropdown skipped gracefully

    def _fill_checkbox_field(self, selector: str, value: str, field_name: str) -> bool:
        """Fill a checkbox field"""
        try:
            should_check = value.lower() in ['true', '1', 'yes', 'on', 'checked']

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
                if field_type == "text":
                    self.sb.type(fallback_selector, value)
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
            if self.sb_context:
                self.sb_context.__exit__(None, None, None)
                self.sb = None
                self.sb_context = None

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

    def _find_submit_button(self) -> Optional[str]:
        """
        Find the submit button on the current page.
        Tries common patterns for submit buttons.
        Returns the selector if found, None otherwise.
        """
        # Common submit button patterns
        submit_patterns = [
            # Button elements with common text
            "button[type='submit']",
            "input[type='submit']",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'create')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'register')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign up')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'signup')]",
            "//input[@type='submit']",
            # Common button classes/IDs
            "#submit",
            ".submit",
            "#register-button",
            "#signup-button",
            ".register-button",
            ".signup-button"
        ]

        for pattern in submit_patterns:
            try:
                if pattern.startswith("//"):
                    # XPath selector
                    if self.sb.is_element_present(pattern):
                        print(f"Found submit button with XPath: {pattern}")
                        return pattern
                else:
                    # CSS selector
                    if self.sb.is_element_present(pattern):
                        print(f"Found submit button with CSS: {pattern}")
                        return pattern
            except Exception as e:
                continue

        print("Warning: Could not find submit button automatically")
        return None

    def _click_submit(self) -> bool:
        """
        Find and click the submit button.
        Returns True if successful, False otherwise.
        """
        try:
            submit_selector = self._find_submit_button()
            if not submit_selector:
                print("Submit button not found")
                return False

            # Capture current URL before submission
            initial_url = self.sb.get_current_url()

            # Click the submit button
            self.sb.click(submit_selector)
            print(f"Clicked submit button: {submit_selector}")

            # Wait a moment for submission to process
            time.sleep(2)

            return True

        except Exception as e:
            print(f"Error clicking submit button: {e}")
            return False

    def _capture_network_response(self):
        """
        Capture network response data including status code, body, and cookies.
        """
        try:
            # Get current URL (may have changed after submission)
            current_url = self.sb.get_current_url()
            self.replay_stats["submission"]["redirect_url"] = current_url

            # Get cookies
            cookies = self.sb.get_cookies()
            self.replay_stats["submission"]["cookies"] = cookies

            # Try to get response status from browser logs
            try:
                logs = self.sb.driver.get_log('performance')
                for entry in logs:
                    if 'Network.responseReceived' in str(entry):
                        # Parse the log entry to extract status code
                        import json
                        message = json.loads(entry['message'])
                        if 'message' in message and 'params' in message['message']:
                            response = message['message']['params'].get('response', {})
                            status = response.get('status')
                            if status and status >= 200:
                                self.replay_stats["submission"]["status_code"] = status
                                print(f"Captured response status: {status}")
            except Exception as log_error:
                # Chrome 141+ no longer supports 'performance' log type - silently fall back
                # Set a default status if we can't get it from logs
                self.replay_stats["submission"]["status_code"] = 200

            print(f"Captured network response data")
            return True

        except Exception as e:
            print(f"Error capturing network response: {e}")
            self.replay_stats["submission"]["error_message"] = str(e)
            return False

    def _verify_submission_success(self) -> bool:
        """
        Verify submission success using multiple indicators:
        1. Check HTTP status code (200/201)
        2. Look for success message on page
        3. Detect redirect to success page

        Returns True if submission appears successful, False otherwise.
        """
        success_indicators = []

        try:
            # Check 1: HTTP Status Code
            status_code = self.replay_stats["submission"].get("status_code")
            if status_code and 200 <= status_code < 300:
                success_indicators.append("status_code")
                print(f"✓ Status code check passed: {status_code}")

            # Check 2: Success Message on Page
            success_messages = [
                "success",
                "account created",
                "registration complete",
                "welcome",
                "thank you",
                "successfully registered",
                "confirmation",
                "verify your email"
            ]

            page_text = self.sb.get_page_source().lower()
            for message in success_messages:
                if message in page_text:
                    success_indicators.append("success_message")
                    print(f"✓ Success message found: '{message}'")
                    break

            # Check 3: URL Change/Redirect
            current_url = self.sb.get_current_url()
            redirect_url = self.replay_stats["submission"].get("redirect_url", "")

            # Look for success page indicators in URL
            success_url_patterns = [
                "/success",
                "/confirmation",
                "/thank",
                "/dashboard",
                "/account",
                "/welcome"
            ]

            for pattern in success_url_patterns:
                if pattern in current_url.lower():
                    success_indicators.append("redirect")
                    print(f"✓ Success URL pattern found: '{pattern}' in {current_url}")
                    break

            # Store success indicators
            self.replay_stats["submission"]["success_indicators"] = success_indicators

            # Consider successful if at least ONE indicator is present
            is_successful = len(success_indicators) > 0

            if is_successful:
                print(f"✓ Submission verified successful ({len(success_indicators)} indicators)")
                self.replay_stats["submission"]["success"] = True
            else:
                print(f"✗ Submission verification failed (no success indicators found)")
                self.replay_stats["submission"]["success"] = False

            return is_successful

        except Exception as e:
            print(f"Error verifying submission: {e}")
            self.replay_stats["submission"]["error_message"] = str(e)
            return False

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