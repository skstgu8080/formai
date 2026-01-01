"""
Field Analyzer - Scrapes form fields from a URL and suggests profile mappings
"""

import asyncio
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright


@dataclass
class FormField:
    """Represents a form field found on a page"""
    selector: str
    field_type: str  # text, email, password, select, checkbox, radio, textarea
    name: str = ""
    id: str = ""
    autocomplete: str = ""
    placeholder: str = ""
    label: str = ""
    aria_label: str = ""
    required: bool = False
    options: List[str] = field(default_factory=list)  # For select fields
    profile_key: str = ""  # Suggested/mapped profile key
    transform: str = ""  # Optional transform (e.g., "date:MM/DD/YYYY", "prefix:UNITED_STATES__")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    """Result of analyzing a URL for form fields"""
    success: bool
    url: str
    fields: List[FormField]
    error: Optional[str] = None
    page_title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "url": self.url,
            "page_title": self.page_title,
            "fields": [f.to_dict() for f in self.fields],
            "error": self.error
        }


# Common field name patterns mapped to profile keys
FIELD_PATTERNS = {
    # Email
    "email": "email",
    "e-mail": "email",
    "emailaddress": "email",
    "email-address": "email",
    "user-email": "email",

    # Names
    "firstname": "firstName",
    "first-name": "firstName",
    "first_name": "firstName",
    "fname": "firstName",
    "givenname": "firstName",
    "given-name": "firstName",

    "lastname": "lastName",
    "last-name": "lastName",
    "last_name": "lastName",
    "lname": "lastName",
    "familyname": "lastName",
    "family-name": "lastName",
    "surname": "lastName",

    "fullname": "fullName",
    "full-name": "fullName",
    "name": "fullName",

    # Phone
    "phone": "phone",
    "telephone": "phone",
    "tel": "phone",
    "phonenumber": "phone",
    "phone-number": "phone",
    "mobile": "phone",
    "cell": "phone",

    # Address
    "address": "address",
    "street": "street",
    "streetaddress": "street",
    "street-address": "street",
    "address1": "street",
    "address-line1": "street",

    "city": "city",
    "locality": "city",

    "state": "state",
    "region": "state",
    "province": "state",
    "administrative-area": "state",

    "zip": "zip",
    "zipcode": "zip",
    "zip-code": "zip",
    "postalcode": "zip",
    "postal-code": "zip",
    "postcode": "zip",

    "country": "country",
    "country-name": "country",

    # Dates
    "birthdate": "birthdate",
    "birthday": "birthdate",
    "dob": "birthdate",
    "dateofbirth": "birthdate",
    "date-of-birth": "birthdate",
    "bday": "birthdate",

    # Password
    "password": "password",
    "pass": "password",
    "pwd": "password",
    "newpassword": "password",
    "new-password": "password",

    # Gender
    "gender": "gender",
    "sex": "gender",
    "civility": "gender",
    "title": "title",
    "prefix": "title",
}


