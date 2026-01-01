#!/usr/bin/env python3
"""
Site Analyzer & Auto-Filler Tool

For ANY signup URL:
1. Visit & scrape ALL form fields
2. Log discovered fields
3. Test endpoint with dummy data
4. Fill form with profile
5. Report results

Usage:
    python tools/site_analyzer.py https://example.com/signup
    python tools/site_analyzer.py https://example.com/signup --fill
    python tools/site_analyzer.py https://example.com/signup --fill --profile roboform-complete-001
"""

import asyncio
import json
import re
import sys
import httpx
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, Page, Browser


# ============================================================================
# FIELD TO PROFILE MAPPING
# ============================================================================

FIELD_MAPPINGS = {
    # First Name variations
    'firstname': 'firstName',
    'first_name': 'firstName',
    'first-name': 'firstName',
    'fname': 'firstName',
    'given_name': 'firstName',
    'givenname': 'firstName',

    # Last Name variations
    'lastname': 'lastName',
    'last_name': 'lastName',
    'last-name': 'lastName',
    'lname': 'lastName',
    'surname': 'lastName',
    'family_name': 'lastName',
    'familyname': 'lastName',

    # Email variations
    'email': 'email',
    'emailaddress': 'email',
    'email_address': 'email',
    'user_email': 'email',
    'useremail': 'email',

    # Password variations
    'password': 'password',
    'pass': 'password',
    'pwd': 'password',
    'user_password': 'password',
    'userpassword': 'password',

    # Phone variations
    'phone': 'phone',
    'phonenumber': 'phone',
    'phone_number': 'phone',
    'telephone': 'phone',
    'tel': 'phone',
    'mobile': 'phone',
    'cellphone': 'phone',

    # Birth date variations
    'birthdate': 'birthdate',
    'birth_date': 'birthdate',
    'dob': 'birthdate',
    'dateofbirth': 'birthdate',
    'date_of_birth': 'birthdate',
    'birthday': 'birthdate',

    # Gender variations
    'gender': 'sex',
    'sex': 'sex',

    # Address
    'address': 'address1',
    'address1': 'address1',
    'street': 'address1',
    'streetaddress': 'address1',

    # City
    'city': 'city',
    'town': 'city',

    # State
    'state': 'state',
    'province': 'state',
    'region': 'state',

    # Zip
    'zip': 'zip',
    'zipcode': 'zip',
    'postalcode': 'zip',
    'postal_code': 'zip',

    # Country
    'country': 'country',
}


@dataclass
class FormField:
    """Represents a discovered form field."""
    tag: str
    type: str
    name: str
    id: str
    placeholder: str
    label: str
    required: bool
    aria_label: str
    selector: str
    profile_key: str = ""
    value: str = ""


@dataclass
class FormData:
    """Represents the entire form."""
    url: str
    action: str
    method: str
    fields: List[FormField] = field(default_factory=list)
    checkboxes: List[FormField] = field(default_factory=list)
    submit_button: Optional[str] = None
    captcha_detected: str = ""


@dataclass
class AnalysisResult:
    """Result of site analysis."""
    url: str
    domain: str
    form: Optional[FormData] = None
    endpoint_test: Dict[str, Any] = field(default_factory=dict)
    fill_result: Dict[str, Any] = field(default_factory=dict)
    classification: str = "unknown"  # working, captcha, blocked, error
    timestamp: str = ""


