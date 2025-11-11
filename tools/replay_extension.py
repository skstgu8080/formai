#!/usr/bin/env python3
"""
Base Extension System for Replay Engine

Provides lifecycle hooks for extending replay behavior without modifying core engine.
Inspired by @puppeteer/replay PuppeteerRunnerExtension but adapted for Python/SeleniumBase.
"""
from typing import Dict, Any, Optional, List
from abc import ABC
from pathlib import Path
from datetime import datetime


class ReplayContext:
    """
    Context object containing state information during replay execution.

    This context is passed to extension hooks and contains all relevant
    information about the current replay session.
    """

    def __init__(
        self,
        profile_data: Dict[str, Any],
        session_name: str,
        replay_stats: Dict[str, Any],
        current_url: str = "",
        browser_driver: Optional[Any] = None
    ):
        """
        Initialize replay context.

        Args:
            profile_data: User profile data for form filling
            session_name: Name of the replay session
            replay_stats: Statistics dictionary tracking replay progress
            current_url: Current browser URL
            browser_driver: SeleniumBase driver instance (sb object)
        """
        self.profile_data = profile_data
        self.session_name = session_name
        self.replay_stats = replay_stats
        self.current_url = current_url
        self.browser_driver = browser_driver
        self.custom_data: Dict[str, Any] = {}  # For extension-specific data


class ReplayExtension(ABC):
    """
    Abstract base class for replay engine extensions.

    Extensions can hook into the replay lifecycle to add custom behavior
    like data transformation, validation, logging, or side effects.

    Lifecycle order:
    1. beforeAllSteps(context) - Called once before any steps execute
    2. For each step:
        a. shouldSkipStep(step, context) - Check if step should be skipped
        b. transformStep(step) - Modify step data before execution
        c. beforeEachStep(step, context) - Called before step executes
        d. [Step executes in engine]
        e. afterEachStep(step, result, context) - Called after step completes
    3. afterAllSteps(results) - Called once after all steps complete
    """

    def __init__(self, engine: Any = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize extension.

        Args:
            engine: Reference to the ProfileReplayEngine instance (optional)
            config: Optional configuration dictionary for the extension
        """
        self.engine = engine
        self.config = config or {}
        self.stats: Dict[str, Any] = {}
        self.name = self.__class__.__name__

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """
        Called once before starting replay of all steps.

        Use this hook to:
        - Initialize extension state
        - Validate prerequisites
        - Set up logging or monitoring
        - Configure browser settings
        - Prepare external resources

        Args:
            context: ReplayContext containing profile data, session info, and browser driver

        Example:
            def beforeAllSteps(self, context: ReplayContext):
                print(f"Starting replay for profile: {context.profile_data.get('profileName')}")
                # Initialize custom tracking
                context.custom_data['start_time'] = time.time()
                # Configure browser
                if context.browser_driver:
                    context.browser_driver.execute_script("window.customFlag = true")
        """
        pass

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        """
        Called before executing each individual step.

        Use this hook to:
        - Log step execution
        - Take screenshots before actions
        - Wait for dynamic content
        - Validate page state
        - Add delays or timing adjustments

        Args:
            step: The step dictionary about to be executed
            context: Current replay context

        Example:
            def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext):
                field_name = step.get('field_name', 'Unknown')
                print(f"About to fill: {field_name}")
                # Add custom delay for specific fields
                if 'email' in field_name.lower():
                    time.sleep(1)  # Extra time for email validation
        """
        pass

    def afterEachStep(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: ReplayContext
    ) -> None:
        """
        Called after executing each individual step.

        Use this hook to:
        - Process execution results
        - Take screenshots after actions
        - Verify field values were set correctly
        - Log success/failure
        - Collect metrics
        - Handle errors or retries

        Args:
            step: The step dictionary that was executed
            result: Result dictionary containing success status, error, execution time, etc.
            context: Current replay context

        Example:
            def afterEachStep(self, step: Dict[str, Any], result: Dict[str, Any], context: ReplayContext):
                if result.get('success'):
                    print(f"✓ {step['field_name']}: {result['execution_time_ms']:.0f}ms")
                else:
                    print(f"✗ {step['field_name']}: {result.get('error', 'Unknown error')}")
                    # Take screenshot on failure
                    if context.browser_driver:
                        context.browser_driver.save_screenshot(f"error_{step['field_name']}.png")
        """
        pass

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """
        Called once after all steps have completed.

        Use this hook to:
        - Generate summary reports
        - Save logs or metrics
        - Clean up resources
        - Send notifications
        - Export results
        - Handle CAPTCHAs

        Args:
            results: List of all step results from the replay
            context: ReplayContext containing browser driver and session info

        Example:
            def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None):
                success_count = sum(1 for r in results if r.get('success'))
                total_count = len(results)
                print(f"Replay complete: {success_count}/{total_count} fields successful")
                # Calculate average execution time
                avg_time = sum(r.get('execution_time_ms', 0) for r in results) / max(len(results), 1)
                print(f"Average field fill time: {avg_time:.0f}ms")
        """
        pass

    def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a step before execution.

        Use this hook to:
        - Modify field values dynamically
        - Change selectors (e.g., switch from ARIA to CSS)
        - Add or remove step properties
        - Adjust timing or delays
        - Apply conditional logic

        Args:
            step: The step dictionary to transform

        Returns:
            Modified step dictionary (or original if no changes)

        Example:
            def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
                # Convert all email values to lowercase
                if step.get('profile_mapping') == 'email':
                    if 'value_to_use' in step:
                        step['value_to_use'] = step['value_to_use'].lower()

                # Switch ARIA selectors to CSS
                selector = step.get('field_selector', '')
                if selector.startswith('aria/'):
                    original_step = step.get('original_step', {})
                    selectors_list = original_step.get('selectors', [])
                    for selector_option in selectors_list:
                        if isinstance(selector_option, list) and len(selector_option) > 0:
                            candidate = selector_option[0]
                            if not candidate.startswith('aria/'):
                                step['field_selector'] = candidate
                                break

                return step
        """
        return step

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        """
        Determine whether to skip a step during execution.

        Use this hook to:
        - Skip optional fields conditionally
        - Avoid filling fields based on profile data
        - Skip steps based on page state
        - Implement conditional workflows
        - Filter out problematic selectors

        Args:
            step: The step to potentially skip
            context: Current replay context

        Returns:
            True to skip the step, False to execute it

        Example:
            def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
                # Skip address2 if profile doesn't have it
                if step.get('profile_mapping') == 'address2':
                    profile_data = context.profile_data
                    if 'data' in profile_data:
                        profile_data = profile_data['data']
                    if not profile_data.get('address2'):
                        print(f"Skipping {step['field_name']} - no data in profile")
                        return True

                # Skip fields with ARIA selectors and no fallback
                selector = step.get('field_selector', '')
                if selector.startswith('aria/'):
                    print(f"Skipping {step['field_name']} - ARIA selector not supported")
                    return True

                return False
        """
        return False

    def onError(self, step: Dict[str, Any], error: Exception) -> bool:
        """
        Called when a step encounters an error.

        Args:
            step: The step that failed
            error: The exception that occurred

        Returns:
            True to continue execution, False to abort
        """
        return True

    def getStats(self) -> Dict[str, Any]:
        """
        Get extension-specific statistics.

        Returns:
            Dictionary of statistics collected by this extension
        """
        return self.stats


