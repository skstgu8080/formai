"""
MultiStepFormManager - Handles multi-page registration flows.

Phase 3 Feature: Wizard forms support.

Detects and navigates multi-step forms (registration wizards) by:
1. Detecting step indicators (progress bars, "Step X of Y")
2. Tracking current step state
3. Filling current step fields only
4. Clicking "Next" (not Submit) to advance
5. Detecting step advancement
6. Repeating until final step
7. Clicking "Submit" on final step
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("multistep-manager")


@dataclass
class StepInfo:
    """Information about a form step."""
    step_number: int
    total_steps: Optional[int] = None
    step_title: Optional[str] = None
    fields_count: int = 0
    url: str = ""
    has_next_button: bool = False
    has_submit_button: bool = False
    is_final_step: bool = False


class MultiStepFormManager:
    """
    Manages multi-page/wizard form flows.

    Tracks form state across pages and handles navigation
    between steps without accidentally submitting early.
    """

    # Keywords indicating "Next" button (not submit)
    NEXT_KEYWORDS = [
        'next', 'continue', 'proceed', 'forward', 'step',
        'siguiente', 'weiter', 'suivant', 'avanti',  # multilingual
        'next step', 'go to', 'move to'
    ]

    # Keywords indicating "Submit/Complete" button (final)
    SUBMIT_KEYWORDS = [
        'submit', 'finish', 'complete', 'register', 'sign up',
        'create account', 'confirm', 'done', 'enviar', 'absenden',
        'place order', 'checkout', 'pay now'
    ]

    # Keywords indicating "Back/Previous" button (skip these)
    BACK_KEYWORDS = [
        'back', 'previous', 'prev', 'return', 'go back',
        'anterior', 'zuruck', 'retour'
    ]

    # Patterns for step indicators
    STEP_PATTERNS = [
        r'step\s*(\d+)\s*(?:of|/)\s*(\d+)',  # "Step 1 of 3"
        r'(\d+)\s*/\s*(\d+)',                 # "1/3"
        r'(\d+)\s*of\s*(\d+)',                # "1 of 3"
        r'page\s*(\d+)\s*(?:of|/)\s*(\d+)',  # "Page 1 of 3"
    ]

    def __init__(self):
        self.current_step = 0
        self.total_steps: Optional[int] = None
        self.step_history: List[StepInfo] = []
        self.step_urls: List[str] = []
        self.filled_steps: List[int] = []

    async def detect_steps(self, page) -> StepInfo:
        """
        Detect wizard structure on current page.

        Args:
            page: Playwright page object

        Returns:
            StepInfo with detected step information
        """
        info = StepInfo(step_number=self.current_step + 1)

        try:
            # Get page URL
            info.url = page.url

            # Method 1: Look for step indicator text
            page_text = await page.evaluate("document.body.innerText")
            for pattern in self.STEP_PATTERNS:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    info.step_number = int(match.group(1))
                    info.total_steps = int(match.group(2))
                    self.total_steps = info.total_steps
                    logger.info(f"[MultiStep] Detected step {info.step_number} of {info.total_steps}")
                    break

            # Method 2: Check for progress bar/stepper
            progress_indicators = await self._find_progress_indicators(page)
            if progress_indicators and not info.total_steps:
                info.total_steps = progress_indicators.get('total', None)
                if progress_indicators.get('current'):
                    info.step_number = progress_indicators['current']

            # Method 3: Look for step-specific classes
            step_elements = await page.query_selector_all('[class*="step"], [class*="wizard"], [class*="progress"]')
            if step_elements and not info.total_steps:
                # Try to count steps from elements
                active_found = False
                step_count = 0
                for el in step_elements:
                    class_name = await el.get_attribute('class') or ''
                    if 'active' in class_name or 'current' in class_name:
                        active_found = True
                        info.step_number = step_count + 1
                    step_count += 1

            # Detect buttons
            info.has_next_button = await self._has_next_button(page)
            info.has_submit_button = await self._has_submit_button(page)

            # Determine if final step
            info.is_final_step = self._is_final_step(info)

            # Count fields on this step
            fields = await page.query_selector_all('input:not([type="hidden"]), select, textarea')
            info.fields_count = len(fields)

            self.current_step = info.step_number
            self.step_history.append(info)

        except Exception as e:
            logger.warning(f"[MultiStep] Error detecting steps: {e}")

        return info

    async def _find_progress_indicators(self, page) -> Optional[Dict]:
        """Find progress bar/stepper and extract step info."""
        try:
            # Check for aria-valuemin/max on progress bars
            progress = await page.query_selector('[role="progressbar"]')
            if progress:
                current = await progress.get_attribute('aria-valuenow')
                max_val = await progress.get_attribute('aria-valuemax')
                if current and max_val:
                    return {'current': int(current), 'total': int(max_val)}

            # Check for numbered steps (1, 2, 3...)
            steppers = await page.query_selector_all('.step, .stepper-item, [class*="wizard-step"]')
            if len(steppers) > 1:
                active_idx = 0
                for i, step in enumerate(steppers):
                    class_name = await step.get_attribute('class') or ''
                    if 'active' in class_name or 'current' in class_name:
                        active_idx = i + 1
                        break
                return {'current': active_idx, 'total': len(steppers)}

        except Exception as e:
            logger.debug(f"[MultiStep] Progress indicator check: {e}")

        return None

    async def _has_next_button(self, page) -> bool:
        """Check if page has a 'Next' button (not submit)."""
        try:
            buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"], a.btn')
            for btn in buttons:
                text = await btn.inner_text() if hasattr(btn, 'inner_text') else ''
                text = text.lower().strip() if text else ''

                # Also check value attribute for input buttons
                value = await btn.get_attribute('value') or ''
                text = text or value.lower()

                # Skip back buttons
                if any(back in text for back in self.BACK_KEYWORDS):
                    continue

                # Check for next keywords
                if any(next_kw in text for next_kw in self.NEXT_KEYWORDS):
                    return True

        except Exception as e:
            logger.debug(f"[MultiStep] Next button check: {e}")

        return False

    async def _has_submit_button(self, page) -> bool:
        """Check if page has a final 'Submit' button."""
        try:
            buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"]')
            for btn in buttons:
                text = await btn.inner_text() if hasattr(btn, 'inner_text') else ''
                text = text.lower().strip() if text else ''

                value = await btn.get_attribute('value') or ''
                text = text or value.lower()

                # Check for submit keywords
                if any(submit_kw in text for submit_kw in self.SUBMIT_KEYWORDS):
                    return True

        except Exception as e:
            logger.debug(f"[MultiStep] Submit button check: {e}")

        return False

    def _is_final_step(self, info: StepInfo) -> bool:
        """Determine if current step is the final one."""
        # If we know total steps, check if we're on the last
        if info.total_steps and info.step_number >= info.total_steps:
            return True

        # If there's a submit button but no next button, probably final
        if info.has_submit_button and not info.has_next_button:
            return True

        return False

    async def is_step_complete(self, page) -> bool:
        """
        Check if current step is complete (filled successfully).

        Returns True if we should advance to next step.
        """
        try:
            # Check for validation errors
            errors = await page.query_selector_all('.error, .invalid, [class*="error"], [class*="invalid"]')
            visible_errors = 0
            for err in errors:
                if await err.is_visible():
                    visible_errors += 1

            if visible_errors > 0:
                logger.warning(f"[MultiStep] {visible_errors} validation errors found")
                return False

            # All required fields should be filled
            required = await page.query_selector_all('[required], .required')
            for field in required:
                value = await field.input_value() if hasattr(field, 'input_value') else ''
                if not value:
                    return False

            return True

        except Exception as e:
            logger.warning(f"[MultiStep] Step complete check: {e}")
            return True  # Assume complete if check fails

    async def find_next_button(self, page) -> Optional[Any]:
        """Find the 'Next' button element to click."""
        try:
            buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"], a.btn')

            best_match = None
            best_score = 0

            for btn in buttons:
                # Skip invisible buttons
                if not await btn.is_visible():
                    continue

                text = ''
                try:
                    text = await btn.inner_text()
                except:
                    pass
                text = text.lower().strip() if text else ''

                value = await btn.get_attribute('value') or ''
                text = text or value.lower()

                # Skip back buttons
                if any(back in text for back in self.BACK_KEYWORDS):
                    continue

                # Score the button
                score = 0
                for next_kw in self.NEXT_KEYWORDS:
                    if next_kw in text:
                        score += 1
                        # Exact match is better
                        if text == next_kw:
                            score += 2

                if score > best_score:
                    best_score = score
                    best_match = btn

            return best_match

        except Exception as e:
            logger.warning(f"[MultiStep] Find next button: {e}")
            return None

    async def find_submit_button(self, page) -> Optional[Any]:
        """Find the final 'Submit' button element."""
        try:
            buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"]')

            best_match = None
            best_score = 0

            for btn in buttons:
                if not await btn.is_visible():
                    continue

                text = ''
                try:
                    text = await btn.inner_text()
                except:
                    pass
                text = text.lower().strip() if text else ''

                value = await btn.get_attribute('value') or ''
                text = text or value.lower()

                # Score the button
                score = 0
                for submit_kw in self.SUBMIT_KEYWORDS:
                    if submit_kw in text:
                        score += 1
                        if text == submit_kw:
                            score += 2

                if score > best_score:
                    best_score = score
                    best_match = btn

            return best_match

        except Exception as e:
            logger.warning(f"[MultiStep] Find submit button: {e}")
            return None

    async def advance_step(self, page) -> Tuple[bool, str]:
        """
        Click Next and wait for new step to load.

        Returns:
            (success, message) tuple
        """
        try:
            current_url = page.url

            # Find and click next button
            next_btn = await self.find_next_button(page)
            if not next_btn:
                return False, "No next button found"

            logger.info(f"[MultiStep] Clicking next button...")
            await next_btn.click()

            # Wait for navigation or AJAX update
            await asyncio.sleep(1)

            # Check if we moved to a new page/step
            new_url = page.url
            url_changed = new_url != current_url

            # Wait for any loading to complete
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass

            # Detect new step
            new_step_info = await self.detect_steps(page)

            if url_changed or new_step_info.step_number > self.current_step:
                self.current_step = new_step_info.step_number
                self.step_urls.append(new_url)
                return True, f"Advanced to step {new_step_info.step_number}"
            else:
                # Check for validation errors
                errors = await page.query_selector_all('.error:visible, .invalid:visible')
                if errors:
                    return False, "Validation errors prevented advancement"
                return False, "Step did not advance"

        except Exception as e:
            return False, f"Error advancing step: {e}"

    async def submit_final(self, page) -> Tuple[bool, str]:
        """
        Click the final submit button.

        Returns:
            (success, message) tuple
        """
        try:
            submit_btn = await self.find_submit_button(page)
            if not submit_btn:
                # Fallback: try any submit type
                submit_btn = await page.query_selector('button[type="submit"], input[type="submit"]')

            if not submit_btn:
                return False, "No submit button found"

            logger.info(f"[MultiStep] Clicking final submit button...")
            await submit_btn.click()

            # Wait for submission response
            await asyncio.sleep(2)

            return True, "Form submitted"

        except Exception as e:
            return False, f"Error submitting: {e}"

    def get_status(self) -> Dict[str, Any]:
        """Get current multi-step form status."""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "steps_completed": len(self.filled_steps),
            "step_history": [
                {
                    "step": s.step_number,
                    "fields": s.fields_count,
                    "url": s.url
                }
                for s in self.step_history
            ],
            "is_multi_step": self.total_steps is not None and self.total_steps > 1
        }

    def reset(self):
        """Reset manager for new form."""
        self.current_step = 0
        self.total_steps = None
        self.step_history = []
        self.step_urls = []
        self.filled_steps = []
