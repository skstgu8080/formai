"""
CaptchaSolver - Multi-strategy CAPTCHA solving.

Strategy chain:
1. 2Captcha API - For reCAPTCHA v2/v3, hCaptcha (requires API key)
2. Vision AI (Ollama + LLaVA) - For simple text/image CAPTCHAs
3. UC Mode Bypass - For Cloudflare, Turnstile (browser-level)
4. Skip & Queue - Mark for manual solving later

NOTE: This is for educational/testing purposes only.
CAPTCHAs exist to prevent automated access - respect site terms.
"""

import asyncio
import base64
import json
import logging
import os
import re
import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger("captcha-solver")


@dataclass
class CaptchaResult:
    """Result of a CAPTCHA solve attempt."""
    success: bool
    solution: Optional[str] = None
    method: str = "none"
    confidence: float = 0.0
    message: str = ""
    needs_manual: bool = False


class CaptchaSolver:
    """
    Multi-strategy CAPTCHA solver using free methods.

    Supports:
    - Simple text CAPTCHAs (vision AI reads text)
    - Math CAPTCHAs (vision AI + calculation)
    - Image selection hints (basic guidance)
    - Cloudflare/Turnstile bypass (UC mode)
    """

    # CAPTCHA detection patterns
    CAPTCHA_SELECTORS = [
        # reCAPTCHA
        'iframe[src*="recaptcha"]',
        '.g-recaptcha',
        '#recaptcha',
        '[class*="recaptcha"]',
        # hCaptcha
        'iframe[src*="hcaptcha"]',
        '.h-captcha',
        '[class*="hcaptcha"]',
        # Cloudflare Turnstile
        'iframe[src*="turnstile"]',
        '.cf-turnstile',
        '[class*="turnstile"]',
        # Generic CAPTCHA
        'img[src*="captcha"]',
        'img[alt*="captcha"]',
        'input[name*="captcha"]',
        '#captcha',
        '.captcha',
        '[class*="captcha"]',
    ]

    # Text CAPTCHA input patterns
    CAPTCHA_INPUT_SELECTORS = [
        'input[name*="captcha"]',
        'input[id*="captcha"]',
        'input[placeholder*="captcha" i]',
        'input[placeholder*="code" i]',
        'input[placeholder*="verify" i]',
        'input[aria-label*="captcha" i]',
    ]

    # 2Captcha API endpoints
    TWOCAPTCHA_IN_URL = "https://2captcha.com/in.php"
    TWOCAPTCHA_RES_URL = "https://2captcha.com/res.php"

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        vision_model: str = "llava",  # LLaVA for vision tasks
        twocaptcha_timeout: int = 120  # Max seconds to wait for 2Captcha solution
    ):
        self.ollama_host = ollama_host
        self.vision_model = vision_model
        self.timeout = 30.0
        self.twocaptcha_timeout = twocaptcha_timeout
        self.twocaptcha_api_key = os.getenv("TWOCAPTCHA_API_KEY", "")

    async def detect_captcha(self, page) -> Dict[str, Any]:
        """
        Detect if page has a CAPTCHA and identify its type.

        Returns:
            {
                "has_captcha": True/False,
                "type": "recaptcha" | "hcaptcha" | "cloudflare" | "text" | "image" | "unknown",
                "selector": "...",
                "input_selector": "..." (for text CAPTCHAs)
            }
        """
        result = {
            "has_captcha": False,
            "type": "unknown",
            "selector": None,
            "input_selector": None,
            "image_src": None
        }

        try:
            for selector in self.CAPTCHA_SELECTORS:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        result["has_captcha"] = True
                        result["selector"] = selector

                        # Determine type
                        if 'recaptcha' in selector.lower():
                            result["type"] = "recaptcha"
                        elif 'hcaptcha' in selector.lower():
                            result["type"] = "hcaptcha"
                        elif 'turnstile' in selector.lower() or 'cloudflare' in selector.lower():
                            result["type"] = "cloudflare"
                        elif 'img' in selector:
                            result["type"] = "image"
                            # Get image source
                            src = await element.get_attribute('src')
                            result["image_src"] = src
                        else:
                            result["type"] = "text"

                        break
                except:
                    continue

            # Find CAPTCHA input if text type
            if result["has_captcha"] and result["type"] in ("text", "image", "unknown"):
                for input_sel in self.CAPTCHA_INPUT_SELECTORS:
                    try:
                        input_el = await page.query_selector(input_sel)
                        if input_el and await input_el.is_visible():
                            result["input_selector"] = input_sel
                            break
                    except:
                        continue

        except Exception as e:
            logger.warning(f"[CAPTCHA] Detection error: {e}")

        return result

    async def solve(self, page, detection: Dict = None) -> CaptchaResult:
        """
        Attempt to solve detected CAPTCHA.

        Args:
            page: Playwright page object
            detection: Result from detect_captcha() or None to auto-detect

        Returns:
            CaptchaResult with solution or failure reason
        """
        if detection is None:
            detection = await self.detect_captcha(page)

        if not detection.get("has_captcha"):
            return CaptchaResult(
                success=True,
                method="none",
                message="No CAPTCHA detected"
            )

        captcha_type = detection.get("type", "unknown")
        logger.info(f"[CAPTCHA] Attempting to solve {captcha_type} CAPTCHA")

        # Strategy 1: Cloudflare/Turnstile - UC Mode bypass
        if captcha_type == "cloudflare":
            return await self._solve_cloudflare(page, detection)

        # Strategy 2: Text/Image CAPTCHA - Vision AI
        if captcha_type in ("text", "image"):
            return await self._solve_text_captcha(page, detection)

        # Strategy 3: reCAPTCHA/hCaptcha - Use 2Captcha API if available
        if captcha_type in ("recaptcha", "hcaptcha"):
            if self.twocaptcha_api_key:
                return await self._solve_with_2captcha(page, detection)
            else:
                return CaptchaResult(
                    success=False,
                    method="skip",
                    message=f"{captcha_type} requires TWOCAPTCHA_API_KEY environment variable",
                    needs_manual=True
                )

        # Unknown - try vision AI as fallback
        return await self._solve_text_captcha(page, detection)

    async def _solve_cloudflare(self, page, detection: Dict) -> CaptchaResult:
        """
        Handle Cloudflare/Turnstile challenges.

        UC Mode should bypass most of these automatically.
        We just need to wait for it to complete.
        """
        try:
            logger.info("[CAPTCHA] Waiting for Cloudflare challenge to auto-solve...")

            # Wait for the challenge to complete (UC mode handles it)
            for _ in range(10):  # Max 10 seconds
                await asyncio.sleep(1)

                # Check if challenge is gone
                detection = await self.detect_captcha(page)
                if not detection.get("has_captcha"):
                    return CaptchaResult(
                        success=True,
                        method="uc_bypass",
                        message="Cloudflare challenge passed via UC mode",
                        confidence=0.9
                    )

                # Check for success indicators
                page_text = await page.evaluate("document.body.innerText")
                if "checking your browser" not in page_text.lower():
                    return CaptchaResult(
                        success=True,
                        method="uc_bypass",
                        message="Cloudflare challenge appears to have passed",
                        confidence=0.7
                    )

            # Timeout - challenge didn't complete
            return CaptchaResult(
                success=False,
                method="uc_bypass",
                message="Cloudflare challenge did not complete in time",
                needs_manual=True
            )

        except Exception as e:
            return CaptchaResult(
                success=False,
                method="uc_bypass",
                message=f"Cloudflare handling error: {e}",
                needs_manual=True
            )

    async def _solve_with_2captcha(self, page, detection: Dict) -> CaptchaResult:
        """
        Solve reCAPTCHA v2 or hCaptcha using 2Captcha API.

        Flow:
        1. Extract sitekey from page
        2. Submit to 2Captcha API
        3. Poll for solution
        4. Inject solution into page
        """
        captcha_type = detection.get("type", "recaptcha")
        page_url = page.url

        try:
            # Step 1: Extract sitekey
            sitekey = await self._extract_sitekey(page, captcha_type)
            if not sitekey:
                return CaptchaResult(
                    success=False,
                    method="2captcha",
                    message=f"Could not find {captcha_type} sitekey on page",
                    needs_manual=True
                )

            logger.info(f"[CAPTCHA] Found {captcha_type} sitekey: {sitekey[:20]}...")

            # Step 2: Submit to 2Captcha
            task_id = await self._submit_to_2captcha(sitekey, page_url, captcha_type)
            if not task_id:
                return CaptchaResult(
                    success=False,
                    method="2captcha",
                    message="Failed to submit CAPTCHA to 2Captcha API",
                    needs_manual=True
                )

            logger.info(f"[CAPTCHA] 2Captcha task submitted: {task_id}")

            # Step 3: Poll for solution (with timeout)
            solution = await self._poll_2captcha_result(task_id)
            if not solution:
                return CaptchaResult(
                    success=False,
                    method="2captcha",
                    message="2Captcha solve timeout or error",
                    needs_manual=True
                )

            logger.info(f"[CAPTCHA] 2Captcha solution received (length: {len(solution)})")

            # Step 4: Inject solution into page
            injected = await self._inject_captcha_solution(page, solution, captcha_type)
            if not injected:
                return CaptchaResult(
                    success=True,
                    solution=solution,
                    method="2captcha",
                    message="Solution received but injection failed - may need manual callback",
                    confidence=0.7
                )

            return CaptchaResult(
                success=True,
                solution=solution,
                method="2captcha",
                message=f"{captcha_type} solved via 2Captcha API",
                confidence=0.95
            )

        except Exception as e:
            logger.error(f"[CAPTCHA] 2Captcha error: {e}")
            return CaptchaResult(
                success=False,
                method="2captcha",
                message=f"2Captcha error: {e}",
                needs_manual=True
            )

    async def _extract_sitekey(self, page, captcha_type: str) -> Optional[str]:
        """
        Extract the sitekey from reCAPTCHA or hCaptcha element.
        """
        try:
            if captcha_type == "recaptcha":
                # Try data-sitekey attribute on .g-recaptcha div
                sitekey = await page.evaluate("""
                    () => {
                        // Method 1: data-sitekey on g-recaptcha div
                        const recaptchaDiv = document.querySelector('.g-recaptcha[data-sitekey]');
                        if (recaptchaDiv) return recaptchaDiv.getAttribute('data-sitekey');

                        // Method 2: data-sitekey on any element
                        const anySitekey = document.querySelector('[data-sitekey]');
                        if (anySitekey) return anySitekey.getAttribute('data-sitekey');

                        // Method 3: Extract from iframe src
                        const iframe = document.querySelector('iframe[src*="recaptcha"]');
                        if (iframe) {
                            const src = iframe.getAttribute('src');
                            const match = src.match(/[?&]k=([^&]+)/);
                            if (match) return match[1];
                        }

                        // Method 4: Look in grecaptcha object
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.enterprise) {
                            const clients = Object.keys(grecaptcha.enterprise.clients || {});
                            if (clients.length > 0) {
                                const client = grecaptcha.enterprise.clients[clients[0]];
                                if (client && client.sitekey) return client.sitekey;
                            }
                        }

                        return null;
                    }
                """)
                return sitekey

            elif captcha_type == "hcaptcha":
                # Try data-sitekey attribute on .h-captcha div
                sitekey = await page.evaluate("""
                    () => {
                        // Method 1: data-sitekey on h-captcha div
                        const hcaptchaDiv = document.querySelector('.h-captcha[data-sitekey]');
                        if (hcaptchaDiv) return hcaptchaDiv.getAttribute('data-sitekey');

                        // Method 2: data-sitekey on any hcaptcha element
                        const anySitekey = document.querySelector('[data-sitekey]');
                        if (anySitekey) return anySitekey.getAttribute('data-sitekey');

                        // Method 3: Extract from iframe src
                        const iframe = document.querySelector('iframe[src*="hcaptcha"]');
                        if (iframe) {
                            const src = iframe.getAttribute('src');
                            const match = src.match(/sitekey=([^&]+)/);
                            if (match) return match[1];
                        }

                        return null;
                    }
                """)
                return sitekey

        except Exception as e:
            logger.warning(f"[CAPTCHA] Error extracting sitekey: {e}")

        return None

    async def _submit_to_2captcha(self, sitekey: str, page_url: str, captcha_type: str) -> Optional[str]:
        """
        Submit CAPTCHA to 2Captcha API and return task ID.
        """
        try:
            params = {
                "key": self.twocaptcha_api_key,
                "pageurl": page_url,
                "json": 1
            }

            if captcha_type == "recaptcha":
                params["method"] = "userrecaptcha"
                params["googlekey"] = sitekey
            elif captcha_type == "hcaptcha":
                params["method"] = "hcaptcha"
                params["sitekey"] = sitekey

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.TWOCAPTCHA_IN_URL, data=params)
                result = response.json()

                if result.get("status") == 1:
                    return result.get("request")
                else:
                    error = result.get("request", "Unknown error")
                    logger.error(f"[CAPTCHA] 2Captcha submit error: {error}")
                    return None

        except Exception as e:
            logger.error(f"[CAPTCHA] 2Captcha submit failed: {e}")
            return None

    async def _poll_2captcha_result(self, task_id: str) -> Optional[str]:
        """
        Poll 2Captcha for the solution with timeout.
        """
        params = {
            "key": self.twocaptcha_api_key,
            "action": "get",
            "id": task_id,
            "json": 1
        }

        start_time = asyncio.get_event_loop().time()
        poll_interval = 5  # Start with 5 seconds

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.twocaptcha_timeout:
                logger.warning(f"[CAPTCHA] 2Captcha timeout after {elapsed:.0f}s")
                return None

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.TWOCAPTCHA_RES_URL, params=params)
                    result = response.json()

                    if result.get("status") == 1:
                        return result.get("request")
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        logger.debug(f"[CAPTCHA] 2Captcha still solving... ({elapsed:.0f}s)")
                    else:
                        error = result.get("request", "Unknown error")
                        logger.error(f"[CAPTCHA] 2Captcha error: {error}")
                        return None

            except Exception as e:
                logger.warning(f"[CAPTCHA] 2Captcha poll error: {e}")

            # Wait before next poll (increase interval gradually)
            await asyncio.sleep(poll_interval)
            if poll_interval < 10:
                poll_interval += 1

    async def _inject_captcha_solution(self, page, solution: str, captcha_type: str) -> bool:
        """
        Inject the CAPTCHA solution into the page.
        """
        try:
            if captcha_type == "recaptcha":
                # Inject into g-recaptcha-response textarea and trigger callback
                result = await page.evaluate(f"""
                    (solution) => {{
                        // Find and fill the response textarea
                        const textarea = document.querySelector('#g-recaptcha-response') ||
                                          document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (textarea) {{
                            textarea.value = solution;
                            textarea.style.display = 'block';  // Make visible temporarily
                        }}

                        // Also fill any other response fields
                        const allTextareas = document.querySelectorAll('textarea[name*="recaptcha"]');
                        allTextareas.forEach(ta => {{ ta.value = solution; }});

                        // Try to trigger the callback
                        if (typeof grecaptcha !== 'undefined') {{
                            try {{
                                // Try different callback methods
                                if (grecaptcha.enterprise && grecaptcha.enterprise.getResponse) {{
                                    // Enterprise reCAPTCHA
                                    const clients = Object.keys(grecaptcha.enterprise.clients || {{}});
                                    if (clients.length > 0) {{
                                        const widgetId = clients[0];
                                        if (grecaptcha.enterprise.clients[widgetId].callback) {{
                                            grecaptcha.enterprise.clients[widgetId].callback(solution);
                                            return true;
                                        }}
                                    }}
                                }}

                                // Standard grecaptcha callback
                                const callback = document.querySelector('.g-recaptcha')?.getAttribute('data-callback');
                                if (callback && typeof window[callback] === 'function') {{
                                    window[callback](solution);
                                    return true;
                                }}

                                // Fallback: find callback in ___grecaptcha_cfg
                                if (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) {{
                                    for (const clientId in window.___grecaptcha_cfg.clients) {{
                                        const client = window.___grecaptcha_cfg.clients[clientId];
                                        for (const key in client) {{
                                            if (client[key] && typeof client[key].callback === 'function') {{
                                                client[key].callback(solution);
                                                return true;
                                            }}
                                        }}
                                    }}
                                }}
                            }} catch (e) {{
                                console.error('reCAPTCHA callback error:', e);
                            }}
                        }}

                        return !!textarea;
                    }}
                """, solution)
                return result

            elif captcha_type == "hcaptcha":
                # Inject into h-captcha-response textarea and trigger callback
                result = await page.evaluate(f"""
                    (solution) => {{
                        // Find and fill the response textarea
                        const textarea = document.querySelector('[name="h-captcha-response"]') ||
                                          document.querySelector('textarea[name*="hcaptcha"]');
                        if (textarea) {{
                            textarea.value = solution;
                        }}

                        // Also fill g-recaptcha-response if present (some sites use both names)
                        const gTextarea = document.querySelector('[name="g-recaptcha-response"]');
                        if (gTextarea) {{
                            gTextarea.value = solution;
                        }}

                        // Try to trigger the callback
                        const callback = document.querySelector('.h-captcha')?.getAttribute('data-callback');
                        if (callback && typeof window[callback] === 'function') {{
                            window[callback](solution);
                            return true;
                        }}

                        // Try hcaptcha object
                        if (typeof hcaptcha !== 'undefined') {{
                            try {{
                                // Some sites expose setResponse
                                if (hcaptcha.setResponse) {{
                                    hcaptcha.setResponse(solution);
                                    return true;
                                }}
                            }} catch (e) {{
                                console.error('hCaptcha callback error:', e);
                            }}
                        }}

                        return !!textarea;
                    }}
                """, solution)
                return result

        except Exception as e:
            logger.error(f"[CAPTCHA] Solution injection failed: {e}")

        return False

    async def _solve_text_captcha(self, page, detection: Dict) -> CaptchaResult:
        """
        Solve text/image CAPTCHA using vision AI (LLaVA).

        Takes a screenshot and asks LLaVA to read the CAPTCHA text.
        """
        try:
            # Find the CAPTCHA image
            image_data = None
            selector = detection.get("selector")

            if detection.get("image_src"):
                # If we have an image src, fetch it
                image_data = await self._fetch_image(detection["image_src"])
            elif selector:
                # Take a screenshot of the CAPTCHA element
                element = await page.query_selector(selector)
                if element:
                    screenshot = await element.screenshot()
                    image_data = base64.b64encode(screenshot).decode('utf-8')

            if not image_data:
                # Fallback: screenshot the whole page and crop
                screenshot = await page.screenshot()
                image_data = base64.b64encode(screenshot).decode('utf-8')

            # Ask LLaVA to read the CAPTCHA
            solution = await self._ask_vision_ai(image_data)

            if solution:
                # Fill in the CAPTCHA input
                input_sel = detection.get("input_selector")
                if input_sel:
                    input_el = await page.query_selector(input_sel)
                    if input_el:
                        await input_el.fill(solution)
                        logger.info(f"[CAPTCHA] Filled solution: {solution}")

                        return CaptchaResult(
                            success=True,
                            solution=solution,
                            method="vision_ai",
                            message="CAPTCHA solved using vision AI",
                            confidence=0.6  # Vision AI isn't always accurate
                        )

                # Couldn't find input, but we have the solution
                return CaptchaResult(
                    success=True,
                    solution=solution,
                    method="vision_ai",
                    message="CAPTCHA read but input not found",
                    confidence=0.5
                )

            return CaptchaResult(
                success=False,
                method="vision_ai",
                message="Vision AI could not read CAPTCHA",
                needs_manual=True
            )

        except Exception as e:
            logger.error(f"[CAPTCHA] Vision AI error: {e}")
            return CaptchaResult(
                success=False,
                method="vision_ai",
                message=f"Vision AI error: {e}",
                needs_manual=True
            )

    async def _fetch_image(self, url: str) -> Optional[str]:
        """Fetch image from URL and return as base64."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            logger.warning(f"[CAPTCHA] Could not fetch image: {e}")
        return None

    async def _ask_vision_ai(self, image_base64: str) -> Optional[str]:
        """
        Ask LLaVA (vision AI) to read the CAPTCHA text.

        Uses Ollama's vision model support.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": """Look at this CAPTCHA image. What text, numbers, or characters do you see?

