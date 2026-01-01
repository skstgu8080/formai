"""
Simple Autofill Engine - URL + Profile + Optional Field Mappings.

Navigates to URL and fills fields using:
1. Stored field mappings (if available) - more precise
2. Auto-detection based on field names/attributes - fallback

Like Lightning Autofill but server-side with Playwright.
"""

import asyncio
import logging
import os
import base64
import httpx
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv

# Load .env file
load_dotenv()

logger = logging.getLogger("simple-autofill")

# Optional 2Captcha API key (for clients who want paid solving)
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")
# Ollama host for vision AI
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class FillResult:
    """Result from auto-fill execution."""
    success: bool
    url: str
    fields_filled: int = 0
    error: Optional[str] = None
    submitted: bool = False
    final_url: Optional[str] = None
    missing_fields: Optional[List[Dict[str, str]]] = None  # Fields that need profile values


class SimpleAutofill:
    """
    Simple auto-fill engine - URL + profile + optional stored mappings.

    Usage:
        engine = SimpleAutofill()
        result = await engine.fill("https://example.com/signup", profile_dict)
        # Or with stored mappings:
        result = await engine.fill("https://example.com/signup", profile_dict, stored_fields)
    """

    def __init__(self, headless: bool = True, submit: bool = False):
        self.headless = headless
        self.submit = submit  # Auto-submit form after filling
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def fill(self, url: str, profile: Dict[str, Any],
                   stored_fields: Optional[List[Dict[str, Any]]] = None) -> FillResult:
        """
        Navigate to URL and auto-fill all detected fields.

        Args:
            url: Website URL to fill
            profile: Profile data dict with field values
            stored_fields: Optional pre-analyzed fields with mappings

        Returns:
            FillResult with success status and fields filled count
        """
        try:
            async with async_playwright() as p:
                self.browser = await p.chromium.launch(headless=self.headless)
                self.page = await self.browser.new_page()

                # Monitor network requests - focus on form submissions
                async def log_request(request):
                    if request.method == "POST":
                        url = request.url
                        # Only log important POSTs (form submissions, not analytics)
                        if '/account' in url or '/register' in url or '/customer' in url:
                            print(f"\n  [FORM POST] {url}")
                            try:
                                post_data = request.post_data
                                if post_data:
                                    print(f"  [FORM DATA] {post_data[:500]}...")
                            except:
                                pass

                self.page.on("request", log_request)

                # Navigate
                logger.info(f"Navigating to: {url}")
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)

                # Check for Cloudflare interstitial (blocks before form loads)
                if await self._detect_cloudflare_interstitial():
                    print("  Cloudflare challenge detected - switching to SeleniumBase UC Mode")
                    # Use SeleniumBase for entire fill when Cloudflare detected
                    await self.browser.close()
                    return await self._fill_with_seleniumbase(url, profile, stored_fields)

                # Close cookie popups
                await self._close_popups()

                # Try clicking register tab if we're on a login page
                await self._click_register_tab()

                # Fill using stored mappings if available, otherwise auto-detect
                missing_fields = []
                if stored_fields:
                    filled = await self._fill_with_mappings(profile, stored_fields)
                    logger.info(f"Filled {filled} fields using stored mappings on {url}")
                else:
                    filled, missing_fields = await self._auto_fill(profile)
                    logger.info(f"Filled {filled} fields via auto-detection on {url}")
                    if missing_fields:
                        logger.info(f"Missing profile fields: {[f['name'] for f in missing_fields]}")

                # Keep browser open briefly to let events settle
                await asyncio.sleep(1)

                # Check for CAPTCHA before submit
                captcha_detected = await self._detect_captcha()
                if captcha_detected:
                    if await self._try_auto_solve_captcha():
                        print("  CAPTCHA auto-solved!")
                    elif not self.headless:
                        await self._wait_for_manual_captcha_solve()

                # Submit form if enabled and fields were filled
                submitted = False
                final_url = url
                if self.submit and filled > 0:
                    submitted = await self._submit_form()
                    await asyncio.sleep(2)  # Wait for redirect/response

                    # Check for CAPTCHA after submit attempt
                    captcha_after = await self._detect_captcha()
                    if captcha_after:
                        if await self._try_auto_solve_captcha():
                            print("  CAPTCHA auto-solved!")
                        elif not self.headless:
                            await self._wait_for_manual_captcha_solve()
                        # Wait for CAPTCHA popup to close
                        await asyncio.sleep(2)

                        # Try direct form submission via JavaScript
                        print("  Submitting form directly...")
                        try:
                            await self.page.evaluate('''
                                const form = document.querySelector('form#create_customer, form[action*="account"]');
                                if (form) {
                                    // Remove any submit event listeners that might block
                                    const newForm = form.cloneNode(true);
                                    form.parentNode.replaceChild(newForm, form);
                                    newForm.submit();
                                }
                            ''')
                            submitted = True
                        except Exception as e:
                            print(f"  Direct submit failed: {e}")
                            # Fallback to button click
                            submitted = await self._submit_form()

                        await asyncio.sleep(3)  # Wait for form submission

                    final_url = self.page.url
                    logger.info(f"Form submitted: {submitted}, final URL: {final_url}")

                return FillResult(
                    success=True,
                    url=url,
                    fields_filled=filled,
                    submitted=submitted,
                    final_url=final_url,
                    missing_fields=missing_fields if missing_fields else None
                )

        except Exception as e:
            logger.error(f"Auto-fill failed for {url}: {e}")
            return FillResult(success=False, url=url, error=str(e))

    async def fill_batch(self, urls: list, profile: Dict[str, Any],
                         on_progress=None) -> list:
        """
        Fill multiple URLs with the same profile.

        Args:
            urls: List of URLs to fill
            profile: Profile data
            on_progress: Optional callback(index, total, result)

        Returns:
            List of FillResult objects
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            result = await self.fill(url, profile)
            results.append(result)

            if on_progress:
                on_progress(i + 1, total, result)

            # Small delay between sites
            await asyncio.sleep(0.5)

        return results

    async def _close_popups(self):
        """Close cookie consent and other popups."""
        popup_selectors = [
            '#onetrust-accept-btn-handler',
            '#onetrust-reject-all-handler',
            '.onetrust-close-btn-handler',
            '[aria-label="Accept cookies"]',
            '[aria-label="Accept all"]',
            '.cookie-accept',
            '.cookie-consent-accept',
            '#accept-cookies',
            '.popup-close',
            '.modal-close',
            '[aria-label="Close"]',
        ]

        for selector in popup_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await btn.click(force=True)
                    logger.info(f"Closed popup: {selector}")
                    await asyncio.sleep(0.3)
                    break
            except:
                continue

    async def _detect_captcha(self) -> bool:
        """Detect if page has a CAPTCHA."""
        captcha_selectors = [
            # reCAPTCHA
            'iframe[src*="recaptcha"]',
            'iframe[title*="reCAPTCHA"]',
            '.g-recaptcha',
            '#g-recaptcha',
            '[data-sitekey]',

            # hCaptcha
            'iframe[src*="hcaptcha"]',
            '.h-captcha',
            '#h-captcha',

            # Cloudflare Turnstile
            'iframe[src*="turnstile"]',
            '.cf-turnstile',

            # GeeTest
            'div.geetest_panel',
            'div.geetest_widget',
            'div.geetest_holder',
            'div.geetest_box',
            '[class*="geetest"]',
            'iframe[src*="geetest"]',
            'iframe[src*="gcaptcha"]',

            # Generic CAPTCHA indicators
            '[class*="captcha"]',
            '[id*="captcha"]',
            'img[alt*="CAPTCHA"]',
            'img[alt*="captcha"]',
        ]

        for selector in captcha_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible(timeout=500):
                    logger.info(f"CAPTCHA detected: {selector}")
                    return True
            except:
                continue

        return False

    async def _detect_cloudflare_interstitial(self) -> bool:
        """Detect if we're on a Cloudflare challenge page."""
        try:
            title = await self.page.title()
            if title and ('just a moment' in title.lower() or 'checking your browser' in title.lower()):
                return True
            indicators = ['iframe[src*="challenges.cloudflare"]', '#challenge-running', '#challenge-stage',
                '.cf-challenge', '#cf-please-wait', '#cf-wrapper', '[id*="cf-turnstile"]']
            for sel in indicators:
                try:
                    if await self.page.locator(sel).count() > 0:
                        return True
                except:
                    continue
            page_content = await self.page.content()
            if 'Checking your browser' in page_content or 'cf-browser-verification' in page_content:
                return True
        except Exception as e:
            logger.debug(f'Cloudflare detection error: {e}')
        return False

    async def _wait_for_cloudflare_pass(self, timeout: int = 15) -> bool:
        """Wait for Cloudflare to auto-pass (free UC Mode style)."""
        print('  Waiting for Cloudflare challenge to auto-pass...')
        for i in range(timeout):
            await asyncio.sleep(1)
            if not await self._detect_cloudflare_interstitial():
                print(f'  Cloudflare passed after {i+1}s')
                return True
        print(f'  Cloudflare did not auto-pass after {timeout}s')
        return False

    async def _fill_with_seleniumbase(self, url: str, profile: Dict[str, Any],
                                       stored_fields: Optional[List[Dict[str, Any]]] = None) -> FillResult:
        """Fill form using SeleniumBase UC Mode - for Cloudflare-protected sites."""
        try:
            from seleniumbase import SB
            fields_filled = 0
            submitted = False
            final_url = url

            with SB(uc=True, headless=self.headless) as sb:
                sb.uc_open_with_reconnect(url, reconnect_time=4)
                sb.sleep(3)

                if 'just a moment' in sb.get_title().lower():
                    try:
                        sb.uc_gui_handle_cf()
                        sb.sleep(4)
                    except:
                        pass

                if 'just a moment' in sb.get_title().lower():
                    return FillResult(success=False, url=url, error="Could not bypass Cloudflare")

                print("  Cloudflare bypassed! Filling form...")
                sb.sleep(2)

                # Map profile keys to label text patterns
                label_patterns = {
                    'firstName': ['first name'],
                    'lastName': ['last name', 'surname'],
                    'email': ['email'],
                    'password': ['password'],
                    'phone': ['phone', 'mobile'],
                    'address': ['address line 1', 'street'],
                    'city': ['city', 'suburb'],
                    'state': ['state', 'province'],
                    'zip': ['zip', 'postal', 'postcode'],
                }

                # Build label -> input ID mapping
                labels = sb.find_elements('label')
                label_map = {}
                for label in labels:
                    text = (label.text or '').lower().replace('required', '').strip()
                    for_attr = label.get_attribute('for')
                    if text and for_attr:
                        label_map[text] = for_attr

                # Fill fields by matching labels
                for key, value in profile.items():
                    if not value:
                        continue
                    patterns = label_patterns.get(key, [key.lower()])
                    filled = False

                    for pattern in patterns:
                        for label_text, input_id in label_map.items():
                            if pattern in label_text:
                                try:
                                    if sb.is_element_visible(f'#{input_id}'):
                                        sb.type(f'#{input_id}', str(value))
                                        fields_filled += 1
                                        print(f"    Filled: {key}")
                                        filled = True
                                        break
                                except:
                                    pass
                        if filled:
                            break

                if self.submit and fields_filled > 0:
                    for sel in ['button[type="submit"]', 'input[type="submit"]', 'button:contains("Create")', 'button:contains("Register")']:
                        try:
                            if sb.is_element_visible(sel):
                                sb.click(sel)
                                submitted = True
                                sb.sleep(3)
                                print("  Form submitted!")
                                break
                        except:
                            continue

                final_url = sb.get_current_url()

            return FillResult(success=True, url=url, fields_filled=fields_filled, submitted=submitted, final_url=final_url)
        except Exception as e:
            return FillResult(success=False, url=url, error=str(e))

    async def _bypass_cloudflare_with_uc(self, url: str) -> bool:
        """Use SeleniumBase UC Mode to bypass Cloudflare and get cf_clearance cookie."""
        try:
            from seleniumbase import SB
            print('  Using SeleniumBase UC Mode...')
            cf_cookies = None
            
            with SB(uc=True, headless=False) as sb:
                sb.uc_open_with_reconnect(url, reconnect_time=4)
                sb.sleep(3)
                
                # Check if passed
                title = sb.get_title().lower()
                if 'just a moment' in title:
                    try:
                        sb.uc_gui_handle_cf()
                        sb.sleep(4)
                    except:
                        pass
                
                title = sb.get_title().lower()
                if 'just a moment' not in title:
                    print('  Cloudflare bypassed!')
                    cf_cookies = sb.get_cookies()
            
            if cf_cookies:
                # Transfer cookies to Playwright context
                playwright_cookies = []
                for c in cf_cookies:
                    playwright_cookies.append({
                        'name': c['name'],
                        'value': c['value'],
                        'domain': c.get('domain', '.themountain.com'),
                        'path': c.get('path', '/'),
                    })
                await self.page.context.add_cookies(playwright_cookies)
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Check if we're past Cloudflare now
                if not await self._detect_cloudflare_interstitial():
                    return True
            
            return False
        except Exception as e:
            print(f'  UC Mode error: {e}')
            return False

    async def _solve_turnstile_2captcha(self) -> bool:
        """Solve Cloudflare Turnstile via 2Captcha as fallback."""
        if not TWOCAPTCHA_API_KEY:
            print('  No 2Captcha API key - cannot solve Turnstile')
            return False
        try:
            from twocaptcha import TwoCaptcha
            import re as regex
            print('  Solving Turnstile with 2Captcha...')
            page_content = await self.page.content()
            page_url = self.page.url
            sitekey = None
            try:
                el = self.page.locator('.cf-turnstile[data-sitekey], [data-turnstile-sitekey], [data-sitekey]').first
                if await el.count() > 0:
                    sitekey = await el.get_attribute('data-sitekey') or await el.get_attribute('data-turnstile-sitekey')
            except:
                pass
            if not sitekey:
                for pattern in [r'data-sitekey=["' + "'" + r']([0-9a-zA-Z_-]+)["' + "'" + r']', r'sitekey["' + "'" + r']?\s*[:=]\s*["' + "'" + r']([0-9a-zA-Z_-]+)']:
                    match = regex.search(pattern, page_content)
                    if match:
                        sitekey = match.group(1)
                        break
            if not sitekey:
                print('  Could not find Turnstile sitekey')
                return False
            print(f'  Found sitekey: {sitekey[:20]}...')
            solver = TwoCaptcha(TWOCAPTCHA_API_KEY, defaultTimeout=180, pollingInterval=5)
            result = solver.turnstile(sitekey=sitekey, url=page_url)
            token = result.get('code')
            if not token:
                print('  2Captcha returned no token')
                return False
            print(f'  Got token: {token[:30]}...')
            js_code = """
                document.querySelectorAll('[name="cf-turnstile-response"], [name="g-recaptcha-response"]')
                    .forEach(el => { el.value = "%s"; });
                if (window.turnstile) { window.turnstile.getResponse = () => "%s"; }
            """ % (token, token)
            await self.page.evaluate(js_code)
            await asyncio.sleep(2)
            try:
                verify_btn = self.page.locator('button:has-text("Verify"), input[type="submit"]').first
                if await verify_btn.is_visible(timeout=1000):
                    await verify_btn.click()
                    await asyncio.sleep(3)
            except:
                await self.page.reload()
                await asyncio.sleep(3)
            if not await self._detect_cloudflare_interstitial():
                print('  Turnstile solved!')
                return True
            print('  Token injected but still blocked')
            return False
        except Exception as e:
            print(f'  Turnstile error: {e}')
            return False


    async def _try_auto_solve_captcha(self) -> bool:
        """Try to automatically solve CAPTCHA. Returns True if solved."""

        # Try clicking reCAPTCHA/hCaptcha checkbox first (free)
        if await self._try_click_captcha_checkbox():
            return True

        # Use 2Captcha service (paid, most reliable)
        if TWOCAPTCHA_API_KEY:
            if await self._solve_with_2captcha():
                return True

        return False

    async def _try_click_captcha_checkbox(self) -> bool:
        """Try clicking reCAPTCHA/hCaptcha checkbox."""
        # Try reCAPTCHA
        recaptcha_selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[title*="reCAPTCHA"]',
        ]

        for selector in recaptcha_selectors:
            try:
                iframe = self.page.frame_locator(selector)
                checkbox = iframe.locator('.recaptcha-checkbox-border, #recaptcha-anchor')
                if await checkbox.is_visible(timeout=1000):
                    logger.info("Clicking reCAPTCHA checkbox...")
                    await checkbox.click()
                    await asyncio.sleep(3)

                    # Check if solved
                    try:
                        checked = iframe.locator('.recaptcha-checkbox-checked, [aria-checked="true"]')
                        if await checked.is_visible(timeout=2000):
                            logger.info("reCAPTCHA checkbox solved!")
                            return True
                    except:
                        pass
            except Exception as e:
                logger.debug(f"reCAPTCHA auto-click failed: {e}")
                continue

        # Try hCaptcha
        try:
            hcaptcha_frame = self.page.frame_locator('iframe[src*="hcaptcha"]')
            hcaptcha_checkbox = hcaptcha_frame.locator('#checkbox')
            if await hcaptcha_checkbox.is_visible(timeout=1000):
                logger.info("Clicking hCaptcha checkbox...")
                await hcaptcha_checkbox.click()
                await asyncio.sleep(3)
                return True
        except:
            pass

        return False

    async def _solve_hcaptcha_images(self) -> bool:
        """
        Solve hCaptcha image selection puzzles using LLaVA.
        Handles "click on all images with X" type challenges.
        """
        try:
            # Check for hCaptcha iframe
            hcaptcha_iframe = None
            iframe_selectors = ['iframe[src*="hcaptcha"]', 'iframe[title*="hCaptcha"]']

            for iframe_sel in iframe_selectors:
                try:
                    iframe = self.page.frame_locator(iframe_sel)
                    # Check if challenge is visible
                    challenge = iframe.locator('div.challenge-container, div.task-image')
                    if await challenge.first.is_visible(timeout=1000):
                        hcaptcha_iframe = iframe
                        logger.info("hCaptcha challenge iframe found")
                        break
                except:
                    continue

            if not hcaptcha_iframe:
                # Try checking for hCaptcha popup/modal
                try:
                    hcaptcha_popup = self.page.locator('div[class*="hcaptcha"], div.h-captcha-challenge')
                    if not await hcaptcha_popup.first.is_visible(timeout=500):
                        return False
                except:
                    return False

            print("  hCaptcha detected, using LLaVA to solve...")
            await asyncio.sleep(1)  # Wait for images to load

            # Take screenshot of the entire page (hCaptcha is usually in a popup)
            screenshot_bytes = await self.page.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # First, ask LLaVA what the challenge is asking for
            print("  Reading hCaptcha challenge with LLaVA...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Get the challenge prompt
                response = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": "llava",
                        "prompt": """You are solving an hCaptcha image puzzle. Look at the screenshot carefully.

STEP 1: Read the text prompt at the top of the CAPTCHA popup. It says something like "Please click on all images containing a [object]" or "Select all images with [object]".

STEP 2: Count the grid - is it 3x3 (9 images) or 4x4 (16 images)?

STEP 3: Look at each image in the grid and identify which ones contain the requested object.

Number the cells 1-9 for 3x3 grid:
[1][2][3]
[4][5][6]
[7][8][9]

IMPORTANT: Only use numbers 1-9 for a 3x3 grid. Do not use numbers higher than 9.

Respond EXACTLY in this format (nothing else):
TASK: [the object to find, e.g., "bicycle" or "traffic light"]
CELLS: [comma-separated cell numbers, e.g., "1,4,7"]""",
                        "images": [screenshot_b64],
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip()
                    print(f"  LLaVA analysis: {answer}")
                    logger.info(f"hCaptcha LLaVA response: {answer}")

                    # Parse the cells
                    import re
                    cells_match = re.search(r'CELLS:\s*([\d,\s]+)', answer, re.IGNORECASE)
                    if cells_match:
                        cells_str = cells_match.group(1)
                        cells = [int(c.strip()) for c in cells_str.split(',') if c.strip().isdigit()]

                        if cells:
                            print(f"  Clicking cells: {cells}")

                            # Find and click the image cells
                            if hcaptcha_iframe:
                                # Click within iframe
                                images = hcaptcha_iframe.locator('div.task-image, div.image-wrapper, div.challenge-image')
                            else:
                                images = self.page.locator('div.task-image, div.image-wrapper, div[class*="captcha-image"]')

                            image_count = await images.count()
                            print(f"  Found {image_count} image cells")

                            for cell_num in cells:
                                if 1 <= cell_num <= image_count:
                                    try:
                                        await images.nth(cell_num - 1).click()
                                        print(f"  Clicked cell {cell_num}")
                                        await asyncio.sleep(0.3)
                                    except Exception as e:
                                        print(f"  Failed to click cell {cell_num}: {e}")

                            # Click verify/submit button
                            await asyncio.sleep(1)

                            # Try multiple verify button selectors
                            verify_selectors = [
                                'button.button-submit',
                                'div.button-submit',
                                'button:has-text("Verify")',
                                'button:has-text("Submit")',
                                'button:has-text("Check")',
                                'button:has-text("Next")',
                                '[aria-label="Submit"]',
                                '.verify-button',
                                '.submit-button',
                            ]

                            verify_clicked = False
                            for verify_sel in verify_selectors:
                                try:
                                    if hcaptcha_iframe:
                                        verify_btn = hcaptcha_iframe.locator(verify_sel).first
                                    else:
                                        verify_btn = self.page.locator(verify_sel).first

                                    if await verify_btn.is_visible(timeout=500):
                                        await verify_btn.click()
                                        print(f"  Clicked verify button: {verify_sel}")
                                        verify_clicked = True
                                        await asyncio.sleep(2)
                                        break
                                except:
                                    continue

                            if verify_clicked:
                                # Check if CAPTCHA was solved (no more challenge visible)
                                await asyncio.sleep(1)
                                try:
                                    if hcaptcha_iframe:
                                        still_visible = await hcaptcha_iframe.locator('div.challenge-container, div.task-image').first.is_visible(timeout=1000)
                                    else:
                                        still_visible = False
                                    if not still_visible:
                                        print("  hCaptcha solved!")
                                        return True
                                except:
                                    return True  # Assume solved if we can't check

        except Exception as e:
            logger.error(f"hCaptcha solve error: {e}")

        return False

    async def _solve_geetest_icon_captcha(self) -> bool:
        """
        Solve GeeTest icon CAPTCHA using LLaVA vision AI.
        Handles "click on the icon that doesn't follow the pattern" type.
        """
        try:
            # Check for GeeTest CAPTCHA - could be in main page or iframe
            geetest_selectors = [
                'div.geetest_panel',
                'div.geetest_widget',
                'div[class*="geetest"]',
                'div.geetest_panel_box',
                'div.geetest_box',
                'div.geetest_holder',
                # Also check for the text that appears in GeeTest
                'text="Click on the icon"',
                'text="click on the icon"',
                ':has-text("follow the pattern")',
            ]

            geetest_found = False

            # First check main page
            for selector in geetest_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible(timeout=500):
                        geetest_found = True
                        logger.info(f"GeeTest found with selector: {selector}")
                        break
                except Exception as e:
                    continue

            # Check for GeeTest iframe
            if not geetest_found:
                try:
                    iframe_selectors = ['iframe[src*="geetest"]', 'iframe[src*="gcaptcha"]']
                    for iframe_sel in iframe_selectors:
                        iframe = self.page.frame_locator(iframe_sel)
                        try:
                            geetest_box = iframe.locator('div.geetest_box, div.geetest_panel').first
                            if await geetest_box.is_visible(timeout=500):
                                geetest_found = True
                                logger.info("GeeTest found in iframe")
                                break
                        except:
                            continue
                except:
                    pass

            # Last resort: check page content for GeeTest indicators
            if not geetest_found:
                try:
                    page_content = await self.page.content()
                    if 'geetest' in page_content.lower() or 'gcaptcha' in page_content.lower():
                        geetest_found = True
                        logger.info("GeeTest detected in page content")
                except:
                    pass

            if not geetest_found:
                return False

            logger.info("GeeTest CAPTCHA detected, attempting vision AI solve...")
            print("  GeeTest icon CAPTCHA detected, using LLaVA...")

            # Take full screenshot of the CAPTCHA area
            await asyncio.sleep(1)  # Wait for CAPTCHA to fully load

            # Try to find the CAPTCHA image grid
            captcha_container = None
            container_selectors = [
                'div.geetest_item_wrap',
                'div.geetest_panel_box',
                'div.geetest_ques_tips',
                'canvas.geetest_canvas_img',
            ]

            for selector in container_selectors:
                try:
                    container = self.page.locator(selector).first
                    if await container.is_visible(timeout=500):
                        captcha_container = container
                        break
                except:
                    continue

            # Take screenshot
            if captcha_container:
                screenshot_bytes = await captcha_container.screenshot()
            else:
                # Fallback: screenshot the whole page
                screenshot_bytes = await self.page.screenshot()

            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # Ask LLaVA to analyze the pattern
            print("  Analyzing pattern with LLaVA...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": "llava",
                        "prompt": """This is a 5x5 grid CAPTCHA puzzle. Each row has 5 icons of the same type, EXCEPT one icon is different.

Look at each row carefully:
- Row 1 (top): All icons should be the same. Which column (1-5) has a different icon?
- Row 2: All icons should be the same. Which column has a different icon?
- Row 3 (middle): All icons should be the same. Which column has a different icon?
- Row 4: All icons should be the same. Which column has a different icon?
- Row 5 (bottom): All icons should be the same. Which column has a different icon?

Find the ONE cell where an icon doesn't match the others in its row.
The cursor/X overlay is NOT the answer - ignore it.

Answer with ONLY two numbers separated by comma: row,column
Example: 3,4 means row 3, column 4""",
                        "images": [screenshot_b64],
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip()
                    logger.info(f"LLaVA response: {answer}")
                    print(f"  LLaVA identified: {answer}")

                    # Parse the coordinates
                    import re
                    coords_match = re.search(r'(\d+)\s*[,\s]\s*(\d+)', answer)
                    if coords_match:
                        row = int(coords_match.group(1))
                        col = int(coords_match.group(2))

                        # Click on the identified icon
                        # GeeTest grid is typically 5x5, calculate click position
                        grid_items = self.page.locator('div.geetest_item_img, div.geetest_item')
                        item_count = await grid_items.count()

                        if item_count > 0:
                            # Calculate index (0-based)
                            index = (row - 1) * 5 + (col - 1)
                            if 0 <= index < item_count:
                                target_item = grid_items.nth(index)
                                await target_item.click()
                                print(f"  Clicked icon at row {row}, col {col}")
                                await asyncio.sleep(1)

                                # Click Next/Verify button
                                next_btn = self.page.locator('button:has-text("Next"), button.geetest_commit, div.geetest_commit')
                                if await next_btn.is_visible(timeout=1000):
                                    await next_btn.click()
                                    await asyncio.sleep(2)

                                logger.info("GeeTest CAPTCHA solved with LLaVA")
                                return True
                        else:
                            # Fallback: click by coordinates on the container
                            box = await captcha_container.bounding_box() if captcha_container else None
                            if box:
                                cell_width = box['width'] / 5
                                cell_height = box['height'] / 5
                                click_x = box['x'] + (col - 0.5) * cell_width
                                click_y = box['y'] + (row - 0.5) * cell_height
                                await self.page.mouse.click(click_x, click_y)
                                print(f"  Clicked at coordinates ({click_x}, {click_y})")
                                await asyncio.sleep(2)
                                return True

        except Exception as e:
            logger.error(f"GeeTest icon CAPTCHA solve error: {e}")

        return False

    async def _solve_with_vision_ai(self) -> bool:
        """Use Ollama Vision AI to solve image CAPTCHAs."""
        try:
            # Find CAPTCHA image
            captcha_img_selectors = [
                'img[alt*="captcha" i]',
                'img[alt*="CAPTCHA"]',
                'img[src*="captcha"]',
                'img[class*="captcha"]',
                '#captcha-image',
                '.captcha-image',
            ]

            captcha_img = None
            for selector in captcha_img_selectors:
                try:
                    img = self.page.locator(selector).first
                    if await img.is_visible(timeout=500):
                        captcha_img = img
                        break
                except:
                    continue

            if not captcha_img:
                logger.debug("No CAPTCHA image found for Vision AI")
                return False

            # Take screenshot of CAPTCHA
            screenshot_bytes = await captcha_img.screenshot()
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # Send to Ollama Vision
            print("  Using Vision AI to read CAPTCHA...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": "llava",  # or bakllava, llava-llama3
                        "prompt": "Read the text in this CAPTCHA image. Only respond with the exact text/characters shown, nothing else.",
                        "images": [screenshot_b64],
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    captcha_text = result.get("response", "").strip()

                    if captcha_text:
                        logger.info(f"Vision AI read CAPTCHA: {captcha_text}")
                        print(f"  CAPTCHA text detected: {captcha_text}")

                        # Find CAPTCHA input field and fill it
                        captcha_input_selectors = [
                            'input[name*="captcha" i]',
                            'input[id*="captcha" i]',
                            'input[placeholder*="captcha" i]',
                            'input[aria-label*="captcha" i]',
                            '#captcha',
                            '.captcha-input',
                        ]

                        for selector in captcha_input_selectors:
                            try:
                                input_field = self.page.locator(selector).first
                                if await input_field.is_visible(timeout=500):
                                    await input_field.fill(captcha_text)
                                    logger.info(f"Filled CAPTCHA input with: {captcha_text}")
                                    return True
                            except:
                                continue

        except Exception as e:
            logger.debug(f"Vision AI CAPTCHA solving failed: {e}")

        return False

    async def _solve_with_2captcha(self) -> bool:
        """
        Use 2Captcha paid service to solve CAPTCHA.
        Supports: reCAPTCHA v2/v3, hCaptcha, Turnstile, GeeTest, FunCaptcha, and more.
        """
        if not TWOCAPTCHA_API_KEY:
            return False

        try:
            from twocaptcha import TwoCaptcha
            import asyncio

            # Configure solver with longer timeout for hCaptcha (can take up to 3 min)
            solver = TwoCaptcha(TWOCAPTCHA_API_KEY, defaultTimeout=180, pollingInterval=5)
            page_url = self.page.url
            print("  Using 2Captcha service...")

            # Detect CAPTCHA type and get parameters
            captcha_type = None
            site_key = None

            # Check for reCAPTCHA
            try:
                recaptcha_selectors = [
                    '.g-recaptcha[data-sitekey]',
                    '[data-sitekey]:not(.h-captcha)',
                    'div.g-recaptcha',
                ]
                for sel in recaptcha_selectors:
                    try:
                        recaptcha_el = self.page.locator(sel).first
                        if await recaptcha_el.is_visible(timeout=300):
                            site_key = await recaptcha_el.get_attribute('data-sitekey')
                            if site_key:
                                captcha_type = 'recaptcha'
                                print(f"  Detected reCAPTCHA: {site_key[:20]}...")
                                break
                    except:
                        continue

                # Try extracting from iframe src
                if not site_key:
                    iframe = self.page.locator('iframe[src*="recaptcha"]').first
                    if await iframe.is_visible(timeout=300):
                        src = await iframe.get_attribute('src')
                        if src and 'k=' in src:
                            import re
                            match = re.search(r'[?&]k=([a-zA-Z0-9_-]+)', src)
                            if match:
                                site_key = match.group(1)
                                captcha_type = 'recaptcha'
                                print(f"  Detected reCAPTCHA from iframe: {site_key[:20]}...")
            except:
                pass

            # Check for hCaptcha
            if not captcha_type:
                try:
                    # Try multiple selectors for hCaptcha sitekey
                    hcaptcha_selectors = [
                        '[data-sitekey].h-captcha',
                        '.h-captcha[data-sitekey]',
                        '[data-hcaptcha-sitekey]',
                        'div.h-captcha',
                    ]
                    for sel in hcaptcha_selectors:
                        try:
                            hcaptcha_el = self.page.locator(sel).first
                            if await hcaptcha_el.is_visible(timeout=300):
                                site_key = await hcaptcha_el.get_attribute('data-sitekey')
                                if site_key:
                                    captcha_type = 'hcaptcha'
                                    print(f"  Detected hCaptcha: {site_key[:20]}...")
                                    break
                        except:
                            continue

                    # Try extracting from iframe src
                    if not site_key:
                        iframes = self.page.locator('iframe[src*="hcaptcha"]')
                        count = await iframes.count()
                        for i in range(count):
                            try:
                                iframe = iframes.nth(i)
                                src = await iframe.get_attribute('src')
                                if src and 'sitekey=' in src:
                                    import re
                                    match = re.search(r'sitekey=([a-f0-9-]+)', src)
                                    if match:
                                        site_key = match.group(1)
                                        captcha_type = 'hcaptcha'
                                        print(f"  Detected hCaptcha from iframe: {site_key[:20]}...")
                                        break
                            except:
                                continue

                    # Try extracting from page source
                    if not site_key:
                        import re
                        page_content = await self.page.content()
                        # Look for hcaptcha sitekey in various formats
                        patterns = [
                            r'data-sitekey=["\']([a-f0-9-]{36,})["\']',
                            r'sitekey["\']?\s*[:=]\s*["\']([a-f0-9-]{36,})["\']',
                            r'hcaptcha\.render\([^)]*sitekey["\']?\s*:\s*["\']([a-f0-9-]+)["\']',
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, page_content, re.IGNORECASE)
                            if match:
                                site_key = match.group(1)
                                captcha_type = 'hcaptcha'
                                print(f"  Detected hCaptcha from source: {site_key[:20]}...")
                                break
                except:
                    pass

            # Check for Cloudflare Turnstile
            if not captcha_type:
                try:
                    turnstile_el = self.page.locator('.cf-turnstile[data-sitekey], [data-turnstile-sitekey]').first
                    if await turnstile_el.is_visible(timeout=500):
                        site_key = await turnstile_el.get_attribute('data-sitekey') or await turnstile_el.get_attribute('data-turnstile-sitekey')
                        captcha_type = 'turnstile'
                        print(f"  Detected Turnstile: {site_key[:20]}...")
                except:
                    pass

            # Check for GeeTest
            if not captcha_type:
                try:
                    page_content = await self.page.content()
                    if 'geetest' in page_content.lower():
                        # Try to extract gt and challenge from page
                        import re
                        gt_match = re.search(r'gt["\']?\s*[:=]\s*["\']([a-f0-9]{32})["\']', page_content)
                        challenge_match = re.search(r'challenge["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']', page_content)
                        if gt_match:
                            site_key = gt_match.group(1)
                            captcha_type = 'geetest'
                            print(f"  Detected GeeTest: {site_key[:20]}...")
                except:
                    pass

            if not captcha_type or not site_key:
                print("  2Captcha: Could not extract sitekey from page")
                logger.debug("No supported CAPTCHA found for 2Captcha")
                return False

            print(f"  Sending {captcha_type} to 2Captcha (this may take 30-60 seconds)...")

            # Solve based on type (run in thread pool since twocaptcha is synchronous)
            loop = asyncio.get_event_loop()

            def solve_captcha():
                try:
                    if captcha_type == 'recaptcha':
                        result = solver.recaptcha(sitekey=site_key, url=page_url)
                        return result.get('code')
                    elif captcha_type == 'hcaptcha':
                        result = solver.hcaptcha(sitekey=site_key, url=page_url)
                        return result.get('code')
                    elif captcha_type == 'turnstile':
                        result = solver.turnstile(sitekey=site_key, url=page_url)
                        return result.get('code')
                    elif captcha_type == 'geetest':
                        # Need challenge parameter for GeeTest
                        result = solver.geetest(gt=site_key, challenge='', url=page_url)
                        return result
                except Exception as e:
                    logger.error(f"2Captcha solve error: {e}")
                    return None

            token = await loop.run_in_executor(None, solve_captcha)

            if token:
                print(f"  2Captcha solved! Token: {str(token)[:50]}...")
                logger.info("2Captcha solved!")

                # Inject token based on CAPTCHA type
                try:
                    if captcha_type == 'recaptcha':
                        await self.page.evaluate(f'''
                            const response = document.querySelector('#g-recaptcha-response, [name="g-recaptcha-response"]');
                            if (response) {{
                                response.innerHTML = "{token}";
                                response.value = "{token}";
                            }}
                            if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {{
                                const callback = grecaptcha.getResponse.toString().match(/callback\\s*:\\s*(\\w+)/);
                                if (callback && window[callback[1]]) window[callback[1]]("{token}");
                            }}
                        ''')
                    elif captcha_type == 'hcaptcha':
                        await self.page.evaluate(f'''
                            // Set all h-captcha-response textareas
                            document.querySelectorAll('[name="h-captcha-response"], [name="g-recaptcha-response"], textarea[name*="captcha"]').forEach(el => {{
                                el.innerHTML = "{token}";
                                el.value = "{token}";
                            }});

                            // Close the hCaptcha overlay/popup
                            const overlays = document.querySelectorAll('div[style*="position: fixed"], .hcaptcha-challenge, div[class*="overlay"]');
                            overlays.forEach(el => {{
                                if (el.querySelector('iframe[src*="hcaptcha"]')) {{
                                    el.style.display = 'none';
                                    el.remove();
                                }}
                            }});

                            // Remove hCaptcha iframes that show the challenge
                            document.querySelectorAll('iframe[src*="hcaptcha.com/challenge"]').forEach(el => {{
                                el.parentElement?.remove();
                            }});

                            // Find and call the callback
                            const widget = document.querySelector('.h-captcha, [data-hcaptcha-widget-id]');
                            if (widget) {{
                                const callback = widget.getAttribute('data-callback');
                                if (callback && typeof window[callback] === 'function') {{
                                    console.log('Calling hCaptcha callback:', callback);
                                    window[callback]('{token}');
                                }}
                            }}

                            // Try to mark hCaptcha as complete
                            const checkbox = document.querySelector('.h-captcha iframe');
                            if (checkbox) {{
                                checkbox.setAttribute('data-hcaptcha-response', '{token}');
                            }}
                        ''')
                    elif captcha_type == 'turnstile':
                        await self.page.evaluate(f'''
                            const response = document.querySelector('[name="cf-turnstile-response"]');
                            if (response) {{ response.value = "{token}"; }}
                        ''')
                    print("  Token injected successfully!")
                except Exception as e:
                    logger.warning(f"Token injection warning: {e}")

                return True

        except ImportError:
            logger.warning("2captcha-python not installed. Run: pip install 2captcha-python")
        except Exception as e:
            logger.error(f"2Captcha solving failed: {e}")

        return False

    async def _wait_for_manual_captcha_solve(self):
        """Wait for user to manually solve CAPTCHA."""
        import sys

        # First try auto-solving
        print("\n  Attempting to auto-solve CAPTCHA...")
        if await self._try_auto_solve_captcha():
            print("  CAPTCHA auto-solved!")
            return

        # Fall back to manual
        print("\n" + "="*60)
        print("  CAPTCHA requires manual solving")
        print("="*60)
        print("  Please solve the CAPTCHA in the browser")
        print("  Press ENTER when done...")
        print("="*60 + "\n")

        # Wait for user input (blocking)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)

        logger.info("User indicated CAPTCHA solved, continuing...")
        await asyncio.sleep(1)  # Brief pause after solve

    async def _click_register_tab(self):
        """Click register/signup tab if on a login page."""
        register_tab_selectors = [
            'a:has-text("Register")',
            'a:has-text("Sign Up")',
            'a:has-text("Create Account")',
            'button:has-text("Register")',
            'button:has-text("Sign Up")',
            '[data-tab="register"]',
            '[href*="register"]',
            '[href*="signup"]',
            '#register-tab',
            '.register-tab',
            '.signup-tab',
        ]

        for selector in register_tab_selectors:
            try:
                tab = self.page.locator(selector).first
                if await tab.is_visible(timeout=300):
                    await tab.click()
                    await asyncio.sleep(1)
                    logger.info(f"Clicked register tab: {selector}")
                    return True
            except:
                continue
        return False

    async def _check_required_checkboxes(self):
        """Check terms, privacy, age verification checkboxes."""
        checkbox_selectors = [
            # Terms and conditions
            'input[type="checkbox"][name*="term"]',
            'input[type="checkbox"][name*="agree"]',
            'input[type="checkbox"][name*="accept"]',
            'input[type="checkbox"][name*="consent"]',
            'input[type="checkbox"][name*="policy"]',
            'input[type="checkbox"][name*="privacy"]',
            'input[type="checkbox"][name*="tos"]',
            'input[type="checkbox"][id*="term"]',
            'input[type="checkbox"][id*="agree"]',
            'input[type="checkbox"][id*="accept"]',
            'input[type="checkbox"][id*="privacy"]',
            # Age verification
            'input[type="checkbox"][name*="age"]',
            'input[type="checkbox"][id*="age"]',
            # Newsletter opt-out (uncheck)
            # Generic required checkboxes
            'input[type="checkbox"][required]',
            'input[type="checkbox"][aria-required="true"]',
        ]

        checked_count = 0
        for selector in checkbox_selectors:
            try:
                checkboxes = self.page.locator(selector)
                count = await checkboxes.count()
                for i in range(count):
                    cb = checkboxes.nth(i)
                    if await cb.is_visible(timeout=300):
                        is_checked = await cb.is_checked()
                        if not is_checked:
                            await cb.check(force=True)
                            checked_count += 1
                            logger.info(f"Checked checkbox: {selector}")
            except:
                continue

        return checked_count

    async def _submit_form(self) -> bool:
        """Find and click the submit/register button."""

        # First, check any required checkboxes (terms, privacy, etc.)
        await self._check_required_checkboxes()
        await asyncio.sleep(0.5)

        # Comprehensive submit button selectors
        submit_selectors = [
            # Specific register/create account buttons (highest priority)
            'button[type="submit"]:has-text("Create")',
            'button[type="submit"]:has-text("Register")',
            'button[type="submit"]:has-text("Sign Up")',
            'button[type="submit"]:has-text("Join")',
            'button:has-text("Create Account")',
            'button:has-text("Create My Account")',
            'button:has-text("Create an Account")',
            'button:has-text("Register")',
            'button:has-text("Sign Up")',
            'button:has-text("Sign up")',
            'button:has-text("Join Now")',
            'button:has-text("Join")',
            'button:has-text("Get Started")',
            'button:has-text("Continue")',
            'button:has-text("Next")',

            # Input submit buttons
            'input[type="submit"][value*="Create"]',
            'input[type="submit"][value*="Register"]',
            'input[type="submit"][value*="Sign"]',
            'input[type="submit"][value*="Join"]',
            'input[type="submit"][value*="Submit"]',
            'input[type="submit"]',

            # Generic submit buttons
            'button[type="submit"]',

            # Common IDs and classes
            '#create-account-btn',
            '#register-btn',
            '#signup-btn',
            '#submit-btn',
            '#btnRegister',
            '#btnSignup',
            '#btnSubmit',
            '#register-button',
            '#signup-button',
            '#create-account',
            '.btn-register',
            '.btn-signup',
            '.btn-submit',
            '.register-btn',
            '.signup-btn',
            '.submit-btn',
            '.create-account-btn',

            # Data attributes
            '[data-action="register"]',
            '[data-action="signup"]',
            '[data-action="submit"]',
            '[data-testid="register-button"]',
            '[data-testid="signup-button"]',
            '[data-testid="submit-button"]',
            '[data-cy="register"]',
            '[data-cy="signup"]',

            # Shopify specific
            'button[data-login-submit]',
            'button.shopify-challenge__button',

            # Form buttons
            'form button:last-of-type',
            'form input[type="submit"]:last-of-type',

            # Links styled as buttons
            'a.btn:has-text("Create")',
            'a.btn:has-text("Register")',
            'a.btn:has-text("Sign Up")',
            'a.button:has-text("Create")',
            'a.button:has-text("Register")',

            # Fallback - any button with submit-like text
            'button:has-text("Submit")',
        ]

        for selector in submit_selectors:
            try:
                btn = self.page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    # Check if button is enabled
                    is_disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    if is_disabled == "true" or is_disabled == "" or aria_disabled == "true":
                        logger.debug(f"Button disabled: {selector}")
                        continue

                    logger.info(f"Clicking submit button: {selector}")

                    # Get current URL to detect navigation
                    old_url = self.page.url

                    # Try clicking with navigation wait
                    try:
                        async with self.page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
                            await btn.click(force=True)
                        logger.info("Form submitted with navigation")
                        return True
                    except:
                        # No navigation - try clicking again (might be AJAX)
                        try:
                            await btn.click(force=True)
                        except:
                            pass
                        await asyncio.sleep(3)

                        # Check if URL changed
                        new_url = self.page.url
                        if new_url != old_url:
                            logger.info(f"Form submitted, redirected to {new_url}")
                            return True

                        # Check for success indicators on page
                        success_texts = [
                            "thank you",
                            "welcome",
                            "account created",
                            "successfully",
                            "confirm your email",
                            "check your inbox",
                            "verification",
                            "almost done",
                            "one more step",
                        ]

                        page_text = await self.page.inner_text("body")
                        page_lower = page_text.lower()

                        for text in success_texts:
                            if text in page_lower:
                                logger.info(f"Form submitted, found success text: {text}")
                                return True

                        # Check for error indicators (form NOT submitted successfully)
                        error_texts = ["error", "invalid", "required", "please enter", "already exists", "already registered"]
                        has_error = any(err in page_lower for err in error_texts)

                        if not has_error:
                            # No obvious error, assume success
                            logger.info("Form submit clicked (assuming success)")
                            return True
                        else:
                            logger.warning("Form may have validation errors")
                            # Continue to try other buttons
                            continue

            except Exception as e:
                logger.debug(f"Submit selector {selector} failed: {e}")
                continue

        logger.warning("No submit button found")
        return False

    async def _fill_with_mappings(self, profile: Dict[str, Any],
                                   fields: List[Dict[str, Any]]) -> int:
        """Fill fields using pre-analyzed stored mappings."""
        filled = 0

        for field in fields:
            selector = field.get("selector", "")
            profile_key = field.get("profile_key", "")
            transform = field.get("transform", "")
            field_type = field.get("field_type", "text")

            if not selector or not profile_key:
                continue

            # Get value from profile
            value = profile.get(profile_key)
            if value is None or value == "":
                continue

            # Apply transform
            value = self._apply_transform(str(value), transform)

            try:
                element = self.page.locator(selector).first
                if not await element.is_visible(timeout=1000):
                    continue

                if field_type == "select":
                    # Try to select option
                    try:
                        await element.select_option(value=value, timeout=1000)
                        filled += 1
                    except:
                        # Try by label
                        try:
                            await element.select_option(label=value, timeout=1000)
                            filled += 1
                        except:
                            pass
                elif field_type == "checkbox":
                    if value.lower() in ["true", "1", "yes", "on"]:
                        await element.check()
                        filled += 1
                elif field_type == "radio":
                    # Find matching radio button
                    radios = self.page.locator(selector)
                    count = await radios.count()
                    for i in range(count):
                        radio = radios.nth(i)
                        radio_value = await radio.get_attribute("value")
                        if radio_value and value.lower() in radio_value.lower():
                            await radio.check()
                            filled += 1
                            break
                else:
                    # Text input
                    await element.fill(value)
                    await element.dispatch_event("input")
                    await element.dispatch_event("change")
                    filled += 1

            except Exception as e:
                logger.debug(f"Failed to fill {selector}: {e}")
                continue

        return filled

    def _apply_transform(self, value: str, transform: str) -> str:
        """Apply data transformation to a value."""
        if not transform:
            return value

        if transform.startswith("date:"):
            # Date format transform
            format_str = transform[5:]  # e.g., "MM/DD/YYYY"
            try:
                # Assume input is YYYY-MM-DD
                parts = value.split("-")
                if len(parts) == 3:
                    year, month, day = parts
                    if format_str == "MM/DD/YYYY":
                        return f"{month}/{day}/{year}"
                    elif format_str == "DD/MM/YYYY":
                        return f"{day}/{month}/{year}"
                    elif format_str == "YYYY-MM-DD":
                        return value
            except:
                pass

        elif transform.startswith("prefix:"):
            # Add prefix
            prefix = transform[7:]
            if not value.startswith(prefix):
                return prefix + value

        elif transform.startswith("upper"):
            return value.upper()

        elif transform.startswith("lower"):
            return value.lower()

        return value

    async def _auto_fill(self, profile: Dict[str, Any]) -> int:
        """Auto-fill all detected form fields."""

        fill_script = r"""
        (profile) => {
            const FIELD_SELECTOR = 'input:not([type=button]):not([type=image]):not([type=reset]):not([type=submit]):not([type=hidden]),select,textarea';

            // Field name aliases
            const ALIASES = {
                'firstname': 'firstName', 'first_name': 'firstName', 'fname': 'firstName', 'given-name': 'firstName', 'givenname': 'firstName',
                'lastname': 'lastName', 'last_name': 'lastName', 'lname': 'lastName', 'family-name': 'lastName', 'surname': 'lastName', 'familyname': 'lastName',
                'emailaddress': 'email', 'e-mail': 'email', 'mail': 'email', 'useremail': 'email', 'customeremail': 'email',
                'tel': 'phone', 'telephone': 'phone', 'mobile': 'phone', 'cellphone': 'phone', 'phonenumber': 'phone',
                'pass': 'password', 'pwd': 'password', 'userpassword': 'password', 'passwd': 'password',
                'confirmpassword': 'password', 'passwordconfirm': 'password', 'password2': 'password', 'repassword': 'password',
                'passconfirm': 'password', 'confirmpass': 'password', 'passwordconfirmation': 'password', 'verifypassword': 'password',
                'dob': 'birthdate', 'birthday': 'birthdate', 'birth_date': 'birthdate', 'dateofbirth': 'birthdate', 'birthDay': 'birthdate',
                'zipcode': 'zip', 'postal': 'zip', 'postalcode': 'zip', 'postcode': 'zip',
                'region': 'state', 'province': 'state', 'stateprovince': 'state',
                'streetaddress': 'address1', 'address': 'address1', 'street': 'address1', 'addressline1': 'address1',
                'city': 'city', 'town': 'city', 'locality': 'city',
                'country': 'country', 'countrycode': 'country',
                'alias': 'username', 'nickname': 'username', 'displayname': 'username', 'screenname': 'username', 'handle': 'username',
            };

            function getValue(fieldName) {
                if (!fieldName) return null;

                // Handle Shopify-style names: customer[first_name] -> first_name
                let cleanName = fieldName;
                const bracketMatch = fieldName.match(/\[([^\]]+)\]/);
                if (bracketMatch) {
                    cleanName = bracketMatch[1];  // Extract content from brackets
                }

                const key = cleanName.toLowerCase().replace(/[^a-z0-9]/g, '');
                const keyLower = cleanName.toLowerCase();

                // Special handling for password confirmation fields
                if (keyLower.includes('confirm') && keyLower.includes('pass') ||
                    keyLower.includes('verify') && keyLower.includes('pass') ||
                    keyLower.includes('retype') && keyLower.includes('pass') ||
                    keyLower.includes('re-enter') && keyLower.includes('pass') ||
                    key === 'password2' || key === 'confirmpassword' || key === 'passwordconfirm') {
                    return profile.password || null;
                }

                // Direct match
                for (const [k, v] of Object.entries(profile)) {
                    if (k.toLowerCase() === key && v !== null && v !== undefined && v !== '') {
                        return v;
                    }
                }

                // Alias match
                const aliasKey = ALIASES[key];
                if (aliasKey && profile[aliasKey]) {
                    return profile[aliasKey];
                }

                // Partial match for common patterns
                if (keyLower.includes('first') && keyLower.includes('name')) return profile.firstName;
                if (keyLower.includes('last') && keyLower.includes('name')) return profile.lastName;
                if (keyLower.includes('email')) return profile.email;
                if (keyLower.includes('password') || keyLower.includes('pass')) return profile.password;
                if (keyLower.includes('phone') || keyLower.includes('mobile')) return profile.phone;
                if (keyLower.includes('birth') || keyLower.includes('dob')) return profile.birthdate;

                return null;
            }

            function formatDate(value) {
                if (!value || !value.includes('-')) return value;
                const parts = value.split('-');
                if (parts.length !== 3) return value;
                return parts[1] + '/' + parts[2] + '/' + parts[0]; // MM/DD/YYYY
            }

            let filled = 0;
            const missingFields = [];  // Track fields we couldn't fill
            const fields = document.querySelectorAll(FIELD_SELECTOR);

            for (const field of fields) {
                try {
                    if (field.type === 'radio') continue;
                    if (!field.offsetParent) continue;
                    if (field.value && field.value.trim() !== '') continue;

                    const name = field.name || field.id || '';
                    if (!name) continue;

                    let value = getValue(name);
                    if (value === null) {
                        // Track this as a missing field if it looks like a real form field
                        const placeholder = field.placeholder || '';
                        const type = field.type || 'text';
                        // Skip hidden, checkbox without label context, search fields
                        if (type !== 'hidden' && type !== 'search' && !name.toLowerCase().includes('search')) {
                            missingFields.push({
                                name: name,
                                type: type,
                                placeholder: placeholder,
                                label: field.labels?.[0]?.textContent?.trim() || ''
                            });
                        }
                        continue;
                    }

                    // Format birthdate
                    if (name.toLowerCase().includes('birth') || name.toLowerCase() === 'dob') {
                        value = formatDate(value);
                    }

                    if (field.tagName === 'SELECT') {
                        const valUpper = String(value).toUpperCase();
                        for (const opt of field.options) {
                            if (opt.value.toUpperCase().includes(valUpper) || opt.text.toUpperCase().includes(valUpper)) {
                                field.value = opt.value;
                                field.dispatchEvent(new Event('change', {bubbles: true}));
                                filled++;
                                break;
                            }
                        }
                    } else if (field.type === 'checkbox') {
                        if (value === true || value === 'true' || value === '1') {
                            field.checked = true;
                            field.dispatchEvent(new Event('change', {bubbles: true}));
                            filled++;
                        }
                    } else {
                        field.focus();
                        field.value = String(value);
                        field.dispatchEvent(new Event('input', {bubbles: true}));
                        field.dispatchEvent(new Event('change', {bubbles: true}));
                        field.blur();
                        filled++;
                    }
                } catch (e) {}
            }

            // Handle password confirmation fields explicitly
            // These are password fields that contain "confirm", "verify", "retype", etc.
            if (profile.password) {
                const passwordConfirmSelectors = [
                    'input[type="password"][name*="confirm"]',
                    'input[type="password"][name*="Confirm"]',
                    'input[type="password"][name*="verify"]',
                    'input[type="password"][name*="Verify"]',
                    'input[type="password"][name*="retype"]',
                    'input[type="password"][name*="re-enter"]',
                    'input[type="password"][name*="password2"]',
                    'input[type="password"][name*="password_confirm"]',
                    'input[type="password"][id*="confirm"]',
                    'input[type="password"][id*="Confirm"]',
                    'input[type="password"][id*="verify"]',
                    'input[type="password"][id*="retype"]',
                    'input[type="password"][id*="password2"]',
                    'input[type="password"][placeholder*="Confirm"]',
                    'input[type="password"][placeholder*="confirm"]',
                    'input[type="password"][placeholder*="Verify"]',
                    'input[type="password"][placeholder*="verify"]',
                    'input[type="password"][placeholder*="Re-enter"]',
                    'input[type="password"][placeholder*="Retype"]',
                    'input[name="customer[password_confirmation]"]',
                    'input[name="password_confirmation"]',
                    'input[name="confirmPassword"]',
                    'input[name="confirm_password"]',
                    'input[name="passwordConfirmation"]',
                    '#confirmPassword',
                    '#confirm-password',
                    '#password-confirm',
                    '#password2',
                    '#ConfirmPassword',
                ];

                for (const selector of passwordConfirmSelectors) {
                    try {
                        const confirmField = document.querySelector(selector);
                        if (confirmField && confirmField.offsetParent && !confirmField.value) {
                            confirmField.focus();
                            confirmField.value = profile.password;
                            confirmField.dispatchEvent(new Event('input', {bubbles: true}));
                            confirmField.dispatchEvent(new Event('change', {bubbles: true}));
                            confirmField.blur();
                            filled++;
                            break;  // Only fill one confirm field
                        }
                    } catch (e) {}
                }
            }

            // Handle state dropdown with country prefix
            const stateField = document.querySelector('#state, [name="state"]');
            if (stateField && stateField.tagName === 'SELECT' && profile.state && !stateField.value) {
                const stateUpper = profile.state.toUpperCase();
                for (const opt of stateField.options) {
                    if (opt.value.toUpperCase().includes(stateUpper) || opt.text.toUpperCase().includes(stateUpper)) {
                        stateField.value = opt.value;
                        stateField.dispatchEvent(new Event('change', {bubbles: true}));
                        filled++;
                        break;
                    }
                }
            }

            // Handle civility/gender radio
            const sex = profile.sex || profile.gender;
            if (sex) {
                const sexLower = sex.toLowerCase();
                for (const radio of document.querySelectorAll('input[type="radio"]')) {
                    const name = (radio.name || '').toLowerCase();
                    const val = (radio.value || '').toLowerCase();
                    if (name.includes('civil') || name.includes('gender') || name.includes('sex')) {
                        let match = (sexLower === 'male' && (val === 'mr' || val === 'male' || val === 'm')) ||
                                    (sexLower === 'female' && (val === 'ms' || val === 'mrs' || val === 'female' || val === 'f'));
                        if (match) {
                            radio.checked = true;
                            radio.dispatchEvent(new Event('change', {bubbles: true}));
                            filled++;
                            break;
                        }
                    }
                }
            }

            // Filter out password-related fields from missing (we handle those explicitly)
            const filteredMissing = missingFields.filter(f => {
                const nameLower = f.name.toLowerCase();
                return !nameLower.includes('password') && !nameLower.includes('pwd') && !nameLower.includes('pass');
            });

            return { filled: filled, missingFields: filteredMissing };
        }
        """

        try:
            result = await self.page.evaluate(fill_script, profile)
            if isinstance(result, dict):
                return result.get('filled', 0), result.get('missingFields', [])
            return result, []
        except Exception as e:
            logger.error(f"Auto-fill JS failed: {e}")
            return 0, []


# Quick test function
async def test_fill(url: str, profile: dict):
    """Test filling a single URL."""
    engine = SimpleAutofill(headless=False)
    result = await engine.fill(url, profile)
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    # Test with YSL
    profile = {
        "firstName": "Koodos",
        "lastName": "Record",
        "email": "cixoda1684@mucate.com",
        "password": "KprSecure123!",
        "birthdate": "1992-09-15",
        "sex": "MALE",
        "state": "Texas"
    }
    asyncio.run(test_fill("https://www.ysl.com/en-us/signup", profile))
