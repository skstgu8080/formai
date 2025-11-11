#!/usr/bin/env python3
"""
AI Form Filler - Intelligent form filling using Playwright MCP
No recordings needed - AI analyzes page and fills form automatically
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class AIFormFiller:
    """
    AI-powered form filler using Playwright MCP
    Analyzes forms and fills them intelligently without recordings
    """

    def __init__(self):
        self.field_patterns = {
            # Email patterns
            'email': ['email', 'e-mail', 'e_mail', 'mail', 'email_address', 'emailaddress'],

            # Name patterns
            'firstName': ['first_name', 'fname', 'firstname', 'given_name', 'first-name', 'forename'],
            'lastName': ['last_name', 'lname', 'lastname', 'family_name', 'last-name', 'surname'],
            'fullName': ['full_name', 'fullname', 'name', 'full-name', 'display_name', 'your_name'],

            # Phone patterns
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone_number', 'tel', 'phonenumber'],
            'homePhone': ['home_phone', 'home-phone', 'homephone'],
            'workPhone': ['work_phone', 'work-phone', 'workphone', 'office_phone'],
            'cellPhone': ['cell_phone', 'cell-phone', 'cellphone', 'mobile_phone'],

            # Address patterns
            'address1': ['address', 'address1', 'street', 'address_line_1', 'street_address', 'addr1'],
            'address2': ['address2', 'address_line_2', 'apt', 'apartment', 'suite', 'unit', 'addr2'],
            'city': ['city', 'town', 'locality'],
            'state': ['state', 'province', 'region', 'state_province'],
            'zip': ['zip', 'postal', 'postcode', 'postal_code', 'zipcode', 'zip_code'],
            'country': ['country', 'nation'],

            # Company patterns
            'company': ['company', 'organization', 'employer', 'business', 'company_name'],
            'title': ['title', 'prefix', 'salutation', 'job_title', 'position'],

            # Account patterns
            'username': ['username', 'user_name', 'login', 'userid', 'user_id', 'user'],
            'password': ['password', 'pass', 'pwd', 'passphrase'],

            # Date patterns
            'birthMonth': ['birth_month', 'dob_month', 'bmonth', 'month_of_birth'],
            'birthDay': ['birth_day', 'dob_day', 'bday', 'day_of_birth'],
            'birthYear': ['birth_year', 'dob_year', 'byear', 'year_of_birth'],
            'age': ['age', 'years_old'],

            # Other
            'sex': ['sex', 'gender'],
            'ssn': ['ssn', 'social_security', 'social_security_number', 'social'],
            'website': ['website', 'url', 'web_site', 'homepage'],
            'linkedin': ['linkedin', 'linkedin_url', 'linkedin_profile'],
        }

    def analyze_field(self, field_info: Dict[str, Any]) -> Optional[str]:
        """
        Analyze a form field and determine which profile field it maps to

        Args:
            field_info: Field information from accessibility tree or HTML

        Returns:
            Profile field name that matches, or None
        """
        # Extract field identifiers
        name = field_info.get('name', '').lower()
        id_attr = field_info.get('id', '').lower()
        label = field_info.get('label', '').lower()
        placeholder = field_info.get('placeholder', '').lower()
        aria_label = field_info.get('aria-label', '').lower()

        # Combine all identifiers for matching
        search_text = f"{name} {id_attr} {label} {placeholder} {aria_label}"

        # Try to match against known patterns
        for profile_field, patterns in self.field_patterns.items():
            for pattern in patterns:
                if pattern in search_text:
                    return profile_field

        return None

    def parse_snapshot_for_fields(self, snapshot: str) -> List[Dict[str, Any]]:
        """
        Parse accessibility tree snapshot to extract form fields

        Args:
            snapshot: Accessibility tree snapshot text

        Returns:
            List of detected form fields with metadata
        """
        fields = []

        # Parse snapshot (accessibility tree is text-based)
        # Look for form inputs, textboxes, selects, etc.
        lines = snapshot.split('\n') if isinstance(snapshot, str) else []

        for line in lines:
            # Look for input indicators
            if any(keyword in line.lower() for keyword in ['textbox', 'input', 'combobox', 'field']):
                # Extract field information from the line
                # Accessibility tree format: "textbox 'Email Address' [name='email']"

                field_info = {
                    'line': line,
                    'name': '',
                    'label': '',
                    'type': 'text',
                    'selector': ''
                }

                # Extract label (text in quotes)
                label_match = re.search(r"['\"]([^'\"]+)['\"]", line)
                if label_match:
                    field_info['label'] = label_match.group(1)

                # Extract name attribute
                name_match = re.search(r"name=['\"]([^'\"]+)['\"]", line)
                if name_match:
                    field_info['name'] = name_match.group(1)
                    field_info['selector'] = f"[name='{name_match.group(1)}']"

                # Extract ID
                id_match = re.search(r"id=['\"]([^'\"]+)['\"]", line)
                if id_match:
                    field_info['id'] = id_match.group(1)
                    if not field_info['selector']:
                        field_info['selector'] = f"#{id_match.group(1)}"

                # Determine field type
                if 'combobox' in line.lower() or 'select' in line.lower():
                    field_info['type'] = 'select'
                elif 'checkbox' in line.lower():
                    field_info['type'] = 'checkbox'
                elif 'radio' in line.lower():
                    field_info['type'] = 'radio'

                # Map to profile field
                profile_field = self.analyze_field(field_info)
                if profile_field:
                    field_info['profile_field'] = profile_field
                    fields.append(field_info)

        return fields

    def map_profile_to_fields(self, profile: Dict[str, Any], detected_fields: List[Dict]) -> List[Dict[str, str]]:
        """
        Map profile data to detected form fields

        Args:
            profile: User profile data
            detected_fields: Fields detected from page

        Returns:
            List of field mappings ready for MCP fill_form
        """
        mappings = []

        for field in detected_fields:
            profile_field = field.get('profile_field')
            if not profile_field:
                continue

            # Get value from profile
            value = profile.get(profile_field)
            if not value:
                continue

            # Convert value to string
            value_str = str(value)

            # Create MCP field mapping
            mapping = {
                'name': field.get('label', field.get('name', 'Unknown')),
                'ref': field.get('selector', ''),
                'type': field.get('type', 'textbox'),
                'value': value_str
            }

            mappings.append(mapping)

        return mappings

    async def fill_form_intelligently(
        self,
        url: str,
        profile: Dict[str, Any],
        mcp_controller,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Intelligently fill form using AI analysis

        Args:
            url: Form URL
            profile: User profile data
            mcp_controller: MCP controller instance
            use_llm: Whether to use LLM for analysis (falls back to pattern matching)

        Returns:
            Fill result with details
        """
        results = {
            "status": "started",
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "fields_filled": 0,
            "errors": [],
            "analysis_method": "llm" if use_llm else "pattern_matching"
        }

        try:
            # Step 1: Navigate to URL
            print(f"[AI] Navigating to {url}...")
            nav_result = await mcp_controller.navigate(url)
            results["steps"].append({"action": "navigate", "result": nav_result})

            if not nav_result.get("success"):
                results["status"] = "failed"
                results["error"] = f"Navigation failed: {nav_result.get('error')}"
                return results

            # Step 2: Take snapshot to analyze page
            print("[AI] Taking page snapshot...")
            snapshot_result = await mcp_controller.take_snapshot()
            results["steps"].append({"action": "snapshot", "result": "success" if snapshot_result.get("success") else "failed"})

            if not snapshot_result.get("success"):
                results["status"] = "failed"
                results["error"] = f"Snapshot failed: {snapshot_result.get('error')}"
                return results

            snapshot_data = snapshot_result.get("snapshot", "")

            # Step 3: Analyze form fields (LLM or pattern matching)
            field_mappings = []

            if use_llm:
                print("[AI] Using LLM to analyze form structure...")
                from tools.llm_field_analyzer import get_llm_analyzer

                llm_analyzer = get_llm_analyzer()
                profile_fields = list(profile.keys())

                llm_result = await llm_analyzer.analyze_form_with_llm(
                    snapshot=snapshot_data,
                    profile_fields=profile_fields
                )

                if "error" in llm_result:
                    print(f"[AI] LLM analysis failed: {llm_result['error']}")
                    print("[AI] Falling back to pattern matching...")
                    use_llm = False
                    results["analysis_method"] = "pattern_matching_fallback"
                else:
                    # Convert LLM mappings to MCP format
                    llm_mappings = llm_result.get("mappings", [])
                    results["detected_fields"] = len(llm_mappings)
                    print(f"[AI] LLM detected {len(llm_mappings)} form fields")

                    for mapping in llm_mappings:
                        profile_field = mapping.get("profile_field")
                        value = profile.get(profile_field)

                        if value:
                            field_mappings.append({
                                "name": mapping.get("field_label", "Unknown"),
                                "ref": mapping.get("field_selector", ""),
                                "type": "textbox",
                                "value": str(value)
                            })

            # Fallback to pattern matching if LLM not used or failed
            if not use_llm or not field_mappings:
                print("[AI] Analyzing form structure with pattern matching...")
                detected_fields = self.parse_snapshot_for_fields(snapshot_data)
                results["detected_fields"] = len(detected_fields)
                print(f"[AI] Detected {len(detected_fields)} form fields")

                # Map profile data to fields
                print("[AI] Mapping profile data to form fields...")
                field_mappings = self.map_profile_to_fields(profile, detected_fields)

            results["mapped_fields"] = len(field_mappings)
            print(f"[AI] Mapped {len(field_mappings)} fields")

            # Step 5: Fill form using MCP
            if field_mappings:
                print(f"[AI] Filling {len(field_mappings)} fields...")
                fill_result = await mcp_controller.fill_form(field_mappings)
                results["steps"].append({"action": "fill_form", "result": fill_result})

                if fill_result.get("success"):
                    results["fields_filled"] = fill_result.get("fields_filled", 0)
                    print(f"[AI] Successfully filled {results['fields_filled']} fields")
                else:
                    results["errors"].append(f"Fill failed: {fill_result.get('error')}")

            # Step 6: Take screenshot for verification
            print("[AI] Taking verification screenshot...")
            screenshot_result = await mcp_controller.take_screenshot()
            results["steps"].append({"action": "screenshot", "result": "success" if screenshot_result.get("success") else "failed"})

            if screenshot_result.get("success"):
                results["screenshot"] = screenshot_result.get("screenshot")

            # Determine final status
            if results["fields_filled"] > 0:
                results["status"] = "success"
            elif len(detected_fields) == 0:
                results["status"] = "no_fields_found"
                results["error"] = "No form fields detected on page"
            else:
                results["status"] = "partial"
                results["error"] = "Detected fields but couldn't fill them"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            results["errors"].append(str(e))

        return results


# Singleton instance
_ai_form_filler = None

def get_ai_form_filler() -> AIFormFiller:
    """Get or create AI form filler instance"""
    global _ai_form_filler
    if _ai_form_filler is None:
        _ai_form_filler = AIFormFiller()
    return _ai_form_filler
