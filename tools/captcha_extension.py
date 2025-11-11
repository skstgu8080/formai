#!/usr/bin/env python3
"""
CAPTCHA Extension - Automatic CAPTCHA detection and solving

Integrates with SeleniumBase UC Mode's built-in CAPTCHA solving capabilities.
Detects CAPTCHA presence and automatically handles solving using UC methods.
"""
import time
from typing import Dict, Any, List, Optional
from tools.replay_extension import ReplayExtension, ReplayContext


class CaptchaExtension(ReplayExtension):
    """
    Extension that automatically detects and solves CAPTCHAs during replay.

    Features:
    - Automatic CAPTCHA detection after form filling
    - Integration with UC Mode CAPTCHA solving
    - reCAPTCHA v2/v3 support
    - hCaptcha support
    - GUI-assisted solving fallback
    - Configurable solving strategies
    - Statistics tracking
    """

    def __init__(
        self,
        engine: Any = None,
        config: Optional[Dict[str, Any]] = None,
        auto_solve: bool = True,
        solve_after_fill: bool = True,
        max_solve_time: int = 120
    ):
        """
        Initialize CAPTCHA extension.

        Args:
            engine: Reference to ProfileReplayEngine instance
            config: Optional configuration dictionary
            auto_solve: Automatically solve CAPTCHAs when detected
            solve_after_fill: Solve CAPTCHA after all fields filled (default True)
            max_solve_time: Maximum time to wait for CAPTCHA solve in seconds
        """
        super().__init__(engine, config)
        self.auto_solve = auto_solve
        self.solve_after_fill = solve_after_fill
        self.max_solve_time = max_solve_time

        # CAPTCHA detection patterns
        self.captcha_selectors = [
            "iframe[src*='recaptcha']",           # reCAPTCHA v2
            "iframe[src*='hcaptcha']",            # hCaptcha
            "[class*='g-recaptcha']",             # reCAPTCHA div
            "[class*='h-captcha']",               # hCaptcha div
            "#recaptcha",                         # ID-based reCAPTCHA
            ".captcha-container",                 # Generic CAPTCHA container
        ]

        # Statistics
        self.stats = {
            "captchas_detected": 0,
            "captchas_solved": 0,
            "captchas_failed": 0,
            "captcha_types": [],
            "solve_times": [],
            "manual_interventions": 0
        }

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """
        Log CAPTCHA extension activation.

        Args:
            context: ReplayContext containing browser driver and session info
        """
        print(f"\n{'='*60}")
        print(f"CAPTCHA Extension - Active")
        print(f"{'='*60}")
        print(f"Auto-solve: {self.auto_solve}")
        print(f"Solve after fill: {self.solve_after_fill}")
        print(f"Max solve time: {self.max_solve_time}s")
        print(f"{'='*60}\n")

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """
        Handle CAPTCHA after all fields are filled.

        Args:
            results: List of all step execution results
            context: ReplayContext containing browser driver
        """
        if not self.solve_after_fill:
            return

        # Get browser driver from context
        if not context or not context.browser_driver:
            print("[CAPTCHA] No browser driver available in context")
            return

        browser_driver = context.browser_driver

        print(f"\n{'='*60}")
        print("CAPTCHA Extension - Post-Fill Check")
        print(f"{'='*60}")

        # Detect CAPTCHA
        captcha_type = self._detect_captcha(browser_driver)

        if captcha_type:
            print(f"[CAPTCHA] Detected: {captcha_type}")
            self.stats["captchas_detected"] += 1
            self.stats["captcha_types"].append(captcha_type)

            if self.auto_solve:
                success = self._solve_captcha(browser_driver, captcha_type)
                if success:
                    print(f"[CAPTCHA] Successfully solved {captcha_type}")
                    self.stats["captchas_solved"] += 1
                else:
                    print(f"[CAPTCHA] Failed to solve {captcha_type}")
                    self.stats["captchas_failed"] += 1
            else:
                print("[CAPTCHA] Auto-solve disabled, waiting for manual intervention")
                self._wait_for_manual_solve(browser_driver)
        else:
            print("[CAPTCHA] No CAPTCHA detected on page")

        print(f"{'='*60}\n")

    def _detect_captcha(self, driver: Any) -> Optional[str]:
        """
        Detect CAPTCHA presence on the page.

        Args:
            driver: SeleniumBase driver instance

        Returns:
            CAPTCHA type string if detected, None otherwise
        """
        try:
            # Check for reCAPTCHA v2
            if self._element_exists(driver, "iframe[src*='recaptcha/api2']"):
                return "reCAPTCHA v2"

            # Check for reCAPTCHA v3 (invisible)
            if self._element_exists(driver, "iframe[src*='recaptcha/enterprise']"):
                return "reCAPTCHA v3 (Enterprise)"

            # Check for hCaptcha
            if self._element_exists(driver, "iframe[src*='hcaptcha']"):
                return "hCaptcha"

            # Check for generic CAPTCHA containers
            for selector in self.captcha_selectors:
                if self._element_exists(driver, selector):
                    return "Generic CAPTCHA"

            return None

        except Exception as e:
            print(f"[CAPTCHA] Error detecting CAPTCHA: {e}")
            return None

    def _element_exists(self, driver: Any, selector: str, timeout: float = 1.0) -> bool:
        """
        Check if element exists without throwing exception.

        Args:
            driver: SeleniumBase driver instance
            selector: CSS selector to check
            timeout: Maximum wait time in seconds

        Returns:
            True if element exists, False otherwise
        """
        try:
            driver.wait_for_element_present(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def _solve_captcha(self, driver: Any, captcha_type: str) -> bool:
        """
        Solve CAPTCHA using UC Mode methods.

        Args:
            driver: SeleniumBase driver instance
            captcha_type: Type of CAPTCHA detected

        Returns:
            True if solved successfully, False otherwise
        """
        start_time = time.time()

        try:
            print(f"[CAPTCHA] Attempting to solve {captcha_type}...")

            # UC Mode has multiple CAPTCHA solving methods
            if hasattr(driver, 'uc_gui_handle_captcha'):
                print("[CAPTCHA] Using uc_gui_handle_captcha() method")
                driver.uc_gui_handle_captcha()

                # Wait for CAPTCHA to disappear
                time.sleep(3)

                # Verify CAPTCHA is gone
                if not self._detect_captcha(driver):
                    solve_time = time.time() - start_time
                    self.stats["solve_times"].append(solve_time)
                    print(f"[CAPTCHA] Solved in {solve_time:.1f}s")
                    return True

            # Fallback to click-based method
            elif hasattr(driver, 'uc_gui_click_captcha'):
                print("[CAPTCHA] Using uc_gui_click_captcha() method")
                driver.uc_gui_click_captcha()

                time.sleep(3)

                if not self._detect_captcha(driver):
                    solve_time = time.time() - start_time
                    self.stats["solve_times"].append(solve_time)
                    print(f"[CAPTCHA] Solved in {solve_time:.1f}s")
                    return True

            else:
                print("[CAPTCHA] No UC Mode CAPTCHA methods available")
                print("[CAPTCHA] Falling back to manual intervention")
                self._wait_for_manual_solve(driver)
                return True

            print("[CAPTCHA] CAPTCHA still present after solve attempt")
            return False

        except Exception as e:
            print(f"[CAPTCHA] Error solving CAPTCHA: {e}")
            return False

    def _wait_for_manual_solve(self, driver: Any) -> None:
        """
        Wait for user to manually solve CAPTCHA.

        Args:
            driver: SeleniumBase driver instance
        """
        print(f"\n{'='*60}")
        print("MANUAL CAPTCHA INTERVENTION REQUIRED")
        print(f"{'='*60}")
        print("Please solve the CAPTCHA manually in the browser window.")
        print(f"Waiting up to {self.max_solve_time} seconds...")
        print(f"{'='*60}\n")

        self.stats["manual_interventions"] += 1
        start_time = time.time()

        # Poll for CAPTCHA disappearance
        while time.time() - start_time < self.max_solve_time:
            time.sleep(2)

            if not self._detect_captcha(driver):
                elapsed = time.time() - start_time
                print(f"\n[CAPTCHA] CAPTCHA solved manually in {elapsed:.1f}s")
                self.stats["captchas_solved"] += 1
                return

        print(f"\n[CAPTCHA] Timeout waiting for manual CAPTCHA solve")
        self.stats["captchas_failed"] += 1

    def getStats(self) -> Dict[str, Any]:
        """
        Get CAPTCHA solving statistics.

        Returns:
            Dictionary of statistics
        """
        stats = self.stats.copy()

        if stats["solve_times"]:
            stats["average_solve_time"] = sum(stats["solve_times"]) / len(stats["solve_times"])
        else:
            stats["average_solve_time"] = 0

        if stats["captchas_detected"] > 0:
            stats["success_rate"] = (stats["captchas_solved"] / stats["captchas_detected"]) * 100
        else:
            stats["success_rate"] = 0

        return stats

    def onError(self, step: Dict[str, Any], error: Exception) -> bool:
        """
        Handle errors during CAPTCHA solving.

        Args:
            step: The step that failed
            error: The exception that occurred

        Returns:
            True to continue execution, False to abort
        """
        print(f"[CAPTCHA ERROR] {error}")
        return self.config.get("continue_on_error", True)