IMPORTANT:
- Only tell me the EXACT characters you see in the CAPTCHA
- No explanations, just the characters
- If it's a math problem, solve it and give me the answer
- If you can't read it clearly, make your best guess

Answer with ONLY the CAPTCHA solution:""",
                        "images": [image_base64],
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("response", "").strip()

                    # Clean up the answer
                    answer = self._clean_captcha_answer(answer)

                    if answer:
                        logger.info(f"[CAPTCHA] Vision AI read: {answer}")
                        return answer

        except Exception as e:
            logger.error(f"[CAPTCHA] Ollama vision error: {e}")

        return None

    def _clean_captcha_answer(self, text: str) -> str:
        """Clean up vision AI response to get just the CAPTCHA answer."""
        if not text:
            return ""

        # Remove common prefixes/suffixes
        text = text.strip()

        # If it looks like a math problem result, extract the number
        if '=' in text:
            text = text.split('=')[-1].strip()

        # Remove quotes
        text = text.strip('"\'')

        # Remove common phrases
        for phrase in ['the answer is', 'captcha is', 'text is', 'i see', 'the text says']:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE).strip()

        # If multiple lines, take the shortest (likely just the answer)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) > 1:
            text = min(lines, key=len)

        return text.strip()

    async def handle_captcha_if_present(self, page) -> CaptchaResult:
        """
        Convenience method to detect and solve in one call.

        Use this in form filling workflow.
        """
        detection = await self.detect_captcha(page)

        if detection["has_captcha"]:
            logger.info(f"[CAPTCHA] Found {detection['type']} CAPTCHA")
            return await self.solve(page, detection)

        return CaptchaResult(
            success=True,
            method="none",
            message="No CAPTCHA present"
        )
