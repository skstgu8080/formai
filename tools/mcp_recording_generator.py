#!/usr/bin/env python3
"""
MCP Recording Generator - Automated form recording using Chrome DevTools MCP

Discovers form fields via DOM inspection and generates Chrome Recorder compatible JSON.
NO screenshots - uses text-based DOM queries and accessibility tree parsing.
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class MCPRecordingGenerator:
    """
    Automated recording generator using Chrome DevTools MCP.

    Workflow:
    1. Navigate to target URL
    2. Discover all form fields via DOM inspection
    3. Generate appropriate sample data
    4. Track interactions in Chrome Recorder format
    5. Export to JSON file
    """

    def __init__(self, mcp_client=None):
        """
        Initialize MCP recording generator.

        Args:
            mcp_client: Chrome DevTools MCP client instance (if None, expects manual MCP calls)
        """
        self.mcp_client = mcp_client
        self.discovered_fields = []
        self.recording_steps = []
        self.metadata = {}

        # Sample data patterns for different field types
        self.sample_data_patterns = {
            "firstName": "John",
            "first_name": "John",
            "fname": "John",
            "lastName": "Smith",
            "last_name": "Smith",
            "lname": "Smith",
            "email": "john.smith@example.com",
            "emailAddress": "john.smith@example.com",
            "phone": "(555) 123-4567",
            "phoneNumber": "(555) 123-4567",
            "mobile": "(555) 123-4567",
            "tel": "(555) 123-4567",
            "password": "SecurePass123!",
            "pwd": "SecurePass123!",
            "confirmPassword": "SecurePass123!",
            "address": "123 Main St",
            "address1": "123 Main St",
            "street": "123 Main St",
            "address2": "Apt 4B",
            "city": "New York",
            "state": "NY",
            "province": "NY",
            "zip": "10001",
            "zipCode": "10001",
            "postalCode": "10001",
            "country": "USA",
            "company": "Example Corp",
            "companyName": "Example Corp",
            "organization": "Example Corp",
            "website": "https://example.com",
            "url": "https://example.com",
            "jobTitle": "Software Engineer",
            "title": "Mr",
            "position": "Software Engineer"
        }

    def get_field_discovery_script(self) -> str:
        """
        Get JavaScript code to discover all form fields on the page.

        Returns:
            JavaScript code as string for execution via MCP evaluate_script
        """
        return """
        (function() {
            const fields = [];
            const selectors = 'input, select, textarea, button[type="submit"]';

            document.querySelectorAll(selectors).forEach((el, index) => {
                // Skip hidden fields unless they're important
                const isVisible = el.offsetParent !== null || el.type === 'hidden';

                // Build best selector
                let selector = null;
                if (el.id) {
                    selector = `#${el.id}`;
                } else if (el.name) {
                    selector = `[name="${el.name}"]`;
                } else if (el.className) {
                    selector = `.${el.className.split(' ')[0]}`;
                } else {
                    selector = `${el.tagName.toLowerCase()}:nth-of-type(${index + 1})`;
                }

                // Extract field metadata
                const field = {
                    index: index,
                    tag: el.tagName.toLowerCase(),
                    type: el.type || 'text',
                    name: el.name || '',
                    id: el.id || '',
                    className: el.className || '',
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    required: el.required || false,
                    disabled: el.disabled || false,
                    readOnly: el.readOnly || false,
                    selector: selector,
                    isVisible: isVisible,
                    label: null,
                    ariaLabel: el.getAttribute('aria-label') || '',
                    autocomplete: el.autocomplete || ''
                };

                // Try to find associated label
                if (el.id) {
                    const label = document.querySelector(`label[for="${el.id}"]`);
                    if (label) {
                        field.label = label.textContent.trim();
                    }
                }

                // For select elements, get options
                if (el.tagName.toLowerCase() === 'select') {
                    field.options = Array.from(el.options).map(opt => ({
                        value: opt.value,
                        text: opt.text
                    }));
                }

                fields.push(field);
            });

            return {
                total_fields: fields.length,
                visible_fields: fields.filter(f => f.isVisible).length,
                fields: fields
            };
        })();
        """

    def discover_fields_via_dom(self, dom_query_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse DOM query results to extract form fields.

        Args:
            dom_query_result: Result from MCP evaluate_script with field discovery

        Returns:
            List of discovered fields with metadata
        """
        if not dom_query_result or 'fields' not in dom_query_result:
            print("No fields found in DOM query result")
            return []

        fields = dom_query_result['fields']
        total = dom_query_result.get('total_fields', len(fields))
        visible = dom_query_result.get('visible_fields', len(fields))

        print(f"\n[Field Discovery] Found {total} total fields ({visible} visible)")

        # Filter out disabled, readonly, and submit buttons for now
        fillable_fields = []
        for field in fields:
            # Skip non-fillable fields
            if field.get('disabled') or field.get('readOnly'):
                continue

            # Skip submit buttons (we'll handle those separately)
            if field.get('type') == 'submit':
                continue

            # Skip hidden fields unless they have a name (might be important)
            if not field.get('isVisible') and not field.get('name'):
                continue

            fillable_fields.append(field)

        print(f"[Field Discovery] {len(fillable_fields)} fillable fields identified")

        self.discovered_fields = fillable_fields
        return fillable_fields

    def generate_sample_value(self, field: Dict[str, Any]) -> str:
        """
        Generate appropriate sample value for a field.

        Args:
            field: Field metadata dict

        Returns:
            Sample value string
        """
        field_name = field.get('name', '').lower()
        field_id = field.get('id', '').lower()
        field_type = field.get('type', 'text').lower()
        placeholder = field.get('placeholder', '').lower()
        label = (field.get('label') or '').lower()

        # Try to match against known patterns
        search_text = f"{field_name} {field_id} {placeholder} {label}"

        # Check patterns
        for pattern, sample_value in self.sample_data_patterns.items():
            if pattern.lower() in search_text:
                return sample_value

        # Type-based defaults
        if field_type == 'email':
            return "test@example.com"
        elif field_type == 'tel' or 'phone' in search_text:
            return "(555) 123-4567"
        elif field_type == 'password':
            return "SecurePass123!"
        elif field_type == 'number':
            return "25"
        elif field_type == 'date':
            return "2024-01-15"
        elif field_type == 'url':
            return "https://example.com"
        elif field_type == 'checkbox':
            return "true"
        elif field_type == 'radio':
            return "true"
        elif field.get('tag') == 'select':
            # Return first option value if available
            options = field.get('options', [])
            if options and len(options) > 1:
                # Skip empty first option
                return options[1].get('value', '')
            return ""

        # Default for text fields
        if 'name' in search_text:
            return "John Smith"
        elif 'company' in search_text or 'organization' in search_text:
            return "Example Corp"
        elif 'address' in search_text:
            return "123 Main St"
        elif 'city' in search_text:
            return "New York"
        elif 'message' in search_text or 'comment' in search_text:
            return "This is a test message"

        return "Sample Value"

    def generate_chrome_recorder_steps(
        self,
        url: str,
        fields: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate Chrome Recorder compatible steps.

        Args:
            url: Target URL
            fields: List of fields to fill (uses discovered_fields if None)

        Returns:
            List of recording steps in Chrome Recorder format
        """
        if fields is None:
            fields = self.discovered_fields

        steps = []

        # Step 1: Navigate to URL
        navigate_step = {
            "type": "navigate",
            "url": url,
            "assertedEvents": [
                {
                    "type": "navigation",
                    "url": url,
                    "title": ""
                }
            ]
        }
        steps.append(navigate_step)

        # Step 2: Fill each field
        for field in fields:
            field_type = field.get('type', 'text')
            tag = field.get('tag', 'input')

            # Generate sample value
            sample_value = self.generate_sample_value(field)

            # Build selectors array (priority order)
            selectors = []
            if field.get('id'):
                selectors.append([f"#{field['id']}"])
            if field.get('name'):
                selectors.append([f"[name='{field['name']}']"])
            if field.get('selector'):
                selectors.append([field['selector']])

            # Generate appropriate step based on field type
            if field_type == 'checkbox' or field_type == 'radio':
                # Click step for checkbox/radio
                step = {
                    "type": "click",
                    "selectors": selectors,
                    "target": "main",
                    "offsetX": 0,
                    "offsetY": 0
                }
            elif tag == 'select':
                # Change step for select/dropdown
                step = {
                    "type": "change",
                    "selectors": selectors,
                    "value": sample_value,
                    "target": "main"
                }
            else:
                # Change step for text inputs
                step = {
                    "type": "change",
                    "selectors": selectors,
                    "value": sample_value,
                    "target": "main",
                    "offsetX": 0,
                    "offsetY": 0
                }

            steps.append(step)

        self.recording_steps = steps
        return steps

    def export_to_chrome_recorder_json(
        self,
        url: str,
        title: str = None,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        Export recording to Chrome Recorder JSON format.

        Args:
            url: Target URL
            title: Recording title
            output_file: Optional file path to save JSON

        Returns:
            Chrome Recorder JSON dict
        """
        if not self.recording_steps:
            raise Exception("No recording steps generated. Call generate_chrome_recorder_steps() first.")

        # Generate title if not provided
        if not title:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            title = f"{domain} Form Recording"

        # Build Chrome Recorder JSON
        recording_json = {
            "title": title,
            "timeout": 5000,
            "steps": self.recording_steps,
            "metadata": {
                "generated_by": "FormAI MCP Recording Generator",
                "generated_at": datetime.now().isoformat(),
                "url": url,
                "total_fields": len(self.discovered_fields),
                "discovery_method": "DOM inspection via Chrome DevTools MCP"
            }
        }

        # Save to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(recording_json, f, indent=2)
            print(f"\n[Export] Recording saved to: {output_file}")

        return recording_json

    def generate_recording(
        self,
        url: str,
        dom_query_result: Dict[str, Any],
        title: str = None,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: discover fields, generate steps, export JSON.

        Args:
            url: Target URL
            dom_query_result: Result from MCP field discovery script
            title: Recording title
            output_file: File path to save recording

        Returns:
            Chrome Recorder JSON dict
        """
        print(f"\n{'='*60}")
        print(f"MCP RECORDING GENERATOR")
        print(f"{'='*60}")
        print(f"URL: {url}")

        # Step 1: Discover fields
        print(f"\n[Step 1] Discovering fields via DOM inspection...")
        fields = self.discover_fields_via_dom(dom_query_result)

        if not fields:
            raise Exception("No fillable fields discovered")

        # Show discovered fields
        print(f"\nDiscovered Fields:")
        for i, field in enumerate(fields, 1):
            field_name = field.get('name') or field.get('id') or 'unnamed'
            field_type = field.get('type', 'text')
            print(f"  {i}. {field_name} ({field_type})")

        # Step 2: Generate recording steps
        print(f"\n[Step 2] Generating Chrome Recorder steps...")
        steps = self.generate_chrome_recorder_steps(url, fields)
        print(f"OK - {len(steps)} steps generated (1 navigate + {len(fields)} fills)")

        # Step 3: Export to JSON
        print(f"\n[Step 3] Exporting to Chrome Recorder JSON...")
        recording_json = self.export_to_chrome_recorder_json(url, title, output_file)

        print(f"\n{'='*60}")
        print(f"RECORDING GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Title: {recording_json['title']}")
        print(f"Fields: {len(fields)}")
        print(f"Steps: {len(steps)}")

        return recording_json
