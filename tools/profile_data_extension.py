#!/usr/bin/env python3
"""
Profile Data Extension - Concrete extension for profile data injection

Transforms field values using profile data during replay. Handles nested profile
structures, provides fallback values, and validates field fills.
"""
import time
from typing import Dict, Any, Optional, Callable, List
from tools.replay_extension import ReplayExtension, ReplayContext


class ProfileDataExtension(ReplayExtension):
    """
    Extension that injects profile data into replay steps.

    Features:
    - Maps field profile_mapping to profile data
    - Handles nested profile structures (profile.data.field)
    - Fallback to sample values if profile field missing
    - Custom value transformers (e.g., format phone numbers)
    - Value validation before filling
    - Screenshot capture on field errors
    - Field-level success tracking
    """

    def __init__(
        self,
        engine: Any = None,
        config: Optional[Dict[str, Any]] = None,
        use_recorded_values: bool = False
    ):
        """
        Initialize profile data extension.

        Args:
            engine: Reference to the ProfileReplayEngine instance
            config: Optional configuration dictionary
            use_recorded_values: If True, use recorded sample values instead of profile data (preview mode)
        """
        super().__init__(engine, config)
        self.use_recorded_values = use_recorded_values

        # Value transformers for specific field types
        self.transformers: Dict[str, Callable[[str], str]] = {
            "phone": self._format_phone,
            "zip": self._format_zip,
            "ssn": self._format_ssn,
        }

        # Statistics tracking
        self.stats = {
            "fields_processed": 0,
            "profile_values_used": 0,
            "sample_values_used": 0,
            "default_values_used": 0,
            "validation_failures": 0,
            "transform_failures": 0,
            "field_results": []
        }

    def beforeAllSteps(self, context: ReplayContext) -> None:
        """
        Log profile being used and initialize tracking.

        Args:
            context: ReplayContext containing profile data, session info, and browser driver
        """
        profile_name = context.profile_data.get("profileName", "Unknown")
        mode = "Preview Mode (using recorded sample values)" if self.use_recorded_values else "Production Mode (using profile data)"

        print(f"\n{'='*60}")
        print(f"Profile Data Extension - Starting Replay")
        print(f"{'='*60}")
        print(f"Profile: {profile_name}")
        print(f"Mode: {mode}")
        print(f"Session: {context.session_name}")
        print(f"{'='*60}\n")

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        """
        Log before each step and prepare for injection.

        Args:
            step: The step about to be executed
            context: Current replay context
        """
        field_name = step.get("field_name", "Unknown Field")
        profile_mapping = step.get("profile_mapping", "")

        step_num = self.stats["fields_processed"] + 1
        print(f"\n[Step {step_num}] Processing: {field_name}")
        if profile_mapping:
            print(f"  >> Profile mapping: {profile_mapping}")

    def afterEachStep(self, step: Dict[str, Any], result: Dict[str, Any], context: ReplayContext) -> None:
        """
        Verify field was filled correctly and track results.

        Args:
            step: The step that was executed
            result: The execution result containing success, error, timing, etc.
            context: Current replay context
        """
        field_name = step.get("field_name", "Unknown Field")
        success = result.get("success", False)
        value_used = result.get("value_used", "")
        execution_time = result.get("execution_time_ms", 0)

        # Track field result
        field_result = {
            "step_index": self.stats["fields_processed"],
            "field_name": field_name,
            "success": success,
            "value_used": value_used,
            "execution_time_ms": execution_time,
            "error": result.get("error")
        }
        self.stats["field_results"].append(field_result)

        # Log result
        if success:
            print(f"  [OK] Successfully filled with: '{value_used[:50]}{'...' if len(value_used) > 50 else ''}'")
            print(f"  [TIME] Execution time: {execution_time}ms")
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"  [FAIL] Failed to fill field: {error_msg}")

            # Capture screenshot on error if enabled in config
            if self.config.get("screenshot_on_error", True):
                self._capture_error_screenshot(step, self.stats["fields_processed"], context)

    def afterAllSteps(self, results: List[Dict[str, Any]], context: ReplayContext = None) -> None:
        """
        Log completion statistics.

        Args:
            results: List of all step execution results
            context: ReplayContext containing browser driver and session info
        """
        total_fields = len(results)
        successful_fields = sum(1 for r in results if r.get("success", False))
        failed_fields = total_fields - successful_fields
        success_rate = (successful_fields / max(total_fields, 1)) * 100

        print(f"\n{'='*60}")
        print(f"Profile Data Extension - Replay Complete")
        print(f"{'='*60}")
        print(f"Total Fields: {total_fields}")
        print(f"Successful: {successful_fields}")
        print(f"Failed: {failed_fields}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"\nValue Sources:")
        print(f"  - Profile values: {self.stats['profile_values_used']}")
        print(f"  - Sample values: {self.stats['sample_values_used']}")
        print(f"  - Default values: {self.stats['default_values_used']}")
        print(f"\nValidation:")
        print(f"  - Validation failures: {self.stats['validation_failures']}")
        print(f"  - Transform failures: {self.stats['transform_failures']}")
        print(f"{'='*60}\n")

    def transformStep(self, step: Dict[str, Any], context: ReplayContext) -> Dict[str, Any]:
        """
        Replace placeholder values with profile data.

        Args:
            step: The original step data
            context: Current replay context with profile data

        Returns:
            Modified step with profile data injected
        """
        self.stats["fields_processed"] += 1

        # Preview mode: keep recorded sample values
        if self.use_recorded_values:
            sample_value = step.get("sample_value", "")
            if sample_value:
                self.stats["sample_values_used"] += 1
            return step

        # Production mode: inject profile data
        profile_mapping = step.get("profile_mapping", "")
        if not profile_mapping:
            # No profile mapping, keep original
            return step

        # Get value from profile
        value, value_source = self._get_profile_value(context.profile_data, profile_mapping, step)

        # Track value source
        if value_source == "profile":
            self.stats["profile_values_used"] += 1
        elif value_source == "sample":
            self.stats["sample_values_used"] += 1
        elif value_source == "default":
            self.stats["default_values_used"] += 1

        # Apply custom transformers if available
        field_type = step.get("field_type", "textbox")
        if field_type in self.transformers:
            try:
                value = self.transformers[field_type](value)
            except Exception as e:
                print(f"  ⚠ Transform failed for {field_type}: {e}")
                self.stats["transform_failures"] += 1

        # Validate value
        if not self._validate_value(value, step):
            self.stats["validation_failures"] += 1
            print(f"  ⚠ Value validation failed for: {step.get('field_name')}")

        # Create modified step
        modified_step = step.copy()
        modified_step["value_to_use"] = value
        modified_step["value_source"] = value_source

        return modified_step

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        """
        Determine whether to skip a step during execution.

        Args:
            step: The step to potentially skip
            context: Current replay context

        Returns:
            True to skip the step, False to execute it
        """
        # Don't skip any steps by default
        return False

    def _get_profile_value(
        self,
        profile_data: Dict[str, Any],
        profile_mapping: str,
        field_mapping: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Get the appropriate value from profile data.

        Handles nested profile structures and provides fallback values.
        Based on ProfileReplayEngine._get_profile_value() (lines 373-394).

        Args:
            profile_data: The complete profile data
            profile_mapping: The field to extract from profile (e.g., "firstName", "data.firstName")
            field_mapping: The field mapping containing sample_value and field_type

        Returns:
            Tuple of (value, source) where source is "profile", "sample", or "default"
        """
        # Handle nested profile data structures
        if "data" in profile_data and isinstance(profile_data["data"], dict):
            # Business profile format: {"data": {"firstName": "John"}}
            profile_values = profile_data["data"]
        else:
            # Direct profile format: {"firstName": "John"}
            profile_values = profile_data

        # Support nested mapping like "data.firstName"
        value = self._get_nested_value(profile_values, profile_mapping)

        if value:
            return str(value), "profile"

        # Fallback to sample value
        sample_value = field_mapping.get("sample_value", "")
        if sample_value:
            return str(sample_value), "sample"

        # Generate default value
        default_value = self._generate_default_value(
            profile_mapping,
            field_mapping.get("field_type", "textbox")
        )
        return default_value, "default"

    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to extract from
            key_path: Dot-separated path (e.g., "address.city")

        Returns:
            Value at path, or None if not found
        """
        keys = key_path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _generate_default_value(self, profile_mapping: str, field_type: str) -> str:
        """
        Generate default values for missing profile data.

        Args:
            profile_mapping: The field name being mapped
            field_type: The type of field (textbox, select, etc.)

        Returns:
            Default value string
        """
        defaults = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "(555) 123-4567",
            "company": "Example Corp",
            "address1": "123 Main St",
            "address2": "Suite 100",
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "USA",
            "website": "https://example.com",
            "jobTitle": "Software Engineer"
        }

        return defaults.get(profile_mapping, "Default Value")

    def _validate_value(self, value: str, step: Dict[str, Any]) -> bool:
        """
        Validate value before filling.

        Args:
            value: The value to validate
            step: The step containing validation rules

        Returns:
            True if valid, False otherwise
        """
        # Basic validation: ensure value is not empty
        if not value or not value.strip():
            return False

        # Type-specific validation
        field_type = step.get("field_type", "textbox")

        if field_type == "email":
            return "@" in value and "." in value

        if field_type == "phone":
            # Allow various phone formats
            digits = "".join(c for c in value if c.isdigit())
            return len(digits) >= 10

        if field_type == "url" or field_type == "website":
            return value.startswith("http://") or value.startswith("https://") or "." in value

        # Default: valid if not empty
        return True

    def _format_phone(self, value: str) -> str:
        """
        Format phone number consistently.

        Args:
            value: Raw phone number

        Returns:
            Formatted phone number
        """
        # Extract digits
        digits = "".join(c for c in value if c.isdigit())

        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

        # Return original if can't format
        return value

    def _format_zip(self, value: str) -> str:
        """
        Format ZIP code consistently.

        Args:
            value: Raw ZIP code

        Returns:
            Formatted ZIP code
        """
        # Extract digits
        digits = "".join(c for c in value if c.isdigit())

        if len(digits) == 5:
            return digits
        elif len(digits) == 9:
            return f"{digits[:5]}-{digits[5:]}"

        return value

    def _format_ssn(self, value: str) -> str:
        """
        Format SSN consistently.

        Args:
            value: Raw SSN

        Returns:
            Formatted SSN
        """
        # Extract digits
        digits = "".join(c for c in value if c.isdigit())

        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"

        return value

    def _capture_error_screenshot(self, step: Dict[str, Any], step_index: int, context: ReplayContext) -> None:
        """
        Capture screenshot when field fill fails.

        Args:
            step: The step that failed
            step_index: Index of the failed step
            context: Current replay context with browser driver
        """
        try:
            if context.browser_driver:
                screenshot_name = f"error_step_{step_index}_{step.get('field_name', 'unknown')}"
                screenshot_name = screenshot_name.replace(" ", "_")
                context.browser_driver.save_screenshot(f"screenshots/{screenshot_name}.png")
                print(f"  📸 Error screenshot saved: {screenshot_name}.png")
        except Exception as e:
            print(f"  ⚠ Could not capture screenshot: {e}")

    def onError(self, step: Dict[str, Any], error: Exception) -> bool:
        """
        Handle step errors.

        Args:
            step: The step that failed
            error: The exception that occurred

        Returns:
            True to continue execution, False to abort
        """
        field_name = step.get("field_name", "Unknown Field")
        print(f"  [ERROR] Error in field '{field_name}': {error}")

        # Continue execution by default
        return self.config.get("continue_on_error", True)
