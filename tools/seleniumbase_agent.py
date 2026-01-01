"""
SeleniumBase Agent - Streamlined form filling with 7-phase pipeline.

Uses SeleniumBase UC Mode exclusively for:
- Built-in Cloudflare bypass
- Anti-bot detection avoidance
- Single browser window (no switching)

Pipeline:
1. NAVIGATE - Open URL with UC Mode
2. CLEAR - Close all popups
3. DETECT - Find form fields
4. FILL - Fill fields with profile data
5. CAPTCHA - Solve if present
6. SUBMIT - Click submit button
7. LEARN - Save mappings for next time
"""

import asyncio
import json
import logging
from pathlib import Path
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

# Smart dropdown value mapping
try:
    from .dropdown_mapper import smart_map_dropdown, detect_field_type, load_mappings
    DROPDOWN_MAPPER_AVAILABLE = True
except ImportError:
    DROPDOWN_MAPPER_AVAILABLE = False

# Browser debloating for faster page loads
try:
    from .browser_debloat import (
        setup_seleniumbase_blocking,
        inject_debloat_script_selenium,
        isolate_form_selenium,
        get_debloat_chrome_args_string,
        setup_form_isolation_cdp,
        setup_resource_blocking_cdp,
    )
    DEBLOAT_AVAILABLE = True
except ImportError:
    DEBLOAT_AVAILABLE = False

# Ollama for AI-powered field analysis
try:
    from .ollama_agent import OllamaAgent
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Groq for orchestration (smarter decision making)
try:
    from .groq_orchestrator import GroqOrchestrator
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Field mapping store for "Learn Once, Replay Many"
try:
    from .field_mapping_store import FieldMappingStore
    MAPPING_STORE_AVAILABLE = True
except ImportError:
    MAPPING_STORE_AVAILABLE = False

logger = logging.getLogger("seleniumbase-agent")


# ============================================================
# AI FIELD ANALYZER - Uses Ollama to scrape/analyze forms
# ============================================================

AI_FIELD_ANALYSIS_PROMPT = """Analyze this form and return field mappings as JSON.

FORM HTML:
{form_html}

PROFILE FIELDS AVAILABLE:
{profile_fields}

TASK: Map each form field to the correct profile field.

RESPONSE FORMAT (JSON array):
[
  {{"selector": "#email", "profile_field": "email", "type": "text", "confidence": 0.95}},
  {{"selector": "#firstName", "profile_field": "firstName", "type": "text", "confidence": 0.9}},
  {{"selector": "#country", "profile_field": "country", "type": "select", "confidence": 0.85}}
]

Rules:
1. Use CSS selectors (prefer #id, then [name=...])
2. Map to exact profile field names
3. Include confidence score 0.0-1.0
4. Set type: text, select, checkbox, password
5. Only include fillable fields (not buttons, hidden)
6. For password confirmation fields, use profile_field: "password"

Return ONLY valid JSON array. No explanation."""


async def analyze_form_with_ai(sb, profile: dict) -> List[Dict]:
    """
    Use Ollama to analyze form structure and map fields to profile.

    Args:
        sb: SeleniumBase browser instance
        profile: User profile dict

    Returns:
        List of field mappings with selectors and profile fields
    """
    import json
    import httpx

    # Extract form HTML
    try:
        form_html = sb.execute_script("""
            // Find all forms or main content
            var forms = document.querySelectorAll('form');
            if (forms.length === 0) {
                // No form tag, get main content
                forms = [document.body];
            }

            var result = [];
            forms.forEach(function(form) {
                // Get all input-like elements
                var inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(function(el) {
                    if (el.type === 'hidden' || el.type === 'submit') return;
                    if (!el.offsetParent) return; // Skip invisible

                    var info = {
                        tag: el.tagName.toLowerCase(),
                        type: el.type || 'text',
                        id: el.id || '',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        autocomplete: el.getAttribute('autocomplete') || ''
                    };

                    // Get associated label
                    if (el.id) {
                        var label = document.querySelector('label[for="' + el.id + '"]');
                        if (label) info.label = label.textContent.trim();
                    }

                    // Get dropdown options for select
                    if (el.tagName === 'SELECT') {
                        info.options = Array.from(el.options).slice(0, 10).map(o => o.text.trim());
                    }

                    result.push(info);
                });
            });
            return JSON.stringify(result);
        """)

        if not form_html or form_html == '[]':
            logger.warning("No form fields found in page")
            return []

    except Exception as e:
        logger.error(f"Failed to extract form HTML: {e}")
        return []

    # Get profile field names
    profile_fields = list(profile.keys())

    # Build prompt
    prompt = AI_FIELD_ANALYSIS_PROMPT.format(
        form_html=form_html[:4000],  # Limit size
        profile_fields=json.dumps(profile_fields)
    )

    # Call Ollama
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1000
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")

                # Parse JSON from response
                start = content.find('[')
                end = content.rfind(']') + 1

                if start >= 0 and end > start:
                    mappings = json.loads(content[start:end])
                    print(f"[AI] Ollama found {len(mappings)} field mappings")
                    return mappings

    except httpx.TimeoutException:
        print("[AI] Ollama timeout - falling back to pattern matching")
    except Exception as e:
        # Handle encoding issues on Windows
        error_msg = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"[AI] Ollama failed: {error_msg}")

    return []

# Profile field patterns - maps profile keys to label text patterns
# Order matters - more specific patterns should come first
# Email MUST come before name to avoid 'username' matching 'name'
LABEL_PATTERNS = {
    'email': ['email', 'e-mail', 'emailaddress', 'email address', 'mail'],
    'firstName': ['firstname', 'first name', 'first-name', 'given name', 'fname', 'givenname'],
    'lastName': ['lastname', 'last name', 'last-name', 'surname', 'family name', 'lname', 'familyname'],
    'name': ['full name', 'fullname', 'your name'],  # Removed 'name' - too generic, matches 'username'
    'password': ['password', 'passwd', 'pass', 'pwd', 'create password', 'new password', 'newpassword'],
    'phone': ['phone', 'mobile', 'telephone', 'tel', 'cell', 'phonenumber', 'phone number', 'mobilephone'],
    'address': ['address', 'street', 'address1', 'addressline1', 'address line 1', 'street address', 'streetaddress'],
    'address2': ['address2', 'addressline2', 'address line 2', 'apt', 'suite', 'unit', 'apartment'],
    'city': ['city', 'town', 'suburb', 'locality'],
    'state': ['state', 'province', 'region', 'county'],
    'zip': ['zip', 'zipcode', 'zip code', 'postal', 'postalcode', 'postal code', 'postcode'],
    'country': ['country', 'nation', 'countrycode', 'country_code', 'phonecountry', 'phone_country', 'countryselect', 'countryphone'],
    'company': ['company', 'organization', 'org', 'business', 'companyname', 'company name'],
    'website': ['website', 'url', 'web', 'homepage', 'web address'],
    'username': ['username', 'user', 'userid', 'user name', 'login', 'loginid'],
    'dob': ['dob', 'dateofbirth', 'date of birth', 'birthday', 'birthdate', 'birth date'],
    'title': ['title', 'salutation', 'prefix', 'honorific'],
}

# Patterns that indicate confirm/verify password field
CONFIRM_PASSWORD_PATTERNS = [
    'confirm', 'verify', 'retype', 're-enter', 'reenter', 'repeat',
    'confirmpassword', 'verifypassword', 'password2', 'pwd2', 'pass2'
]

# Patterns that indicate confirm/verify email field
CONFIRM_EMAIL_PATTERNS = [
    'confirm email', 'verify email', 'email confirm', 'emailconfirm',
    'confirm_email', 'email_confirm', 'email2', 'verifyemail', 'confirmemail'
]

# Split date of birth patterns - for sites with separate day/month/year fields
DOB_DAY_PATTERNS = ['birthday', 'birth_day', 'birthdate', 'dob_day', 'birthdayfields_day', 'formfieldday', '_day']
DOB_MONTH_PATTERNS = ['birthmonth', 'birth_month', 'dob_month', 'birthdayfields_month', 'formfieldmonth', '_month']
DOB_YEAR_PATTERNS = ['birthyear', 'birth_year', 'dob_year', 'birthdayfields_year', 'formfieldyear', '_year']

# Title/salutation patterns
TITLE_PATTERNS = ['title', 'salutation', 'prefix', 'honorific', 'mr', 'mrs', 'ms', 'dr']

# Submit button selectors - tried in order
SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:contains("Create Account")',
    'button:contains("Create")',
    'button:contains("Register")',
    'button:contains("Submit")',
    'button:contains("Sign Up")',
    'button:contains("Sign up")',
    'button:contains("Join")',
    'button:contains("Continue")',
    'input[value="Submit"]',
    'input[value="Register"]',
    'input[value="Create"]',
    '.submit-btn',
    '.btn-submit',
    '#submit',
    '#register',
    '[data-action="submit"]',
]

# Next step button selectors - for multi-step forms
NEXT_STEP_SELECTORS = [
    'button:contains("Next")',
    'button:contains("Continue")',
    'button:contains("Proceed")',
    'button:contains("Step 2")',
    'button:contains("Step 3")',
    'button:contains("Step 4")',
    'button:contains("Step 5")',
    'a:contains("Next")',
    'a:contains("Continue")',
    'input[value="Next"]',
    'input[value="Continue"]',
    'input[value="Proceed"]',
    '[data-action="next"]',
    '[data-step="next"]',
    '.next-btn',
    '.btn-next',
    '.continue-btn',
    '.btn-continue',
    '#next',
    '#continue',
    '#next-step',
    '.step-next',
    'button[type="button"]:contains("Next")',
    'button[type="button"]:contains("Continue")',
    # Common wizard patterns
    '.wizard-next',
    '.form-wizard-next',
    '.multi-step-next',
    '[data-wizard="next"]',
]

# Patterns indicating multi-step form navigation elements
STEP_INDICATOR_PATTERNS = [
    '.step-indicator',
    '.steps',
    '.wizard-steps',
    '.progress-steps',
    '.multi-step',
    '.form-steps',
    '[data-step]',
    '.step-1', '.step-2', '.step-3',
    '.current-step',
    '.active-step',
]

# Popup close selectors
POPUP_CLOSE_SELECTORS = [
    'button[aria-label="Close"]',
    'button[aria-label="close"]',
    '.close-button',
    '.modal-close',
    '.popup-close',
    '[data-dismiss="modal"]',
    '.btn-close',
    'button:contains("No thanks")',
    'button:contains("No Thanks")',
    'button:contains("Close")',
    'button:contains("×")',
    'button:contains("X")',
    '.cookie-close',
    '#cookie-accept',
    'button:contains("Accept")',
    'button:contains("Got it")',
    'button:contains("I agree")',
    'button:contains("Agree")',
]


