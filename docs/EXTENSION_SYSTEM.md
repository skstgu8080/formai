# Extension System for Profile Replay Engine

## Overview

The Profile Replay Engine now supports a powerful extension system that allows you to customize and extend replay behavior without modifying the core engine code. Extensions hook into the replay lifecycle at key points to add custom logic, transformations, validations, logging, and more.

## Architecture

### Core Components

1. **ReplayExtension** (`tools/replay_extension.py`)
   - Abstract base class for all extensions
   - Defines lifecycle hook methods
   - Examples: LoggingExtension, ScreenshotExtension

2. **ProfileDataExtension** (`tools/profile_data_extension.py`)
   - Built-in extension for profile data injection
   - Handles mapping profile fields to form fields
   - Provides value transformation and validation

3. **ReplayContext** (`tools/replay_extension.py`)
   - Context object passed to all hooks
   - Contains: profile_data, replay_stats, current_url, session_name, browser_driver
   - Allows extensions to access and modify shared state

4. **ProfileReplayEngine** (`tools/profile_replay_engine.py`)
   - Main replay engine with extension support
   - Registers and manages extensions
   - Calls extension hooks at appropriate points

## Lifecycle Hooks

Extensions can implement these methods to hook into the replay process:

### 1. beforeAllSteps(context: ReplayContext)
Called once before starting replay of all steps.

**Use cases:**
- Initialize extension state
- Validate prerequisites
- Set up logging or monitoring
- Configure browser settings
- Prepare external resources

**Example:**
```python
def beforeAllSteps(self, context: ReplayContext) -> None:
    print(f"Starting replay for profile: {context.profile_data.get('profileName')}")
    context.custom_data['start_time'] = time.time()
```

### 2. beforeEachStep(step, context)
Called before executing each individual step.

**Use cases:**
- Log step execution
- Take screenshots before actions
- Wait for dynamic content
- Validate page state
- Add delays or timing adjustments

**Example:**
```python
def beforeEachStep(self, step: Dict[str, Any], context: ReplayContext) -> None:
    field_name = step.get('field_name', 'Unknown')
    print(f"About to fill: {field_name}")
```

### 3. transformStep(step) → Dict[str, Any]
Transform a step before execution. Return the modified step dictionary.

**Use cases:**
- Modify field values dynamically
- Change selectors (e.g., switch from ARIA to CSS)
- Add or remove step properties
- Apply conditional logic

**Example:**
```python
def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
    # Convert email to lowercase
    if step.get('profile_mapping') == 'email':
        if 'value_to_use' in step:
            step['value_to_use'] = step['value_to_use'].lower()
    return step
```

### 4. shouldSkipStep(step, context) → bool
Determine whether to skip a step. Return True to skip, False to execute.

**Use cases:**
- Skip optional fields conditionally
- Avoid filling fields based on profile data
- Skip steps based on page state
- Implement conditional workflows

**Example:**
```python
def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
    # Skip address2 if profile doesn't have it
    if step.get('profile_mapping') == 'address2':
        profile_data = context.profile_data
        if not profile_data.get('address2'):
            return True
    return False
```

### 5. afterEachStep(step, result, context)
Called after executing each individual step.

**Use cases:**
- Process execution results
- Take screenshots after actions
- Verify field values were set correctly
- Log success/failure
- Collect metrics

**Example:**
```python
def afterEachStep(self, step: Dict[str, Any], result: Dict[str, Any], context: ReplayContext) -> None:
    if result.get('success'):
        print(f"[OK] {step['field_name']}: {result['execution_time_ms']:.0f}ms")
    else:
        print(f"[FAIL] {step['field_name']}: {result.get('error')}")
```

### 6. afterAllSteps(results: List[Dict[str, Any]])
Called once after all steps have completed.

**Use cases:**
- Generate summary reports
- Save logs or metrics
- Clean up resources
- Send notifications
- Export results

**Example:**
```python
def afterAllSteps(self, results: List[Dict[str, Any]]) -> None:
    success_count = sum(1 for r in results if r.get('success'))
    total_count = len(results)
    print(f"Replay complete: {success_count}/{total_count} successful")
```

## Usage Examples

### Basic Usage

```python
from tools.profile_replay_engine import ProfileReplayEngine
from tools.profile_data_extension import ProfileDataExtension

# Create replay engine
engine = ProfileReplayEngine(use_stealth=True, headless=False)

# Register ProfileDataExtension for profile data injection
profile_ext = ProfileDataExtension(use_recorded_values=False)
engine.register_extension(profile_ext)

# Load profile data
profile_data = {
    "profileName": "John Doe",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com"
}

# Replay with extensions
result = engine.replay_recording(
    recording_id="your-recording-id",
    profile_data=profile_data,
    session_name="example-replay"
)
```

### Creating Custom Extensions

