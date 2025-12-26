#!/usr/bin/env python3
"""
SeleniumBase Automation Module - Browser automation with UC Mode best practices
Following official SeleniumBase UC Mode guidelines for maximum stealth
"""
import asyncio
import json
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import platform

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Check if verbose automation logging is enabled
AUTOMATION_VERBOSE = os.getenv("AUTOMATION_VERBOSE", "false").lower() == "true"

# UC Mode configuration
UC_RECONNECT_TIME = float(os.getenv("UC_RECONNECT_TIME", "4.0"))
UC_INCOGNITO = os.getenv("UC_INCOGNITO", "true").lower() == "true"

class SeleniumAutomation:
    """SeleniumBase automation with UC Mode best practices for anti-detection"""

    # Value mappings for dropdowns that use numeric values
    DROPDOWN_VALUE_MAPPINGS = {
        # Credit card types
        "Visa (Preferred)": "9",
        "Visa": "9",
        "Master Card": "6",
        "MasterCard": "6",
        "American Express": "1",
        "AmEx": "1",
        "Discover": "4",
        "Diners Club": "19",
        # Month names to numbers
        "Jan": "1",
        "Feb": "2",
        "Mar": "3",
        "Apr": "4",
        "May": "5",
        "Jun": "6",
        "Jul": "7",
        "Aug": "8",
        "Sep": "9",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12"
    }

    def __init__(self, session_id: str, profile: dict, use_stealth: bool = True, reconnect_time: float = None):
        self.session_id = session_id
        self.profile = profile
        self.use_stealth = use_stealth
        self.reconnect_time = reconnect_time or UC_RECONNECT_TIME
        self.sb = None
        self.sb_context = None
        self.driver = None  # Direct driver reference for UC Mode methods
        self.current_url = None
        self.field_mappings = {}
        self.load_field_mappings()

    def load_field_mappings(self):
        """Load saved field mappings from field_mappings and recordings directories"""
        # Load from field_mappings directory
        mappings_dir = Path("field_mappings")
        if mappings_dir.exists():
            for file in mappings_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        mapping = json.load(f)
                        self.field_mappings[mapping['url']] = mapping['mappings']
                except:
                    pass

        # Load from recordings directory
        recordings_dir = Path("recordings")
        if recordings_dir.exists():
            for file in recordings_dir.glob("*.json"):
                if file.name in ['recordings_index.json', 'recordings.json']:
                    continue
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        recording = json.load(f)
                        if 'url' in recording and 'field_mappings' in recording:
                            url = recording['url']
                            self.field_mappings[url] = recording['field_mappings']
                            if AUTOMATION_VERBOSE:
                                logger.info(f"Loaded {len(recording['field_mappings'])} field mappings from recording: {recording.get('recording_name', file.name)}")
                except Exception as e:
                    if AUTOMATION_VERBOSE:
                        logger.warning(f"Could not load recording {file.name}: {e}")
                    pass

    async def start(self, url: str) -> bool:
        """Start browser and navigate to URL using UC Mode best practices"""
        try:
            # Setup Chrome with full permissions (auto-grant all)
            chrome_options = self._setup_chrome_permissions()

            # Use UC Mode with incognito for maximum stealth
            self.sb_context = SB(
                uc=self.use_stealth,
                headed=True,
                incognito=UC_INCOGNITO,
                chromium_arg=chrome_options
            )
            self.sb = self.sb_context.__enter__()
            self.driver = self.sb.driver  # Store driver reference

            # Navigate using UC Mode's uc_open_with_reconnect
            if self.use_stealth:
                logger.info(f"UC Mode: Opening {url} with reconnect_time={self.reconnect_time}")
                self.driver.uc_open_with_reconnect(url, self.reconnect_time)
                self.current_url = url
            else:
                self.sb.open(url)
                self.current_url = url

            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            if AUTOMATION_VERBOSE:
                import traceback
                traceback.print_exc()
            return False

    def _setup_chrome_permissions(self):
        """Setup Chrome options for full permissions (no prompts)"""
        options = []

        # Disable all permission prompts
        options.extend([
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ])

        # Auto-grant all permissions via preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 1,  # Allow notifications
            "profile.default_content_setting_values.media_stream_mic": 1,  # Allow microphone
            "profile.default_content_setting_values.media_stream_camera": 1,  # Allow camera
            "profile.default_content_setting_values.geolocation": 1,  # Allow location
            "profile.default_content_setting_values.automatic_downloads": 1,  # Allow downloads
            "download.prompt_for_download": False,  # No download prompts
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,  # Disable safe browsing warnings
            "profile.default_content_settings.popups": 0,  # Allow popups
            "profile.password_manager_enabled": False,  # Disable password manager prompts
            "credentials_enable_service": False,
        }

        # Create persistent profile directory for FormAI (cross-platform)
        if platform.system() == "Windows":
            profile_dir = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "FormAI" / "ChromeProfile"
        else:
            profile_dir = Path.home() / ".config" / "formai" / "chrome_profile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        options.append(f"--user-data-dir={str(profile_dir)}")

        # Store prefs in a way SeleniumBase can use them
        prefs_file = profile_dir / "Default" / "Preferences"
        prefs_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with prefs_file.open('w') as f:
                json.dump({"profile": {"content_settings": {"exceptions": prefs}}}, f, indent=2)
        except:
            pass  # If it fails, Chrome will create it

        return ",".join(options)

    async def detect_and_fill_forms(self) -> int:
        """Detect form fields and fill them with profile data"""
        fields_filled = 0

        try:
            # Handle any CAPTCHAs first
            await self.handle_captcha()

            # Check if we have a recording for the current URL
            recording_mappings = self.field_mappings.get(self.current_url, [])

            if recording_mappings:
                if AUTOMATION_VERBOSE:
                    logger.info(f"Using recording with {len(recording_mappings)} field mappings for {self.current_url}")
                fields_filled = await self._fill_from_recording(recording_mappings)
                if AUTOMATION_VERBOSE:
                    logger.info(f"Filled {fields_filled} fields using recording")
            else:
                if AUTOMATION_VERBOSE:
                    logger.warning(f"No recording found for {self.current_url}, using pattern matching")
                # Fallback to pattern matching
                field_patterns = {
                    'email': ['email', 'e-mail', 'mail', 'username'],
                    'firstName': ['firstname', 'first_name', 'fname', 'given_name', 'forename'],
                    'lastName': ['lastname', 'last_name', 'lname', 'surname', 'family_name'],
                    'fullName': ['fullname', 'name', 'your_name', 'display_name'],
                    'phone': ['phone', 'tel', 'mobile', 'cell', 'phonenumber'],
                    'address': ['address', 'street', 'addr', 'address1', 'address_line'],
                    'city': ['city', 'town', 'locality'],
                    'state': ['state', 'province', 'region'],
                    'zip': ['zip', 'postal', 'postcode', 'zipcode']
                }

                if self.use_stealth:
                    fields_filled = await self._fill_with_uc_mode(field_patterns)
                else:
                    fields_filled = await self._fill_standard(field_patterns)

                await self._handle_dropdowns()

            return fields_filled

        except Exception as e:
            logger.error(f"Error detecting/filling forms: {e}")
            if AUTOMATION_VERBOSE:
                import traceback
                traceback.print_exc()
            return fields_filled

    async def _fill_from_recording(self, field_mappings: List[Dict]) -> int:
        """Fill form fields using recording field mappings with UC Mode"""
        fields_filled = 0
        fields_skipped = 0
        total_fields = len(field_mappings)

        if AUTOMATION_VERBOSE:
            logger.info(f"Processing {total_fields} fields from recording...")

        for mapping in field_mappings:
            try:
                field_name = mapping.get('field_name', 'unknown')
                field_selector = mapping.get('field_selector', '')
                field_type = mapping.get('field_type', 'textbox')
                profile_mapping = mapping.get('profile_mapping', '')

                # Get value from profile
                profile_value = None
                if profile_mapping:
                    if 'data' in self.profile and isinstance(self.profile['data'], dict):
                        profile_value = self.profile['data'].get(profile_mapping)
                    if not profile_value:
                        profile_value = self.profile.get(profile_mapping)

                if not profile_value:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"SKIP {field_name}: No value in profile for '{profile_mapping}'")
                    fields_skipped += 1
                    continue

                # Fill the field based on type using UC Mode methods
                if field_type == 'select':
                    success = await self._fill_select_uc_mode(field_selector, str(profile_value), field_name)
                else:
                    success = await self._fill_text_uc_mode(field_selector, str(profile_value), field_name)

                if success:
                    fields_filled += 1
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"FILL {field_name} = {profile_value}")
                else:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"FAIL {field_name}: Could not fill")
                    fields_skipped += 1

                # Human-like delay between fields
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.error(f"Failed to fill {mapping.get('field_name', 'unknown')}: {e}")
                fields_skipped += 1
                continue

        logger.info(f"Filled {fields_filled}/{total_fields} fields, skipped {fields_skipped}")
        return fields_filled

    async def _fill_text_uc_mode(self, selector: str, value: str, field_name: str = "") -> bool:
        """Fill a text input field using UC Mode methods"""
        try:
            if self.use_stealth:
                # Check if element exists
                if self.sb.is_element_present(selector):
                    # Use UC click for stealth
                    self.driver.uc_click(selector, reconnect_time=0.5)
                    await asyncio.sleep(0.2)

                    # Clear and type using standard methods after UC click
                    element = self.sb.find_element(selector)
                    element.clear()
                    await asyncio.sleep(0.1)
                    element.send_keys(value)
                    return True
                else:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"Element not found (UC Mode): {selector}")
                    return False
            else:
                # Standard Selenium
                elements = self.sb.find_elements(selector)
                if elements and len(elements) > 0:
                    element = elements[0]
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        return True
                return False
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Error filling text field {field_name}: {e}")
            return False

    async def _fill_select_uc_mode(self, selector: str, value: str, field_name: str = "") -> bool:
        """Fill a select dropdown field using UC Mode with reconnect strategy"""
        try:
            mapped_value = self.DROPDOWN_VALUE_MAPPINGS.get(value, value)

            if AUTOMATION_VERBOSE:
                logger.debug(f"SELECT Field (UC Mode): {field_name}, Selector: {selector}, Value: '{value}' -> '{mapped_value}'")

            if not self.sb.is_element_present(selector):
                if AUTOMATION_VERBOSE:
                    logger.debug(f"Select element not found: {selector}")
                return False

            # Use UC click to focus on dropdown
            self.driver.uc_click(selector, reconnect_time=0.5)
            await asyncio.sleep(0.2)

            # Strategy 1: Select by value using JavaScript (most reliable)
            try:
                js_script = f"""
                    const select = document.querySelector('{selector}');
                    if (select && select.offsetParent !== null) {{
                        select.focus();
                        select.value = '{mapped_value}';
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        return select.value === '{mapped_value}';
                    }}
                    return false;
                """
                result = self.sb.execute_script(js_script)

                if result:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"SUCCESS (UC Mode): {field_name} filled with '{value}'")
                    await asyncio.sleep(0.3)
                    return True
            except Exception as e:
                if AUTOMATION_VERBOSE:
                    logger.debug(f"UC Mode select strategy failed: {e}")

            #Strategy 2: Try selecting by visible text
            try:
                js_script = f"""
                    const select = document.querySelector('{selector}');
                    if (select) {{
                        const options = Array.from(select.options);
                        const option = options.find(opt => opt.text === '{value}' || opt.text.trim() === '{value}');
                        if (option) {{
                            select.value = option.value;
                            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                """
                result = self.sb.execute_script(js_script)
                if result:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"Selected by text (UC Mode): {field_name} = {value}")
                    await asyncio.sleep(0.3)
                    return True
            except Exception as e:
                if AUTOMATION_VERBOSE:
                    logger.debug(f"UC Mode text selection failed: {e}")

            return False

        except Exception as e:
            logger.error(f"Exception in _fill_select_uc_mode for {field_name}: {e}")
            return False

    async def _fill_with_uc_mode(self, field_patterns: Dict) -> int:
        """Fill forms using UC Mode methods for anti-detection"""
        fields_filled = 0

        for field_type, patterns in field_patterns.items():
            if field_type not in self.profile or not self.profile[field_type]:
                continue

            value = self.profile[field_type]

            for pattern in patterns:
                try:
                    selectors = [
                        f"input[name*='{pattern}']",
                        f"input[id*='{pattern}']",
                        f"input[placeholder*='{pattern}']",
                        f"textarea[name*='{pattern}']"
                    ]

                    for selector in selectors:
                        try:
                            if self.sb.is_element_present(selector):
                                # Use UC click with reconnect
                                self.driver.uc_click(selector, reconnect_time=0.5)
                                await asyncio.sleep(0.3)

                                # Type value
                                element = self.sb.find_element(selector)
                                element.clear()
                                await asyncio.sleep(0.2)
                                element.send_keys(value)

                                fields_filled += 1
                                await asyncio.sleep(0.5)
                                break
                        except:
                            continue
                except:
                    continue

        return fields_filled

    async def _fill_standard(self, field_patterns: Dict) -> int:
        """Fill forms using standard Selenium methods"""
        fields_filled = 0

        for field_type, patterns in field_patterns.items():
            if field_type not in self.profile or not self.profile[field_type]:
                continue

            value = self.profile[field_type]

            for pattern in patterns:
                try:
                    elements = self.sb.find_elements(
                        f"input[name*='{pattern}' i], input[id*='{pattern}' i], textarea[name*='{pattern}' i]"
                    )

                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.clear()
                            element.send_keys(value)
                            fields_filled += 1
                            await asyncio.sleep(0.3)
                            break
                except:
                    continue

        return fields_filled

    async def _handle_dropdowns(self):
        """Detect and handle dropdown selections"""
        try:
            dropdown_patterns = {
                'state': ['state', 'province', 'region'],
                'country': ['country', 'nation'],
                'month': ['month', 'birth_month'],
                'year': ['year', 'birth_year']
            }

            for field_type, patterns in dropdown_patterns.items():
                if field_type not in self.profile:
                    continue

                value = self.profile[field_type]

                for pattern in patterns:
                    try:
                        selects = self.sb.find_elements(f"select[name*='{pattern}' i], select[id*='{pattern}' i]")

                        for select_element in selects:
                            if select_element.is_displayed():
                                self.sb.select_option_by_text(select_element, value)
                                await asyncio.sleep(0.3)
                                break
                    except:
                        continue
        except:
            pass

    async def click_element(self, selector: str, use_reconnect: bool = True) -> bool:
        """Click an element using UC Mode uc_click for stealth"""
        try:
            if self.use_stealth and use_reconnect:
                # Use UC Mode uc_click with reconnect
                self.driver.uc_click(selector, reconnect_time=self.reconnect_time)
                return True
            else:
                # Standard click
                self.sb.click(selector)
                return True
        except:
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        """Type text with human-like behavior"""
        try:
            if self.use_stealth:
                # Use UC click first, then type
                self.driver.uc_click(selector, reconnect_time=0.5)
                await asyncio.sleep(0.2)
                element = self.sb.find_element(selector)
                element.clear()
                element.send_keys(text)
                return True
            else:
                element = self.sb.find_element(selector)
                element.clear()
                element.send_keys(text)
                return True
        except:
            return False

    async def take_screenshot(self, filename: str = None) -> str:
        """Take a screenshot of the current page"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recordings/screenshot_{self.session_id}_{timestamp}.png"

            Path("recordings").mkdir(exist_ok=True)
            self.sb.save_screenshot(filename)
            return filename
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None

    async def extract_form_fields(self) -> List[Dict]:
        """Extract all form fields from the current page"""
        fields = []

        try:
            inputs = self.sb.find_elements("input, textarea, select")

            for element in inputs:
                try:
                    field_info = {
                        'tag': element.tag_name,
                        'type': element.get_attribute('type') or 'text',
                        'name': element.get_attribute('name'),
                        'id': element.get_attribute('id'),
                        'placeholder': element.get_attribute('placeholder'),
                        'required': element.get_attribute('required') is not None,
                        'value': element.get_attribute('value')
                    }
                    fields.append(field_info)
                except:
                    continue

            return fields
        except Exception as e:
            logger.error(f"Error extracting form fields: {e}")
            return fields

    async def save_field_mapping(self, url: str, mappings: Dict):
        """Save field mappings for a URL"""
        mappings_dir = Path("field_mappings")
        mappings_dir.mkdir(exist_ok=True)

        safe_filename = url.replace('://', '_').replace('/', '_')[:100]
        file_path = mappings_dir / f"{safe_filename}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'mappings': mappings,
                'created': datetime.now().isoformat()
            }, f, indent=2)

        self.field_mappings[url] = mappings

    async def handle_captcha(self) -> bool:
        """Handle CAPTCHA challenges using SeleniumBase built-in methods"""
        try:
            if not self.use_stealth:
                return True

            # Check for common CAPTCHA indicators
            captcha_indicators = [
                "recaptcha",
                "captcha",
                "challenge",
                "verify you're human",
                "turnstile",
                "cloudflare"
            ]

            page_source = self.sb.get_page_source().lower()

            for indicator in captcha_indicators:
                if indicator in page_source:
                    logger.warning(f"CAPTCHA detected: {indicator}")

                    # Try SeleniumBase's solve_captcha() first (recommended method)
                    try:
                        logger.info("Attempting to solve CAPTCHA using sb.solve_captcha()")
                        self.sb.solve_captcha()
                        logger.info("CAPTCHA solved successfully")
                        await asyncio.sleep(2)
                        return True
                    except Exception as e:
                        logger.warning(f"sb.solve_captcha() failed: {e}, trying UC Mode methods")

                        # Fallback 1: UC Mode's built-in CAPTCHA handling
                        try:
                            logger.info("Attempting uc_gui_handle_captcha")
                            self.driver.uc_gui_handle_captcha()
                            logger.info("CAPTCHA handling completed")
                            await asyncio.sleep(2)
                            return True
                        except Exception as e2:
                            logger.warning(f"uc_gui_handle_captcha failed: {e2}")

                            # Fallback 2: try uc_gui_click_captcha
                            try:
                                logger.info("Trying uc_gui_click_captcha as final fallback")
                                self.driver.uc_gui_click_captcha()
                                logger.info("CAPTCHA click completed")
                                await asyncio.sleep(2)
                                return True
                            except Exception as e3:
                                logger.error(f"All CAPTCHA methods failed: {e3}")
                                return False

            return True
        except Exception as e:
            logger.error(f"Error in handle_captcha: {e}")
            return True

    async def close(self):
        """Close the browser session"""
        try:
            if self.sb_context:
                self.sb_context.__exit__(None, None, None)
                self.sb = None
                self.driver = None
                self.sb_context = None
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            pass

    async def get_page_info(self) -> Dict:
        """Get current page information"""
        try:
            return {
                'url': self.sb.get_current_url(),
                'title': self.sb.get_title(),
                'ready_state': self.sb.execute_script("return document.readyState"),
                'has_forms': len(self.sb.find_elements("form")) > 0
            }
        except:
            return {}


class FormFieldDetector:
    """Smart form field detection and mapping"""

    @staticmethod
    def detect_field_type(element_info: Dict) -> Optional[str]:
        """Detect the type of form field based on attributes"""
        input_type = element_info.get('type', '').lower()
        name = element_info.get('name', '').lower()
        id_attr = element_info.get('id', '').lower()
        placeholder = element_info.get('placeholder', '').lower()

        combined = f"{name} {id_attr} {placeholder} {input_type}"

        # Detection rules
        if 'email' in combined or input_type == 'email':
            return 'email'
        elif any(x in combined for x in ['firstname', 'first_name', 'fname']):
            return 'first_name'
        elif any(x in combined for x in ['lastname', 'last_name', 'lname']):
            return 'last_name'
        elif any(x in combined for x in ['phone', 'tel', 'mobile']):
            return 'phone'
        elif any(x in combined for x in ['address', 'street', 'addr']):
            return 'address'
        elif 'city' in combined:
            return 'city'
        elif 'state' in combined or 'province' in combined:
            return 'state'
        elif any(x in combined for x in ['zip', 'postal', 'postcode']):
            return 'zip'
        elif 'password' in combined or input_type == 'password':
            return 'password'
        elif 'date' in combined or input_type == 'date':
            return 'date_of_birth'

        return None

    @staticmethod
    def create_mapping(fields: List[Dict], profile: Dict) -> Dict:
        """Create automatic field mappings based on detection"""
        mapping = {}

        for field in fields:
            field_type = FormFieldDetector.detect_field_type(field)

            if field_type and field_type in profile:
                if field.get('id'):
                    selector = f"#{field['id']}"
                elif field.get('name'):
                    selector = f"[name='{field['name']}']"
                else:
                    continue

                mapping[selector] = {
                    'type': field_type,
                    'value': profile[field_type]
                }

        return mapping