class SiteAnalyzer:
    """Analyzes signup forms and fills them."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def analyze(self, url: str, profile: dict = None, do_fill: bool = False, wait_for_captcha: bool = False) -> AnalysisResult:
        """
        Full analysis pipeline:
        1. Visit URL
        2. Scrape form fields
        3. Test endpoint
        4. Optionally fill form
        """
        result = AnalysisResult(
            url=url,
            domain=urlparse(url).netloc,
            timestamp=datetime.now().isoformat()
        )

        try:
            await self._start_browser()

            # Step 1: Visit and scrape
            print(f"\n{'='*70}")
            print(f"ANALYZING: {url}")
            print(f"{'='*70}")

            form_data = await self._scrape_form(url)
            result.form = form_data

            # Step 2: Log fields
            self._log_fields(form_data, profile)

            # Step 3: Detect CAPTCHA
            captcha = await self._detect_captcha()
            if captcha:
                form_data.captcha_detected = captcha
                result.classification = "captcha"
                print(f"\n[!] CAPTCHA DETECTED: {captcha}")

            # Step 4: Test endpoint (if no captcha)
            if not captcha and form_data.action:
                result.endpoint_test = await self._test_endpoint(form_data)

            # Step 5: Fill form (if requested and profile provided)
            if do_fill and profile:
                # Fill even if CAPTCHA - user will solve manually
                result.fill_result = await self._fill_form(form_data, profile, wait_for_captcha and bool(captcha))
                if result.fill_result.get('success'):
                    result.classification = "working"
                else:
                    result.classification = "error"
            elif captcha:
                result.classification = "captcha"
            else:
                result.classification = "analyzed"

        except Exception as e:
            print(f"\n[ERROR] {e}")
            result.classification = "error"
            result.fill_result = {"error": str(e)}

        finally:
            await self._close_browser()

        return result

    async def _start_browser(self):
        """Start Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await context.new_page()

    async def _close_browser(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _close_popups(self):
        """Close cookie consent and other popups."""
        popup_selectors = [
            # Cookie consent
            '#onetrust-accept-btn-handler',
            '.onetrust-accept-btn-handler',
            '[id*="accept"][id*="cookie"]',
            '[class*="accept"][class*="cookie"]',
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Accept")',
            'button:has-text("I Agree")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Continue")',
            # Close buttons
            '.popup-close',
            '.modal-close',
            '[aria-label="Close"]',
            '[aria-label="close"]',
            '.close-button',
            'button.close',
        ]

        for selector in popup_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click(force=True)
                    print(f"  Closed popup: {selector}")
                    await asyncio.sleep(0.5)
                    break
            except:
                continue

        # Press Escape as fallback
        try:
            await self.page.keyboard.press('Escape')
        except:
            pass

    async def _scrape_form(self, url: str) -> FormData:
        """Visit URL and scrape all form fields."""
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)  # Wait for dynamic content

        # Close cookie/consent popups
        await self._close_popups()

        # Find form
        form_data = FormData(url=url, action="", method="POST")

        # Get form action/method - find the main registration/signup form
        form_info = await self.page.evaluate("""
            () => {
                // Try to find registration/signup form specifically
                const formSelectors = [
                    'form[action*="register"]',
                    'form[action*="signup"]',
                    'form[action*="sign-up"]',
                    'form[action*="account"]',
                    'form[action*="create"]',
                    'form[id*="register"]',
                    'form[id*="signup"]',
                    'form[class*="register"]',
                    'form[class*="signup"]',
                    'form:has(input[type="password"])',  // Form with password field
                ];

                let form = null;
                for (const selector of formSelectors) {
                    form = document.querySelector(selector);
                    if (form) break;
                }

                // Fallback to first form with password field
                if (!form) {
                    const forms = document.querySelectorAll('form');
                    for (const f of forms) {
                        if (f.querySelector('input[type="password"]')) {
                            form = f;
                            break;
                        }
                    }
                }

                // Last fallback
                if (!form) form = document.querySelector('form');

                if (form) {
                    return {
                        action: form.action || '',
                        method: (form.method || 'POST').toUpperCase(),
                        formSelector: form.id ? `#${form.id}` : 'form:has(input[type="password"])'
                    };
                }
                return { action: window.location.href, method: 'POST', formSelector: 'form' };
            }
        """)
        form_data.action = form_info['action']
        form_data.method = form_info['method']
        form_selector = form_info.get('formSelector', 'form')

        # Scrape ALL form elements within the target form
        elements = await self.page.evaluate("""
            (formSelector) => {
                const results = { fields: [], checkboxes: [], submit: null };

                // Find the target form
                const targetForm = document.querySelector(formSelector) || document;

                // Find all inputs within that form
                targetForm.querySelectorAll('input, select, textarea').forEach((el, idx) => {
                    const type = el.type || el.tagName.toLowerCase();
                    const name = el.name || '';
                    const id = el.id || '';

                    // Skip hidden/submit types for field list
                    if (type === 'hidden') return;

                    // Find label
                    let label = '';
                    if (el.id) {
                        const labelEl = document.querySelector(`label[for="${el.id}"]`);
                        if (labelEl) label = labelEl.textContent.trim();
                    }
                    if (!label && el.closest('label')) {
                        label = el.closest('label').textContent.trim();
                    }

                    // Build selector
                    let selector = '';
                    if (id) selector = `#${id}`;
                    else if (name) selector = `[name="${name}"]`;
                    else selector = `${el.tagName.toLowerCase()}:nth-of-type(${idx + 1})`;

                    const fieldData = {
                        tag: el.tagName.toLowerCase(),
                        type: type,
                        name: name,
                        id: id,
                        placeholder: el.placeholder || '',
                        label: label,
                        required: el.required || false,
                        aria_label: el.getAttribute('aria-label') || '',
                        selector: selector
                    };

                    if (type === 'checkbox' || type === 'radio') {
                        results.checkboxes.push(fieldData);
                    } else if (type === 'submit') {
                        results.submit = selector;
                    } else {
                        results.fields.push(fieldData);
                    }
                });

                // Find submit button within form
                if (!results.submit) {
                    // Try multiple selectors in priority order
                    const submitSelectors = [
                        'input[type="submit"]',
                        'button[type="submit"]',
                        'button:not([type])',
                        '[class*="submit"]',
                        '[value*="Continue"]',
                        '[value*="Submit"]',
                        '[value*="Register"]',
                        '[value*="Create"]',
                        '[value*="Sign"]',
                    ];
                    for (const sel of submitSelectors) {
                        const btn = targetForm.querySelector(sel);
                        if (btn) {
                            if (btn.id) {
                                results.submit = `#${btn.id}`;
                            } else if (btn.name) {
                                results.submit = `[name="${btn.name}"]`;
                            } else if (btn.value) {
                                results.submit = `input[value="${btn.value}"]`;
                            } else {
                                results.submit = sel;
                            }
                            break;
                        }
                    }
                }

                return results;
            }
        """, form_selector)

        # Convert to FormField objects and map to profile keys
        for f in elements['fields']:
            field = FormField(**f)
            field.profile_key = self._map_to_profile_key(field)
            form_data.fields.append(field)

        for c in elements['checkboxes']:
            checkbox = FormField(**c)
            form_data.checkboxes.append(checkbox)

        form_data.submit_button = elements['submit']

        return form_data

    def _map_to_profile_key(self, field: FormField) -> str:
        """Map field to profile key using intelligent matching."""
        # Check name, id, placeholder, label, aria_label
        candidates = [
            field.name.lower().replace('[', '_').replace(']', ''),
            field.id.lower(),
            field.placeholder.lower(),
            field.label.lower(),
            field.aria_label.lower()
        ]

        for candidate in candidates:
            # Remove common prefixes/suffixes
            cleaned = re.sub(r'^(customer|user|account|register|signup|form)[_\-\[\]]?', '', candidate)
            cleaned = re.sub(r'[_\-\[\]]?(field|input|txt)$', '', cleaned)
            cleaned = cleaned.replace('_', '').replace('-', '').replace(' ', '')

            if cleaned in FIELD_MAPPINGS:
                return FIELD_MAPPINGS[cleaned]

            # Partial match
            for pattern, profile_key in FIELD_MAPPINGS.items():
                if pattern in cleaned or cleaned in pattern:
                    return profile_key

        # Type-based fallback
        if field.type == 'email':
            return 'email'
        if field.type == 'password':
            return 'password'
        if field.type == 'tel':
            return 'phone'
        if field.type == 'date':
            return 'birthdate'

        return ""

    def _log_fields(self, form: FormData, profile: dict = None):
        """Log discovered fields to terminal."""
        print(f"\n{'='*70}")
        print(f"FORM ACTION: {form.action}")
        print(f"FORM METHOD: {form.method}")
        print(f"{'='*70}")

        print(f"\n[FIELDS FOUND: {len(form.fields)}]")
        print(f"{'-'*70}")
        print(f"{'TYPE':<12} | {'NAME':<25} | {'PROFILE KEY':<15} | {'HAS VALUE'}")
        print(f"{'-'*70}")

        for f in form.fields:
            has_value = "YES" if profile and f.profile_key and profile.get(f.profile_key) else "NO"
            if not f.profile_key:
                has_value = "UNMAPPED"
            print(f"{f.type:<12} | {f.name[:25]:<25} | {f.profile_key:<15} | {has_value}")

        if form.checkboxes:
            print(f"\n[CHECKBOXES: {len(form.checkboxes)}]")
            print(f"{'-'*70}")
            for c in form.checkboxes:
                print(f"  [{c.type}] {c.name or c.id} - {c.label[:50] if c.label else 'No label'}")

        if form.submit_button:
            print(f"\n[SUBMIT BUTTON]: {form.submit_button}")
        else:
            print(f"\n[!] NO SUBMIT BUTTON FOUND")

    async def _detect_captcha(self) -> str:
        """Detect CAPTCHA presence on page."""
        captcha_signatures = await self.page.evaluate("""
            () => {
                const html = document.documentElement.innerHTML.toLowerCase();
                const detected = [];

                // hCaptcha
                if (html.includes('hcaptcha') || document.querySelector('[data-hcaptcha]') ||
                    document.querySelector('.h-captcha') || document.querySelector('iframe[src*="hcaptcha"]')) {
                    detected.push('hCaptcha');
                }

                // reCAPTCHA
                if (html.includes('recaptcha') || document.querySelector('.g-recaptcha') ||
                    document.querySelector('iframe[src*="recaptcha"]')) {
                    detected.push('reCAPTCHA');
                }

                // Cloudflare
                if (html.includes('cf-turnstile') || document.querySelector('.cf-turnstile') ||
                    document.querySelector('iframe[src*="challenges.cloudflare"]')) {
                    detected.push('Cloudflare');
                }

                // Generic captcha
                if (document.querySelector('[class*="captcha"]') ||
                    document.querySelector('[id*="captcha"]')) {
                    if (detected.length === 0) detected.push('Unknown CAPTCHA');
                }

                return detected.join(', ');
            }
        """)
        return captcha_signatures

    async def _test_endpoint(self, form: FormData) -> Dict[str, Any]:
        """Test form endpoint with dummy POST."""
        print(f"\n[TESTING ENDPOINT]")
        print(f"URL: {form.action}")

        # Build dummy data
        dummy_data = {}
        for f in form.fields:
            if f.type == 'email':
                dummy_data[f.name] = 'test@example.com'
            elif f.type == 'password':
                dummy_data[f.name] = 'TestPass123!'
            elif f.name:
                dummy_data[f.name] = 'TestValue'

        for c in form.checkboxes:
            if c.name:
                dummy_data[c.name] = 'on'

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                if form.method == 'POST':
                    resp = await client.post(form.action, data=dummy_data)
                else:
                    resp = await client.get(form.action, params=dummy_data)

                result = {
                    "status_code": resp.status_code,
                    "final_url": str(resp.url),
                    "redirected": str(resp.url) != form.action,
                    "content_length": len(resp.content),
                    "success": resp.status_code in [200, 201, 302, 303],
                }

                # Check for error keywords
                text = resp.text.lower()
                if 'captcha' in text or 'robot' in text or 'bot' in text:
                    result['blocked'] = True
                    result['block_reason'] = 'CAPTCHA/Bot detection'
                elif 'error' in text and 'success' not in text:
                    result['has_errors'] = True

                print(f"  Status: {result['status_code']}")
                print(f"  Redirected: {result['redirected']}")
                if result.get('blocked'):
                    print(f"  [!] BLOCKED: {result['block_reason']}")

                return result

        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"error": str(e)}

    async def _fill_form(self, form: FormData, profile: dict, wait_for_captcha: bool = False) -> Dict[str, Any]:
        """Fill form with profile data."""
        print(f"\n[FILLING FORM]")

        # Close any popups first
        await self._close_popups()

        filled = 0
        checked = 0
        errors = []

        # Fill each field
        for f in form.fields:
            if not f.profile_key:
                continue

            value = profile.get(f.profile_key, '')
            if not value:
                # Try alternate keys
                for alt in [f.profile_key.lower(), f.profile_key.upper()]:
                    if profile.get(alt):
                        value = profile.get(alt)
                        break

            if not value:
                continue

            try:
                element = await self.page.query_selector(f.selector)
                if element:
                    if f.tag == 'select':
                        await element.select_option(value=str(value))
                    else:
                        await element.fill(str(value))
                    filled += 1
                    print(f"  Filled: {f.name} = {str(value)[:30]}...")
            except Exception as e:
                errors.append(f"{f.name}: {e}")

        # Check checkboxes
        for c in form.checkboxes:
            try:
                element = await self.page.query_selector(c.selector)
                if element:
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.click(force=True)
                        checked += 1
                        print(f"  Checked: {c.name or c.id}")
            except Exception as e:
                errors.append(f"Checkbox {c.name}: {e}")

        # Wait for manual CAPTCHA solving if needed
        if wait_for_captcha:
            # Check if there's a CAPTCHA present
            captcha_present = await self.page.evaluate("""
                () => {
                    const selectors = [
                        '[class*="captcha"]', '[id*="captcha"]',
                        'iframe[src*="captcha"]', 'iframe[src*="hcaptcha"]',
                        'iframe[src*="recaptcha"]', '[class*="cf-turnstile"]',
                        '.g-recaptcha', '.h-captcha'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) return true;
                    }
                    return false;
                }
            """)

            if captcha_present:
                print(f"\n  ═══════════════════════════════════════════════")
                print(f"  [CAPTCHA] Solve the CAPTCHA in the browser window")
                print(f"  [CAPTCHA] Waiting up to 5 minutes...")
                print(f"  ═══════════════════════════════════════════════")

                # Wait up to 5 minutes for user to solve CAPTCHA
                for i in range(300):
                    await asyncio.sleep(1)
                    captcha_visible = await self.page.evaluate("""
                        () => {
                            const selectors = [
                                '[class*="captcha"]', '[id*="captcha"]',
                                'iframe[src*="captcha"]', 'iframe[src*="hcaptcha"]',
                                'iframe[src*="recaptcha"]', '[class*="cf-turnstile"]',
                                '.g-recaptcha', '.h-captcha'
                            ];
                            for (const sel of selectors) {
                                const el = document.querySelector(sel);
                                if (el && el.offsetParent !== null) return true;
                            }
                            return false;
                        }
                    """)
                    if not captcha_visible:
                        print(f"  [CAPTCHA] Solved! Continuing...")
                        await asyncio.sleep(1)  # Brief pause after solving
                        break
                    if i % 30 == 0 and i > 0:
                        mins_left = (300-i) // 60
                        print(f"  [CAPTCHA] Still waiting... ({mins_left}m remaining)")
                else:
                    print(f"  [CAPTCHA] Timeout - proceeding anyway")

        # Submit - try multiple approaches
        submitted = False
        submit_selectors = [
            form.submit_button,
            'input[type="submit"]',
            'button[type="submit"]',
            'button:has-text("Continue")',
            'button:has-text("Submit")',
            'button:has-text("Register")',
            'button:has-text("Create")',
            'button:has-text("Sign")',
            'input[value*="Continue"]',
            'input[value*="Submit"]',
            'input[value*="Register"]',
        ]

        await asyncio.sleep(0.5)
        await self._close_popups()

        for selector in submit_selectors:
            if not selector:
                continue
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click(force=True)
                    submitted = True
                    print(f"  Submitted form ({selector})")
                    await asyncio.sleep(3)
                    break
            except:
                continue

        # Last resort: JavaScript
        if not submitted:
            try:
                await self.page.evaluate("""
                    () => {
                        const btn = document.querySelector('input[type="submit"], button[type="submit"]');
                        if (btn) btn.click();
                    }
                """)
                submitted = True
                print(f"  Submitted form (JS fallback)")
                await asyncio.sleep(3)
            except Exception as e:
                errors.append(f"Submit: {e}")

        # Check result
        final_url = self.page.url

        result = {
            "success": filled > 0 and submitted,
            "fields_filled": filled,
            "checkboxes_checked": checked,
            "submitted": submitted,
            "final_url": final_url,
            "url_changed": final_url != form.url,
            "errors": errors
        }

        print(f"\n{'='*70}")
        print(f"RESULT: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"{'='*70}")
        print(f"  Fields filled: {filled}/{len(form.fields)}")
        print(f"  Checkboxes: {checked}/{len(form.checkboxes)}")
        print(f"  Submitted: {submitted}")
        print(f"  URL changed: {result['url_changed']}")
        if final_url != form.url:
            print(f"  Final URL: {final_url}")
        if errors:
            print(f"  Errors: {len(errors)}")
            for e in errors[:3]:
                print(f"    - {e}")

        return result


def load_profile(profile_id: str = None) -> dict:
    """Load profile from JSON file."""
    profiles_dir = Path(__file__).parent.parent / "profiles"

    if profile_id:
        # Try exact match
        profile_file = profiles_dir / f"{profile_id}.json"
        if profile_file.exists():
            return json.loads(profile_file.read_text(encoding='utf-8'))

        # Try partial match
        for f in profiles_dir.glob("*.json"):
            if profile_id in f.stem:
                return json.loads(f.read_text(encoding='utf-8'))

    # Return first profile
    for f in profiles_dir.glob("*.json"):
        return json.loads(f.read_text(encoding='utf-8'))

    return {}


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Site Analyzer & Auto-Filler')
    parser.add_argument('url', help='URL to analyze')
    parser.add_argument('--fill', action='store_true', help='Fill form after analysis')
    parser.add_argument('--profile', '-p', help='Profile ID to use')
    parser.add_argument('--visible', action='store_true', help='Show browser')
    parser.add_argument('--save', action='store_true', help='Save recording after analysis')

    args = parser.parse_args()

    profile = load_profile(args.profile) if args.fill else None

    if args.fill and profile:
        pname = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        print(f"Using profile: {pname} ({profile.get('email', '')})")

    analyzer = SiteAnalyzer(headless=not args.visible)
    result = await analyzer.analyze(args.url, profile, args.fill)

    # Save recording if requested
    if args.save and result.form:
        recording = generate_recording(result)
        rec_dir = Path(__file__).parent.parent / "recordings"
        rec_file = rec_dir / f"{result.domain.replace('.', '-')}.json"
        rec_file.write_text(json.dumps(recording, indent=2), encoding='utf-8')
        print(f"\nRecording saved: {rec_file}")

    print(f"\n[CLASSIFICATION]: {result.classification.upper()}")

    return result


def generate_recording(result: AnalysisResult) -> dict:
    """Generate recording JSON from analysis result."""
    steps = [
        {
            "type": "setViewport",
            "width": 1280,
            "height": 800,
            "deviceScaleFactor": 1,
            "isMobile": False,
            "hasTouch": False,
            "isLandscape": False
        },
        {
            "type": "navigate",
            "url": result.url,
            "assertedEvents": [{"type": "navigation", "url": result.url}]
        }
    ]

    # Add field steps
    for f in result.form.fields:
        if f.profile_key:
            steps.append({
                "type": "change",
                "selectors": [[f.selector]],
                "value": f"{{{{{{f.profile_key}}}}}}",
                "target": "main",
                "_fieldInfo": {
                    "name": f.name,
                    "type": f.type,
                    "label": f.label,
                    "profile_key": f.profile_key
                }
            })

    # Add checkbox steps
    for c in result.form.checkboxes:
        steps.append({
            "type": "click",
            "selectors": [[c.selector]],
            "target": "main",
            "offsetX": 5,
            "offsetY": 5,
            "_isCheckbox": True
        })

    # Add submit
    if result.form.submit_button:
        steps.append({
            "type": "click",
            "selectors": [[result.form.submit_button]],
            "target": "main",
            "offsetX": 10,
            "offsetY": 10,
            "_isSubmit": True
        })

    return {
        "recording_id": result.domain.replace('.', '-'),
        "recording_name": f"{result.domain} Signup",
        "url": result.url,
        "original_url": result.url,
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "created_timestamp": result.timestamp,
        "total_fields": len(result.form.fields),
        "total_checkboxes": len(result.form.checkboxes),
        "steps": steps,
        "title": f"{result.domain} Signup",
        "_source": "site_analyzer"
    }


async def batch_analyze(sites_file: str, output_file: str = None, do_fill: bool = False, wait_for_captcha: bool = False):
    """Analyze multiple sites from a file."""
    sites_path = Path(sites_file)
    if not sites_path.exists():
        print(f"File not found: {sites_file}")
        return

    # Read URLs
    urls = []
    with open(sites_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)

    print(f"\n{'='*70}")
    print(f"BATCH ANALYSIS: {len(urls)} sites")
    if wait_for_captcha:
        print(f"MODE: Manual CAPTCHA solving (browser visible)")
    print(f"{'='*70}")

    profile = load_profile() if do_fill else None
    results = {
        'working': [],
        'captcha': [],
        'error': [],
        'analyzed': []
    }

    # Force visible browser when waiting for CAPTCHA
    headless = not wait_for_captcha

    for i, url in enumerate(urls):
        print(f"\n[{i+1}/{len(urls)}] {url[:60]}...")
        try:
            analyzer = SiteAnalyzer(headless=headless)
            result = await analyzer.analyze(url, profile, do_fill, wait_for_captcha=wait_for_captcha)

            results[result.classification].append({
                'url': url,
                'domain': result.domain,
                'fields': len(result.form.fields) if result.form else 0,
                'captcha': result.form.captcha_detected if result.form else ''
            })
        except Exception as e:
            results['error'].append({'url': url, 'error': str(e)})

    # Summary
    print(f"\n{'='*70}")
    print(f"BATCH RESULTS")
    print(f"{'='*70}")
    print(f"  Working:  {len(results['working'])}")
    print(f"  CAPTCHA:  {len(results['captcha'])}")
    print(f"  Analyzed: {len(results['analyzed'])}")
    print(f"  Errors:   {len(results['error'])}")

    # Save results
    if output_file:
        output_path = Path(output_file)
        output_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(f"\nResults saved to: {output_file}")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Site Analyzer & Auto-Filler')
    parser.add_argument('url', nargs='?', help='URL to analyze (or --batch for multiple)')
    parser.add_argument('--fill', action='store_true', help='Fill form after analysis')
    parser.add_argument('--profile', '-p', help='Profile ID to use')
    parser.add_argument('--visible', action='store_true', help='Show browser')
    parser.add_argument('--captcha', action='store_true', help='Wait for manual CAPTCHA solving')
    parser.add_argument('--save', action='store_true', help='Save recording after analysis')
    parser.add_argument('--batch', '-b', help='Batch analyze sites from file')
    parser.add_argument('--output', '-o', help='Output file for batch results')

    args = parser.parse_args()

    if args.batch:
        asyncio.run(batch_analyze(args.batch, args.output, args.fill, args.captcha))
    elif args.url:
        # Single URL mode
        async def run_single():
            # Force visible when captcha solving is enabled
            headless = not (args.visible or args.captcha)
            profile = load_profile(args.profile) if args.fill else None

            if profile:
                pname = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
                print(f"Using profile: {pname} ({profile.get('email', '')})")

            if args.captcha:
                print(f"CAPTCHA mode: Browser visible for manual solving")

            analyzer = SiteAnalyzer(headless=headless)
            result = await analyzer.analyze(args.url, profile, args.fill, wait_for_captcha=args.captcha)

            # Save recording if requested
            if args.save and result.form:
                recording = generate_recording(result)
                rec_dir = Path(__file__).parent.parent / "recordings"
                rec_file = rec_dir / f"{result.domain.replace('.', '-')}.json"
                rec_file.write_text(json.dumps(recording, indent=2), encoding='utf-8')
                print(f"\nRecording saved: {rec_file}")

            print(f"\n[CLASSIFICATION]: {result.classification.upper()}")

        asyncio.run(run_single())
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python tools/site_analyzer.py https://example.com/signup")
        print("  python tools/site_analyzer.py https://example.com/signup --fill")
        print("  python tools/site_analyzer.py https://example.com/signup --fill --captcha  # Manual CAPTCHA solving")
        print("  python tools/site_analyzer.py --batch sites/sites.md --output results.json")
        print("  python tools/site_analyzer.py --batch sites/sites_captcha.md --fill --captcha  # Fill with CAPTCHA")