```python
from tools.replay_extension import ReplayExtension, ReplayContext

class CustomValidationExtension(ReplayExtension):
    """Custom extension for email validation"""

    def transformStep(self, step: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure all emails are lowercase
        if 'email' in step.get('field_name', '').lower():
            if 'value_to_use' in step:
                step['value_to_use'] = step['value_to_use'].lower()
        return step

    def shouldSkipStep(self, step: Dict[str, Any], context: ReplayContext) -> bool:
        # Skip invalid emails
        if 'email' in step.get('field_name', '').lower():
            value = step.get('value_to_use', '')
            if value and '@' not in value:
                print(f"Skipping invalid email: {value}")
                return True
        return False

# Register custom extension
engine = ProfileReplayEngine()
engine.register_extension(CustomValidationExtension())
```

### Multiple Extensions

```python
from tools.replay_extension import LoggingExtension, ScreenshotExtension

# Create engine
engine = ProfileReplayEngine()

# Register multiple extensions
engine.register_extension(ProfileDataExtension(use_recorded_values=False))
engine.register_extension(LoggingExtension(verbose=True))
engine.register_extension(ScreenshotExtension(on_error=True))

# Extensions are called in registration order
```

## ProfileDataExtension Features

The built-in ProfileDataExtension provides:

### Profile Mapping
- Maps `profile_mapping` field to profile data
- Supports nested structures (e.g., `data.firstName`)
- Handles both flat and nested profile formats

### Fallback Values
1. Profile data (primary)
2. Sample values from recording (fallback)
3. Default values (last resort)

### Value Transformers
- Phone number formatting: `(555) 123-4567`
- ZIP code formatting: `12345` or `12345-6789`
- SSN formatting: `123-45-6789`

### Value Validation
- Email: Must contain `@` and `.`
- Phone: Must have at least 10 digits
- URL: Must start with `http://` or `https://`

### Statistics Tracking
- Fields processed
- Value sources (profile/sample/default)
- Validation failures
- Transform failures

## Best Practices

### 1. Extension Design
- Keep extensions focused on a single responsibility
- Use descriptive class names ending in "Extension"
- Document the purpose and use cases

### 2. Error Handling
- Always handle exceptions in lifecycle hooks
- Log errors but don't crash the replay
- Return appropriate values (False to skip, modified dict, etc.)

### 3. Performance
- Avoid expensive operations in hooks
- Use caching when appropriate
- Don't block the replay unnecessarily

### 4. Context Usage
- Use `context.custom_data` for extension-specific state
- Don't modify `context.replay_stats` directly (read-only)
- Access browser via `context.browser_driver`

### 5. Testing
- Test extensions independently
- Use mock contexts for unit tests
- Test extension combinations

## Extension API Reference

### ReplayContext

```python
class ReplayContext:
    profile_data: Dict[str, Any]      # User profile data
    session_name: str                  # Replay session name
    replay_stats: Dict[str, Any]       # Statistics (read-only)
    current_url: str                   # Current browser URL
    browser_driver: Any                # SeleniumBase driver
    custom_data: Dict[str, Any]        # Extension-specific data
```

### ProfileReplayEngine Methods

```python
# Register an extension
engine.register_extension(extension: ReplayExtension)

# Unregister an extension
engine.unregister_extension(extension: ReplayExtension)

# List registered extensions
extensions: List[ReplayExtension] = engine.extensions
```

## Troubleshooting

### Extension Not Called
- Check that extension is registered before calling `replay_recording()`
- Verify extension implements the hook methods correctly
- Check for exceptions in hook methods

### Transform Not Applied
- Ensure `transformStep()` returns the modified step
- Check that modifications are made to a copy of the step
- Verify transform logic is correct

### Steps Being Skipped
- Check `shouldSkipStep()` return value
- Multiple extensions: ANY returning True will skip
- Log skip decisions for debugging

## Migration Guide

### From Direct Engine Modification
If you were modifying the engine directly:

**Before:**
```python
# Modified _fill_field() in profile_replay_engine.py
```

**After:**
```python
class CustomExtension(ReplayExtension):
    def transformStep(self, step):
        # Your custom logic here
        return step

engine.register_extension(CustomExtension())
```

### From Callback-Based Hooks
If you were using progress callbacks:

**Before:**
```python
def custom_callback(update):
    # Handle update
    pass

engine.set_progress_callback(custom_callback)
```

**After:**
```python
class CallbackExtension(ReplayExtension):
    def afterEachStep(self, step, result, context):
        # Handle result
        pass

engine.register_extension(CallbackExtension())
```

## Examples

See:
- `examples/extension_usage_example.py` - Comprehensive usage examples
- `tests/test_extension_system.py` - Unit tests for extensions
- `tools/replay_extension.py` - Base classes and examples

## Future Enhancements

Potential future additions:
- Async hook support
- Extension dependencies
- Extension marketplace
- Hot-reload extensions
- Extension configuration UI
