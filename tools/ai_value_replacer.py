"""
AI-powered value replacement for Chrome DevTools recordings.

This module replaces sample values in recordings with actual profile data
using AI to intelligently map fields and handle format conversions.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class AIValueReplacer:
    """Replaces recording values with profile data using AI analysis."""

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-chat"):
        """
        Initialize AI value replacer.

        Args:
            api_key: OpenRouter API key
            model: Model to use for analysis (default: deepseek-chat)
        """
        self.api_key = api_key
        self.model = model
        self.api_base = "https://openrouter.ai/api/v1/chat/completions"

    def replace_recording_values(
        self,
        recording: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replace all values in recording with profile data.

        Args:
            recording: Chrome DevTools recording
            profile: User profile data

        Returns:
            Modified recording with profile values
        """
        logger.info(f"Replacing values in recording: {recording.get('title', 'Unknown')}")

        modified_recording = recording.copy()
        modified_recording['steps'] = []

        # Track which fields we've filled to avoid duplicates
        filled_fields = set()

        for step in recording.get('steps', []):
            step_type = step.get('type', '')

            # Only process steps that set values
            if step_type in ['change', 'click'] and 'selectors' in step:
                modified_step = step.copy()

                # Get field identifier from selectors
                field_id = self._get_field_identifier(step.get('selectors', []))

                # Skip if we already filled this field
                if field_id in filled_fields:
                    continue

                # Get the original sample value
                original_value = step.get('value', '')

                if original_value and step_type == 'change':
                    # Use AI to map to profile field
                    profile_value = self._map_field_with_ai(
                        field_id,
                        original_value,
                        profile,
                        step.get('selectors', [])
                    )

                    if profile_value:
                        modified_step['value'] = profile_value
                        filled_fields.add(field_id)
                        logger.info(f"Replaced {field_id}: '{original_value}' → '{profile_value}'")

                modified_recording['steps'].append(modified_step)
            else:
                # Keep non-value steps as-is (navigate, keydown, etc.)
                modified_recording['steps'].append(step.copy())

        return modified_recording

    def _get_field_identifier(self, selectors: List[List[str]]) -> str:
        """Extract a unique field identifier from selectors."""
        if not selectors:
            return ""

        # Try to get ID selector
        for selector_group in selectors:
            for selector in selector_group:
                if selector.startswith('#'):
                    return selector
                elif selector.startswith('aria/'):
                    return selector

        # Fallback to first selector
        return selectors[0][0] if selectors[0] else ""

    def _map_field_with_ai(
        self,
        field_id: str,
        sample_value: str,
        profile: Dict[str, Any],
        selectors: List[List[str]]
    ) -> Optional[str]:
        """
        Use AI to map field to profile data and return appropriate value.

        Args:
            field_id: Field identifier (e.g., "#firstName")
            sample_value: Original recorded value
            profile: User profile data
            selectors: All available selectors for context

        Returns:
            Profile value or None if no match
        """
        # First try direct pattern matching for common cases (faster)
        direct_match = self._try_direct_match(field_id, sample_value, profile, selectors)
        if direct_match:
            return direct_match

        # Fall back to AI for complex mappings
        return self._ai_field_mapping(field_id, sample_value, profile, selectors)

    def _try_direct_match(
        self,
        field_id: str,
        sample_value: str,
        profile: Dict[str, Any],
        selectors: List[List[str]]
    ) -> Optional[str]:
        """Try direct pattern matching before using AI."""
        field_lower = field_id.lower()

        # Get all selector text for analysis
        selector_text = ' '.join([
            ' '.join(group) for group in selectors
        ]).lower()

        # Date field detection
        if self._is_date_field(field_lower, selector_text, sample_value):
            return self._construct_date_value(profile, sample_value)

        # Name fields
        if 'firstname' in field_lower or 'first-name' in field_lower or 'fname' in field_lower:
            return profile.get('firstName', profile.get('firstname', ''))

        if 'lastname' in field_lower or 'last-name' in field_lower or 'lname' in field_lower:
            return profile.get('lastName', profile.get('lastname', ''))

        # Email
        if 'email' in field_lower or 'e-mail' in field_lower:
            return profile.get('email', '')

        # Phone
        if 'phone' in field_lower or 'mobile' in field_lower or 'tel' in field_lower:
            return profile.get('phone', profile.get('mobilePhone', ''))

        # Address fields
        if 'address' in field_lower and 'line1' in field_lower:
            return profile.get('address', profile.get('homeAddress', ''))

        if 'city' in field_lower:
            return profile.get('city', profile.get('homeCity', ''))

        if 'state' in field_lower or 'province' in field_lower:
            return profile.get('state', profile.get('homeState', ''))

        if 'zip' in field_lower or 'postal' in field_lower:
            return profile.get('zipCode', profile.get('homeZip', ''))

        if 'country' in field_lower:
            return profile.get('country', profile.get('homeCountry', ''))

        # Gender
        if 'gender' in field_lower or 'sex' in field_lower:
            gender = profile.get('gender', '')
            # Normalize gender values
            if gender.lower() in ['m', 'male', 'man']:
                return 'MALE'
            elif gender.lower() in ['f', 'female', 'woman']:
                return 'FEMALE'
            return gender

        return None

    def _is_date_field(self, field_id: str, selector_text: str, sample_value: str) -> bool:
        """Detect if this is a date field."""
        date_patterns = [
            'birthdate', 'birth-date', 'dob', 'date-of-birth',
            'birthday', 'birth_date', 'dateofbirth'
        ]

        # Check field ID
        for pattern in date_patterns:
            if pattern in field_id:
                return True

        # Check all selectors
        for pattern in date_patterns:
            if pattern in selector_text:
                return True

        # Check if sample value looks like a date
        if sample_value:
            # Check for date patterns: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY
            if re.match(r'\d{4}-\d{2}-\d{2}', sample_value):
                return True
            if re.match(r'\d{2}/\d{2}/\d{4}', sample_value):
                return True

        return False

    def _construct_date_value(self, profile: Dict[str, Any], sample_value: str) -> Optional[str]:
        """
        Construct date value from profile data.

        Handles both separate components (birthMonth, birthDay, birthYear)
        and full date fields.
        """
        # Try to get separate components first
        month = profile.get('birthMonth', '')
        day = profile.get('birthDay', '')
        year = profile.get('birthYear', '')

        if month and day and year:
            # Convert month name to number if needed
            month_num = self._convert_month_to_number(month)

            # Detect format from sample value
            if sample_value:
                if '-' in sample_value:
                    # ISO format: YYYY-MM-DD
                    return f"{year}-{month_num:02d}-{int(day):02d}"
                elif sample_value.startswith(year):
                    # Year first: YYYY/MM/DD
                    return f"{year}/{month_num:02d}/{int(day):02d}"
                else:
                    # Month first: MM/DD/YYYY
                    return f"{month_num:02d}/{int(day):02d}/{year}"
            else:
                # Default to ISO format
                return f"{year}-{month_num:02d}-{int(day):02d}"

        # Try full date field
        full_date = profile.get('birthdate', profile.get('dateOfBirth', ''))
        if full_date:
            return full_date

        return None

    def _convert_month_to_number(self, month: str) -> int:
        """Convert month name or number to integer."""
        if month.isdigit():
            return int(month)

        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }

        return month_map.get(month.lower(), 1)

    def _ai_field_mapping(
        self,
        field_id: str,
        sample_value: str,
        profile: Dict[str, Any],
        selectors: List[List[str]]
    ) -> Optional[str]:
        """
        Use AI to intelligently map field to profile data.

        This is used for complex fields that don't match simple patterns.
        """
        try:
            # Build prompt for AI
            prompt = self._build_mapping_prompt(field_id, sample_value, profile, selectors)

            # Call OpenRouter API
            response = requests.post(
                self.api_base,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a form field mapping expert. Return ONLY the value to fill, no explanation."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                value = result['choices'][0]['message']['content'].strip()

                # Clean up response (remove quotes, extra text)
                value = value.strip('"\'')

                logger.info(f"AI mapped {field_id} to: {value}")
                return value
            else:
                logger.error(f"OpenRouter API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"AI mapping failed: {e}")
            return None

    def _build_mapping_prompt(
        self,
        field_id: str,
        sample_value: str,
        profile: Dict[str, Any],
        selectors: List[List[str]]
    ) -> str:
        """Build prompt for AI field mapping."""
        return f"""Map this form field to the profile data.

Field ID: {field_id}
Sample Value: {sample_value}
All Selectors: {json.dumps(selectors)}

Profile Data:
{json.dumps(profile, indent=2)}

What value from the profile should be used for this field?
Return ONLY the value, nothing else."""


def replace_values_in_recording(
    recording_path: str,
    profile: Dict[str, Any],
    api_key: str,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to replace values in a recording file.

    Args:
        recording_path: Path to recording JSON file
        profile: User profile data
        api_key: OpenRouter API key
        output_path: Optional output path (if None, returns modified recording)

    Returns:
        Modified recording
    """
    with open(recording_path, 'r', encoding='utf-8') as f:
        recording = json.load(f)

    replacer = AIValueReplacer(api_key)
    modified_recording = replacer.replace_recording_values(recording, profile)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(modified_recording, f, indent=2)
        logger.info(f"Saved modified recording to: {output_path}")

    return modified_recording
