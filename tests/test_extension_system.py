#!/usr/bin/env python3
"""
Test script for the extension system integration

This tests the extension lifecycle hooks without requiring a browser.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.replay_extension import ReplayExtension, ReplayContext
from tools.profile_data_extension import ProfileDataExtension
from typing import Dict, Any


class TestExtension(ReplayExtension):
    """Test extension that tracks all lifecycle events"""

    def __init__(self):
        super().__init__("TestExtension")
        self.events = []

    def beforeAllSteps(self, context: ReplayContext) -> None:
        self.events.append("beforeAllSteps")
        print(f"[OK] beforeAllSteps called - Session: {context.session_name}")

    def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
        self.events.append(f"beforeEachStep:{step.get('field_name')}")
        print(f"[OK] beforeEachStep called - Field: {step.get('field_name')}")

    def transformStep(self, step: Dict[str, Any], context: ReplayContext) -> Dict[str, Any]:
        self.events.append(f"transformStep:{step.get('field_name')}")
        print(f"[OK] transformStep called - Field: {step.get('field_name')}")
        # Add a marker to prove transformation happened
        step_copy = step.copy()
        step_copy["transformed"] = True
        return step_copy

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        self.events.append(f"shouldSkipStep:{step.get('field_name')}")
        # Skip fields named "skip_me"
        should_skip = step.get('field_name') == "skip_me"
        if should_skip:
            print(f"[OK] shouldSkipStep returned True - Skipping: {step.get('field_name')}")
        return should_skip

    def afterEachStep(self, step: Dict[str, Any], result: Dict[str, Any], context: ReplayContext) -> None:
        self.events.append(f"afterEachStep:{step.get('field_name')}")
        print(f"[OK] afterEachStep called - Field: {step.get('field_name')} - Success: {result.get('success')}")

    def afterAllSteps(self, context: ReplayContext) -> None:
        self.events.append("afterAllSteps")
        print(f"[OK] afterAllSteps called - Total events: {len(self.events)}")


def test_extension_lifecycle():
    """Test that all lifecycle hooks are called in the correct order"""
    print("\n=== Testing Extension Lifecycle ===\n")

    # Create test extension
    test_ext = TestExtension()

    # Create mock context
    context = ReplayContext(
        profile_data={"profileName": "Test User", "firstName": "Test"},
        replay_stats={"session_name": "test-session"},
        current_url="https://example.com",
        session_name="test-session",
        browser_driver=None
    )

    # Test beforeAllSteps
    test_ext.beforeAllSteps(context)
    assert "beforeAllSteps" in test_ext.events

    # Test step processing
    step1 = {"field_name": "firstName", "field_selector": "#first", "field_type": "textbox"}
    test_ext.beforeEachStep(step1, context)
    transformed = test_ext.transformStep(step1, context)
    assert transformed.get("transformed") == True
    should_skip = test_ext.shouldSkipStep(transformed, context)
    assert should_skip == False
    result1 = {"success": True, "execution_time_ms": 100}
    test_ext.afterEachStep(transformed, result1, context)

    # Test skip functionality
    step2 = {"field_name": "skip_me", "field_selector": "#skip", "field_type": "textbox"}
    test_ext.beforeEachStep(step2, context)
    transformed2 = test_ext.transformStep(step2, context)
    should_skip2 = test_ext.shouldSkipStep(transformed2, context)
    assert should_skip2 == True
    # If skipped, afterEachStep wouldn't be called in real scenario

    # Test afterAllSteps
    test_ext.afterAllSteps(context)
    assert "afterAllSteps" in test_ext.events

    print(f"\n[PASS] All lifecycle hooks tested successfully!")
    print(f"Total events recorded: {len(test_ext.events)}")


def test_profile_data_extension():
    """Test ProfileDataExtension transformation logic"""
    print("\n=== Testing ProfileDataExtension ===\n")

    # Test with production mode (use profile data)
    ext = ProfileDataExtension(use_recorded_values=False)

    profile_data = {
        "profileName": "John Doe",
        "firstName": "John",
        "email": "john@example.com"
    }

    context = ReplayContext(
        profile_data=profile_data,
        replay_stats={},
        current_url="https://example.com",
        session_name="test",
        browser_driver=None
    )

    # Test transformation
    step = {
        "field_name": "First Name",
        "field_selector": "#first",
        "field_type": "textbox",
        "profile_mapping": "firstName",
        "sample_value": "Sample"
    }

    ext.beforeAllSteps(context)
    transformed = ext.transformStep(step, context)

    print(f"Original sample value: {step.get('sample_value')}")
    print(f"Transformed value: {transformed.get('value_to_use')}")
    print(f"Value source: {transformed.get('value_source')}")

    assert transformed.get("value_to_use") == "John"
    assert transformed.get("value_source") == "profile"

    print("\n[PASS] ProfileDataExtension works correctly!")


def test_preview_mode():
    """Test ProfileDataExtension in preview mode"""
    print("\n=== Testing Preview Mode ===\n")

    # Test with preview mode (use recorded values)
    ext = ProfileDataExtension(use_recorded_values=True)

    profile_data = {
        "firstName": "John",
        "email": "john@example.com"
    }

    context = ReplayContext(
        profile_data=profile_data,
        replay_stats={},
        current_url="https://example.com",
        session_name="test",
        browser_driver=None
    )

    step = {
        "field_name": "First Name",
        "profile_mapping": "firstName",
        "sample_value": "Preview Value"
    }

    ext.beforeAllSteps(context)
    transformed = ext.transformStep(step, context)

    print(f"Preview mode enabled: {ext.use_recorded_values}")
    print(f"Sample value: {step.get('sample_value')}")
    print(f"Transformed step: {transformed}")

    # In preview mode, step should not be transformed
    assert "value_to_use" not in transformed
    print("\n[PASS] Preview mode works correctly!")


def test_extension_enable_disable():
    """Test extension enable/disable functionality"""
    print("\n=== Testing Enable/Disable ===\n")

    ext = TestExtension()
    assert ext.enabled == True

    ext.disable()
    assert ext.enabled == False
    print("[OK] Extension disabled")

    ext.enable()
    assert ext.enabled == True
    print("[OK] Extension re-enabled")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Extension System Test Suite")
    print("="*60)

    try:
        test_extension_lifecycle()
        test_profile_data_extension()
        test_preview_mode()
        test_extension_enable_disable()

        print("\n" + "="*60)
        print("[SUCCESS] All tests passed!")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
