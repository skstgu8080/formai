#!/usr/bin/env python3
"""
Example: How to use ProfileDataExtension with ProfileReplayEngine

This demonstrates integrating the extension system into the replay engine.
"""
from tools.profile_replay_engine import ProfileReplayEngine
from tools.profile_data_extension import ProfileDataExtension
from tools.replay_extension import ExtensionManager


def example_replay_with_extension():
    """
    Example of using ProfileDataExtension with replay engine.

    Shows how to:
    1. Create extension manager
    2. Register profile data extension
    3. Configure extension behavior
    4. Hook into replay lifecycle
    """

    # Create replay engine
    engine = ProfileReplayEngine(use_stealth=True, headless=False)

    # Create extension manager
    extension_manager = ExtensionManager()

    # Create and configure profile data extension
    profile_extension = ProfileDataExtension(
        engine=engine,
        config={
            "screenshot_on_error": True,     # Capture screenshots on errors
            "continue_on_error": True,       # Don't stop on individual field failures
        },
        use_recorded_values=False  # Use profile data (not preview mode)
    )

    # Register extension
    extension_manager.register(profile_extension)

    # Example profile data
    profile_data = {
        "profileName": "John Doe",
        "data": {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@company.com",
            "phone": "5551234567",
            "company": "Acme Corp",
            "address1": "123 Business Ave",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94102"
        }
    }

    # Example recording data
    recording = {
        "id": "rec_123",
        "name": "Contact Form",
        "url": "https://example.com/contact",
        "steps": [
            {
                "field_name": "First Name",
                "field_selector": "#firstName",
                "field_type": "textbox",
                "profile_mapping": "firstName",
                "sample_value": "Test"
            },
            {
                "field_name": "Email",
                "field_selector": "#email",
                "field_type": "email",
                "profile_mapping": "email",
                "sample_value": "test@example.com"
            },
            {
                "field_name": "Phone",
                "field_selector": "#phone",
                "field_type": "phone",
                "profile_mapping": "phone",
                "sample_value": "555-1234"
            }
        ]
    }

    # Lifecycle hook: Before all steps
    extension_manager.beforeAllSteps(recording, profile_data)

    # Process each step
    for step_index, step in enumerate(recording["steps"]):

        # Lifecycle hook: Before each step
        extension_manager.beforeEachStep(step, step_index)

        # Transform step (inject profile data)
        transformed_step = extension_manager.transformStep(step, profile_data)

        print(f"\nOriginal value: {step.get('sample_value')}")
        print(f"Transformed value: {transformed_step.get('value_to_use')}")
        print(f"Value source: {transformed_step.get('value_source')}")

        # Simulate field fill result
        result = {
            "success": True,
            "value_used": transformed_step.get("value_to_use"),
            "execution_time_ms": 150,
            "error": None
        }

        # Lifecycle hook: After each step
        extension_manager.afterEachStep(step, step_index, result)

    # Lifecycle hook: After all steps
    results = [
        {"success": True, "field_name": "First Name"},
        {"success": True, "field_name": "Email"},
        {"success": True, "field_name": "Phone"}
    ]
    extension_manager.afterAllSteps(results)

    # Get extension statistics
    all_stats = extension_manager.getAllStats()
    print("\n\nExtension Statistics:")
    for ext_name, stats in all_stats.items():
        print(f"\n{ext_name}:")
        for key, value in stats.items():
            if key != "field_results":  # Skip detailed results for brevity
                print(f"  {key}: {value}")


def example_integration_into_replay_engine():
    """
    Example showing where to integrate extension manager in ProfileReplayEngine.

    This would be added to profile_replay_engine.py's replay_recording method.
    """

    print("\n" + "="*60)
    print("Integration Example:")
    print("="*60)
    print("""
    In profile_replay_engine.py, add:

    class ProfileReplayEngine:
        def __init__(self, ...):
            ...
            # Add extension manager
            self.extension_manager = ExtensionManager()

        def replay_recording(self, recording_id, profile_data, ...):
            # Before processing
            self.extension_manager.beforeAllSteps(recording, profile_data)

            # For each field
            for idx, field_mapping in enumerate(field_mappings):

                # Transform step
                field_mapping = self.extension_manager.transformStep(
                    field_mapping,
                    profile_data
                )

                # Before step
                self.extension_manager.beforeEachStep(field_mapping, idx)

                try:
                    # Execute step (existing fill logic)
                    result = self._fill_field(field_mapping, profile_data, progress)

                    # After step
                    self.extension_manager.afterEachStep(
                        field_mapping,
                        idx,
                        result
                    )
                except Exception as e:
                    # Handle error
                    should_continue = self.extension_manager.onError(
                        field_mapping,
                        e
                    )
                    if not should_continue:
                        break

            # After all steps
            self.extension_manager.afterAllSteps(field_results)
    """)


if __name__ == "__main__":
    print("="*60)
    print("ProfileDataExtension Usage Example")
    print("="*60)

    # Run the example
    example_replay_with_extension()

    # Show integration guide
    example_integration_into_replay_engine()