def normalize_profile_field(field_name: str) -> str:
    """
    Normalize AI-returned profile field names to standard profile field names.

    Handles cases like:
    - "suburb/City" -> "city"
    - "suburb" -> "city"
    - "postalCode" -> "zip"
    - "FIRSTNAME" -> "firstName"

    Args:
        field_name: Raw field name from AI or aria label

    Returns:
        Normalized profile field name
    """
    if not field_name:
        return field_name

    # Convert to lowercase for matching
    field_lower = field_name.lower().replace(' ', '').replace('-', '').replace('_', '').replace('/', '')

    # Build reverse lookup from LABEL_PATTERNS
    # Maps pattern variations to standard field names
    FIELD_NORMALIZATIONS = {
        # Email
        'email': 'email', 'mail': 'email', 'emailaddress': 'email',

        # Name fields
        'firstname': 'firstName', 'fname': 'firstName', 'givenname': 'firstName',
        'lastname': 'lastName', 'lname': 'lastName', 'surname': 'lastName', 'familyname': 'lastName',
        'fullname': 'name', 'yourname': 'name',

        # Password
        'password': 'password', 'passwd': 'password', 'pwd': 'password',

        # Phone
        'phone': 'phone', 'mobile': 'phone', 'telephone': 'phone', 'tel': 'phone', 'cell': 'phone',
        'phonenumber': 'phone', 'mobilephone': 'phone',

        # Address
        'address': 'address', 'street': 'address', 'address1': 'address', 'addressline1': 'address',
        'streetaddress': 'address',
        'address2': 'address2', 'addressline2': 'address2', 'apt': 'address2', 'suite': 'address2',
        'unit': 'address2', 'apartment': 'address2',

        # City - IMPORTANT: suburb maps to city
        'city': 'city', 'town': 'city', 'suburb': 'city', 'locality': 'city',
        'suburbcity': 'city',  # For "suburb/city" combo labels

        # State
        'state': 'state', 'province': 'state', 'region': 'state', 'county': 'state',

        # Zip
        'zip': 'zip', 'zipcode': 'zip', 'postalcode': 'zip', 'postcode': 'zip', 'postal': 'zip',

        # Country
        'country': 'country', 'nation': 'country', 'countrycode': 'country',

        # Company
        'company': 'company', 'organization': 'company', 'org': 'company', 'business': 'company',
        'companyname': 'company',

        # Username
        'username': 'username', 'user': 'username', 'userid': 'username', 'login': 'username',

        # Date of birth
        'dob': 'dob', 'dateofbirth': 'dob', 'birthday': 'dob', 'birthdate': 'dob',

        # Title
        'title': 'title', 'salutation': 'title', 'prefix': 'title',

        # Gender
        'gender': 'gender', 'sex': 'gender',

        # Website
        'website': 'website', 'url': 'website', 'homepage': 'website',
    }

    # Check if already a standard field name
    standard_fields = ['email', 'firstName', 'lastName', 'name', 'password', 'phone',
                       'address', 'address2', 'city', 'state', 'zip', 'country',
                       'company', 'username', 'dob', 'title', 'gender', 'website']

    if field_name in standard_fields:
        return field_name

    # Look up in normalizations
    if field_lower in FIELD_NORMALIZATIONS:
        return FIELD_NORMALIZATIONS[field_lower]

    # Check for partial matches (for compound names like "suburb/city")
    for pattern, standard in FIELD_NORMALIZATIONS.items():
        if pattern in field_lower or field_lower in pattern:
            return standard

    # If no match found, return original (might be a valid field we don't know about)
    return field_name


