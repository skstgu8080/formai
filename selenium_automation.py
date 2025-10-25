#!/usr/bin/env python3
"""
SeleniumBase Automation Module - Browser automation with anti-detection
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
import pyautogui

# Configure logging - only show warnings and errors by default
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Check if verbose automation logging is enabled
AUTOMATION_VERBOSE = os.getenv("AUTOMATION_VERBOSE", "false").lower() == "true"

class SeleniumAutomation:
    """SeleniumBase automation with CDP mode for anti-detection"""

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

    def __init__(self, session_id: str, profile: dict, use_stealth: bool = True):
        self.session_id = session_id
        self.profile = profile
        self.use_stealth = use_stealth
        self.sb = None
        self.sb_context = None  # Store context manager to prevent premature closure
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

        # Load from recordings directory (IMPORTANT: these have comprehensive field mappings)
        recordings_dir = Path("recordings")
        if recordings_dir.exists():
            for file in recordings_dir.glob("*.json"):
                if file.name in ['recordings_index.json', 'recordings.json']:
                    continue  # Skip index files
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        recording = json.load(f)
                        if 'url' in recording and 'field_mappings' in recording:
                            url = recording['url']
                            # Convert recording format to internal format
                            self.field_mappings[url] = recording['field_mappings']
                            if AUTOMATION_VERBOSE:
                                logger.info(f"Loaded {len(recording['field_mappings'])} field mappings from recording: {recording.get('recording_name', file.name)}")
                except Exception as e:
                    if AUTOMATION_VERBOSE:
                        logger.warning(f"Could not load recording {file.name}: {e}")
                    pass

    async def start(self, url: str) -> bool:
        """Start browser and navigate to URL"""
        try:
            # Use UC mode for undetected Chrome with CDP capabilities
            # Store the context manager to prevent it from closing prematurely
            self.sb_context = SB(uc=self.use_stealth, headed=True, incognito=False)
            self.sb = self.sb_context.__enter__()

            # Navigate to URL
            if self.use_stealth:
                # Activate CDP mode for enhanced stealth
                self.sb.activate_cdp_mode(url)
                self.current_url = url
            else:
                self.sb.open(url)
                self.current_url = url

            await asyncio.sleep(2)  # Wait for page to load
            return True
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            if AUTOMATION_VERBOSE:
                import traceback
                traceback.print_exc()
            return False

    async def detect_and_fill_forms(self) -> int:
        """Detect form fields and fill them with profile data"""
        fields_filled = 0

        try:
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

                # Try CDP mode methods for better anti-detection
                if self.use_stealth and hasattr(self.sb, 'cdp'):
                    fields_filled = await self._fill_with_cdp(field_patterns)
                else:
                    fields_filled = await self._fill_standard(field_patterns)

                # Handle dropdowns
                await self._handle_dropdowns()

            return fields_filled

        except Exception as e:
            logger.error(f"Error detecting/filling forms: {e}")
            if AUTOMATION_VERBOSE:
                import traceback
                traceback.print_exc()
            return fields_filled

    async def _fill_from_recording(self, field_mappings: List[Dict]) -> int:
        """Fill form fields using recording field mappings"""
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
                    # Handle nested profile structure (e.g., profile.data.firstName or profile.firstName)
                    if 'data' in self.profile and isinstance(self.profile['data'], dict):
                        profile_value = self.profile['data'].get(profile_mapping)
                    if not profile_value:
                        profile_value = self.profile.get(profile_mapping)

                if not profile_value:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"SKIP {field_name}: No value in profile for '{profile_mapping}'")
                    fields_skipped += 1
                    continue

                # Fill the field based on type
                if field_type == 'select':
                    success = await self._fill_select_field(field_selector, str(profile_value), field_name)
                else:
                    success = await self._fill_text_field(field_selector, str(profile_value), field_name)

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

        # Always show summary - this is useful info
        logger.info(f"Filled {fields_filled}/{total_fields} fields, skipped {fields_skipped}")
        return fields_filled

    async def _fill_text_field(self, selector: str, value: str, field_name: str = "") -> bool:
        """Fill a text input field with anti-detection"""
        try:
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                # Use CDP mode for stealth
                if self.sb.cdp.is_element_present(selector):
                    self.sb.cdp.click(selector)
                    await asyncio.sleep(0.2)
                    self.sb.cdp.clear(selector)
                    await asyncio.sleep(0.1)
                    self.sb.cdp.type(selector, value)
                    return True
                else:
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"Element not found (CDP): {selector}")
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
                if AUTOMATION_VERBOSE:
                    logger.debug(f"Element not found (Standard): {selector}")
                return False
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Error filling text field {field_name}: {e}")
            return False

    async def _fill_select_field(self, selector: str, value: str, field_name: str = "") -> bool:
        """Fill a select dropdown field with multiple fallback strategies"""
        try:
            # Get mapped value if available
            mapped_value = self.DROPDOWN_VALUE_MAPPINGS.get(value, value)

            if AUTOMATION_VERBOSE:
                logger.debug(f"SELECT Field: {field_name}, Selector: {selector}, Value: '{value}' -> '{mapped_value}', Mode: {'CDP' if self.use_stealth else 'Standard'}")

            if self.use_stealth and hasattr(self.sb, 'cdp'):
                result = await self._fill_select_cdp(selector, value, mapped_value, field_name)
            else:
                result = await self._fill_select_standard(selector, value, mapped_value, field_name)

            if AUTOMATION_VERBOSE:
                if result:
                    logger.debug(f"SUCCESS: {field_name} filled with '{value}'")
                else:
                    logger.debug(f"FAILED: {field_name} could not be filled")

            return result

        except Exception as e:
            logger.error(f"Exception in _fill_select_field for {field_name}: {e}")
            if AUTOMATION_VERBOSE:
                import traceback
                traceback.print_exc()
            return False

    async def _fill_select_cdp(self, selector: str, value: str, mapped_value: str, field_name: str) -> bool:
        """Fill select field using CDP mode - matches Chrome DevTools recording interaction"""

        # First, check if element exists and get its current state
        if AUTOMATION_VERBOSE:
            logger.debug("CDP: Checking element existence...")
        if not self.sb.cdp.is_element_present(selector):
            if AUTOMATION_VERBOSE:
                logger.debug(f"CDP: Element NOT found: {selector}")
            return False

        if AUTOMATION_VERBOSE:
            logger.debug(f"CDP: Element found: {selector}")

        # Get dropdown options for debugging
        if AUTOMATION_VERBOSE:
            try:
                options_script = f"""
                    const select = document.querySelector('{selector}');
                    if (select) {{
                        return Array.from(select.options).map(opt => ({{
                            value: opt.value,
                            text: opt.text,
                            selected: opt.selected
                        }}));
                    }}
                    return [];
                """
                options = self.sb.execute_script(options_script)
                logger.debug("CDP: Available options:")
                for opt in options:
                    marker = " ← CURRENT" if opt['selected'] else ""
                    logger.debug(f"  value='{opt['value']}' text='{opt['text']}'{marker}")
            except Exception as e:
                logger.debug(f"CDP: Could not fetch options: {e}")

        # Strategy 1: Click then Change (mimics Chrome DevTools recording)
        if AUTOMATION_VERBOSE:
            logger.debug("CDP: Strategy 1 - Click + Change")
        try:
            js_script = f"""
                const select = document.querySelector('{selector}');
                if (select && select.offsetParent !== null) {{
                    console.log('Step 1: Focus and click');
                    select.focus();
                    select.click();

                    console.log('Step 2: Set value to {mapped_value}');
                    select.value = '{mapped_value}';

                    console.log('Step 3: Trigger events');
                    select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    select.dispatchEvent(new Event('input', {{ bubbles: true }}));

                    console.log('Step 4: Verify - current value:', select.value);
                    return select.value === '{mapped_value}';
                }}
                console.error('Element not found or not visible');
                return false;
            """
            result = self.sb.execute_script(js_script)

            # Verify what was actually selected
            verify_script = f"return document.querySelector('{selector}').value;"
            actual_value = self.sb.execute_script(verify_script)

            if AUTOMATION_VERBOSE:
                logger.debug(f"CDP: Strategy 1 result: {result}, actual: '{actual_value}' (expected: '{mapped_value}')")

            if result:
                if AUTOMATION_VERBOSE:
                    logger.debug("CDP: Strategy 1 SUCCESS")
                await asyncio.sleep(0.3)
                return True
            else:
                if AUTOMATION_VERBOSE:
                    logger.debug("CDP: Strategy 1 FAILED - trying alternatives")
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"CDP: Strategy 1 exception: {e}")
                import traceback
                traceback.print_exc()

        # Strategy 2: Try selecting by visible text (fallback)
        try:
            js_script = f"""
                const select = document.querySelector('{selector}');
                if (select) {{
                    select.focus();
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
                    logger.debug(f"Selected by text (CDP): {field_name} = {value}")
                await asyncio.sleep(0.3)
                return True
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"CDP Strategy 2 failed: {e}")

        # Strategy 3: Try partial text match (last resort)
        try:
            js_script = f"""
                const select = document.querySelector('{selector}');
                if (select) {{
                    select.focus();
                    const options = Array.from(select.options);
                    const option = options.find(opt => opt.text.includes('{value}'));
                    if (option) {{
                        select.value = option.value;
                        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            """
            result = self.sb.execute_script(js_script)
            if result:
                if AUTOMATION_VERBOSE:
                    logger.debug(f"Selected by partial text (CDP): {field_name} = {value}")
                await asyncio.sleep(0.3)
                return True
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"CDP Strategy 3 failed: {e}")

        if AUTOMATION_VERBOSE:
            logger.debug(f"All CDP strategies failed for {field_name}")
        return False

    async def _fill_select_standard(self, selector: str, value: str, mapped_value: str, field_name: str) -> bool:
        """Fill select field using standard Selenium - click first, then select"""
        elements = self.sb.find_elements(selector)
        if not elements or len(elements) == 0:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Select element not found (Standard): {selector}")
            return False

        element = elements[0]
        from selenium.webdriver.support.select import Select
        select_element = Select(element)

        # Strategy 1: Click + Select by value (matches Chrome recording pattern)
        try:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Attempting click+select by value for {field_name}")
            # Step 1: Click to focus
            element.click()
            await asyncio.sleep(0.1)

            # Step 2: Select by value
            select_element.select_by_value(mapped_value)
            if AUTOMATION_VERBOSE:
                logger.debug(f"Selected by value with click (Standard): {field_name} = {mapped_value}")
            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Standard Strategy 1 (click+value) failed: {e}")

        # Strategy 2: Click + Select by visible text
        try:
            element.click()
            await asyncio.sleep(0.1)
            select_element.select_by_visible_text(value)
            if AUTOMATION_VERBOSE:
                logger.debug(f"Selected by text with click (Standard): {field_name} = {value}")
            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Standard Strategy 2 (click+text) failed: {e}")

        # Strategy 3: Try partial text match
        try:
            element.click()
            await asyncio.sleep(0.1)
            for option in select_element.options:
                if value in option.text:
                    select_element.select_by_value(option.get_attribute('value'))
                    if AUTOMATION_VERBOSE:
                        logger.debug(f"Selected by partial text (Standard): {field_name} = {value}")
                    await asyncio.sleep(0.3)
                    return True
        except Exception as e:
            if AUTOMATION_VERBOSE:
                logger.debug(f"Standard Strategy 3 (partial) failed: {e}")

        if AUTOMATION_VERBOSE:
            logger.debug(f"All Standard strategies failed for {field_name}")
        return False

    async def _fill_with_cdp(self, field_patterns: Dict) -> int:
        """Fill forms using CDP mode for anti-detection"""
        fields_filled = 0

        for field_type, patterns in field_patterns.items():
            if field_type not in self.profile or not self.profile[field_type]:
                continue

            value = self.profile[field_type]

            for pattern in patterns:
                try:
                    # Try different selector strategies
                    selectors = [
                        f"input[name*='{pattern}']",
                        f"input[id*='{pattern}']",
                        f"input[placeholder*='{pattern}']",
                        f"textarea[name*='{pattern}']"
                    ]

                    for selector in selectors:
                        try:
                            if self.sb.cdp.is_element_present(selector):
                                # Use CDP click and type for stealth
                                self.sb.cdp.click(selector)
                                await asyncio.sleep(0.3)  # Human-like delay

                                # Clear existing text first
                                self.sb.cdp.clear(selector)
                                await asyncio.sleep(0.2)

                                # Type with human-like speed
                                self.sb.cdp.type(selector, value)
                                fields_filled += 1
                                await asyncio.sleep(0.5)  # Pause between fields
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
                    # Find elements matching pattern
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
            # Common dropdown patterns for states, countries, etc.
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
                        # Find select elements
                        selects = self.sb.find_elements(f"select[name*='{pattern}' i], select[id*='{pattern}' i]")

                        for select_element in selects:
                            if select_element.is_displayed():
                                # Use SeleniumBase select method
                                self.sb.select_option_by_text(select_element, value)
                                await asyncio.sleep(0.3)
                                break
                    except:
                        continue
        except:
            pass

    async def click_element(self, selector: str) -> bool:
        """Click an element with anti-detection"""
        try:
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                # Use CDP click for stealth
                if self.sb.cdp.is_element_present(selector):
                    self.sb.cdp.click(selector)
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
            if self.use_stealth and hasattr(self.sb, 'cdp'):
                # CDP typing
                self.sb.cdp.click(selector)
                await asyncio.sleep(0.2)
                self.sb.cdp.type(selector, text)
                return True
            else:
                # Standard typing
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
            # Find all input fields
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
        """Handle CAPTCHA challenges (basic implementation)"""
        try:
            # Check for common CAPTCHA indicators
            captcha_indicators = [
                "recaptcha",
                "captcha",
                "challenge",
                "verify you're human"
            ]

            page_source = self.sb.get_page_source().lower()

            for indicator in captcha_indicators:
                if indicator in page_source:
                    logger.warning(f"CAPTCHA detected: {indicator}")
                    # Here you could integrate with CAPTCHA solving services
                    # or use PyAutoGUI for manual solving assistance
                    return False

            return True
        except:
            return True

    async def close(self):
        """Close the browser session"""
        try:
            if self.sb_context:
                self.sb_context.__exit__(None, None, None)
                self.sb = None
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
        # Check input type
        input_type = element_info.get('type', '').lower()
        name = element_info.get('name', '').lower()
        id_attr = element_info.get('id', '').lower()
        placeholder = element_info.get('placeholder', '').lower()

        # Combined attributes for detection
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
                # Create selector for the field
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