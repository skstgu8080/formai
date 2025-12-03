#!/usr/bin/env python3
"""
FormAI Autofill Engine - Bulk Fill + Actions

Navigate to URL → bulk fill all fields → check boxes → select radios → click submit
~10x faster than step-by-step replay.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from seleniumbase import SB

logger = logging.getLogger("autofill-engine")


@dataclass
class AutofillResult:
    """Result from autofill execution."""
    success: bool
    fields_filled: int = 0
    checkboxes_checked: int = 0
    radios_selected: int = 0
    submitted: bool = False
    error: Optional[str] = None


class AutofillEngine:
    """
    Bulk fill engine for form automation.

    Instead of step-by-step replay:
    1. Parse recording to extract field selectors, checkboxes, radios, submit button
    2. Navigate to URL
    3. Bulk fill ALL text fields at once via JavaScript
    4. Check all checkboxes
    5. Select radio buttons
    6. Click submit
    """

    def __init__(self, headless: bool = True, field_delay: float = 0.3):
        self.headless = headless
        self.field_delay = field_delay  # Delay between field fills (seconds)
        self.sb = None
        self.driver = None

    async def execute(self, recording: dict, profile: dict) -> AutofillResult:
        """
        Execute recording with bulk fill approach.

        Args:
            recording: Chrome DevTools recording with field selectors
            profile: User profile data to fill

        Returns:
            AutofillResult with success status and counts
        """
        try:
            # 1. Parse recording into categories
            fields, checkboxes, radios, submit_selector = self._parse_recording(recording)

            logger.info(f"Parsed recording: {len(fields)} fields, {len(checkboxes)} checkboxes, "
                       f"{len(radios)} radios, submit={'yes' if submit_selector else 'no'}")

            # 2. Get URL from recording
            url = self._get_url_from_recording(recording)
            if not url:
                return AutofillResult(success=False, error="No URL found in recording")

            # 3. Start browser and navigate
            with SB(uc=True, headless=self.headless) as sb:
                self.sb = sb
                self.driver = sb.driver

                # Navigate to URL
                logger.info(f"Navigating to: {url}")
                self.driver.get(url)
                await self._wait_for_page_load()

                # 4. BULK FILL all text fields at once
                fields_filled = await self._bulk_fill_fields(fields, profile)
                logger.info(f"Bulk filled {fields_filled} fields")

                # 5. Check all checkboxes
                checkboxes_checked = await self._check_checkboxes(checkboxes)
                logger.info(f"Checked {checkboxes_checked} checkboxes")

                # 6. Select radio buttons
                radios_selected = await self._select_radios(radios)
                logger.info(f"Selected {radios_selected} radio buttons")

                # 7. Click submit
                submitted = False
                if submit_selector:
                    submitted = await self._click_submit(submit_selector)
                    logger.info(f"Submit clicked: {submitted}")

                    # Wait for form submission to complete
                    if submitted:
                        await asyncio.sleep(2)

                return AutofillResult(
                    success=True,
                    fields_filled=fields_filled,
                    checkboxes_checked=checkboxes_checked,
                    radios_selected=radios_selected,
                    submitted=submitted
                )

        except Exception as e:
            logger.error(f"Autofill failed: {e}", exc_info=True)
            return AutofillResult(success=False, error=str(e))

    def _parse_recording(self, recording: dict) -> Tuple[List[dict], List[str], List[dict], Optional[str]]:
        """
        Parse recording into categories.

        Returns:
            Tuple of (fields, checkboxes, radios, submit_selector)
        """
        fields = []       # Text inputs, selects, textareas with profile mapping
        checkboxes = []   # Checkbox selectors to check
        radios = []       # Radio button selectors with values
        submit_selector = None

        steps = recording.get("steps", [])

        for step in steps:
            step_type = step.get("type", "")

            if step_type == "change":
                # Field interaction - determine type
                selectors = step.get("selectors", [])
                if not selectors:
                    continue

                # Get best selector (first one)
                selector = self._get_best_selector(selectors)
                value = step.get("value", "")

                # Detect field type from selector
                field_type = self._detect_field_type(selector, step)

                if field_type == "checkbox":
                    checkboxes.append(selector)
                elif field_type == "radio":
                    radios.append({"selector": selector, "value": value})
                else:
                    # Text field - extract profile key from value or infer from selectors
                    profile_key = self._extract_profile_key(value, selectors)
                    if profile_key:
                        fields.append({
                            "selector": selector,
                            "profile_key": profile_key
                        })
                    else:
                        # Value is literal, not a profile reference
                        fields.append({
                            "selector": selector,
                            "literal_value": value
                        })

            elif step_type == "click":
                selectors = step.get("selectors", [])
                if not selectors:
                    continue

                selector = self._get_best_selector(selectors)

                # Check if this is a checkbox click
                if self._is_checkbox_click(selector, selectors):
                    checkboxes.append(selector)
                # Check if this is a submit button
                elif self._is_submit_click(step):
                    submit_selector = selector

        return fields, checkboxes, radios, submit_selector

    def _get_best_selector(self, selectors: list) -> str:
        """Get the best selector from a list (prefer CSS over XPath)."""
        if not selectors:
            return ""

        for sel in selectors:
            if isinstance(sel, list):
                sel = sel[0] if sel else ""
            if isinstance(sel, str):
                # Prefer CSS selectors over aria or xpath
                if not sel.startswith("aria/") and not sel.startswith("xpath/"):
                    return sel

        # Fallback to first selector
        first = selectors[0]
        if isinstance(first, list):
            return first[0] if first else ""
        return first if isinstance(first, str) else ""

    def _detect_field_type(self, selector: str, step: dict) -> str:
        """Detect if field is checkbox, radio, or text input."""
        selector_lower = selector.lower()

        # Check selector for type hints
        if 'type="checkbox"' in selector_lower or '[type=checkbox]' in selector_lower:
            return "checkbox"
        if 'type="radio"' in selector_lower or '[type=radio]' in selector_lower:
            return "radio"

        # Check step metadata if available
        if step.get("inputType") == "checkbox":
            return "checkbox"
        if step.get("inputType") == "radio":
            return "radio"

        # Check value - booleans suggest checkbox
        value = step.get("value", "")
        if value in [True, False, "true", "false", "on", "off"]:
            return "checkbox"

        return "text"

    def _extract_profile_key(self, value: str, selectors: list = None) -> Optional[str]:
        """
        Extract profile key from recording value or selectors.

        Values in recordings may be:
        - Literal: "john@example.com"
        - Template: "{{email}}" or "{email}"
        - Profile reference: "profile.email"

        If value is gibberish (from recording), use aria labels or field IDs to infer.
        """
        # Check for template syntax: {{key}} or {key}
        if value and isinstance(value, str):
            match = re.match(r'\{\{?(\w+)\}?\}?', value)
            if match:
                return match.group(1)

            # Check for profile. prefix
            if value.startswith("profile."):
                return value[8:]

        # ALWAYS try to infer from selectors first - this is more reliable
        # than checking if the value looks like a profile key
        if selectors:
            inferred = self._infer_profile_key_from_selectors(selectors)
            if inferred:
                return inferred

        # Fallback: Check if value looks like a known profile key
        if value and isinstance(value, str):
            known_keys = [
                'firstName', 'lastName', 'email', 'phone', 'address', 'city',
                'state', 'zipCode', 'country', 'gender', 'sex', 'birthdate',
                'password', 'username', 'fullName', 'middleName'
            ]
            if value in known_keys:
                return value

        return None

    def _infer_profile_key_from_selectors(self, selectors: list) -> Optional[str]:
        """Infer profile key from aria labels or field IDs/names."""
        # Mapping of common aria labels/field names to profile keys
        field_mapping = {
            # Names
            'first name': 'firstName',
            'firstname': 'firstName',
            'first': 'firstName',
            'last name': 'lastName',
            'lastname': 'lastName',
            'last': 'lastName',
            'full name': 'fullName',
            'name': 'firstName',

            # Contact
            'email': 'email',
            'e-mail': 'email',
            'email address': 'email',
            'phone': 'phone',
            'telephone': 'phone',
            'mobile': 'phone',

            # Address
            'address': 'address',
            'street': 'address',
            'city': 'city',
            'state': 'state',
            'province': 'state',
            'zip': 'zipCode',
            'zipcode': 'zipCode',
            'postal': 'zipCode',
            'postal code': 'zipCode',
            'country': 'country',

            # Account
            'password': 'password',
            'pass': 'password',
            'username': 'username',
            'user': 'username',

            # Personal
            'gender': 'gender',
            'sex': 'sex',
            'birthdate': 'birthdate',
            'birth date': 'birthdate',
            'date of birth': 'date_of_birth',
            'dob': 'date_of_birth',
            'birthday': 'birthdate',

            # Date components
            'month': 'birthMonth',
            'birth month': 'birthMonth',
            'day': 'birthDay',
            'birth day': 'birthDay',
            'year': 'birthYear',
            'birth year': 'birthYear',
        }

        for sel in selectors:
            if isinstance(sel, list):
                sel = sel[0] if sel else ""
            if not isinstance(sel, str):
                continue

            # Check aria labels: aria/First name
            if sel.startswith("aria/"):
                aria_text = sel[5:].lower().strip()
                if aria_text in field_mapping:
                    return field_mapping[aria_text]
                # Partial match
                for key, profile_key in field_mapping.items():
                    if key in aria_text or aria_text in key:
                        return profile_key

            # Check ID selectors: #RegisterForm-FirstName
            if sel.startswith("#"):
                field_id = sel[1:].lower()
                # Extract meaningful part (after hyphen or underscore)
                parts = re.split(r'[-_]', field_id)
                for part in parts:
                    if part in field_mapping:
                        return field_mapping[part]
                    for key, profile_key in field_mapping.items():
                        if key.replace(' ', '') == part or part in key.replace(' ', ''):
                            return profile_key

        return None

    def _is_checkbox_click(self, selector: str, selectors: list) -> bool:
        """Determine if a click is on a checkbox element."""
        # Check selector patterns
        selector_lower = selector.lower()

        # Common checkbox ID patterns
        checkbox_patterns = [
            'consent', 'agree', 'accept', 'terms', 'privacy',
            'marketing', 'newsletter', 'subscribe', 'checkbox',
            'opt-in', 'optin', 'check'
        ]

        for pattern in checkbox_patterns:
            if pattern in selector_lower:
                return True

        # Check all selectors for type="checkbox"
        for sel in selectors:
            if isinstance(sel, list):
                sel = sel[0] if sel else ""
            if isinstance(sel, str):
                if 'type="checkbox"' in sel.lower() or '[type=checkbox]' in sel.lower():
                    return True

        return False

    def _is_submit_click(self, step: dict) -> bool:
        """Determine if a click step is a form submit."""
        selectors = step.get("selectors", [])

        # Flatten nested selectors to get all selector strings
        flat_selectors = []
        for sel in selectors:
            if isinstance(sel, list):
                flat_selectors.extend(sel)
            elif isinstance(sel, str):
                flat_selectors.append(sel)

        for sel in flat_selectors:
            if not isinstance(sel, str):
                continue

            sel_lower = sel.lower()

            # Check for submit indicators in selector
            if any(indicator in sel_lower for indicator in [
                'type="submit"',
                '[type=submit]',
                'btn-submit',
                'submitbutton',
                'form-submit'
            ]):
                return True

            # Check button text from aria selectors
            if sel.startswith("aria/"):
                text = sel[5:].lower()
                if any(word in text for word in ['submit', 'send', 'continue', 'next', 'finish', 'create', 'register', 'sign up', 'signup']):
                    return True

            # Check for button element with submit-like text
            if 'button' in sel_lower:
                return True

        return False

    def _get_url_from_recording(self, recording: dict) -> Optional[str]:
        """Extract target URL from recording."""
        for step in recording.get("steps", []):
            if step.get("type") == "navigate":
                return step.get("url")
        return None

    async def _wait_for_page_load(self, timeout: int = 10):
        """Wait for page to fully load."""
        try:
            # Wait for document ready state
            await asyncio.sleep(1)

            for _ in range(timeout * 2):
                ready_state = self.driver.execute_script("return document.readyState")
                logger.debug(f"Page ready state: {ready_state}")
                if ready_state == "complete":
                    break
                await asyncio.sleep(0.5)

            # Extra wait for dynamic content (React/Vue/Angular apps)
            await asyncio.sleep(3)

            # Log page info
            title = self.driver.execute_script("return document.title")
            logger.info(f"Page loaded: {title}")

        except Exception as e:
            logger.warning(f"Page load wait error: {e}")

    async def _bulk_fill_fields(self, fields: List[dict], profile: dict) -> int:
        """
        Bulk fill all text fields at once via JavaScript.

        This is ~10x faster than filling fields one by one.
        """
        if not fields:
            return 0

        # Build selector -> value mappings
        mappings = {}

        for field in fields:
            selector = field.get("selector", "")
            if not selector:
                continue

            # Get value from profile or literal
            if "profile_key" in field:
                key = field["profile_key"]
                value = self._get_profile_value(profile, key)
            else:
                value = field.get("literal_value", "")

            if value:
                mappings[selector] = value

        if not mappings:
            return 0

        try:
            logger.info(f"Bulk fill mappings: {mappings}")

            # Use SeleniumBase methods directly which handle UC mode properly
            filled = 0
            for selector, value in mappings.items():
                try:
                    # Use SeleniumBase's type method which handles UC mode
                    if self.sb.is_element_visible(selector):
                        try:
                            # Get element tag and input type
                            elem_info = self.sb.execute_script(f"""
                                var el = document.querySelector('{selector}');
                                return el ? {{tag: el.tagName, type: el.type || 'text'}} : null;
                            """)
                            if not elem_info:
                                logger.warning(f"Element not found: {selector}")
                                continue

                            tag = elem_info.get('tag', '')
                            input_type = elem_info.get('type', 'text')

                            if tag == 'SELECT':
                                # For dropdowns, try multiple selection strategies
                                selected = self._select_dropdown_value(selector, value)
                                if selected:
                                    filled += 1
                                    logger.info(f"Selected {selector}: {value}")
                                    await asyncio.sleep(self.field_delay)
                                else:
                                    logger.warning(f"Could not select {value} in {selector}")
                            elif input_type == 'date':
                                # HTML5 date input - set via JS with YYYY-MM-DD format
                                formatted = self._format_date_for_input_type(value, 'date')
                                self.sb.execute_script(f"""
                                    var el = document.querySelector('{selector}');
                                    if (el) {{
                                        el.value = '{formatted}';
                                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                                    }}
                                """)
                                filled += 1
                                logger.info(f"Set date {selector}: {formatted}")
                                await asyncio.sleep(self.field_delay)
                            else:
                                # For text inputs, clear and type
                                self.sb.type(selector, value)
                                filled += 1
                                logger.info(f"Filled {selector}")
                                await asyncio.sleep(self.field_delay)
                        except Exception as type_err:
                            logger.warning(f"Could not fill {selector}: {type_err}")
                    else:
                        logger.warning(f"Element not visible: {selector}")

                except Exception as e:
                    logger.error(f"Error filling {selector}: {e}")

            logger.info(f"Bulk filled {filled}/{len(mappings)} fields")
            return filled

        except Exception as e:
            logger.error(f"Bulk fill error: {e}", exc_info=True)
            return 0

    def _get_profile_value(self, profile: dict, key: str) -> str:
        """Get value from profile, supporting nested keys and 'data' wrapper."""
        if not key:
            return ""

        # Flatten profile if it has a 'data' wrapper
        flat_profile = profile.get("data", profile) if isinstance(profile.get("data"), dict) else profile

        # Direct key lookup
        if key in flat_profile:
            return str(flat_profile[key])

        # Try case-insensitive
        key_lower = key.lower()
        for k, v in flat_profile.items():
            if k.lower() == key_lower:
                return str(v)

        # Try nested lookup (personal.firstName)
        if "." in key:
            parts = key.split(".")
            obj = flat_profile
            for part in parts:
                if isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return ""
            return str(obj) if obj else ""

        # Fallback: construct birthdate from components if requesting date field
        if key_lower in ['birthdate', 'date_of_birth', 'dob']:
            constructed = self._construct_date_from_components(flat_profile)
            if constructed:
                return constructed

        return ""

    def _format_date_for_input_type(self, value: str, input_type: str) -> str:
        """Format date value for HTML5 date input (YYYY-MM-DD)."""
        if input_type != 'date':
            return value
        # Already in ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return value
        # Try to parse common formats and convert
        for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%B %d, %Y', '%b %d, %Y']:
            try:
                return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return value

    def _construct_date_from_components(self, profile: dict) -> str:
        """Construct ISO date from birthMonth/birthDay/birthYear."""
        month = self._get_profile_value(profile, 'birthMonth')
        day = self._get_profile_value(profile, 'birthDay')
        year = self._get_profile_value(profile, 'birthYear')
        if not (month and day and year):
            return ""
        try:
            month_num = int(month) if month.isdigit() else self._month_to_number(month)
            day_num = int(day) if day.isdigit() else 1
            return f"{year}-{month_num:02d}-{day_num:02d}"
        except (ValueError, TypeError):
            return ""

    def _month_to_number(self, month: str) -> int:
        """Convert month name to number."""
        months = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
            'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
            'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
            'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        return months.get(month.lower()[:3], 1)

    def _select_dropdown_value(self, selector: str, value: str) -> bool:
        """
        Select a value in a dropdown with smart matching.

        Tries multiple strategies:
        1. Exact text match
        2. Case-insensitive text match
        3. Value attribute match (exact)
        4. Value attribute match (case-insensitive)
        5. Partial text match
        """
        if not value:
            return False

        value_lower = value.lower().strip()

        try:
            # Get all options from the select
            options = self.sb.execute_script(f"""
                var sel = document.querySelector('{selector}');
                if (!sel) return null;
                return Array.from(sel.options).map(o => ({{
                    value: o.value,
                    text: o.text,
                    index: o.index
                }}));
            """)

            if not options:
                return False

            # Strategy 1: Exact text match
            for opt in options:
                if opt['text'] == value:
                    self.sb.execute_script(f"document.querySelector('{selector}').selectedIndex = {opt['index']}")
                    self._trigger_change_event(selector)
                    return True

            # Strategy 2: Case-insensitive text match
            for opt in options:
                if opt['text'].lower().strip() == value_lower:
                    self.sb.execute_script(f"document.querySelector('{selector}').selectedIndex = {opt['index']}")
                    self._trigger_change_event(selector)
                    return True

            # Strategy 3: Exact value attribute match
            for opt in options:
                if opt['value'] == value:
                    self.sb.execute_script(f"document.querySelector('{selector}').value = '{opt['value']}'")
                    self._trigger_change_event(selector)
                    return True

            # Strategy 4: Case-insensitive value match
            for opt in options:
                if opt['value'].lower().strip() == value_lower:
                    self.sb.execute_script(f"document.querySelector('{selector}').value = '{opt['value']}'")
                    self._trigger_change_event(selector)
                    return True

            # Strategy 5: Partial text match (value contains or is contained)
            for opt in options:
                opt_text_lower = opt['text'].lower().strip()
                if value_lower in opt_text_lower or opt_text_lower in value_lower:
                    self.sb.execute_script(f"document.querySelector('{selector}').selectedIndex = {opt['index']}")
                    self._trigger_change_event(selector)
                    return True

            # Strategy 6: Gender-specific mapping
            gender_map = {
                'm': 'male', 'f': 'female', 'male': 'male', 'female': 'female',
                'man': 'male', 'woman': 'female', 'boy': 'male', 'girl': 'female'
            }
            mapped_value = gender_map.get(value_lower)
            if mapped_value:
                for opt in options:
                    if mapped_value in opt['text'].lower():
                        self.sb.execute_script(f"document.querySelector('{selector}').selectedIndex = {opt['index']}")
                        self._trigger_change_event(selector)
                        return True

            logger.warning(f"No matching option found for '{value}' in {selector}")
            return False

        except Exception as e:
            logger.error(f"Dropdown selection error: {e}")
            return False

    def _trigger_change_event(self, selector: str):
        """Trigger change event on element."""
        self.sb.execute_script(f"""
            var el = document.querySelector('{selector}');
            if (el) {{
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
            }}
        """)

    async def _check_checkboxes(self, checkboxes: List[str]) -> int:
        """Check all checkboxes using SeleniumBase methods."""
        if not checkboxes:
            return 0

        checked = 0
        for selector in checkboxes:
            try:
                if self.sb.is_element_visible(selector):
                    # Use SeleniumBase click which handles UC mode
                    if not self.sb.is_selected(selector):
                        self.sb.click(selector)
                        checked += 1
                        logger.info(f"Checked checkbox: {selector}")
                        await asyncio.sleep(self.field_delay)
                    else:
                        logger.debug(f"Checkbox already checked: {selector}")
                        checked += 1
                else:
                    logger.warning(f"Checkbox not visible: {selector}")
            except Exception as e:
                logger.error(f"Checkbox error for {selector}: {e}")

        return checked

    async def _select_radios(self, radios: List[dict]) -> int:
        """Select radio buttons using SeleniumBase methods."""
        if not radios:
            return 0

        selected = 0
        for radio in radios:
            selector = radio.get("selector", "")
            try:
                if self.sb.is_element_visible(selector):
                    self.sb.click(selector)
                    selected += 1
                    logger.info(f"Selected radio: {selector}")
                    await asyncio.sleep(self.field_delay)
                else:
                    logger.warning(f"Radio not visible: {selector}")
            except Exception as e:
                logger.error(f"Radio error for {selector}: {e}")

        return selected

    async def _click_submit(self, selector: str) -> bool:
        """Click the submit button using SeleniumBase."""
        if not selector:
            return False

        try:
            if self.sb.is_element_visible(selector):
                self.sb.click(selector)
                logger.info(f"Clicked submit: {selector}")
                return True
            else:
                logger.warning(f"Submit button not visible: {selector}")
                return False
        except Exception as e:
            logger.error(f"Submit click error: {e}")
            return False