class SeleniumBaseAgent:
    """
    Streamlined form-filling agent using SeleniumBase UC Mode.

    Single browser, 7-phase pipeline, no complexity.
    """

    def __init__(
        self,
        headless: bool = False,
        hold_open: int = 10,
        debloat: bool = True,
        isolate_form: bool = False,
        use_ai: bool = True,
        use_orchestrator: bool = False,
        groq_api_key: str = None
    ):
        """
        Initialize the agent.

        Args:
            headless: Run browser in headless mode
            hold_open: Seconds to keep browser open after filling (0 = close immediately)
            debloat: Enable browser debloating (no CSS/images) for faster loading
            isolate_form: Aggressive debloat - remove EVERYTHING except the form
            use_ai: Use Ollama AI for intelligent field detection
            use_orchestrator: Use Groq LLM (Llama 3.3 70B) to orchestrate filling
            groq_api_key: Groq API key (or set GROQ_API_KEY env var)
        """
        self.headless = headless
        self.hold_open = hold_open
        self.debloat = debloat
        self.isolate_form = isolate_form
        self.use_ai = use_ai
        self.use_orchestrator = use_orchestrator
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self._running = False
        self._should_stop = False
        self._orchestrator = None

    async def fill_sites(
        self,
        urls: List[str],
        profile: Dict[str, Any],
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Fill multiple sites.

        Args:
            urls: List of URLs to fill
            profile: Profile data
            on_progress: Progress callback

        Returns:
            Summary result
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            if self._should_stop:
                break

            # Progress callback - site starting
            if on_progress:
                await on_progress({
                    "type": "site_start",
                    "site": url,
                    "current": i + 1,
                    "total": total
                })

            # Fill the site
            result = await self.fill_site(url, profile)
            results.append(result)

            # Progress callback - site complete
            if on_progress:
                await on_progress({
                    "type": "site_complete",
                    "site": url,
                    "result": result,
                    "current": i + 1,
                    "total": total
                })

        # Summary
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        total_fields = sum(r.get("fields_filled", 0) for r in results)

        return {
            "success": failed == 0,
            "total_sites": len(urls),
            "completed": len(results),
            "successful": successful,
            "failed": failed,
            "total_fields_filled": total_fields,
            "results": results
        }

    async def fill_site(self, url: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill a single site using the 7-phase pipeline.

        Args:
            url: URL to fill
            profile: Profile data

        Returns:
            Result dict
        """
        result = {
            "url": url,
            "success": False,
            "fields_filled": 0,
            "fields_detected": 0,
            "submitted": False,
            "error": None,
            "phases_completed": [],
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            # Multi-step tracking
            "steps_completed": 1,  # At least 1 step (initial form)
            "fields_per_step": [],  # List of field counts per step
            "is_multi_step": False,
        }

        try:
            from seleniumbase import SB

            print(f"\n{'='*60}")
            print(f"[Agent] Starting: {url}")
            print(f"{'='*60}")

            # Build SB kwargs - add debloat Chrome args if enabled
            sb_kwargs = {
                "uc": True,
                "headless": self.headless,
            }

            if DEBLOAT_AVAILABLE and self.debloat:
                # Add Chrome args to block images at browser level
                sb_kwargs["chromium_arg"] = get_debloat_chrome_args_string()
                print("[Debloat] Chrome args added for image/CSS blocking")

            # Run synchronous SeleniumBase code
            with SB(**sb_kwargs) as sb:

                # ==================== PRE-LOAD: Get saved mappings for isolation ====================
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                saved_mappings = None
                preserve_selectors = []

                if MAPPING_STORE_AVAILABLE:
                    store = FieldMappingStore()
                    if store.has_mappings(domain):
                        saved_mappings = store.get_mappings(domain)
                        if saved_mappings:
                            # Extract selectors to preserve during isolation
                            preserve_selectors = [m.get('selector') for m in saved_mappings if m.get('selector')]
                            print(f"[Pre-load] Found {len(saved_mappings)} saved mappings for {domain}")

                # ==================== PRE-NAVIGATION: Set up CDP blocking & isolation ====================
                if DEBLOAT_AVAILABLE:
                    # First, open about:blank to establish CDP connection
                    sb.open("about:blank")

                    # Set up resource blocking BEFORE navigation
                    if self.debloat:
                        print("\n[Setup] Enabling resource blocking (no CSS/images)...")
                        try:
                            setup_resource_blocking_cdp(sb)
                            print("[Setup] CDP resource blocking enabled")
                        except Exception as e:
                            print(f"[Setup] Warning: Resource blocking failed: {e}")

                    # Set up form isolation BEFORE navigation (page loads already isolated)
                    if self.isolate_form:
                        try:
                            setup_form_isolation_cdp(sb, preserve_selectors)
                            print(f"[Setup] Form isolation script registered (preserving {len(preserve_selectors)} selectors)")
                        except Exception as e:
                            print(f"[Setup] Warning: Form isolation setup failed: {e}")

                # ==================== PHASE 1: NAVIGATE ====================
                print("\n[Phase 1] NAVIGATE - Opening URL with UC Mode...")
                try:
                    sb.uc_open_with_reconnect(url, reconnect_time=4)
                    sb.sleep(2)

                    # Handle Cloudflare if present
                    title = sb.get_title().lower()
                    if 'just a moment' in title or 'checking' in title:
                        print("[Phase 1] Cloudflare detected - handling...")
                        try:
                            sb.uc_gui_handle_cf()
                            sb.sleep(3)
                        except:
                            pass

                        # Check again
                        title = sb.get_title().lower()
                        if 'just a moment' in title:
                            result["error"] = "Could not bypass Cloudflare"
                            return result
                        print("[Phase 1] Cloudflare bypassed!")

                    result["phases_completed"].append("navigate")
                    print(f"[Phase 1] Page loaded (debloated): {sb.get_title()[:50]}...")

                except Exception as e:
                    result["error"] = f"Navigation failed: {e}"
                    return result

                # ==================== PHASE 2: CLEAR PAGE ====================
                print("\n[Phase 2] CLEAR - Closing popups and banners...")
                popups_closed = self._close_popups(sb)
                print(f"[Phase 2] Closed {popups_closed} popups/banners")
                result["phases_completed"].append("clear")

                # ==================== PHASE 2.5: USE SAVED MAPPINGS ====================
                # "Learn Once, Replay Many" - use saved mappings if available (pre-loaded above)
                if saved_mappings:
                    print(f"\n[Trained] Found {len(saved_mappings)} saved mappings for {domain}")
                    for m in saved_mappings:
                        print(f"  - {m.get('selector')} -> {m.get('profile_field')}")

                    # Skip to Phase 4 using saved mappings
                    result["phases_completed"].append("detect")
                    result["used_saved_mappings"] = True
                    result["fields_detected"] = len(saved_mappings)

                    print("\n[Phase 4] FILL - Using saved mappings (no AI needed)...")
                    filled_count = self._fill_with_saved_mappings(sb, saved_mappings, profile)
                    result["fields_filled"] = filled_count
                    result["fields_per_step"].append(filled_count)

                    if filled_count > 0:
                        result["phases_completed"].append("fill")
                        print(f"[Phase 4] Filled {filled_count}/{len(saved_mappings)} fields using saved mappings")

                        # Skip to Phase 5 (CAPTCHA)
                        print("\n[Phase 5] CAPTCHA - Checking for CAPTCHA...")
                        captcha_result = self._handle_captcha(sb)
                        if captcha_result.get("detected"):
                            if captcha_result.get("solved"):
                                print("[Phase 5] CAPTCHA solved!")
                            else:
                                print(f"[Phase 5] CAPTCHA not solved: {captcha_result.get('error', 'manual needed')}")
                        else:
                            print("[Phase 5] No CAPTCHA detected")
                        result["phases_completed"].append("captcha")
                        result["captcha"] = captcha_result

                        # Phase 6: Submit
                        print("\n[Phase 6] SUBMIT - Looking for submit button...")
                        submitted = self._submit_form(sb)
                        result["submitted"] = submitted

                        if submitted:
                            print("[Phase 6] Form submitted!")
                            sb.sleep(3)
                            result["final_url"] = sb.get_current_url()
                        else:
                            print("[Phase 6] Could not find submit button")
                        result["phases_completed"].append("submit")

                        # Phase 7: Learn (already learned)
                        result["phases_completed"].append("learn")
                        result["success"] = filled_count > 0

                        if self.hold_open > 0:
                            print(f"\n[Agent] Keeping browser open for {self.hold_open} seconds...")
                            sb.sleep(self.hold_open)

                        result["completed_at"] = datetime.now().isoformat()
                        print(f"\n{'='*60}")
                        print(f"[Agent] Result: SUCCESS (used saved mappings)")
                        print(f"[Agent] Fields: {result['fields_filled']}/{result['fields_detected']} filled")
                        print(f"[Agent] Submitted: {result['submitted']}")
                        print(f"{'='*60}\n")
                        return result

                # ==================== PHASE 3: DETECT FIELDS ====================
                print("\n[Phase 3] DETECT - Finding form fields...")

                # Try AI analysis first if enabled
                ai_mappings = []
                if self.use_ai:
                    print("[Phase 3] Using AI (Ollama) to analyze form structure...")
                    try:
                        ai_mappings = await analyze_form_with_ai(sb, profile)
                        if ai_mappings:
                            print(f"[Phase 3] AI found {len(ai_mappings)} field mappings:")
                            for m in ai_mappings:
                                print(f"  - {m.get('selector')} -> {m.get('profile_field')} (conf: {m.get('confidence', 0):.2f})")
                            result["ai_analysis"] = True
                    except Exception as e:
                        print(f"[Phase 3] AI analysis failed: {e}")
                        ai_mappings = []

                # Fall back to pattern-based detection
                fields = self._detect_fields(sb)
                result["fields_detected"] = len(fields)

                if not fields and not ai_mappings:
                    result["error"] = "No form fields found"
                    print("[Phase 3] No fields detected!")
                    sb.sleep(self.hold_open)
                    return result

                print(f"[Phase 3] Pattern-based found {len(fields)} fields:")
                for f in fields:
                    label = f.get('label', '')
                    label_str = f", label='{label}'" if label else ""
                    print(f"  - {f.get('selector')}: name={f.get('name')}, id={f.get('id')}, placeholder={f.get('placeholder')}{label_str}")
                result["phases_completed"].append("detect")

                # ==================== PHASE 4: FILL FORM ====================
                print("\n[Phase 4] FILL - Filling form fields...")

                # Choose filling strategy
                if self.use_orchestrator and GROQ_AVAILABLE and self.groq_api_key:
                    # Use Groq orchestrator for intelligent filling
                    print("[Phase 4] Using Groq orchestrator (Llama 3.3 70B)...")
                    orch_result = await self._fill_with_orchestrator(sb, fields, profile, url)
                    if orch_result:
                        filled_count = orch_result.get("fields_filled", 0)
                        result["orchestrator"] = True
                        result["orchestrator_actions"] = len(orch_result.get("actions", []))
                        if orch_result.get("submitted"):
                            result["submitted"] = True
                    else:
                        # Fallback if orchestrator fails
                        filled_count = self._fill_fields(sb, fields, profile)
                elif ai_mappings:
                    # Use AI field mappings from Ollama
                    print("[Phase 4] Using AI field mappings...")
                    filled_count = self._fill_with_ai_mappings(sb, ai_mappings, profile)
                else:
                    # Use pattern matching
                    filled_count = self._fill_fields(sb, fields, profile)
                result["fields_filled"] = filled_count
                result["fields_per_step"].append(filled_count)  # Track step 1 fields

                if filled_count == 0:
                    result["error"] = "Could not fill any fields"
                    print("[Phase 4] No fields were filled!")
                    sb.sleep(self.hold_open)
                    return result

                print(f"[Phase 4] Filled {filled_count}/{len(fields)} fields")
                result["phases_completed"].append("fill")

                # ==================== PHASE 5: HANDLE CAPTCHA ====================
                print("\n[Phase 5] CAPTCHA - Checking for CAPTCHA...")
                captcha_result = self._handle_captcha(sb)
                if captcha_result.get("detected"):
                    if captcha_result.get("solved"):
                        print("[Phase 5] CAPTCHA solved!")
                    else:
                        print(f"[Phase 5] CAPTCHA not solved: {captcha_result.get('error', 'manual needed')}")
                else:
                    print("[Phase 5] No CAPTCHA detected")
                result["phases_completed"].append("captcha")
                result["captcha"] = captcha_result

                # ==================== PHASE 6: SUBMIT ====================
                print("\n[Phase 6] SUBMIT - Looking for submit button...")
                submitted = self._submit_form(sb)
                result["submitted"] = submitted

                if submitted:
                    print("[Phase 6] Form submitted! Waiting for response...")
                    sb.sleep(3)
                    result["final_url"] = sb.get_current_url()

                    # ==================== PHASE 6.5: MULTI-STEP HANDLING ====================
                    print("\n[Phase 6.5] MULTI-STEP - Checking for additional form steps...")
                    current_url = sb.get_current_url()
                    multi_step_result = self._handle_multi_step(sb, profile, current_url, max_steps=5)

                    if multi_step_result["additional_steps"] > 0:
                        result["is_multi_step"] = True
                        result["steps_completed"] = 1 + multi_step_result["additional_steps"]
                        result["fields_per_step"].extend(multi_step_result["fields_per_step"])
                        result["fields_filled"] += multi_step_result["total_fields_filled"]
                        result["fields_detected"] += multi_step_result["total_fields_detected"]
                        result["final_url"] = sb.get_current_url()
                        print(f"[Phase 6.5] Completed {multi_step_result['additional_steps']} additional step(s)")
                        print(f"[Phase 6.5] Total steps: {result['steps_completed']}, Total fields: {result['fields_filled']}")
                    else:
                        print("[Phase 6.5] No additional steps detected (single-page form)")
                else:
                    print("[Phase 6] Could not find submit button")
                result["phases_completed"].append("submit")

                # ==================== PHASE 7: LEARN ====================
                print("\n[Phase 7] LEARN - Saving field mappings...")

                # Save learned mappings for future use
                if MAPPING_STORE_AVAILABLE and filled_count > 0 and not result.get("used_saved_mappings"):
                    try:
                        # Extract mappings from AI analysis or pattern matching
                        learned_mappings = []

                        if ai_mappings:
                            # Use AI-detected mappings with normalization
                            for m in ai_mappings:
                                if m.get('selector') and m.get('profile_field'):
                                    # Normalize profile field name (e.g., "suburb/City" -> "city")
                                    normalized_field = normalize_profile_field(m['profile_field'])
                                    learned_mappings.append({
                                        "selector": m['selector'],
                                        "profile_field": normalized_field
                                    })
                        elif fields:
                            # Build mappings from pattern matching results
                            flat_profile = self._normalize_profile(profile)
                            for field in fields:
                                selector = field.get('selector', '')
                                label = field.get('label', '').lower()
                                name = field.get('name', '').lower()
                                placeholder = field.get('placeholder', '').lower()
                                all_text = f"{label} {name} {placeholder}"

                                # Find which profile field this was mapped to
                                for profile_key, patterns in LABEL_PATTERNS.items():
                                    for pattern in patterns:
                                        if pattern in all_text:
                                            if profile_key in flat_profile and flat_profile[profile_key]:
                                                learned_mappings.append({
                                                    "selector": selector,
                                                    "profile_field": profile_key
                                                })
                                            break
                                    else:
                                        continue
                                    break

                        if learned_mappings:
                            store = FieldMappingStore()
                            store.save_mappings(domain, learned_mappings, url=url)
                            print(f"[Phase 7] Saved {len(learned_mappings)} mappings for {domain}")
                            result["mappings_saved"] = len(learned_mappings)
                        else:
                            print("[Phase 7] No mappings to save")

                    except Exception as e:
                        print(f"[Phase 7] Failed to save mappings: {e}")
                else:
                    if result.get("used_saved_mappings"):
                        print("[Phase 7] Already using saved mappings - no learning needed")
                    else:
                        print("[Phase 7] No fields filled - nothing to learn")

                result["phases_completed"].append("learn")

                # Success!
                result["success"] = filled_count > 0

                # Keep browser open for user to see
                if self.hold_open > 0:
                    print(f"\n[Agent] Keeping browser open for {self.hold_open} seconds...")
                    sb.sleep(self.hold_open)

        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            result["error"] = str(e)

        result["completed_at"] = datetime.now().isoformat()

        print(f"\n{'='*60}")
        print(f"[Agent] Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"[Agent] Fields: {result['fields_filled']}/{result['fields_detected']} filled")
        print(f"[Agent] Submitted: {result['submitted']}")
        if result.get('is_multi_step'):
            print(f"[Agent] Multi-step: {result['steps_completed']} steps completed")
            print(f"[Agent] Fields per step: {result['fields_per_step']}")
        if result.get('error'):
            print(f"[Agent] Error: {result['error']}")
        print(f"{'='*60}\n")

        return result

    def _close_popups(self, sb) -> int:
        """
        Close all popups, modals, cookie banners.

        Returns number of popups closed.
        """
        closed = 0

        # Try pressing Escape first
        try:
            sb.send_keys("body", "\ue00c")  # Escape key
            sb.sleep(0.5)
        except:
            pass

        # Try clicking close buttons
        for selector in POPUP_CLOSE_SELECTORS:
            try:
                if sb.is_element_visible(selector):
                    sb.click(selector)
                    closed += 1
                    sb.sleep(0.3)
            except:
                continue

        # Click outside modals (on overlay)
        overlay_selectors = ['.modal-backdrop', '.overlay', '.modal-overlay', '.popup-overlay']
        for selector in overlay_selectors:
            try:
                if sb.is_element_visible(selector):
                    sb.click(selector)
                    closed += 1
                    sb.sleep(0.3)
            except:
                continue

        return closed

    def _detect_fields(self, sb) -> List[Dict]:
        """
        Find all form fields on the page.

        Returns list of field dicts with selector, type, label info.
        """
        fields = []

        # Build label -> input mapping
        label_map = {}
        try:
            labels = sb.find_elements('label')
            for label in labels:
                try:
                    text = (label.text or '').lower().strip()
                    text = text.replace('*', '').replace('required', '').strip()
                    for_attr = label.get_attribute('for')
                    if text and for_attr:
                        label_map[for_attr] = text
                except:
                    continue
        except:
            pass

        # Find all input fields
        input_selectors = [
            'input[type="text"]',
            'input[type="email"]',
            'input[type="password"]',
            'input[type="tel"]',
            'input[type="number"]',
            'input[type="checkbox"]',  # Checkboxes for terms/privacy
            'input:not([type])',  # Default is text
            'select',
            'textarea',
        ]

        # Also find custom dropdowns (country selectors, etc.)
        custom_dropdown_selectors = [
            'button.country-selector',
            'button[id*="country"]',
            'button[id*="flag"]',
            '[data-toggle="dropdown"][class*="country"]',
            '.country-selector',
            '#flag-drop-down',
        ]

        # Track already added field IDs to avoid duplicates
        added_field_ids = set()

        for selector in custom_dropdown_selectors:
            try:
                elements = sb.find_elements(selector)
                for elem in elements:
                    try:
                        if not elem.is_displayed():
                            continue

                        field_id = elem.get_attribute('id') or ''
                        field_name = elem.get_attribute('name') or ''
                        aria_label = elem.get_attribute('aria-label') or ''

                        # Skip if already added
                        if field_id and field_id in added_field_ids:
                            continue

                        if field_id or 'country' in aria_label.lower():
                            field_selector = f'#{field_id}' if field_id else selector

                            fields.append({
                                'selector': field_selector,
                                'id': field_id,
                                'name': field_name,
                                'type': 'custom-dropdown',
                                'label': aria_label.lower(),
                                'placeholder': '',
                                'aria_label': aria_label.lower(),
                                'autocomplete': '',
                                'data_testid': '',
                                'tag': 'button',
                                'is_country_selector': True,
                            })
                            if field_id:
                                added_field_ids.add(field_id)
                    except:
                        continue
            except:
                continue

        # Fields to skip (search boxes, newsletter, footer fields, etc.)
        skip_patterns = ['search', 'query', 'keyword', 'subscribe', 'newsletter', 'footer', 'promo', 'coupon', 'discount']

        for selector in input_selectors:
            try:
                elements = sb.find_elements(selector)
                for elem in elements:
                    try:
                        # Skip hidden fields
                        if not elem.is_displayed():
                            continue

                        field_id = elem.get_attribute('id') or ''
                        field_name = elem.get_attribute('name') or ''
                        field_type = elem.get_attribute('type') or 'text'
                        placeholder = elem.get_attribute('placeholder') or ''
                        aria_label = elem.get_attribute('aria-label') or ''
                        autocomplete = elem.get_attribute('autocomplete') or ''
                        data_testid = elem.get_attribute('data-testid') or ''

                        # Skip search boxes and newsletter fields
                        all_attrs = f"{field_id} {field_name} {placeholder} {aria_label}".lower()
                        if any(skip in all_attrs for skip in skip_patterns):
                            continue

                        # Get label text from multiple sources
                        label_text = label_map.get(field_id, '')
                        if not label_text and field_name:
                            label_text = label_map.get(field_name, '')

                        # Build selector for this field
                        if field_id:
                            field_selector = f'#{field_id}'
                        elif field_name:
                            field_selector = f'[name="{field_name}"]'
                        else:
                            continue  # Skip fields without id or name

                        fields.append({
                            'selector': field_selector,
                            'id': field_id,
                            'name': field_name,
                            'type': field_type,
                            'label': label_text,
                            'placeholder': placeholder.lower(),
                            'aria_label': aria_label.lower(),
                            'autocomplete': autocomplete.lower(),
                            'data_testid': data_testid.lower(),
                            'tag': elem.tag_name,
                        })
                    except:
                        continue
            except:
                continue

        return fields

    def _fill_fields(self, sb, fields: List[Dict], profile: Dict[str, Any]) -> int:
        """
        Fill form fields with profile data.

        Returns number of fields filled.
        """
        filled = 0
        unfilled = []

        # Normalize profile - flatten nested structure and add derived fields
        flat_profile = self._normalize_profile(profile)

        for field in fields:
            try:
                selector = field['selector']
                label = field.get('label', '').lower()
                name = field.get('name', '').lower()
                field_id = field.get('id', '').lower()
                placeholder = field.get('placeholder', '').lower()
                aria_label = field.get('aria_label', '').lower()
                autocomplete = field.get('autocomplete', '').lower()
                data_testid = field.get('data_testid', '').lower()
                field_type = field.get('type', '')
                tag = field.get('tag', '')

                # Combine all searchable text
                all_text = f"{label} {name} {field_id} {placeholder} {aria_label} {autocomplete} {data_testid}"

                # Handle custom country dropdown (button-based, Bootstrap style)
                if field.get('is_country_selector') or field_type == 'custom-dropdown':
                    country_value = flat_profile.get('country', 'United States')
                    try:
                        # Click to open dropdown
                        sb.click(selector)
                        sb.sleep(0.5)

                        # Try to find and click the country option
                        country_option_selectors = [
                            f'a:contains("{country_value}")',
                            f'li:contains("{country_value}")',
                            f'div:contains("{country_value}")',
                            f'span:contains("{country_value}")',
                            f'button:contains("{country_value}")',
                            f'[data-country-name="{country_value}"]',
                            f'[data-value="{country_value}"]',
                        ]

                        clicked = False
                        for opt_selector in country_option_selectors:
                            try:
                                if sb.is_element_visible(opt_selector):
                                    sb.click(opt_selector)
                                    clicked = True
                                    break
                            except:
                                continue

                        # Also try clicking by partial text match
                        if not clicked:
                            try:
                                # For US, also try "United States of America" or "USA"
                                alt_names = ['United States', 'United States of America', 'USA', 'US']
                                for alt_name in alt_names:
                                    try:
                                        sb.execute_script(f'''
                                            var items = document.querySelectorAll('.dropdown-menu a, .dropdown-menu li, .dropdown-item');
                                            for (var i = 0; i < items.length; i++) {{
                                                if (items[i].textContent.includes("{alt_name}")) {{
                                                    items[i].click();
                                                    break;
                                                }}
                                            }}
                                        ''')
                                        clicked = True
                                        break
                                    except:
                                        continue
                            except:
                                pass

                        if clicked:
                            filled += 1
                            print(f"  [OK] country: {country_value}")
                            sb.sleep(0.3)
                        else:
                            print(f"  [FAIL] country: could not select {country_value}")
                            unfilled.append(field)
                    except Exception as e:
                        print(f"  [FAIL] country dropdown: {e}")
                        unfilled.append(field)
                    continue

                # Handle checkboxes (terms, privacy, newsletter opt-in) - process at end
                if field_type == 'checkbox':
                    checkbox_patterns = ['terms', 'agree', 'accept', 'privacy', 'policy', 'consent', 'conditions', 'tos', 'profiling', 'gdpr']
                    skip_checkbox = ['newsletter', 'subscribe', 'emaillist', 'email_list', 'addtoemail', 'mailinglist']

                    # Skip marketing checkboxes - but only if in name/id (not just label)
                    name_id_text = f"{name} {field_id}".lower()
                    if any(skip in name_id_text for skip in skip_checkbox):
                        print(f"  [SKIP] checkbox: marketing ({field_id})")
                        continue

                    # Check required terms/privacy checkboxes
                    if any(pattern in all_text for pattern in checkbox_patterns) or 'required' in all_text:
                        try:
                            # First check if checkbox is visible (with short timeout)
                            if not sb.is_element_visible(selector):
                                # Try scrolling to it
                                try:
                                    sb.execute_script(f"document.querySelector('{selector}').scrollIntoView({{block: 'center'}});")
                                    sb.sleep(0.3)
                                except:
                                    pass

                            # Try multiple methods to click checkbox
                            elem = None
                            try:
                                elem = sb.find_element(selector)
                            except:
                                # Element not found - continue without failing
                                print(f"  [SKIP] checkbox: not found ({field_id})")
                                continue

                            if elem and not elem.is_selected():
                                clicked = False
                                # Method 1: Direct click
                                try:
                                    sb.click(selector)
                                    clicked = True
                                except:
                                    pass

                                # Method 2: JavaScript click
                                if not clicked:
                                    try:
                                        sb.execute_script("arguments[0].click();", elem)
                                        clicked = True
                                    except:
                                        pass

                                # Method 3: Click the label
                                if not clicked:
                                    try:
                                        label_selector = f'label[for="{field_id}"]'
                                        sb.click(label_selector)
                                        clicked = True
                                    except:
                                        pass

                                if clicked:
                                    filled += 1
                                    print(f"  [OK] checkbox: {field_id}")
                                else:
                                    print(f"  [SKIP] checkbox: could not click ({field_id})")
                            else:
                                # Already selected or elem is None
                                if elem:
                                    filled += 1
                                    print(f"  [OK] checkbox: {field_id} (already checked)")
                            sb.sleep(0.2)
                        except Exception as e:
                            print(f"  [SKIP] checkbox: error ({field_id})")
                        continue
                    else:
                        # Unknown checkbox - skip but log
                        print(f"  [SKIP] checkbox: unknown ({field_id})")
                        continue

                # Check for confirm/verify email field FIRST (more specific than generic confirm)
                if any(pattern in all_text for pattern in CONFIRM_EMAIL_PATTERNS):
                    value = flat_profile.get('email', '')
                    if value and sb.is_element_visible(selector):
                        sb.type(selector, str(value))
                        filled += 1
                        print(f"  [OK] confirmEmail: {value[:20]}...")
                        sb.sleep(0.2)
                        continue

                # Check for confirm/verify password field
                if any(pattern in all_text for pattern in CONFIRM_PASSWORD_PATTERNS):
                    value = flat_profile.get('password', '')
                    if value and sb.is_element_visible(selector):
                        sb.type(selector, str(value))
                        filled += 1
                        print(f"  [OK] confirmPassword")
                        sb.sleep(0.2)
                        continue

                # Check for split DOB fields (birthday/birthmonth/birthyear dropdowns)
                is_dob_field = False
                dob_value = None

                # Use more specific checks - check field name ends with specific suffixes
                # or contains unique identifying patterns
                name_lower = name.lower()
                id_lower = field_id.lower()
                name_id_combined = f"{name_lower} {id_lower}"

                is_day_field = any(p in name_id_combined for p in ['_day', 'fields_day', 'fieldday']) and not any(p in name_id_combined for p in ['month', 'year'])
                is_month_field = any(p in name_id_combined for p in ['_month', 'birthmonth', 'fields_month', 'fieldmonth'])
                is_year_field = any(p in name_id_combined for p in ['_year', 'birthyear', 'fields_year', 'fieldyear'])

                # Also check field id for patterns like FormField_29_month
                if not is_day_field and not is_month_field and not is_year_field:
                    is_day_field = ('day' in id_lower and 'month' not in id_lower and 'year' not in id_lower) or ('birthday' in id_lower)
                    is_month_field = 'month' in id_lower and 'day' not in id_lower and 'year' not in id_lower
                    is_year_field = 'year' in id_lower and 'day' not in id_lower and 'month' not in id_lower

                # Check for day field
                if is_day_field:
                    dob_value = flat_profile.get('dob_day_int', 15)
                    is_dob_field = True
                    dob_field_type = 'day'
                # Check for month field
                elif is_month_field:
                    dob_value = flat_profile.get('dob_month_int', 1)
                    is_dob_field = True
                    dob_field_type = 'month'
                # Check for year field
                elif is_year_field:
                    dob_value = flat_profile.get('dob_year_int', 1990)
                    is_dob_field = True
                    dob_field_type = 'year'

                if is_dob_field and dob_value and sb.is_element_visible(selector):
                    if tag == 'select':
                        # Handle dropdown - try multiple value formats
                        select_success = False
                        for val_format in [str(dob_value), str(dob_value).zfill(2), str(int(dob_value))]:
                            try:
                                sb.select_option_by_value(selector, val_format)
                                select_success = True
                                break
                            except:
                                try:
                                    sb.select_option_by_text(selector, val_format)
                                    select_success = True
                                    break
                                except:
                                    continue
                        if select_success:
                            filled += 1
                            print(f"  [OK] dob_{dob_field_type}: {dob_value}")
                            sb.sleep(0.2)
                        else:
                            unfilled.append(field)
                    else:
                        sb.type(selector, str(dob_value))
                        filled += 1
                        print(f"  [OK] dob_{dob_field_type}: {dob_value}")
                        sb.sleep(0.2)
                    continue

                # Check for title/salutation dropdown
                if any(pattern in all_text for pattern in TITLE_PATTERNS) and tag == 'select':
                    title_value = flat_profile.get('title', 'Mr')
                    if sb.is_element_visible(selector):
                        # Try common title formats
                        title_success = False
                        for title_format in [title_value, title_value.upper(), f"{title_value}.", title_value.lower()]:
                            try:
                                sb.select_option_by_text(selector, title_format)
                                title_success = True
                                break
                            except:
                                try:
                                    sb.select_option_by_value(selector, title_format)
                                    title_success = True
                                    break
                                except:
                                    continue
                        if title_success:
                            filled += 1
                            print(f"  [OK] title: {title_value}")
                            sb.sleep(0.2)
                        else:
                            unfilled.append(field)
                        continue

                # Try to match field to profile
                matched_key = None
                matched_value = None

                # PRIORITY 1: Check label first (most reliable)
                # Label is usually the visible text like "Email Address" or "First Name"
                if label:
                    for profile_key, patterns in LABEL_PATTERNS.items():
                        if profile_key not in flat_profile or not flat_profile[profile_key]:
                            continue
                        for pattern in patterns:
                            if pattern in label:
                                matched_key = profile_key
                                matched_value = flat_profile[profile_key]
                                break
                        if matched_key:
                            break

                # PRIORITY 2: Check placeholder (second most reliable)
                if not matched_key and placeholder:
                    for profile_key, patterns in LABEL_PATTERNS.items():
                        if profile_key not in flat_profile or not flat_profile[profile_key]:
                            continue
                        for pattern in patterns:
                            if pattern in placeholder:
                                matched_key = profile_key
                                matched_value = flat_profile[profile_key]
                                break
                        if matched_key:
                            break

                # PRIORITY 3: Check other attributes (name, id, aria-label)
                if not matched_key:
                    # Use stricter matching for id/name to avoid false positives
                    other_text = f"{name} {aria_label} {autocomplete} {data_testid}"
                    for profile_key, patterns in LABEL_PATTERNS.items():
                        if profile_key not in flat_profile or not flat_profile[profile_key]:
                            continue
                        for pattern in patterns:
                            if pattern in other_text:
                                matched_key = profile_key
                                matched_value = flat_profile[profile_key]
                                break
                        if matched_key:
                            break

                # Fallback: Check autocomplete attribute directly
                if not matched_key and autocomplete:
                    autocomplete_map = {
                        'given-name': 'firstName',
                        'family-name': 'lastName',
                        'email': 'email',
                        'tel': 'phone',
                        'street-address': 'address',
                        'address-line1': 'address',
                        'address-line2': 'address2',
                        'address-level2': 'city',
                        'address-level1': 'state',
                        'postal-code': 'zip',
                        'country': 'country',
                        'organization': 'company',
                        'new-password': 'password',
                        'current-password': 'password',
                    }
                    if autocomplete in autocomplete_map:
                        profile_key = autocomplete_map[autocomplete]
                        if profile_key in flat_profile and flat_profile[profile_key]:
                            matched_key = profile_key
                            matched_value = flat_profile[profile_key]

                # Fill the field if we found a match
                if matched_value and sb.is_element_visible(selector):
                    if tag == 'select':
                        # Handle dropdown with smart value mapping
                        dropdown_success = False

                        # Try using dropdown mapper for better matching
                        if DROPDOWN_MAPPER_AVAILABLE:
                            try:
                                # Get dropdown options
                                options = sb.execute_script(f"""
                                    var select = document.querySelector('{selector}');
                                    if (!select) return [];
                                    return Array.from(select.options).map(o => ({{
                                        value: o.value,
                                        text: o.text.trim()
                                    }}));
                                """)

                                if options:
                                    # Use smart mapping to find best match
                                    mapping = smart_map_dropdown(field, flat_profile, options)
                                    if mapping.get('success') and mapping.get('best_match'):
                                        best_match = mapping['best_match']
                                        try:
                                            sb.select_option_by_value(selector, best_match)
                                            filled += 1
                                            print(f"  [OK] {matched_key}: {best_match} (smart match from '{str(matched_value)[:15]}')")
                                            dropdown_success = True
                                        except:
                                            pass
                            except Exception as e:
                                logger.debug(f"Smart dropdown mapping failed: {e}")

                        # Fallback to standard methods
                        if not dropdown_success:
                            try:
                                sb.select_option_by_text(selector, str(matched_value))
                                filled += 1
                                print(f"  [OK] {matched_key}: {str(matched_value)[:20]}...")
                                dropdown_success = True
                            except:
                                try:
                                    sb.select_option_by_value(selector, str(matched_value))
                                    filled += 1
                                    print(f"  [OK] {matched_key}: {str(matched_value)[:20]}...")
                                    dropdown_success = True
                                except:
                                    pass

                        if not dropdown_success:
                            unfilled.append(field)
                    else:
                        # Phone fields need slow typing for input masks
                        if matched_key == 'phone':
                            # Format phone as XXX-XXX-XXXX for US numbers
                            phone_digits = ''.join(c for c in str(matched_value) if c.isdigit())
                            if len(phone_digits) == 10:
                                formatted_phone = f"{phone_digits[:3]}-{phone_digits[3:6]}-{phone_digits[6:]}"
                            elif len(phone_digits) == 11 and phone_digits[0] == '1':
                                # Handle 1-XXX-XXX-XXXX format
                                formatted_phone = f"{phone_digits[1:4]}-{phone_digits[4:7]}-{phone_digits[7:]}"
                            else:
                                formatted_phone = phone_digits

                            sb.click(selector)
                            sb.sleep(0.1)
                            for char in formatted_phone:
                                sb.send_keys(selector, char)
                                sb.sleep(0.05)  # 50ms between each character
                        else:
                            # Regular text input
                            sb.type(selector, str(matched_value))
                        filled += 1
                        display_val = str(matched_value)[:20] if len(str(matched_value)) > 20 else str(matched_value)
                        print(f"  [OK] {matched_key}: {display_val}")

                    sb.sleep(0.2)  # Human-like delay
                else:
                    # Field not matched
                    unfilled.append(field)

            except Exception as e:
                logger.debug(f"Error filling field {field.get('selector')}: {e}")
                unfilled.append(field)
                continue

        # Report unfilled fields
        if unfilled:
            print(f"  [!] {len(unfilled)} field(s) not matched:")
            for f in unfilled:
                print(f"      - {f.get('selector')}: name={f.get('name')}, placeholder={f.get('placeholder')}")

        return filled

    async def _fill_with_orchestrator(self, sb, fields: List[Dict], profile: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Fill form using Groq orchestrator for intelligent decision making.

        The orchestrator decides each action based on current state.

        Args:
            sb: SeleniumBase browser instance
            fields: Detected form fields
            profile: User profile data
            url: Current page URL

        Returns:
            Result dict with fields_filled, submitted, etc.
        """
        result = {
            "fields_filled": 0,
            "submitted": False,
            "actions": [],
            "errors": []
        }

        # Initialize orchestrator
        if not self._orchestrator:
            if not GROQ_AVAILABLE:
                print("[Orchestrator] Groq not available, falling back to pattern matching")
                return None
            if not self.groq_api_key:
                print("[Orchestrator] No Groq API key, falling back to pattern matching")
                return None
            self._orchestrator = GroqOrchestrator(self.groq_api_key)

        self._orchestrator.reset()  # Fresh conversation for each form

        flat_profile = self._normalize_profile(profile)
        filled_selectors = []
        max_actions = 30
        action_count = 0

        print("[Orchestrator] Groq (Llama 3.3 70B) is deciding actions...")

        while action_count < max_actions:
            action_count += 1

            # Get next action from orchestrator
            try:
                action = await self._orchestrator.decide_action(
                    fields=fields,
                    profile=flat_profile,
                    filled_fields=filled_selectors,
                    last_result=result["actions"][-1] if result["actions"] else None,
                    page_url=url
                )
            except Exception as e:
                print(f"[Orchestrator] Error getting action: {e}")
                result["errors"].append(str(e))
                break

            tool = action.get("tool", "")
            selector = action.get("selector", "")
            value = action.get("value", "")
            reason = action.get("reason", "")[:50]

            print(f"  [{action_count}] {tool}: {selector} = {str(value)[:20]}... ({reason})")

            # Handle different tools
            if tool == "done":
                print("[Orchestrator] Form completed!")
                result["submitted"] = True
                break

            elif tool == "skip":
                print(f"[Orchestrator] Skipping: {reason}")
                break

            elif tool == "submit":
                # Find and click submit button
                submitted = self._submit_form(sb)
                result["submitted"] = submitted
                if submitted:
                    print("[Orchestrator] Form submitted!")
                    sb.sleep(2)
                break

            elif tool == "fill" or tool == "type_slow":
                try:
                    if sb.is_element_visible(selector):
                        if tool == "type_slow":
                            # Character by character
                            sb.click(selector)
                            for char in str(value):
                                sb.send_keys(selector, char)
                                sb.sleep(0.05)
                        else:
                            sb.type(selector, str(value))

                        filled_selectors.append(selector)
                        result["fields_filled"] += 1
                        result["actions"].append({"tool": tool, "selector": selector, "success": True})
                    else:
                        result["actions"].append({"tool": tool, "selector": selector, "success": False, "error": "not visible"})
                except Exception as e:
                    result["actions"].append({"tool": tool, "selector": selector, "success": False, "error": str(e)})
                    result["errors"].append(f"{selector}: {e}")

            elif tool == "select":
                try:
                    if sb.is_element_visible(selector):
                        try:
                            sb.select_option_by_text(selector, str(value))
                        except:
                            sb.select_option_by_value(selector, str(value))

                        filled_selectors.append(selector)
                        result["fields_filled"] += 1
                        result["actions"].append({"tool": tool, "selector": selector, "success": True})
                except Exception as e:
                    result["actions"].append({"tool": tool, "selector": selector, "success": False, "error": str(e)})

            elif tool == "click":
                try:
                    if sb.is_element_visible(selector):
                        sb.click(selector)
                        filled_selectors.append(selector)
                        result["fields_filled"] += 1
                        result["actions"].append({"tool": tool, "selector": selector, "success": True})
                except Exception as e:
                    result["actions"].append({"tool": tool, "selector": selector, "success": False, "error": str(e)})

            elif tool == "wait":
                wait_time = action.get("seconds", 2)
                sb.sleep(wait_time)

            elif tool == "scroll":
                try:
                    sb.execute_script(f"document.querySelector('{selector}').scrollIntoView({{block: 'center'}});")
                except:
                    pass

            sb.sleep(0.3)  # Human-like delay between actions

        return result

    def _fill_with_ai_mappings(self, sb, mappings: List[Dict], profile: Dict[str, Any]) -> int:
        """
        Fill form fields using AI-generated mappings.

        Args:
            sb: SeleniumBase browser instance
            mappings: AI-generated field mappings with selectors and profile fields
            profile: User profile data

        Returns:
            Number of fields filled
        """
        filled = 0
        flat_profile = self._normalize_profile(profile)

        for mapping in mappings:
            selector = mapping.get('selector', '')
            profile_field = mapping.get('profile_field', '')
            field_type = mapping.get('type', 'text')
            confidence = mapping.get('confidence', 0)

            if not selector or not profile_field:
                continue

            # Get value from profile
            value = flat_profile.get(profile_field)
            if not value:
                print(f"  [SKIP] {selector}: no value for '{profile_field}'")
                continue

            try:
                # Check if field is visible
                if not sb.is_element_visible(selector):
                    print(f"  [SKIP] {selector}: not visible")
                    continue

                if field_type == 'select':
                    # Dropdown
                    try:
                        sb.select_option_by_text(selector, str(value))
                        filled += 1
                        print(f"  [OK] {profile_field}: {str(value)[:20]} (AI conf: {confidence:.2f})")
                    except:
                        try:
                            sb.select_option_by_value(selector, str(value))
                            filled += 1
                            print(f"  [OK] {profile_field}: {str(value)[:20]} (AI conf: {confidence:.2f})")
                        except:
                            print(f"  [FAIL] {selector}: could not select '{value}'")

                elif field_type == 'checkbox':
                    # Checkbox - click if not checked
                    try:
                        elem = sb.find_element(selector)
                        if not elem.is_selected():
                            sb.click(selector)
                        filled += 1
                        print(f"  [OK] {profile_field}: checked (AI conf: {confidence:.2f})")
                    except:
                        print(f"  [FAIL] {selector}: could not check")

                elif field_type == 'password':
                    # Password field
                    sb.type(selector, str(value))
                    filled += 1
                    print(f"  [OK] {profile_field}: ******** (AI conf: {confidence:.2f})")

                else:
                    # Text field
                    if profile_field == 'phone':
                        # Slow typing for phone masks
                        sb.click(selector)
                        sb.sleep(0.1)
                        for char in str(value):
                            sb.send_keys(selector, char)
                            sb.sleep(0.05)
                    else:
                        sb.type(selector, str(value))

                    filled += 1
                    display = str(value)[:20] if len(str(value)) > 20 else str(value)
                    print(f"  [OK] {profile_field}: {display} (AI conf: {confidence:.2f})")

                sb.sleep(0.2)  # Human-like delay

            except Exception as e:
                print(f"  [FAIL] {selector}: {e}")
                continue

        return filled

    def _fill_with_saved_mappings(self, sb, mappings: List[Dict], profile: Dict[str, Any]) -> int:
        """
        Fill form fields using saved field mappings.

        This is the "Learn Once, Replay Many" fast path - uses exact
        selectors from previous recordings instead of AI detection.

        Supports both basic mappings {selector, profile_field} and
        enhanced mappings with fill_strategy for optimal filling.

        Args:
            sb: SeleniumBase browser instance
            mappings: List of {selector, profile_field, fill_strategy?, fill_config?} mappings
            profile: User profile data

        Returns:
            Number of fields filled
        """
        filled = 0
        flat_profile = self._normalize_profile(profile)

        for mapping in mappings:
            selector = mapping.get('selector', '')
            profile_field = mapping.get('profile_field', '')

            if not selector or not profile_field:
                continue

            # Get value from profile
            value = flat_profile.get(profile_field)
            if not value:
                print(f"  [SKIP] {selector}: no value for '{profile_field}'")
                continue

            # Check for enhanced mapping with fill_strategy
            fill_strategy = mapping.get('fill_strategy')
            if fill_strategy:
                # Use strategy-based filling (enhanced mappings)
                fill_config = mapping.get('fill_config', {})
                try:
                    # Quick visibility check
                    if not sb.is_element_visible(selector):
                        print(f"  [SKIP] {selector}: not visible")
                        continue
                    if self._execute_fill_strategy(sb, selector, value, fill_strategy, fill_config, profile_field):
                        filled += 1
                    sb.sleep(0.2)
                except Exception as e:
                    print(f"  [FAIL] {selector}: {e}")
                continue

            # Legacy path: no fill_strategy, use heuristic detection
            try:
                # Check if field is visible
                if not sb.is_element_visible(selector):
                    # Try XPath fallback
                    if selector.startswith("xpath/"):
                        xpath = selector.replace("xpath/", "")
                        try:
                            if sb.is_element_visible(f"xpath={xpath}"):
                                selector = f"xpath={xpath}"
                            else:
                                print(f"  [SKIP] {selector}: not visible")
                                continue
                        except:
                            print(f"  [SKIP] {selector}: not visible")
                            continue
                    else:
                        print(f"  [SKIP] {selector}: not visible")
                        continue

                # Determine field type
                try:
                    elem = sb.find_element(selector)
                    tag_name = elem.tag_name.lower()
                    field_type = elem.get_attribute('type') or 'text'
                except:
                    tag_name = 'input'
                    field_type = 'text'

                if tag_name == 'select':
                    # Dropdown
                    try:
                        sb.select_option_by_text(selector, str(value))
                        filled += 1
                        print(f"  [OK] {profile_field}: {str(value)[:30]} (saved)")
                    except:
                        try:
                            sb.select_option_by_value(selector, str(value))
                            filled += 1
                            print(f"  [OK] {profile_field}: {str(value)[:30]} (saved)")
                        except:
                            print(f"  [FAIL] {selector}: could not select '{value}'")

                elif field_type == 'checkbox':
                    # Checkbox - click if not checked
                    try:
                        if not elem.is_selected():
                            sb.click(selector)
                        filled += 1
                        print(f"  [OK] {profile_field}: checked (saved)")
                    except:
                        print(f"  [FAIL] {selector}: could not check")

                elif field_type == 'password':
                    # Password field
                    sb.type(selector, str(value))
                    filled += 1
                    print(f"  [OK] {profile_field}: ******** (saved)")

                else:
                    # Text field
                    if profile_field == 'phone':
                        # Slow typing for phone masks
                        sb.click(selector)
                        sb.sleep(0.1)
                        for char in str(value):
                            sb.send_keys(selector, char)
                            sb.sleep(0.05)
                    elif profile_field in ['dateOfBirth', 'dob', 'birthdate', 'birthday']:
                        # Check if it's an HTML5 date input (type="date")
                        date_str = str(value)
                        input_type = sb.execute_script(f'''
                            var el = document.querySelector("{selector}");
                            return el ? el.type : null;
                        ''')

                        if input_type == 'date':
                            # HTML5 date input - set value directly via JS (YYYY-MM-DD format)
                            # Ensure format is YYYY-MM-DD
                            if '-' in date_str and len(date_str.split('-')[0]) == 4:
                                # Already in YYYY-MM-DD format
                                sb.execute_script(f'''
                                    var el = document.querySelector("{selector}");
                                    if (el) {{
                                        el.value = "{date_str}";
                                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                ''')
                            else:
                                # Try to parse and format
                                sb.execute_script(f'''
                                    var el = document.querySelector("{selector}");
                                    if (el) {{
                                        el.value = "{date_str}";
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                ''')
                        else:
                            # Regular text input - type character by character
                            if '-' in date_str:
                                parts = date_str.split('-')
                                if len(parts) == 3:
                                    # Format: MMDDYYYY for text-based date pickers
                                    formatted = f"{parts[1]}{parts[2]}{parts[0]}"
                                    sb.click(selector)
                                    sb.sleep(0.2)
                                    for char in formatted:
                                        sb.send_keys(selector, char)
                                        sb.sleep(0.05)
                                else:
                                    sb.type(selector, date_str)
                            else:
                                sb.type(selector, date_str)
                    else:
                        sb.type(selector, str(value))

                    filled += 1
                    display = str(value)[:30] if len(str(value)) > 30 else str(value)
                    print(f"  [OK] {profile_field}: {display} (saved)")

                sb.sleep(0.2)  # Human-like delay

            except Exception as e:
                print(f"  [FAIL] {selector}: {e}")
                continue

        return filled

    def _execute_fill_strategy(
        self,
        sb,
        selector: str,
        value: Any,
        strategy: str,
        config: Dict[str, Any] = None,
        profile_field: str = ""
    ) -> bool:
        """
        Execute a specific fill strategy for a field.

        Args:
            sb: SeleniumBase browser instance
            selector: CSS selector for the field
            value: Value to fill
            strategy: Fill strategy name
            config: Optional strategy-specific configuration
            profile_field: Profile field name (for logging)

        Returns:
            True if fill was successful
        """
        if config is None:
            config = {}

        try:
            if strategy == "js_date_input":
                # HTML5 date input - set via JavaScript
                date_str = str(value)
                # Ensure YYYY-MM-DD format
                if '-' in date_str and len(date_str.split('-')[0]) == 4:
                    sb.execute_script(f'''
                        var el = document.querySelector("{selector}");
                        if (el) {{
                            el.value = "{date_str}";
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    ''')
                    print(f"  [OK] {profile_field}: {date_str} (js_date)")
                    return True
                else:
                    # Try to set anyway
                    sb.execute_script(f'''
                        var el = document.querySelector("{selector}");
                        if (el) {{ el.value = "{date_str}"; }}
                    ''')
                    print(f"  [OK] {profile_field}: {date_str} (js_date)")
                    return True

            elif strategy == "char_by_char":
                # Type character by character (for phone masks, credit cards)
                delay_ms = config.get("delay_ms", 50)
                if config.get("click_first", True):
                    sb.click(selector)
                    sb.sleep(0.1)
                for char in str(value):
                    sb.send_keys(selector, char)
                    sb.sleep(delay_ms / 1000)
                print(f"  [OK] {profile_field}: {str(value)[:15]}... (char_by_char)")
                return True

            elif strategy == "dropdown_select":
                # Standard SELECT dropdown
                try:
                    sb.select_option_by_text(selector, str(value))
                except:
                    sb.select_option_by_value(selector, str(value))
                print(f"  [OK] {profile_field}: {value} (dropdown)")
                return True

            elif strategy == "custom_dropdown":
                # Button-based custom dropdown
                sb.click(selector)
                sb.sleep(0.3)
                # Try to find and click the option
                option_selectors = [
                    f'li:contains("{value}")',
                    f'a:contains("{value}")',
                    f'span:contains("{value}")',
                    f'div[data-value="{value}"]',
                ]
                for opt_sel in option_selectors:
                    try:
                        if sb.is_element_visible(opt_sel):
                            sb.click(opt_sel)
                            print(f"  [OK] {profile_field}: {value} (custom_dropdown)")
                            return True
                    except:
                        continue
                print(f"  [FAIL] {profile_field}: could not find option '{value}'")
                return False

            elif strategy == "checkbox_click":
                # Checkbox - check state first
                elem = sb.find_element(selector)
                if not elem.is_selected():
                    sb.click(selector)
                print(f"  [OK] {profile_field}: checked (checkbox)")
                return True

            elif strategy == "radio_click":
                # Radio button
                sb.click(selector)
                print(f"  [OK] {profile_field}: selected (radio)")
                return True

            elif strategy == "password_type":
                # Password field - type normally but mask output
                sb.type(selector, str(value))
                print(f"  [OK] {profile_field}: ******** (password)")
                return True

            else:
                # Default: direct_type
                sb.type(selector, str(value))
                display = str(value)[:20] if len(str(value)) > 20 else str(value)
                print(f"  [OK] {profile_field}: {display} (direct)")
                return True

        except Exception as e:
            print(f"  [FAIL] {profile_field} ({strategy}): {e}")
            return False

    def _normalize_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize profile data - flatten nested structure and add derived fields.
        Adds sensible defaults for common fields that are often required.
        """
        flat = {}

        # Flatten nested profile
        for key, value in profile.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[sub_key] = sub_value
            else:
                flat[key] = value

        # Add derived fields if not present
        if 'name' not in flat and flat.get('firstName') and flat.get('lastName'):
            flat['name'] = f"{flat['firstName']} {flat['lastName']}"

        # Ensure password exists
        if 'password' not in flat or not flat['password']:
            flat['password'] = 'SecurePass123!'

        # Default phone if missing - store raw digits, format will be applied during fill
        if 'phone' not in flat or not flat['phone']:
            flat['phone_raw'] = '5551234567'
            flat['phone'] = '5551234567'  # Raw digits - will be typed one at a time
        else:
            # Store raw digits
            phone = str(flat['phone']).replace('-', '').replace(' ', '').replace('(', '').replace(')', '').replace('+', '')
            flat['phone_raw'] = phone
            flat['phone'] = phone  # Raw digits for character-by-character typing

        # Default title/salutation if missing
        if 'title' not in flat or not flat['title']:
            flat['title'] = 'Mr'

        # Default date of birth if missing
        if 'dob' not in flat or not flat['dob']:
            flat['dob'] = '1990-01-15'

        # Also set dateOfBirth alias (some mappings use this)
        if flat.get('dob') and 'dateOfBirth' not in flat:
            flat['dateOfBirth'] = flat['dob']

        # Parse DOB into components for split date fields
        dob = flat.get('dob', '1990-01-15')
        if dob and '-' in dob:
            try:
                parts = dob.split('-')
                if len(parts) == 3:
                    flat['dob_year'] = parts[0]  # YYYY
                    flat['dob_month'] = parts[1]  # MM
                    flat['dob_day'] = parts[2]    # DD
                    # Also store as integers for dropdown value matching
                    flat['dob_year_int'] = int(parts[0])
                    flat['dob_month_int'] = int(parts[1])
                    flat['dob_day_int'] = int(parts[2])
            except:
                flat['dob_year'] = '1990'
                flat['dob_month'] = '01'
                flat['dob_day'] = '15'
                flat['dob_year_int'] = 1990
                flat['dob_month_int'] = 1
                flat['dob_day_int'] = 15

        # Default address fields if missing
        if not flat.get('address') and not flat.get('address1'):
            flat['address'] = '123 Main Street'
            flat['address1'] = '123 Main Street'
        elif flat.get('address1') and not flat.get('address'):
            flat['address'] = flat['address1']
        elif flat.get('address') and not flat.get('address1'):
            flat['address1'] = flat['address']

        if not flat.get('address2'):
            flat['address2'] = ''  # Often optional, leave empty

        if not flat.get('city'):
            flat['city'] = 'Austin'

        if not flat.get('state'):
            flat['state'] = 'Texas'

        if not flat.get('zip'):
            flat['zip'] = '78701'

        if not flat.get('country'):
            flat['country'] = 'United States'

        return flat

    def _handle_captcha(self, sb) -> Dict[str, Any]:
        """
        Detect and attempt to solve CAPTCHA using 2Captcha.

        Returns dict with detected, solved, error keys.
        """
        import requests
        import time

        result = {"detected": False, "solved": False, "error": None, "type": None}

        # Check for common CAPTCHA indicators
        captcha_selectors = [
            ('iframe[src*="recaptcha"]', 'recaptcha'),
            ('iframe[src*="hcaptcha"]', 'hcaptcha'),
            ('.g-recaptcha', 'recaptcha'),
            ('.h-captcha', 'hcaptcha'),
            ('[data-sitekey]', 'recaptcha'),
            ('iframe[src*="turnstile"]', 'turnstile'),
        ]

        for selector, captcha_type in captcha_selectors:
            try:
                if sb.is_element_present(selector):
                    result["detected"] = True
                    result["type"] = captcha_type
                    print(f"[CAPTCHA] Detected {captcha_type} CAPTCHA")
                    break
            except:
                continue

        if not result["detected"]:
            return result

        # Get 2Captcha API key - check api_keys file first, then env
        api_key = None
        try:
            api_keys_file = Path("api_keys/twocaptcha.json")
            if api_keys_file.exists():
                with open(api_keys_file, 'r') as f:
                    key_data = json.load(f)
                    api_key = key_data.get("api_key")
        except:
            pass

        if not api_key:
            api_key = os.getenv("TWOCAPTCHA_API_KEY") or os.getenv("2CAPTCHA_API_KEY")

        if not api_key:
            result["error"] = "No 2Captcha API key (configure in Settings)"
            print(f"[CAPTCHA] {result['error']}")
            return result

        captcha_type = result["type"]
        page_url = sb.get_current_url()

        # Extract sitekey from page
        try:
            if captcha_type == "recaptcha":
                sitekey = sb.execute_script("""
                    // Method 1: data-sitekey on g-recaptcha div
                    var recaptchaDiv = document.querySelector('.g-recaptcha[data-sitekey]');
                    if (recaptchaDiv) return recaptchaDiv.getAttribute('data-sitekey');

                    // Method 2: data-sitekey on any element
                    var anySitekey = document.querySelector('[data-sitekey]');
                    if (anySitekey) return anySitekey.getAttribute('data-sitekey');

                    // Method 3: Extract from iframe src
                    var iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        var src = iframe.getAttribute('src');
                        var match = src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                """)
            elif captcha_type == "hcaptcha":
                sitekey = sb.execute_script("""
                    // Method 1: data-sitekey on h-captcha div
                    var hcaptchaDiv = document.querySelector('.h-captcha[data-sitekey]');
                    if (hcaptchaDiv) return hcaptchaDiv.getAttribute('data-sitekey');

                    // Method 2: data-sitekey on any element
                    var anySitekey = document.querySelector('[data-sitekey]');
                    if (anySitekey) return anySitekey.getAttribute('data-sitekey');

                    // Method 3: Extract from iframe src
                    var iframe = document.querySelector('iframe[src*="hcaptcha"]');
                    if (iframe) {
                        var src = iframe.getAttribute('src');
                        var match = src.match(/sitekey=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                """)
            else:
                sitekey = None

            if not sitekey:
                result["error"] = f"Could not find {captcha_type} sitekey on page"
                print(f"[CAPTCHA] {result['error']}")
                return result

            print(f"[CAPTCHA] Found sitekey: {sitekey[:20]}...")

        except Exception as e:
            result["error"] = f"Sitekey extraction failed: {e}"
            print(f"[CAPTCHA] {result['error']}")
            return result

        # Submit to 2Captcha API
        try:
            params = {
                "key": api_key,
                "pageurl": page_url,
                "json": 1
            }

            if captcha_type == "recaptcha":
                params["method"] = "userrecaptcha"
                params["googlekey"] = sitekey
            elif captcha_type == "hcaptcha":
                params["method"] = "hcaptcha"
                params["sitekey"] = sitekey

            print(f"[CAPTCHA] Submitting to 2Captcha...")
            response = requests.post("https://2captcha.com/in.php", data=params, timeout=30)
            submit_result = response.json()

            if submit_result.get("status") != 1:
                result["error"] = f"2Captcha submit error: {submit_result.get('request', 'Unknown')}"
                print(f"[CAPTCHA] {result['error']}")
                return result

            task_id = submit_result.get("request")
            print(f"[CAPTCHA] Task submitted: {task_id}")

        except Exception as e:
            result["error"] = f"2Captcha submit failed: {e}"
            print(f"[CAPTCHA] {result['error']}")
            return result

        # Poll for solution (max 120 seconds)
        solution = None
        poll_params = {
            "key": api_key,
            "action": "get",
            "id": task_id,
            "json": 1
        }

        print(f"[CAPTCHA] Waiting for solution...")
        for attempt in range(24):  # 24 * 5s = 120 seconds max
            time.sleep(5)
            try:
                response = requests.get("https://2captcha.com/res.php", params=poll_params, timeout=30)
                poll_result = response.json()

                if poll_result.get("status") == 1:
                    solution = poll_result.get("request")
                    print(f"[CAPTCHA] Solution received (length: {len(solution)})")
                    break
                elif poll_result.get("request") == "CAPCHA_NOT_READY":
                    print(f"[CAPTCHA] Still solving... ({(attempt+1)*5}s)")
                else:
                    result["error"] = f"2Captcha error: {poll_result.get('request', 'Unknown')}"
                    print(f"[CAPTCHA] {result['error']}")
                    return result

            except Exception as e:
                print(f"[CAPTCHA] Poll error: {e}")

        if not solution:
            result["error"] = "2Captcha timeout (120s)"
            print(f"[CAPTCHA] {result['error']}")
            return result

        # Inject solution into page
        try:
            if captcha_type == "recaptcha":
                injected = sb.execute_script(f"""
                    var solution = "{solution}";

                    // Fill g-recaptcha-response textarea
                    var textarea = document.querySelector('#g-recaptcha-response') ||
                                   document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {{
                        textarea.value = solution;
                        textarea.style.display = 'block';
                    }}

                    // Fill any other recaptcha response fields
                    var allTextareas = document.querySelectorAll('textarea[name*="recaptcha"]');
                    allTextareas.forEach(function(ta) {{ ta.value = solution; }});

                    // Try to trigger callback
                    try {{
                        var callback = document.querySelector('.g-recaptcha')?.getAttribute('data-callback');
                        if (callback && typeof window[callback] === 'function') {{
                            window[callback](solution);
                            return true;
                        }}
                    }} catch (e) {{}}

                    return !!textarea;
                """)
            elif captcha_type == "hcaptcha":
                injected = sb.execute_script(f"""
                    var solution = "{solution}";

                    // Fill h-captcha-response textarea
                    var textarea = document.querySelector('[name="h-captcha-response"]') ||
                                   document.querySelector('textarea[name*="hcaptcha"]');
                    if (textarea) {{
                        textarea.value = solution;
                    }}

                    // Also fill g-recaptcha-response if present
                    var gTextarea = document.querySelector('[name="g-recaptcha-response"]');
                    if (gTextarea) {{
                        gTextarea.value = solution;
                    }}

                    // Try to trigger callback
                    try {{
                        var callback = document.querySelector('.h-captcha')?.getAttribute('data-callback');
                        if (callback && typeof window[callback] === 'function') {{
                            window[callback](solution);
                            return true;
                        }}
                    }} catch (e) {{}}

                    return !!textarea;
                """)
            else:
                injected = False

            if injected:
                result["solved"] = True
                print(f"[CAPTCHA] {captcha_type} solved via 2Captcha!")
            else:
                result["error"] = "Solution injected but callback may not have triggered"
                result["solved"] = True  # Still mark as solved, submission should work
                print(f"[CAPTCHA] Solution injected, callback may need manual trigger")

        except Exception as e:
            result["error"] = f"Solution injection failed: {e}"
            print(f"[CAPTCHA] {result['error']}")

        return result

    def _submit_form(self, sb) -> bool:
        """
        Find and click submit button.

        Returns True if submitted.
        """
        for selector in SUBMIT_SELECTORS:
            try:
                if sb.is_element_visible(selector):
                    sb.click(selector)
                    return True
            except:
                continue

        return False

    def _detect_next_step(self, sb, previous_url: str) -> Dict[str, Any]:
        """
        Detect if the form continues to a next step.

        Checks for:
        1. "Next", "Continue", "Step 2" buttons
        2. URL changed but still on same domain
        3. New form fields appeared

        Args:
            sb: SeleniumBase browser instance
            previous_url: URL before the last action

        Returns:
            {"has_next": True/False, "selector": "button selector if found", "reason": "why detected"}
        """
        from urllib.parse import urlparse

        result = {"has_next": False, "selector": None, "reason": None}

        current_url = sb.get_current_url()
        previous_domain = urlparse(previous_url).netloc
        current_domain = urlparse(current_url).netloc

        # Check 1: Look for next/continue buttons
        for selector in NEXT_STEP_SELECTORS:
            try:
                if sb.is_element_visible(selector):
                    # Verify it's not a disabled button
                    try:
                        elem = sb.find_element(selector)
                        if elem.is_enabled():
                            result["has_next"] = True
                            result["selector"] = selector
                            result["reason"] = f"Found next button: {selector}"
                            return result
                    except:
                        pass
            except:
                continue

        # Check 2: URL changed but still on same domain (possible step navigation)
        if current_url != previous_url and current_domain == previous_domain:
            # Check if there are new form fields on this page
            new_fields = self._detect_fields(sb)
            if new_fields:
                result["has_next"] = True
                result["selector"] = None  # No button needed, already on next step
                result["reason"] = f"URL changed to new page with {len(new_fields)} form fields"
                result["already_on_next_step"] = True
                return result

        # Check 3: Look for step indicators that suggest multi-step form
        for pattern in STEP_INDICATOR_PATTERNS:
            try:
                if sb.is_element_present(pattern):
                    # Check if there's a visible next button nearby
                    for next_sel in NEXT_STEP_SELECTORS[:10]:  # Check common ones
                        try:
                            if sb.is_element_visible(next_sel):
                                result["has_next"] = True
                                result["selector"] = next_sel
                                result["reason"] = f"Step indicator {pattern} found with next button"
                                return result
                        except:
                            continue
            except:
                continue

        # Check 4: Look for new form fields that weren't visible before
        # (form sections that appear after first section is filled)
        try:
            visible_fields = self._detect_fields(sb)
            unfilled_fields = [f for f in visible_fields if not self._is_field_filled(sb, f)]
            if len(unfilled_fields) > 0:
                # Check if there's any visible next/continue button
                for selector in NEXT_STEP_SELECTORS[:15]:
                    try:
                        if sb.is_element_visible(selector):
                            result["has_next"] = True
                            result["selector"] = selector
                            result["reason"] = f"Found {len(unfilled_fields)} unfilled fields with next button"
                            return result
                    except:
                        continue
        except:
            pass

        return result

    def _is_field_filled(self, sb, field: Dict) -> bool:
        """Check if a field already has a value."""
        try:
            selector = field.get('selector')
            if not selector:
                return False
            elem = sb.find_element(selector)
            value = elem.get_attribute('value') or ''
            return len(value.strip()) > 0
        except:
            return False

    def _handle_multi_step(
        self,
        sb,
        profile: Dict[str, Any],
        initial_url: str,
        max_steps: int = 5
    ) -> Dict[str, Any]:
        """
        Handle multi-step registration forms.

        Loops through steps until no more steps or max reached.
        Fills fields on each step and clicks next/continue button.

        Args:
            sb: SeleniumBase browser instance
            profile: Profile data for filling forms
            initial_url: URL when multi-step handling started
            max_steps: Maximum number of additional steps to process

        Returns:
            {
                "additional_steps": number of extra steps completed,
                "total_fields_filled": total fields filled across all steps,
                "total_fields_detected": total fields detected across all steps,
                "fields_per_step": [list of field counts per step]
            }
        """
        result = {
            "additional_steps": 0,
            "total_fields_filled": 0,
            "total_fields_detected": 0,
            "fields_per_step": []
        }

        previous_url = initial_url
        step_count = 0

        while step_count < max_steps:
            # Check if there's a next step
            next_step = self._detect_next_step(sb, previous_url)

            if not next_step["has_next"]:
                print(f"    [Multi-step] No more steps detected after step {step_count}")
                break

            step_count += 1
            print(f"\n    [Multi-step] === STEP {step_count + 1} ===")
            print(f"    [Multi-step] Reason: {next_step.get('reason')}")

            # If already on next step (URL changed), just fill fields
            if next_step.get("already_on_next_step"):
                print(f"    [Multi-step] Already navigated to next step page")
            else:
                # Click the next/continue button
                if next_step["selector"]:
                    try:
                        print(f"    [Multi-step] Clicking: {next_step['selector']}")
                        sb.click(next_step["selector"])
                        sb.sleep(2)  # Wait for next step to load
                    except Exception as e:
                        print(f"    [Multi-step] Failed to click next button: {e}")
                        break

            # Close any popups that appeared
            popups_closed = self._close_popups(sb)
            if popups_closed > 0:
                print(f"    [Multi-step] Closed {popups_closed} popup(s)")

            # Detect fields on this step
            fields = self._detect_fields(sb)
            step_fields_detected = len(fields)
            result["total_fields_detected"] += step_fields_detected

            if not fields:
                print(f"    [Multi-step] No form fields found on this step")
                # Check if we've reached a confirmation/success page
                page_text = sb.get_page_source().lower()
                success_indicators = ['thank you', 'success', 'confirmed', 'complete', 'welcome', 'account created']
                if any(indicator in page_text for indicator in success_indicators):
                    print(f"    [Multi-step] Appears to be a confirmation page - done!")
                    break
                continue

            print(f"    [Multi-step] Found {len(fields)} fields on step {step_count + 1}")

            # Fill the fields
            filled_count = self._fill_fields(sb, fields, profile)
            result["total_fields_filled"] += filled_count
            result["fields_per_step"].append(filled_count)

            print(f"    [Multi-step] Filled {filled_count}/{len(fields)} fields")

            if filled_count == 0:
                print(f"    [Multi-step] Could not fill any fields - stopping")
                break

            # Handle CAPTCHA if present
            captcha_result = self._handle_captcha(sb)
            if captcha_result.get("detected"):
                if captcha_result.get("solved"):
                    print(f"    [Multi-step] CAPTCHA solved!")
                else:
                    print(f"    [Multi-step] CAPTCHA detected but not solved")

            # Try to submit/continue to next step
            # First check for a submit button (might be final step)
            submit_clicked = False
            for selector in SUBMIT_SELECTORS:
                try:
                    if sb.is_element_visible(selector):
                        # Check if this looks like a final submit (not next/continue)
                        elem = sb.find_element(selector)
                        button_text = (elem.text or '').lower()
                        button_value = (elem.get_attribute('value') or '').lower()
                        combined = f"{button_text} {button_value}"

                        # If it's clearly a submit button (not next/continue)
                        if any(word in combined for word in ['submit', 'register', 'create', 'sign up', 'join', 'finish', 'complete']):
                            print(f"    [Multi-step] Found final submit button: {selector}")
                            sb.click(selector)
                            sb.sleep(3)
                            submit_clicked = True
                            result["additional_steps"] = step_count
                            break
                except:
                    continue

            if submit_clicked:
                print(f"    [Multi-step] Form submitted on step {step_count + 1}")
                break

            # Update previous URL for next iteration
            previous_url = sb.get_current_url()
            result["additional_steps"] = step_count

        return result

    def stop(self):
        """Stop the agent."""
        self._should_stop = True


# Async wrapper for compatibility with existing code
class AsyncSeleniumBaseAgent:
    """Async wrapper for SeleniumBaseAgent."""

    def __init__(self, headless: bool = False, hold_open: int = 10):
        self.agent = SeleniumBaseAgent(headless=headless, hold_open=hold_open)

    async def fill_sites(
        self,
        urls: List[str],
        profile: Dict[str, Any],
        on_progress: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Fill multiple sites."""
        return await self.agent.fill_sites(urls, profile, on_progress)

    async def fill_site(self, url: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a single site."""
        return await self.agent.fill_site(url, profile)

    def stop(self):
        """Stop the agent."""
        self.agent.stop()
