"""
Chrome DevTools Replay Engine using Playwright

Replays Chrome DevTools recordings natively using Playwright,
exactly like Chrome's native replay functionality.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)


class ChromeDevToolsReplay:
    """Replay Chrome DevTools recordings using Playwright"""

    def __init__(self):
        """Initialize replay engine"""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.progress_callback = None
        self.replay_stats = {
            "start_time": None,
            "end_time": None,
            "recording_id": None,
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "errors": [],
            "step_results": []
        }

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    async def _send_progress_update(
        self,
        status: str,
        message: str,
        progress: float = 0,
        step_data: Dict = None
    ):
        """Send progress update to callback if available"""
        if self.progress_callback:
            update = {
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                "step_data": step_data or {},
                "stats": self.replay_stats.copy()
            }
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(update)
            else:
                self.progress_callback(update)

    async def initialize_browser(self, headless: bool = False):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        logger.info("Playwright browser initialized")

    async def close_browser(self):
        """Close Playwright browser"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser closed")

    async def replay_recording(
        self,
        recording: Dict[str, Any],
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Replay a Chrome DevTools recording using Playwright.

        Args:
            recording: Recording data with steps (should have profile values already replaced)
            headless: Run in headless mode

        Returns:
            Dict with replay results
        """
        try:
            self.replay_stats["start_time"] = datetime.now().isoformat()
            self.replay_stats["recording_id"] = recording.get("recording_id", "unknown")

            recording_name = recording.get("recording_name") or recording.get("title", "Unknown Recording")
            await self._send_progress_update("loading", f"Starting replay: {recording_name}")

            # Initialize browser
            await self.initialize_browser(headless=headless)

            # Get steps from recording
            steps = recording.get("steps", [])
            if not steps:
                raise Exception("No steps found in recording")

            self.replay_stats["total_steps"] = len(steps)

            # Replay each step
            total_steps = len(steps)
            for idx, step in enumerate(steps):
                step_progress = 10 + (idx / total_steps * 85)
                await self._replay_step(step, idx, step_progress)

                # Small delay between steps for stability
                await asyncio.sleep(0.3)

            # Replay completed successfully
            self.replay_stats["end_time"] = datetime.now().isoformat()
            await self._send_progress_update("completed", "Replay completed successfully!", 100)

            # Keep browser open for a moment to see results
            await asyncio.sleep(2)

            return {
                "success": True,
                "stats": self.replay_stats,
                "message": "Replay completed successfully"
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Replay failed: {error_msg}", exc_info=True)
            self.replay_stats["errors"].append(error_msg)
            self.replay_stats["end_time"] = datetime.now().isoformat()
            await self._send_progress_update("error", f"Replay failed: {error_msg}", 0)

            return {
                "success": False,
                "stats": self.replay_stats,
                "error": error_msg
            }

        finally:
            await self.close_browser()

    async def _replay_step(self, step: Dict[str, Any], idx: int, progress: float):
        """
        Replay a single step from the recording.

        This mimics Chrome DevTools native replay behavior.
        """
        step_type = step.get("type", "")
        logger.info(f"Step {idx + 1}: {step_type}")

        try:
            if step_type == "setViewport":
                await self._replay_set_viewport(step, progress)

            elif step_type == "navigate":
                await self._replay_navigate(step, progress)

            elif step_type == "click":
                await self._replay_click(step, progress)

            elif step_type == "change":
                await self._replay_change(step, progress)

            elif step_type == "keyDown":
                await self._replay_key_down(step, progress)

            elif step_type == "keyUp":
                await self._replay_key_up(step, progress)

            elif step_type == "scroll":
                await self._replay_scroll(step, progress)

            elif step_type == "waitForElement":
                await self._replay_wait_for_element(step, progress)

            else:
                logger.warning(f"Unknown step type: {step_type}")

            self.replay_stats["successful_steps"] += 1
            self.replay_stats["step_results"].append({
                "step": idx + 1,
                "type": step_type,
                "status": "success"
            })

        except Exception as e:
            error_msg = f"Step {idx + 1} ({step_type}) failed: {str(e)}"
            logger.error(error_msg)
            self.replay_stats["failed_steps"] += 1
            self.replay_stats["errors"].append(error_msg)
            self.replay_stats["step_results"].append({
                "step": idx + 1,
                "type": step_type,
                "status": "failed",
                "error": str(e)
            })

    async def _replay_set_viewport(self, step: Dict[str, Any], progress: float):
        """Set viewport size"""
        width = step.get("width", 1280)
        height = step.get("height", 720)
        await self.page.set_viewport_size({"width": width, "height": height})
        await self._send_progress_update("viewport", f"Set viewport: {width}x{height}", progress)

    async def _replay_navigate(self, step: Dict[str, Any], progress: float):
        """Navigate to URL"""
        url = step.get("url", "")
        await self._send_progress_update("navigating", f"Navigating to {url}", progress)

        # Wait for navigation to complete
        await self.page.goto(url, wait_until="networkidle", timeout=30000)

        await self._send_progress_update("navigated", f"Loaded {url}", progress)

    async def _replay_click(self, step: Dict[str, Any], progress: float):
        """Click element"""
        selectors = step.get("selectors", [])
        target = step.get("target", "element")

        await self._send_progress_update("clicking", f"Clicking {target}", progress)

        # Try each selector until one works
        element = await self._find_element(selectors)
        if element:
            await element.click()
            logger.info(f"Clicked element: {target}")
        else:
            raise Exception(f"Could not find element to click: {target}")

    async def _replay_change(self, step: Dict[str, Any], progress: float):
        """Fill form field (change event)"""
        selectors = step.get("selectors", [])
        value = step.get("value", "")

        # Extract field name for logging
        field_name = "field"
        if selectors and selectors[0]:
            first_selector = selectors[0][0] if isinstance(selectors[0], list) else selectors[0]
            if first_selector.startswith("aria/"):
                field_name = first_selector.replace("aria/", "")
            elif first_selector.startswith("#"):
                field_name = first_selector[1:]

        await self._send_progress_update("filling", f"Filling {field_name}: {value}", progress)

        # Try each selector until one works
        element = await self._find_element(selectors)
        if element:
            # Clear existing value first
            await element.fill("")
            # Fill with new value
            await element.fill(value)
            logger.info(f"Filled {field_name} with: {value}")
        else:
            raise Exception(f"Could not find element to fill: {field_name}")

    async def _replay_key_down(self, step: Dict[str, Any], progress: float):
        """Send key down event"""
        key = step.get("key", "")
        if key:
            await self.page.keyboard.down(key)

    async def _replay_key_up(self, step: Dict[str, Any], progress: float):
        """Send key up event"""
        key = step.get("key", "")
        if key:
            await self.page.keyboard.up(key)

    async def _replay_scroll(self, step: Dict[str, Any], progress: float):
        """Scroll page"""
        x = step.get("x", 0)
        y = step.get("y", 0)
        await self.page.evaluate(f"window.scrollTo({x}, {y})")

    async def _replay_wait_for_element(self, step: Dict[str, Any], progress: float):
        """Wait for element to appear"""
        selectors = step.get("selectors", [])
        await self._find_element(selectors, timeout=10000)

    async def _find_element(self, selectors: List[List[str]], timeout: int = 5000):
        """
        Find element using multiple selector strategies.

        Chrome DevTools recordings provide multiple selectors in priority order.
        We try each one until we find a match.

        Args:
            selectors: List of selector groups (ARIA, CSS, XPath, etc.)
            timeout: Timeout in milliseconds

        Returns:
            ElementHandle or None
        """
        if not selectors:
            return None

        for selector_group in selectors:
            if not selector_group:
                continue

            for selector in selector_group if isinstance(selector_group, list) else [selector_group]:
                try:
                    # Handle different selector types
                    if selector.startswith("aria/"):
                        # ARIA selector - convert to role/label selector
                        aria_label = selector.replace("aria/", "")

                        # Try different ARIA selector strategies
                        strategies = [
                            f"[aria-label='{aria_label}']",
                            f"[placeholder='{aria_label}']",
                            f"label:has-text('{aria_label}') + input",
                            f"input[name*='{aria_label.lower()}']",
                            f"input[id*='{aria_label.lower()}']"
                        ]

                        for strategy in strategies:
                            try:
                                element = await self.page.wait_for_selector(
                                    strategy,
                                    timeout=timeout,
                                    state="visible"
                                )
                                if element:
                                    return element
                            except:
                                continue

                    elif selector.startswith("xpath/"):
                        # XPath selector
                        xpath = selector.replace("xpath/", "")
                        element = await self.page.wait_for_selector(
                            f"xpath={xpath}",
                            timeout=timeout,
                            state="visible"
                        )
                        if element:
                            return element

                    elif selector.startswith("pierce/"):
                        # Pierce selector (shadow DOM)
                        pierce_selector = selector.replace("pierce/", "")
                        element = await self.page.wait_for_selector(
                            pierce_selector,
                            timeout=timeout,
                            state="visible"
                        )
                        if element:
                            return element

                    else:
                        # Regular CSS selector
                        element = await self.page.wait_for_selector(
                            selector,
                            timeout=timeout,
                            state="visible"
                        )
                        if element:
                            return element

                except Exception as e:
                    # Try next selector
                    logger.debug(f"Selector failed: {selector} - {str(e)}")
                    continue

        return None


async def replay_recording_with_profile(
    recording: Dict[str, Any],
    profile: Dict[str, Any],
    api_key: str,
    headless: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to replay recording with AI value replacement.

    Args:
        recording: Chrome DevTools recording
        profile: User profile data
        api_key: OpenRouter API key for AI value replacement
        headless: Run browser in headless mode

    Returns:
        Replay results
    """
    from .ai_value_replacer import AIValueReplacer

    # Step 1: Replace values with profile data
    logger.info("Replacing recording values with profile data...")
    replacer = AIValueReplacer(api_key)
    modified_recording = replacer.replace_recording_values(recording, profile)

    # Step 2: Replay modified recording
    logger.info("Replaying modified recording...")
    replay_engine = ChromeDevToolsReplay()
    result = await replay_engine.replay_recording(modified_recording, headless=headless)

    return result
