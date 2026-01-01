# Multi-Step Forms

> Handle wizard-style registration flows

## Overview

The MultiStepFormManager handles registration wizards that span multiple pages/steps.

**Key File:** `tools/multistep_manager.py`

---

## How It Works

```
Step 1: Basic Info       Step 2: Contact         Step 3: Confirm
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ First Name      │     │ Email           │     │ Review Details  │
│ Last Name       │ ──► │ Phone           │ ──► │                 │
│ [Next]          │     │ [Next]          │     │ [Submit]        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

The manager:
1. Detects step indicators
2. Fills current step only
3. Clicks "Next" (not Submit)
4. Repeats until final step
5. Clicks "Submit" on final step

---

## MultiStepFormManager Class

**File:** `tools/multistep_manager.py:39-448`

```python
from tools.multistep_manager import MultiStepFormManager

manager = MultiStepFormManager()

# Detect current step
step_info = await manager.detect_steps(page)
print(f"Step {step_info.step_number} of {step_info.total_steps}")

# Fill fields, then advance
await manager.advance_step(page)

# On final step
if step_info.is_final_step:
    await manager.submit_final(page)
```

---

## Step Detection

### Method 1: Text Patterns

Looks for text like:
- "Step 1 of 3"
- "1/3"
- "Page 2 of 5"

```python
STEP_PATTERNS = [
    r'step\s*(\d+)\s*(?:of|/)\s*(\d+)',
    r'(\d+)\s*/\s*(\d+)',
    r'page\s*(\d+)\s*(?:of|/)\s*(\d+)',
]
```

### Method 2: Progress Indicators

Checks for:
- `[role="progressbar"]` with aria-valuenow/max
- `.step`, `.stepper-item` elements
- `[class*="wizard-step"]`

### Method 3: Active Step Classes

Looks for `.active` or `.current` on step elements.

---

## Button Detection

### Next Keywords

```python
NEXT_KEYWORDS = [
    'next', 'continue', 'proceed', 'forward',
    'siguiente', 'weiter', 'suivant'  # multilingual
]
```

### Submit Keywords

```python
SUBMIT_KEYWORDS = [
    'submit', 'finish', 'complete', 'register',
    'create account', 'confirm', 'done'
]
```

### Back Keywords (Skip)

```python
BACK_KEYWORDS = [
    'back', 'previous', 'prev', 'return'
]
```

---

## StepInfo Dataclass

```python
@dataclass
class StepInfo:
    step_number: int
    total_steps: Optional[int]
    step_title: Optional[str]
    fields_count: int
    url: str
    has_next_button: bool
    has_submit_button: bool
    is_final_step: bool
```

---

## Key Methods

| Method | Purpose |
|--------|---------|
| `detect_steps(page)` | Analyze current step |
| `is_step_complete(page)` | Check for validation errors |
| `find_next_button(page)` | Locate "Next" button |
| `find_submit_button(page)` | Locate "Submit" button |
| `advance_step(page)` | Click Next, wait for new step |
| `submit_final(page)` | Click final Submit |
| `get_status()` | Get current state |
| `reset()` | Clear state for new form |

---

## Final Step Detection

A step is considered final if:
1. `step_number >= total_steps`, OR
2. Has submit button but no next button

```python
def _is_final_step(self, info: StepInfo) -> bool:
    if info.total_steps and info.step_number >= info.total_steps:
        return True
    if info.has_submit_button and not info.has_next_button:
        return True
    return False
```

---

## Validation Check

Before advancing, check for errors:

```python
async def is_step_complete(self, page) -> bool:
    # Check for error elements
    errors = await page.query_selector_all('.error, .invalid')
    if any(await err.is_visible() for err in errors):
        return False

    # Check required fields are filled
    required = await page.query_selector_all('[required]')
    for field in required:
        if not await field.input_value():
            return False

    return True
```

---

## Integration with SeleniumBase Agent

**File:** `tools/seleniumbase_agent.py`

In Phase 6 (SUBMIT):

```python
# Phase 6.5: Multi-step handling
if self._is_multi_step_form(sb):
    manager = MultiStepFormManager()

    while not step_info.is_final_step:
        # Fill current step
        await self._fill_fields(sb, step_fields, profile)

        # Advance to next step
        success, msg = await manager.advance_step(page)
        if not success:
            break

        # Detect new step
        step_info = await manager.detect_steps(page)

    # Submit final step
    await manager.submit_final(page)
```

---

## Status Tracking

```python
status = manager.get_status()
# Returns:
{
    "current_step": 2,
    "total_steps": 3,
    "steps_completed": 1,
    "step_history": [
        {"step": 1, "fields": 4, "url": "..."},
        {"step": 2, "fields": 6, "url": "..."}
    ],
    "is_multi_step": True
}
```

---

## URL Changes

The manager tracks URL changes between steps:

```python
self.step_urls: List[str] = []

# After advancing
if url_changed:
    self.step_urls.append(new_url)
```

---

## Error Handling

```python
success, message = await manager.advance_step(page)

if not success:
    if "validation" in message.lower():
        # Fill missing required fields
        pass
    elif "no next button" in message.lower():
        # Maybe already on final step
        pass
```

---

## Common Patterns

### Progress Bar with Numbers

```html
<div class="progress">
  <div class="step active">1</div>
  <div class="step">2</div>
  <div class="step">3</div>
</div>
```

### Text-Based Indicator

```html
<p class="step-info">Step 2 of 4</p>
```

### Button States

```html
<!-- Step 1-2 -->
<button type="button">Next</button>

<!-- Final step -->
<button type="submit">Create Account</button>
```