class ExtensionManager:
    """
    Manages multiple extensions for the replay engine.

    Coordinates extension lifecycle calls in the correct order.
    """

    def __init__(self):
        self.extensions: List[ReplayExtension] = []

    def register(self, extension: ReplayExtension) -> None:
        """Register an extension."""
        self.extensions.append(extension)

    def unregister(self, extension: ReplayExtension) -> None:
        """Unregister an extension."""
        if extension in self.extensions:
            self.extensions.remove(extension)

    def clear(self) -> None:
        """Remove all extensions."""
        self.extensions.clear()

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """Call beforeAllSteps on all extensions."""
        for ext in self.extensions:
            ext.beforeAllSteps(context)

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        """Call beforeEachStep on all extensions."""
        for ext in self.extensions:
            ext.beforeEachStep(step, context)

    def afterEachStep(self, step: Dict[str, Any], result: Dict[str, Any], context: ReplayContext) -> None:
        """Call afterEachStep on all extensions."""
        for ext in self.extensions:
            ext.afterEachStep(step, result, context)

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """Call afterAllSteps on all extensions."""
        for ext in self.extensions:
            ext.afterAllSteps(results, context)

    def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all extension transformations to a step.

        Transformations are applied in registration order.
        """
        transformed_step = step
        for ext in self.extensions:
            transformed_step = ext.transformStep(transformed_step)
        return transformed_step

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        """
        Check if any extension wants to skip this step.

        Returns True if ANY extension returns True.
        """
        for ext in self.extensions:
            if ext.shouldSkipStep(step, context):
                return True
        return False

    def onError(self, step: Dict[str, Any], error: Exception) -> bool:
        """
        Call onError on all extensions.

        Returns False if any extension returns False.
        """
        should_continue = True
        for ext in self.extensions:
            if not ext.onError(step, error):
                should_continue = False
        return should_continue

    def getAllStats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics from all extensions.

        Returns:
            Dictionary mapping extension class names to their stats
        """
        return {
            ext.__class__.__name__: ext.getStats()
            for ext in self.extensions
        }


