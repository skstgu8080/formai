"""
Recording Trainer - Extract Field Mappings from Chrome DevTools Recordings

Parses Chrome DevTools recordings to extract field mappings,
enabling "Learn Once, Replay Many" - fill a form once, use forever.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("recording-trainer")


def normalize_profile_field(field_name: str) -> str:
    """
    Normalize field names to standard profile field names.

    Handles variations like:
    - "suburb/City" -> "city"
    - "first_name" -> "firstName"
    - "postalCode" -> "zip"
    """
    if not field_name:
        return field_name

    # Convert to lowercase for matching
    field_lower = field_name.lower().replace(' ', '').replace('-', '').replace('_', '').replace('/', '')

    NORMALIZATIONS = {
        'firstname': 'firstName', 'fname': 'firstName', 'givenname': 'firstName',
        'lastname': 'lastName', 'lname': 'lastName', 'surname': 'lastName', 'familyname': 'lastName',
        'fullname': 'name', 'yourname': 'name',
        'email': 'email', 'mail': 'email', 'emailaddress': 'email',
        'password': 'password', 'passwd': 'password', 'pwd': 'password',
        'phone': 'phone', 'mobile': 'phone', 'telephone': 'phone', 'tel': 'phone', 'cell': 'phone',
        'address': 'address', 'street': 'address', 'address1': 'address', 'addressline1': 'address',
        'address2': 'address2', 'addressline2': 'address2', 'apt': 'address2', 'suite': 'address2',
        'city': 'city', 'town': 'city', 'suburb': 'city', 'locality': 'city', 'suburbcity': 'city',
        'state': 'state', 'province': 'state', 'region': 'state',
        'zip': 'zip', 'zipcode': 'zip', 'postalcode': 'zip', 'postcode': 'zip', 'postal': 'zip',
        'country': 'country', 'nation': 'country',
        'company': 'company', 'organization': 'company', 'companyname': 'company',
        'username': 'username', 'user': 'username', 'login': 'username',
        'dob': 'dateOfBirth', 'dateofbirth': 'dateOfBirth', 'birthday': 'dateOfBirth', 'birthdate': 'dateOfBirth',
        'gender': 'gender', 'sex': 'gender',
    }

    # Check if already a standard field name
    standard_fields = ['email', 'firstName', 'lastName', 'name', 'password', 'phone',
                       'address', 'address2', 'city', 'state', 'zip', 'country',
                       'company', 'username', 'dateOfBirth', 'gender', 'middleName', 'jobTitle']

    if field_name in standard_fields:
        return field_name

    if field_lower in NORMALIZATIONS:
        return NORMALIZATIONS[field_lower]

    # Check partial matches
    for pattern, standard in NORMALIZATIONS.items():
        if pattern in field_lower or field_lower in pattern:
            return standard

    return field_name


class RecordingTrainer:
    """
    Extract field mappings from Chrome DevTools recordings.

    Chrome recordings contain 'change' events with aria labels that
    tell us what type of field it is (First name, Email, etc).
    We map these to profile fields for automated filling.
    """

    # Map aria labels to profile fields
    ARIA_TO_PROFILE = {
        # Name fields
        'first name': 'firstName',
        'firstname': 'firstName',
        'given name': 'firstName',
        'last name': 'lastName',
        'lastname': 'lastName',
        'family name': 'lastName',
        'surname': 'lastName',
        'full name': 'name',
        'name': 'name',
        'middle name': 'middleName',

        # Contact fields
        'email': 'email',
        'email address': 'email',
        'e-mail': 'email',
        'phone': 'phone',
        'phone number': 'phone',
        'telephone': 'phone',
        'mobile': 'phone',
        'mobile number': 'phone',
        'cell': 'phone',
        'cell phone': 'phone',

        # Address fields
        'address': 'address',
        'address line 1': 'address1',
        'address 1': 'address1',
        'street': 'address1',
        'street address': 'address1',
        'address line 2': 'address2',
        'address 2': 'address2',
        'apartment': 'address2',
        'apt': 'address2',
        'suite': 'address2',
        'city': 'city',
        'town': 'city',
        'state': 'state',
        'province': 'state',
        'region': 'state',
        'zip': 'zip',
        'zip code': 'zip',
        'postal': 'zip',
        'postal code': 'zip',
        'postcode': 'zip',
        'country': 'country',

        # Personal fields
        'password': 'password',
        'birthday': 'dateOfBirth',
        'birthdate': 'dateOfBirth',
        'date of birth': 'dateOfBirth',
        'dob': 'dateOfBirth',
        'birth date': 'dateOfBirth',
        'gender': 'gender',
        'sex': 'gender',

        # Business fields
        'company': 'company',
        'company name': 'company',
        'organization': 'company',
        'business': 'company',
        'job title': 'jobTitle',
        'title': 'jobTitle',
        'position': 'jobTitle',

        # Account fields
        'username': 'username',
        'user name': 'username',
        'login': 'username',
    }

    # CSS selector patterns to infer field type
    SELECTOR_PATTERNS = {
        r'first[-_]?name': 'firstName',
        r'fname': 'firstName',
        r'last[-_]?name': 'lastName',
        r'lname': 'lastName',
        r'full[-_]?name': 'name',
        r'email': 'email',
        r'e[-_]?mail': 'email',
        r'phone': 'phone',
        r'telephone': 'phone',
        r'mobile': 'phone',
        r'password': 'password',
        r'pwd': 'password',
        r'pass': 'password',
        r'birth[-_]?date': 'dateOfBirth',
        r'dob': 'dateOfBirth',
        r'birthday': 'dateOfBirth',
        r'gender': 'gender',
        r'sex': 'gender',
        r'address': 'address1',
        r'street': 'address1',
        r'city': 'city',
        r'state': 'state',
        r'province': 'state',
        r'zip': 'zip',
        r'postal': 'zip',
        r'postcode': 'zip',
        r'country': 'country',
        r'company': 'company',
        r'org': 'company',
        r'username': 'username',
    }

    def __init__(self):
        """Initialize the recording trainer."""
        self.stats = {
            "recordings_processed": 0,
            "fields_extracted": 0,
            "domains_trained": set()
        }

    def extract_mappings(self, recording: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract field mappings from a Chrome DevTools recording.

        Args:
            recording: Chrome DevTools recording JSON

        Returns:
            List of mappings: [{"selector": "#email", "profile_field": "email"}, ...]
        """
        mappings = []
        steps = recording.get("steps", [])

        for step in steps:
            step_type = step.get("type", "")

            # Only process 'change' events (field fills)
            if step_type != "change":
                continue

            selectors = step.get("selectors", [])
            if not selectors:
                continue

            # Try to determine the profile field from aria label or selector
            profile_field = self._determine_profile_field(selectors)
            if not profile_field:
                continue

            # Get the best CSS selector
            css_selector = self._get_best_selector(selectors)
            if not css_selector:
                continue

            # Avoid duplicates
            if any(m["selector"] == css_selector for m in mappings):
                continue

            # Normalize profile field name (e.g., "suburb/City" -> "city")
            normalized_field = normalize_profile_field(profile_field)

            mappings.append({
                "selector": css_selector,
                "profile_field": normalized_field
            })
            logger.debug(f"Extracted mapping: {css_selector} -> {normalized_field}")

        self.stats["fields_extracted"] += len(mappings)
        return mappings

    def _determine_profile_field(self, selectors: List) -> Optional[str]:
        """
        Determine the profile field from selectors.

        Priority:
        1. Aria labels (most reliable)
        2. CSS selector patterns
        """
        # First, try aria labels
        for selector_group in selectors:
            if not selector_group:
                continue

            for selector in (selector_group if isinstance(selector_group, list) else [selector_group]):
                if selector.startswith("aria/"):
                    aria_label = selector.replace("aria/", "").lower().strip()
                    # Remove role prefixes like [role="..."]
                    aria_label = re.sub(r'\[role="[^"]*"\]', '', aria_label).strip()

                    # Skip empty aria labels (after removing role prefixes)
                    if not aria_label:
                        continue

                    # Direct lookup
                    if aria_label in self.ARIA_TO_PROFILE:
                        return self.ARIA_TO_PROFILE[aria_label]

                    # Fuzzy match - only if aria_label is non-empty
                    for pattern, field in self.ARIA_TO_PROFILE.items():
                        if pattern in aria_label or aria_label in pattern:
                            return field

        # Fall back to CSS selector patterns
        for selector_group in selectors:
            if not selector_group:
                continue

            for selector in (selector_group if isinstance(selector_group, list) else [selector_group]):
                if selector.startswith("#") or selector.startswith("."):
                    selector_lower = selector.lower()
                    for pattern, field in self.SELECTOR_PATTERNS.items():
                        if re.search(pattern, selector_lower):
                            return field

        return None

    def _get_best_selector(self, selectors: List) -> Optional[str]:
        """
        Get the best CSS selector from selector groups.

        Priority:
        1. ID selectors (#id)
        2. Pierce selectors (pierce/#id)
        3. XPath as last resort
        """
        id_selector = None
        css_selector = None
        xpath_selector = None

        for selector_group in selectors:
            if not selector_group:
                continue

            for selector in (selector_group if isinstance(selector_group, list) else [selector_group]):
                # Skip aria selectors (not usable directly)
                if selector.startswith("aria/"):
                    continue

                # ID selector is best
                if selector.startswith("#") and not id_selector:
                    id_selector = selector

                # Pierce selector (shadow DOM)
                elif selector.startswith("pierce/"):
                    pierce_sel = selector.replace("pierce/", "")
                    if pierce_sel.startswith("#") and not id_selector:
                        id_selector = pierce_sel
                    elif not css_selector:
                        css_selector = pierce_sel

                # XPath (last resort)
                elif selector.startswith("xpath/"):
                    if not xpath_selector:
                        xpath_selector = selector

                # Regular CSS selector
                elif not css_selector:
                    css_selector = selector

        return id_selector or css_selector or xpath_selector

    def extract_domain(self, recording: Dict[str, Any]) -> Optional[str]:
        """
        Extract the domain from a recording.

        Looks for navigate steps or asserted events.
        """
        steps = recording.get("steps", [])

        for step in steps:
            # Check navigate step
            if step.get("type") == "navigate":
                url = step.get("url", "")
                if url:
                    parsed = urlparse(url)
                    return parsed.netloc

            # Check asserted events
            asserted_events = step.get("assertedEvents", [])
            for event in asserted_events:
                url = event.get("url", "")
                if url:
                    parsed = urlparse(url)
                    return parsed.netloc

        return None

    def extract_url(self, recording: Dict[str, Any]) -> Optional[str]:
        """Extract the URL from a recording."""
        steps = recording.get("steps", [])

        for step in steps:
            if step.get("type") == "navigate":
                return step.get("url")

        return None

    def analyze_field(self, selector: str, sb) -> Dict[str, Any]:
        """
        Analyze a field on the live page to determine optimal fill strategy.

        Args:
            selector: CSS selector for the field
            sb: SeleniumBase browser instance

        Returns:
            Dict with field_info and fill strategy
        """
        try:
            # Get field characteristics via JavaScript
            field_info = sb.execute_script(f'''
                var el = document.querySelector("{selector}");
                if (!el) return null;
                return {{
                    tagName: el.tagName.toLowerCase(),
                    type: el.type || null,
                    inputMode: el.inputMode || null,
                    hasOptions: el.tagName === 'SELECT' ? el.options.length : 0,
                    isCustomDropdown: el.closest('.dropdown, [class*="select"], [class*="combobox"]') !== null,
                    pattern: el.pattern || null,
                    required: el.required || false,
                    placeholder: el.placeholder || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    name: el.name || null,
                    id: el.id || null
                }};
            ''')

            if not field_info:
                return {"fill_strategy": "direct_type", "input_type": "unknown"}

            return self._determine_fill_strategy(field_info)

        except Exception as e:
            logger.warning(f"Failed to analyze field {selector}: {e}")
            return {"fill_strategy": "direct_type", "input_type": "unknown"}

    def _determine_fill_strategy(self, field_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map field characteristics to optimal fill strategy.

        Args:
            field_info: Field metadata from browser

        Returns:
            Dict with fill_strategy, input_type, and optional fill_config
        """
        if not field_info:
            return {"fill_strategy": "direct_type", "input_type": "unknown"}

        tag_name = field_info.get("tagName", "").lower()
        input_type = field_info.get("type", "text")

        # SELECT elements -> dropdown_select
        if tag_name == "select":
            return {
                "fill_strategy": "dropdown_select",
                "input_type": "select",
                "fill_config": {
                    "options_count": field_info.get("hasOptions", 0)
                }
            }

        # Custom dropdown (button-based)
        if field_info.get("isCustomDropdown") and tag_name in ["button", "div", "span"]:
            return {
                "fill_strategy": "custom_dropdown",
                "input_type": "custom-dropdown",
                "fill_config": {
                    "click_to_open": True
                }
            }

        # TEXTAREA -> direct_type (multiline)
        if tag_name == "textarea":
            return {
                "fill_strategy": "direct_type",
                "input_type": "textarea"
            }

        # INPUT elements by type
        if tag_name == "input":
            # HTML5 date input -> JS injection required
            if input_type == "date":
                return {
                    "fill_strategy": "js_date_input",
                    "input_type": "date",
                    "fill_config": {
                        "format": "YYYY-MM-DD",
                        "use_js_injection": True,
                        "dispatch_events": ["input", "change"]
                    }
                }

            # Datetime inputs
            if input_type in ["datetime-local", "time", "month", "week"]:
                return {
                    "fill_strategy": "js_date_input",
                    "input_type": input_type,
                    "fill_config": {
                        "use_js_injection": True
                    }
                }

            # Phone/tel -> character by character (for masks)
            if input_type == "tel":
                return {
                    "fill_strategy": "char_by_char",
                    "input_type": "tel",
                    "fill_config": {
                        "delay_ms": 50,
                        "click_first": True
                    }
                }

            # Number input -> may need special handling
            if input_type == "number":
                return {
                    "fill_strategy": "direct_type",
                    "input_type": "number"
                }

            # Checkbox
            if input_type == "checkbox":
                return {
                    "fill_strategy": "checkbox_click",
                    "input_type": "checkbox",
                    "fill_config": {
                        "check_state_first": True
                    }
                }

            # Radio button
            if input_type == "radio":
                return {
                    "fill_strategy": "radio_click",
                    "input_type": "radio"
                }

            # Password
            if input_type == "password":
                return {
                    "fill_strategy": "password_type",
                    "input_type": "password"
                }

            # Email - direct type but track the type
            if input_type == "email":
                return {
                    "fill_strategy": "direct_type",
                    "input_type": "email"
                }

            # Default text input
            return {
                "fill_strategy": "direct_type",
                "input_type": input_type or "text"
            }

        # Default fallback
        return {
            "fill_strategy": "direct_type",
            "input_type": "unknown"
        }

    def analyze_mappings_live(
        self,
        mappings: List[Dict[str, str]],
        url: str,
        headless: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze all mappings by visiting the actual page.

        Args:
            mappings: List of basic mappings [{selector, profile_field}, ...]
            url: URL to visit for analysis
            headless: Run browser in headless mode

        Returns:
            Enhanced mappings with fill strategies
        """
        from seleniumbase import SB

        enhanced_mappings = []

        try:
            with SB(uc=True, headless=headless) as sb:
                sb.open(url)
                sb.sleep(2)  # Wait for page to fully load

                for mapping in mappings:
                    selector = mapping.get("selector", "")
                    profile_field = mapping.get("profile_field", "")

                    # Analyze the field
                    analysis = self.analyze_field(selector, sb)

                    # Merge basic mapping with analysis
                    enhanced_mapping = {
                        "selector": selector,
                        "profile_field": profile_field,
                        **analysis
                    }
                    enhanced_mappings.append(enhanced_mapping)

                    logger.debug(
                        f"Analyzed {selector}: {analysis.get('fill_strategy')} "
                        f"({analysis.get('input_type')})"
                    )

        except Exception as e:
            logger.error(f"Failed to analyze mappings for {url}: {e}")
            # Return mappings with default strategy if analysis fails
            for mapping in mappings:
                enhanced_mappings.append({
                    **mapping,
                    "fill_strategy": "direct_type",
                    "input_type": "unknown",
                    "analysis_error": str(e)
                })

        return enhanced_mappings

    def train_from_recording(
        self,
        recording: Dict[str, Any],
        store: "FieldMappingStore"
    ) -> Dict[str, Any]:
        """
        Parse recording and save mappings to store.

        Args:
            recording: Chrome DevTools recording JSON
            store: FieldMappingStore instance

        Returns:
            Training result with domain and field count
        """
        domain = self.extract_domain(recording)
        if not domain:
            return {"success": False, "error": "Could not determine domain from recording"}

        url = self.extract_url(recording)
        mappings = self.extract_mappings(recording)

        if not mappings:
            return {
                "success": False,
                "domain": domain,
                "error": "No field mappings could be extracted"
            }

        # Save to store
        store.save_mappings(domain, mappings, url=url)

        self.stats["recordings_processed"] += 1
        self.stats["domains_trained"].add(domain)

        logger.info(f"Trained {domain}: {len(mappings)} field mappings")

        return {
            "success": True,
            "domain": domain,
            "url": url,
            "fields_learned": len(mappings),
            "mappings": mappings
        }


def batch_train_recordings(
    recordings_dir: str = "sites/recordings",
    mappings_dir: str = "field_mappings"
) -> Dict[str, Any]:
    """
    Process all recordings in a directory and extract field mappings.

    Args:
        recordings_dir: Directory containing Chrome recordings
        mappings_dir: Directory to save field mappings

    Returns:
        Batch training results
    """
    from .field_mapping_store import FieldMappingStore

    trainer = RecordingTrainer()
    store = FieldMappingStore(mappings_dir)

    recordings_path = Path(recordings_dir)
    results = {
        "total_recordings": 0,
        "successful": 0,
        "failed": 0,
        "domains_trained": [],
        "errors": []
    }

    if not recordings_path.exists():
        return {"error": f"Recordings directory not found: {recordings_dir}"}

    for recording_file in recordings_path.glob("*.json"):
        # Skip template and batch results
        if recording_file.name in ["TEMPLATE_recording.json", "batch_results.json"]:
            continue

        results["total_recordings"] += 1

        try:
            recording = json.loads(recording_file.read_text(encoding="utf-8"))
            result = trainer.train_from_recording(recording, store)

            if result.get("success"):
                results["successful"] += 1
                if result.get("domain"):
                    results["domains_trained"].append({
                        "domain": result["domain"],
                        "fields": result["fields_learned"],
                        "file": recording_file.name
                    })
            else:
                results["failed"] += 1
                results["errors"].append({
                    "file": recording_file.name,
                    "error": result.get("error", "Unknown error")
                })

        except json.JSONDecodeError as e:
            results["failed"] += 1
            results["errors"].append({
                "file": recording_file.name,
                "error": f"Invalid JSON: {str(e)}"
            })
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "file": recording_file.name,
                "error": str(e)
            })

    logger.info(
        f"Batch training complete: {results['successful']}/{results['total_recordings']} "
        f"recordings processed, {len(results['domains_trained'])} domains trained"
    )

    return results


# CLI testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        print("Batch training all recordings...")
        results = batch_train_recordings()
        print(f"\nResults:")
        print(f"  Total recordings: {results['total_recordings']}")
        print(f"  Successful: {results['successful']}")
        print(f"  Failed: {results['failed']}")
        print(f"\nDomains trained:")
        for d in results.get("domains_trained", [])[:20]:
            print(f"  - {d['domain']}: {d['fields']} fields")
        if len(results.get("domains_trained", [])) > 20:
            print(f"  ... and {len(results['domains_trained']) - 20} more")
    else:
        # Test with reebok recording
        recording_file = Path("sites/recordings/reebok_chrome.json")
        if recording_file.exists():
            recording = json.loads(recording_file.read_text(encoding="utf-8"))
            trainer = RecordingTrainer()

            domain = trainer.extract_domain(recording)
            print(f"Domain: {domain}")

            mappings = trainer.extract_mappings(recording)
            print(f"\nExtracted {len(mappings)} mappings:")
            for m in mappings:
                print(f"  {m['selector']} -> {m['profile_field']}")
        else:
            print("Usage: python recording_trainer.py [batch]")
            print("\nTo batch train all recordings:")
            print("  python recording_trainer.py batch")
