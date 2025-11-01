#!/usr/bin/env python3
"""
Chrome DevTools Recorder Parser - Convert Chrome Recorder JSON to FormAI format
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import hashlib

class ChromeRecorderParser:
    """Parses Chrome DevTools Recorder JSON files and converts them to FormAI format"""

    def __init__(self):
        self.field_type_mapping = {
            # Chrome Recorder types to FormAI profile field mappings
            'change': 'textbox',
            'click': 'button',
            'keydown': 'textbox',
            'keyup': 'textbox',
            'scroll': 'scroll',
            'navigate': 'navigation',
            'waitForElement': 'wait',
            'waitForExpression': 'wait'
        }

        # Common field name patterns for smart detection
        self.field_patterns = {
            'firstName': ['first_name', 'fname', 'firstname', 'given_name', 'first-name'],
            'lastName': ['last_name', 'lname', 'lastname', 'family_name', 'last-name', 'surname'],
            'fullName': ['full_name', 'fullname', 'name', 'full-name', 'display_name'],
            'email': ['email', 'e_mail', 'e-mail', 'email_address', 'emailaddress'],
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone_number'],
            'address1': ['address', 'address1', 'street', 'address_line_1', 'street_address'],
            'address2': ['address2', 'address_line_2', 'apt', 'apartment', 'suite'],
            'city': ['city', 'town', 'locality'],
            'state': ['state', 'province', 'region', 'state_province'],
            'zip': ['zip', 'postal', 'postcode', 'postal_code', 'zipcode'],
            'country': ['country', 'nation'],
            'company': ['company', 'organization', 'employer', 'business'],
            'title': ['title', 'prefix', 'salutation'],
            'username': ['username', 'user_name', 'login', 'userid', 'user_id'],
            'password': ['password', 'pass', 'pwd', 'passphrase'],
            'creditCardNumber': ['cc_number', 'card_number', 'credit_card', 'cardnumber'],
            'creditCardExpMonth': ['exp_month', 'cc_exp_month', 'expiry_month'],
            'creditCardExpYear': ['exp_year', 'cc_exp_year', 'expiry_year'],
            'creditCardCVC': ['cvc', 'cvv', 'security_code', 'cvv2'],
            'birthMonth': ['birth_month', 'dob_month', 'bmonth'],
            'birthDay': ['birth_day', 'dob_day', 'bday'],
            'birthYear': ['birth_year', 'dob_year', 'byear'],
            'age': ['age', 'years_old'],
            'sex': ['sex', 'gender'],
            'ssn': ['ssn', 'social_security', 'social_security_number']
        }

    def parse_chrome_recording(self, chrome_recording_path: str) -> Dict[str, Any]:
        """
        Parse a Chrome DevTools Recorder JSON file

        Args:
            chrome_recording_path: Path to the Chrome Recorder JSON file

        Returns:
            Dict containing parsed recording in FormAI format
        """
        try:
            with open(chrome_recording_path, 'r', encoding='utf-8') as f:
                chrome_data = json.load(f)

            return self._convert_to_formai_format(chrome_data)

        except Exception as e:
            raise Exception(f"Error parsing Chrome recording: {e}")

    def parse_chrome_recording_data(self, chrome_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Chrome DevTools Recorder JSON data directly

        Args:
            chrome_data: Chrome Recorder JSON data as dict

        Returns:
            Dict containing parsed recording in FormAI format
        """
        return self._convert_to_formai_format(chrome_data)

    def _convert_to_formai_format(self, chrome_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Chrome Recorder format to FormAI format"""

        # Extract basic metadata
        title = chrome_data.get('title', 'Imported Chrome Recording')

        url = self._extract_url_from_steps(chrome_data.get('steps', []))

        # Process steps to extract form field interactions
        field_mappings = self._extract_field_mappings(chrome_data.get('steps', []))

        # Generate recording metadata
        recording_id = self._generate_recording_id(title, url)

        formai_recording = {
            "recording_id": recording_id,
            "recording_name": title,
            "url": url,
            "description": f"Imported from Chrome DevTools Recorder - {title}",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "import_source": "chrome_devtools_recorder",
            "total_fields_filled": len(field_mappings),
            "field_mappings": field_mappings,
            "chrome_steps": chrome_data.get('steps', []),  # Keep original for reference
            "success_rate": "pending",  # Will be updated after first successful replay
            "notes": f"Automatically converted from Chrome DevTools Recorder. {len(field_mappings)} form fields detected.",
            "automation_method": "seleniumbase_cdp",
            "created_timestamp": datetime.now().isoformat()
        }

        return formai_recording

    def _extract_url_from_steps(self, steps: List[Dict[str, Any]]) -> str:
        """Extract the main URL from navigation steps"""
        for step in steps:
            if step.get('type') == 'navigate' and step.get('url'):
                return step['url']
        return "unknown"

    def _extract_field_mappings(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract form field interactions from Chrome Recorder steps"""
        field_mappings_dict = {}  # Use dict to deduplicate by selector

        for i, step in enumerate(steps):
            step_type = step.get('type', '')

            # Focus on form interaction steps
            if step_type in ['change', 'click'] and self._is_form_field_step(step):
                field_mapping = self._create_field_mapping(step, i)
                if field_mapping:
                    selector = field_mapping['field_selector']

                    # Keep the last occurrence (most complete value) or first if selector not seen
                    # This deduplicates fields that have multiple change events
                    if selector not in field_mappings_dict:
                        field_mappings_dict[selector] = field_mapping
                    else:
                        # Update with last value (usually the most complete)
                        existing = field_mappings_dict[selector]
                        # Prefer non-empty sample values
                        if field_mapping.get('sample_value'):
                            existing['sample_value'] = field_mapping['sample_value']
                        existing['step_index'] = i  # Update to latest step

        # Convert dict back to list, sorted by step_index to maintain order
        field_mappings = sorted(field_mappings_dict.values(), key=lambda x: x.get('step_index', 0))
        return field_mappings

    def _is_form_field_step(self, step: Dict[str, Any]) -> bool:
        """Determine if a step represents a form field interaction"""
        selectors = step.get('selectors', [])
        if not selectors:
            return False

        # Check if step targets input elements or form controls
        for selector_list in selectors:
            for selector in selector_list:
                # Look for form element patterns
                if any(pattern in selector.lower() for pattern in [
                    'input', 'select', 'textarea', 'form', '[name=', '[id=', '#', 'button[type="submit"]'
                ]):
                    return True

        return False

    def _create_field_mapping(self, step: Dict[str, Any], step_index: int) -> Optional[Dict[str, Any]]:
        """Create a field mapping from a Chrome Recorder step"""
        try:
            selectors = step.get('selectors', [])
            if not selectors:
                return None

            # Use the first available selector
            best_selector = self._get_best_selector(selectors)
            if not best_selector:
                return None

            # Extract field information
            field_name = self._extract_field_name(step, best_selector)
            field_type = self._determine_field_type(step, best_selector)
            profile_mapping = self._map_to_profile_field(field_name, best_selector)
            sample_value = step.get('value', '') or self._generate_sample_value(profile_mapping)

            return {
                "field_name": field_name,
                "field_selector": best_selector,
                "field_type": field_type,
                "profile_mapping": profile_mapping,
                "sample_value": sample_value,
                "step_index": step_index,
                "original_step": step,  # Keep for debugging
                "confidence": self._calculate_confidence(field_name, best_selector, profile_mapping)
            }

        except Exception as e:
            print(f"Warning: Could not create field mapping for step {step_index}: {e}")
            return None

    def _get_best_selector(self, selectors: List[List[str]]) -> Optional[str]:
        """Select the best selector from available options"""
        # Prefer non-ARIA selectors (CSS/XPath)
        for selector_list in selectors:
            for selector in selector_list:
                if not selector.startswith('aria/'):
                    return selector

        # If only ARIA selectors available, return the first one
        for selector_list in selectors:
            if selector_list and len(selector_list) > 0:
                return selector_list[0]

        return None

    def _extract_field_name(self, step: Dict[str, Any], selector: str) -> str:
        """Extract a human-readable field name"""
        # Try to extract from name attribute
        name_match = re.search(r'\[name=["\']([^"\']+)["\']', selector)
        if name_match:
            name = name_match.group(1)
            return self._humanize_field_name(name)

        # Try to extract from ID
        id_match = re.search(r'#([a-zA-Z0-9_-]+)', selector)
        if id_match:
            field_id = id_match.group(1)
            return self._humanize_field_name(field_id)

        # Try to extract from selector patterns
        if 'input' in selector.lower():
            return f"Input Field"
        elif 'select' in selector.lower():
            return f"Select Field"
        elif 'textarea' in selector.lower():
            return f"Text Area"

        return f"Form Field"

    def _humanize_field_name(self, field_name: str) -> str:
        """Convert field names to human-readable format"""
        # Remove common prefixes/suffixes
        field_name = re.sub(r'^(input|field|form)[-_]?', '', field_name, flags=re.IGNORECASE)
        field_name = re.sub(r'[-_]?(input|field|form)$', '', field_name, flags=re.IGNORECASE)

        # Split on common separators and capitalize
        words = re.split(r'[-_\s]+', field_name)
        words = [word.capitalize() for word in words if word]

        return ' '.join(words) or 'Form Field'

    def _determine_field_type(self, step: Dict[str, Any], selector: str) -> str:
        """Determine the field type from the step and selector"""
        step_type = step.get('type', '')

        # Map Chrome step types to field types
        if step_type == 'change':
            if 'select' in selector.lower():
                return 'select'
            elif 'textarea' in selector.lower():
                return 'textarea'
            else:
                return 'textbox'
        elif step_type == 'click':
            if 'button' in selector.lower() or 'submit' in selector.lower():
                return 'button'
            elif 'checkbox' in selector.lower() or 'type="checkbox"' in selector.lower():
                return 'checkbox'
            elif 'radio' in selector.lower() or 'type="radio"' in selector.lower():
                return 'radio'
            else:
                return 'clickable'

        return 'textbox'  # Default

    def _map_to_profile_field(self, field_name: str, selector: str) -> str:
        """Map detected field to profile field name"""
        # Combine field name and selector for pattern matching
        search_text = f"{field_name} {selector}".lower()

        # Check against known patterns
        for profile_field, patterns in self.field_patterns.items():
            for pattern in patterns:
                if pattern in search_text:
                    return profile_field

        # Fallback to basic field name mapping
        field_lower = field_name.lower().replace(' ', '_')

        # Direct mappings
        direct_mappings = {
            'first_name': 'firstName',
            'last_name': 'lastName',
            'full_name': 'fullName',
            'e_mail': 'email',
            'phone_number': 'phone',
            'home_phone': 'homePhone',
            'work_phone': 'workPhone',
            'cell_phone': 'cellPhone',
            'address_1': 'address1',
            'address_2': 'address2',
            'zip_code': 'zip',
            'postal_code': 'zip',
            'credit_card': 'creditCardNumber',
            'birth_date': 'birthDate'
        }

        return direct_mappings.get(field_lower, field_lower)

    def _generate_sample_value(self, profile_mapping: str) -> str:
        """Generate sample values for fields without recorded values"""
        sample_values = {
            'firstName': 'John',
            'lastName': 'Smith',
            'fullName': 'John Smith',
            'email': 'john.smith@example.com',
            'phone': '(555) 123-4567',
            'homePhone': '(555) 123-4567',
            'workPhone': '(555) 987-6543',
            'cellPhone': '(555) 456-7890',
            'address1': '123 Main Street',
            'address2': 'Apt 4B',
            'city': 'New York',
            'state': 'NY',
            'zip': '10001',
            'country': 'USA',
            'company': 'Tech Corp',
            'title': 'Mr.',
            'username': 'johnsmith',
            'password': 'SecurePass123!',
            'creditCardNumber': '4111111111111111',
            'creditCardExpMonth': '12',
            'creditCardExpYear': '2027',
            'creditCardCVC': '123',
            'birthMonth': 'Jan',
            'birthDay': '15',
            'birthYear': '1990',
            'age': '34',
            'sex': 'M',
            'ssn': '123-45-6789'
        }

        return sample_values.get(profile_mapping, 'Sample Value')

    def _calculate_confidence(self, field_name: str, selector: str, profile_mapping: str) -> float:
        """Calculate confidence score for field mapping accuracy"""
        confidence = 0.5  # Base confidence

        # Boost confidence for name attributes
        if '[name=' in selector:
            confidence += 0.3

        # Boost confidence for ID attributes
        if '#' in selector or '[id=' in selector:
            confidence += 0.2

        # Boost confidence for good profile mapping matches
        field_lower = field_name.lower()
        if profile_mapping.lower() in field_lower or field_lower in profile_mapping.lower():
            confidence += 0.2

        # Boost confidence for common field patterns
        for profile_field, patterns in self.field_patterns.items():
            if profile_field == profile_mapping:
                for pattern in patterns:
                    if pattern in selector.lower() or pattern in field_name.lower():
                        confidence += 0.1
                        break

        return min(confidence, 1.0)

    def _generate_recording_id(self, title: str, url: str) -> str:
        """Generate a unique recording ID"""
        content = f"{title}_{url}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def validate_chrome_recording(self, chrome_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate Chrome DevTools Recorder JSON format

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if 'title' not in chrome_data:
            errors.append("Missing 'title' field")

        if 'steps' not in chrome_data:
            errors.append("Missing 'steps' field")
        elif not isinstance(chrome_data['steps'], list):
            errors.append("'steps' must be a list")
        elif len(chrome_data['steps']) == 0:
            errors.append("'steps' list is empty")

        # Validate steps structure
        steps = chrome_data.get('steps', [])
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i} must be a dictionary")
                continue

            if 'type' not in step:
                errors.append(f"Step {i} missing 'type' field")

        # Check for form interactions
        has_form_interactions = any(
            self._is_form_field_step(step) for step in steps
        )

        if not has_form_interactions:
            errors.append("No form field interactions detected in recording")

        return len(errors) == 0, errors

def main():
    """Test the Chrome Recorder Parser"""
    parser = ChromeRecorderParser()

    # Test with sample Chrome Recorder data
    sample_chrome_data = {
        "title": "Test Form Recording",
        "steps": [
            {
                "type": "navigate",
                "url": "https://example.com/form"
            },
            {
                "type": "change",
                "selectors": [["input[name=\"first_name\"]"]],
                "value": "John"
            },
            {
                "type": "change",
                "selectors": [["input[name=\"email\"]"]],
                "value": "john@example.com"
            }
        ]
    }

    # Test validation
    is_valid, errors = parser.validate_chrome_recording(sample_chrome_data)
    print(f"Validation: {'Valid' if is_valid else 'Invalid'}")
    if errors:
        print("Errors:", errors)

    # Test conversion
    if is_valid:
        formai_recording = parser.parse_chrome_recording_data(sample_chrome_data)
        print(f"Converted recording: {formai_recording['recording_name']}")
        print(f"Fields detected: {len(formai_recording['field_mappings'])}")

        for field in formai_recording['field_mappings']:
            print(f"  - {field['field_name']}: {field['profile_mapping']} (confidence: {field['confidence']:.2f})")

if __name__ == "__main__":
    main()