class FieldAnalyzer:
    """Analyzes web pages to extract form fields"""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def analyze(self, url: str) -> AnalysisResult:
        """Visit URL and extract all form fields"""
        fields = []
        page_title = ""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for dynamic content

                # Close popups
                await self._close_popups(page)

                # Get page title
                page_title = await page.title()

                # Extract fields using JavaScript
                fields_data = await page.evaluate('''() => {
                    const fields = [];
                    const selector = 'input:not([type=hidden]):not([type=button]):not([type=image]):not([type=reset]):not([type=submit]), select, textarea';

                    document.querySelectorAll(selector).forEach((el, index) => {
                        // Skip invisible fields
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') return;
                        if (el.offsetWidth === 0 && el.offsetHeight === 0) return;

                        // Get label
                        let label = '';
                        if (el.id) {
                            const labelEl = document.querySelector(`label[for="${el.id}"]`);
                            if (labelEl) label = labelEl.textContent.trim();
                        }
                        if (!label && el.closest('label')) {
                            label = el.closest('label').textContent.trim();
                        }

                        // Get options for select
                        let options = [];
                        if (el.tagName === 'SELECT') {
                            options = Array.from(el.options).slice(0, 20).map(o => o.value);
                        }

                        // Build selector
                        let selector = '';
                        if (el.id) {
                            selector = `#${el.id}`;
                        } else if (el.name) {
                            selector = `[name="${el.name}"]`;
                        } else {
                            // Use index-based selector
                            selector = `${el.tagName.toLowerCase()}:nth-of-type(${index + 1})`;
                        }

                        fields.push({
                            selector: selector,
                            field_type: el.type || el.tagName.toLowerCase(),
                            name: el.name || '',
                            id: el.id || '',
                            autocomplete: el.autocomplete || '',
                            placeholder: el.placeholder || '',
                            label: label,
                            aria_label: el.getAttribute('aria-label') || '',
                            required: el.required || el.getAttribute('aria-required') === 'true',
                            options: options
                        });
                    });

                    // Also find radio button groups
                    const radioGroups = {};
                    document.querySelectorAll('input[type=radio]').forEach(el => {
                        if (!radioGroups[el.name]) {
                            radioGroups[el.name] = {
                                selector: `input[name="${el.name}"]`,
                                field_type: 'radio',
                                name: el.name,
                                id: el.id || '',
                                autocomplete: '',
                                placeholder: '',
                                label: '',
                                aria_label: el.getAttribute('aria-label') || '',
                                required: el.required,
                                options: []
                            };
                        }
                        radioGroups[el.name].options.push(el.value);
                    });

                    Object.values(radioGroups).forEach(r => fields.push(r));

                    return fields;
                }''')

                # Convert to FormField objects and suggest profile keys
                for fd in fields_data:
                    form_field = FormField(
                        selector=fd['selector'],
                        field_type=fd['field_type'],
                        name=fd['name'],
                        id=fd['id'],
                        autocomplete=fd['autocomplete'],
                        placeholder=fd['placeholder'],
                        label=fd['label'],
                        aria_label=fd['aria_label'],
                        required=fd['required'],
                        options=fd['options']
                    )

                    # Suggest profile key
                    form_field.profile_key = self._suggest_profile_key(form_field)

                    # Suggest transform for special fields
                    form_field.transform = self._suggest_transform(form_field)

                    fields.append(form_field)

                await browser.close()

                return AnalysisResult(
                    success=True,
                    url=url,
                    page_title=page_title,
                    fields=fields
                )

        except Exception as e:
            return AnalysisResult(
                success=False,
                url=url,
                page_title=page_title,
                fields=[],
                error=str(e)
            )

    async def _close_popups(self, page):
        """Close common popup dialogs"""
        popup_selectors = [
            '#onetrust-accept-btn-handler',
            '[data-testid="cookie-policy-dialog-accept-button"]',
            '.cookie-accept',
            '#accept-cookies',
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("I Accept")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            '[aria-label="Close"]',
            '.modal-close',
        ]

        for selector in popup_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click()
                    await page.wait_for_timeout(300)
            except:
                pass

    def _suggest_profile_key(self, field: FormField) -> str:
        """Suggest a profile key based on field attributes"""
        # Check all identifying attributes
        candidates = [
            field.name.lower(),
            field.id.lower(),
            field.autocomplete.lower(),
            field.placeholder.lower().replace(' ', ''),
            field.label.lower().replace(' ', ''),
            field.aria_label.lower().replace(' ', '')
        ]

        # Also check field type
        if field.field_type == 'email':
            return 'email'
        if field.field_type == 'tel':
            return 'phone'
        if field.field_type == 'password':
            return 'password'

        # Match against patterns
        for candidate in candidates:
            if not candidate:
                continue
            # Remove common prefixes/suffixes
            clean = candidate.replace('input', '').replace('field', '').replace('txt', '')

            for pattern, key in FIELD_PATTERNS.items():
                if pattern in clean:
                    return key

        return ""  # No suggestion

    def _suggest_transform(self, field: FormField) -> str:
        """Suggest data transform based on field characteristics"""
        name_lower = (field.name + field.id + field.label).lower()

        # Date fields often need format transform
        if 'date' in name_lower or 'birth' in name_lower or 'dob' in name_lower:
            # Check placeholder for format hint
            placeholder = field.placeholder.lower()
            if 'mm/dd' in placeholder:
                return "date:MM/DD/YYYY"
            if 'dd/mm' in placeholder:
                return "date:DD/MM/YYYY"
            if 'yyyy-mm' in placeholder:
                return "date:YYYY-MM-DD"

        # State fields with country prefix
        if field.options and field.profile_key == 'state':
            if any('UNITED_STATES__' in opt for opt in field.options):
                return "prefix:UNITED_STATES__"
            if any('US_' in opt for opt in field.options):
                return "prefix:US_"

        return ""


# Quick test
if __name__ == "__main__":
    async def test():
        analyzer = FieldAnalyzer(headless=True)
        result = await analyzer.analyze("https://www.ysl.com/en-us/signup")
        print(f"Found {len(result.fields)} fields:")
        for f in result.fields:
            print(f"  {f.selector}: {f.field_type} -> {f.profile_key} {f.transform}")

    asyncio.run(test())