class CompositeReplayExtension(ReplayExtension):
    """
    Composite extension that chains multiple extensions together.

    Executes hooks from all child extensions in order.
    """

    def __init__(self, extensions: List[ReplayExtension], engine: Any = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize composite extension.

        Args:
            extensions: List of extensions to chain together
            engine: Reference to the ProfileReplayEngine instance (optional)
            config: Optional configuration dictionary
        """
        super().__init__(engine, config)
        self.extensions = extensions

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """Execute beforeAllSteps for all extensions."""
        for ext in self.extensions:
            ext.beforeAllSteps(context)

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        """Execute beforeEachStep for all extensions."""
        for ext in self.extensions:
            ext.beforeEachStep(step, context)

    def afterEachStep(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: ReplayContext
    ) -> None:
        """Execute afterEachStep for all extensions."""
        for ext in self.extensions:
            ext.afterEachStep(step, result, context)

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """Execute afterAllSteps for all extensions."""
        for ext in self.extensions:
            ext.afterAllSteps(results, context)

    def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute transformStep for all extensions in sequence."""
        transformed = step
        for ext in self.extensions:
            transformed = ext.transformStep(transformed)
        return transformed

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        """Return True if ANY extension says to skip."""
        for ext in self.extensions:
            if ext.shouldSkipStep(step, context):
                return True
        return False

    def onError(self, step: Dict[str, Any], error: Exception) -> bool:
        """Call onError on all extensions, return False if any returns False."""
        should_continue = True
        for ext in self.extensions:
            if not ext.onError(step, error):
                should_continue = False
        return should_continue


# Example extensions for common use cases

class LoggingExtension(ReplayExtension):
    """
    Example extension that logs all replay events to console.
    """

    def __init__(self, verbose: bool = False, engine: Any = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize logging extension.

        Args:
            verbose: If True, log detailed information for each step
            engine: Reference to engine (optional)
            config: Configuration dictionary (optional)
        """
        super().__init__(engine, config)
        self.verbose = verbose

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """Log replay start."""
        profile_name = context.profile_data.get('profileName', 'Unknown')
        print(f"\n{'='*60}")
        print(f"Starting replay session: {context.session_name}")
        print(f"Profile: {profile_name}")
        print(f"{'='*60}\n")

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        """Log step start."""
        if self.verbose:
            field_name = step.get('field_name', 'Unknown')
            selector = step.get('field_selector', 'Unknown')
            print(f">> Filling: {field_name}")
            print(f"  Selector: {selector}")

    def afterEachStep(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: ReplayContext
    ) -> None:
        """Log step result."""
        field_name = step.get('field_name', 'Unknown')
        if result.get('success'):
            status = "[OK]"
            msg = f"{result.get('execution_time_ms', 0):.0f}ms"
        else:
            status = "[FAIL]"
            msg = result.get('error', 'Unknown error')

        print(f"{status} {field_name}: {msg}")

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """Log replay summary."""
        success_count = sum(1 for r in results if r.get('success'))
        total_count = len(results)
        success_rate = (success_count / max(total_count, 1)) * 100

        print(f"\n{'='*60}")
        print(f"Replay complete: {success_count}/{total_count} fields successful ({success_rate:.1f}%)")

        if results:
            total_time = sum(r.get('execution_time_ms', 0) for r in results)
            avg_time = total_time / len(results)
            print(f"Total time: {total_time:.0f}ms | Average: {avg_time:.0f}ms per field")

        print(f"{'='*60}\n")


class ScreenshotExtension(ReplayExtension):
    """
    Example extension that takes screenshots during replay.
    """

    def __init__(
        self,
        screenshot_dir: str = "screenshots",
        on_error: bool = True,
        on_success: bool = False,
        engine: Any = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize screenshot extension.

        Args:
            screenshot_dir: Directory to save screenshots
            on_error: Take screenshots on field failures
            on_success: Take screenshots on field successes
            engine: Reference to engine (optional)
            config: Configuration dictionary (optional)
        """
        super().__init__(engine, config)
        self.screenshot_dir = Path(screenshot_dir)
        self.on_error = on_error
        self.on_success = on_success
        self.screenshot_dir.mkdir(exist_ok=True)

    def afterEachStep(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        context: ReplayContext
    ) -> None:
        """Take screenshot based on result."""
        should_capture = (
            (self.on_error and not result.get('success')) or
            (self.on_success and result.get('success'))
        )

        if should_capture and context.browser_driver:
            field_name = step.get('field_name', 'unknown').replace(' ', '_')
            status = 'success' if result.get('success') else 'error'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{context.session_name}_{field_name}_{status}_{timestamp}.png"
            filepath = self.screenshot_dir / filename

            try:
                context.browser_driver.save_screenshot(str(filepath))
                print(f"  📸 Screenshot saved: {filepath}")
            except Exception as e:
                print(f"  ⚠️ Screenshot failed: {e}")


if __name__ == "__main__":
    # Example usage
    print("ReplayExtension Base Class")
    print("=" * 60)
    print("\nThis module provides lifecycle hooks for customizing replay behavior.")
    print("\nAvailable hooks:")
    print("  - beforeAllSteps(context)")
    print("  - beforeEachStep(step, context)")
    print("  - afterEachStep(step, result, context)")
    print("  - afterAllSteps(results)")
    print("  - transformStep(step)")
    print("  - shouldSkipStep(step, context)")
    print("\nExample extensions included:")
    print("  - LoggingExtension: Console logging with detailed output")
    print("  - ScreenshotExtension: Automatic screenshots on error/success")
    print("  - CompositeReplayExtension: Chain multiple extensions together")
    print("\nSee class docstrings for usage examples.")
