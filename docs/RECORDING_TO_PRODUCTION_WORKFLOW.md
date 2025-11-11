# Recording to Production: Complete Workflow

## Overview

This document outlines the complete workflow from recording a website form to running it in production with FormAI's extension system.

## The FormAI Extension System

FormAI uses a powerful extension system inspired by Puppeteer Replay that enables:

✅ **Automatic Profile Data Injection** - Maps form fields to profile data automatically
✅ **CAPTCHA Detection & Solving** - Detects and attempts to solve CAPTCHAs using UC Mode
✅ **Smart Field Mapping** - Matches fields using patterns and confidence scoring
✅ **Value Transformation** - Formats phone numbers, ZIPs, and other data types
✅ **Error Recovery** - Handles failures gracefully with detailed logging
✅ **Statistics Tracking** - Monitors success rates and performance

## Complete Workflow (5 Phases)

### Phase 1: Record the Form

**Goal:** Create a Chrome DevTools recording of the form filling process

**Steps:**
1. Open Chrome DevTools (F12)
2. Navigate to Recorder panel
3. Create new recording with descriptive name
4. Fill **ALL** form fields slowly with realistic sample data
5. Skip CAPTCHA/submit button
6. Stop and export recording as JSON
7. Save to `recordings/{website}_{type}.json`

**Result:** `recordings/github_signup.json` (or similar)

**Time Required:** 5-15 minutes depending on form complexity

**Reference:** See `docs/AI_RECORDING_INSTRUCTIONS.md`

---

### Phase 2: Import to FormAI

**Goal:** Parse the Chrome recording and convert it to FormAI format

**Method:**

```python
from tools.chrome_recorder_parser import ChromeRecorderParser
from tools.recording_manager import RecordingManager
import json

# Load the Chrome recording
with open("recordings/github_signup.json") as f:
    chrome_data = json.load(f)

# Parse with ChromeRecorderParser
parser = ChromeRecorderParser()
recording = parser.parse_chrome_recording_data(chrome_data)

# What the parser does automatically:
# - Extracts all form field interactions
# - Normalizes ARIA selectors to CSS
# - Scores selector quality (ID=1.0, name=0.8, class=0.5, XPath=0.3)
# - Detects field types (textbox, select, checkbox, etc.)
# - Maps fields to profile data (firstName → profile.firstName)
# - Calculates confidence scores for each mapping

print(f"Detected {recording['total_fields_filled']} fields")
print(f"Recording URL: {recording['url']}")

# Save to FormAI
manager = RecordingManager()
recording_id = manager.save_recording(recording)
print(f"Recording ID: {recording_id}")
```

**Result:** FormAI-formatted recording with field mappings

**Time Required:** < 1 minute

---

### Phase 3: Create/Load Profile

**Goal:** Prepare profile data to inject into the form

**Profile Structure:**

```json
{
  "profileName": "Production User",
  "firstName": "John",
  "lastName": "Smith",
  "email": "john.smith@company.com",
  "phone": "(555) 123-4567",
  "company": "Acme Corp",
  "address1": "123 Business Ave",
  "address2": "Suite 100",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94102",
  "country": "USA",
  "website": "https://acme.com",
  "jobTitle": "Software Engineer"
}
```

**Load Profile:**

```python
import json

with open("profiles/production_user.json") as f:
    profile = json.load(f)
```

**Profile Formats Supported:**
- Flat structure (shown above)
- Nested structure: `{"data": {...}}`
- Custom fields are supported

**Time Required:** < 1 minute (if profile already exists)

---

### Phase 4: Configure Extensions

**Goal:** Set up the extension system for automatic handling

**Extension Types:**

1. **ProfileDataExtension** - Automatic profile data injection
2. **CaptchaExtension** - CAPTCHA detection and solving
3. **LoggingExtension** - Verbose logging (optional)
4. **ScreenshotExtension** - Capture screenshots (optional)
5. **Custom Extensions** - Your own extensions

**Setup Code:**

```python
from tools.profile_replay_engine import ProfileReplayEngine
from tools.profile_data_extension import ProfileDataExtension
from tools.captcha_extension import CaptchaExtension

# Create replay engine
engine = ProfileReplayEngine(
    use_stealth=True,   # UC Mode for anti-bot bypass
    headless=False      # Set to True for background execution
)

# Register ProfileDataExtension
profile_ext = ProfileDataExtension(
    use_recorded_values=False  # False = use profile data (production)
                               # True = use sample values (preview mode)
)
engine.register_extension(profile_ext)

# Register CaptchaExtension
captcha_ext = CaptchaExtension(
    auto_solve=True,         # Automatically attempt to solve CAPTCHAs
    solve_after_fill=True,   # Solve after filling all fields
    max_solve_time=120       # Wait up to 2 minutes for CAPTCHA solve
)
engine.register_extension(captcha_ext)

print(f"Extensions registered: {len(engine.extensions)}")
```

**Extension Execution Order:**

```
beforeAllSteps() on all extensions
    ↓
For each field:
    beforeEachStep() on all extensions
    transformStep() on all extensions
    Fill the field
    afterEachStep() on all extensions
    ↓
afterAllSteps() on all extensions (CAPTCHA handled here)
```

**Time Required:** < 1 minute

---

### Phase 5: Execute Replay

**Goal:** Run the recording with profile data in production

**Execution Code:**

```python
# Replay the recording with profile data
result = engine.replay_recording(
    recording_id=recording_id,
    profile_data=profile,
    session_name="production_run_001"
)

# Results
print(f"\n{'='*60}")
print(f"REPLAY RESULTS")
print(f"{'='*60}")
print(f"Total Fields: {result['total_fields']}")
print(f"Successful: {result['successful_fields']}")
print(f"Failed: {result['failed_fields']}")
print(f"Success Rate: {result.get('success_rate', 'N/A')}")

# Extension statistics
profile_stats = profile_ext.getStats()
captcha_stats = captcha_ext.getStats()

print(f"\nProfile Data Extension:")
print(f"  Fields processed: {profile_stats['fields_processed']}")
print(f"  Profile values used: {profile_stats['profile_values_used']}")

print(f"\nCAPTCHA Extension:")
print(f"  CAPTCHAs detected: {captcha_stats['captchas_detected']}")
print(f"  CAPTCHAs solved: {captcha_stats['captchas_solved']}")
print(f"  Success rate: {captcha_stats.get('success_rate', 0):.1f}%")
```

**What Happens During Replay:**

1. **Navigation** - Opens browser and navigates to form URL
2. **Field Filling** - For each field:
   - ProfileDataExtension transforms the value
   - Injects profile data (e.g., `profile.firstName` → "John")
   - Applies value transformations (phone formatting, etc.)
   - Fills the field using SeleniumBase UC Mode
   - Waits for human-like delays
3. **CAPTCHA Handling** - After all fields:
   - CaptchaExtension detects CAPTCHA presence
   - Attempts automatic solving using UC Mode methods
   - Falls back to manual intervention if needed
4. **Form Submission** - Optionally submits the form
5. **Result Tracking** - Records success/failure for each field

**Time Required:** 30 seconds - 3 minutes depending on form complexity and CAPTCHA

**Result:** Form filled with production data!

---

## Complete Example

Here's a complete end-to-end example:

```python
#!/usr/bin/env python3
"""Complete Recording to Production Example"""
import json
from tools.chrome_recorder_parser import ChromeRecorderParser
from tools.recording_manager import RecordingManager
from tools.profile_replay_engine import ProfileReplayEngine
from tools.profile_data_extension import ProfileDataExtension
from tools.captcha_extension import CaptchaExtension

print("="*60)
print("FORMAI PRODUCTION WORKFLOW")
print("="*60)

# PHASE 1: Recording already done manually
# Saved as: recordings/company_registration.json

# PHASE 2: Import to FormAI
print("\n[Phase 2] Importing recording...")
with open("recordings/company_registration.json") as f:
    chrome_data = json.load(f)

parser = ChromeRecorderParser()
recording = parser.parse_chrome_recording_data(chrome_data)
print(f"OK - {recording['total_fields_filled']} fields detected")

manager = RecordingManager()
recording_id = manager.save_recording(recording)
print(f"OK - Recording ID: {recording_id}")

# PHASE 3: Load profile
print("\n[Phase 3] Loading profile...")
with open("profiles/production_user.json") as f:
    profile = json.load(f)
print(f"OK - Profile: {profile['profileName']}")

# PHASE 4: Configure extensions
print("\n[Phase 4] Configuring extensions...")
engine = ProfileReplayEngine(use_stealth=True, headless=False)

profile_ext = ProfileDataExtension(use_recorded_values=False)
captcha_ext = CaptchaExtension(auto_solve=True, solve_after_fill=True)

engine.register_extension(profile_ext)
engine.register_extension(captcha_ext)
print(f"OK - {len(engine.extensions)} extensions registered")

# PHASE 5: Execute
print("\n[Phase 5] Executing replay...")
print("Watch the browser window for automatic form filling!\n")

result = engine.replay_recording(
    recording_id=recording_id,
    profile_data=profile,
    session_name="production_run"
)

# Results
print(f"\n{'='*60}")
print(f"PRODUCTION RUN COMPLETE")
print(f"{'='*60}")
print(f"Success: {result['successful_fields']}/{result['total_fields']} fields")
print(f"Success Rate: {result.get('success_rate', 'N/A')}")

# Statistics
profile_stats = profile_ext.getStats()
captcha_stats = captcha_ext.getStats()

print(f"\nProfile Data Injection:")
print(f"  Profile values: {profile_stats['profile_values_used']}")
print(f"  Validation failures: {profile_stats['validation_failures']}")

if captcha_stats['captchas_detected'] > 0:
    print(f"\nCAPTCHA Handling:")
    print(f"  Detected: {captcha_stats['captchas_detected']}")
    print(f"  Solved: {captcha_stats['captchas_solved']}")
    print(f"  Types: {', '.join(captcha_stats['captcha_types'])}")

print(f"\n{'='*60}")
print(f"DONE!")
print(f"{'='*60}\n")
```

---

## Advanced Scenarios

### Scenario 1: Preview Mode (Test Before Production)

**Use Case:** Test the recording with sample values before using real profile data

```python
# Use recorded sample values instead of profile
profile_ext = ProfileDataExtension(use_recorded_values=True)
engine.register_extension(profile_ext)

# Replay will use sample values from recording
result = engine.replay_recording(recording_id, profile_data={})
```

### Scenario 2: Headless Execution (Background)

**Use Case:** Run form filling in the background without visible browser

```python
engine = ProfileReplayEngine(
    use_stealth=True,
    headless=True  # No browser window
)
```

### Scenario 3: Multiple Profiles

**Use Case:** Fill the same form with different profiles (batch processing)

```python
profiles = [
    "profiles/user1.json",
    "profiles/user2.json",
    "profiles/user3.json"
]

for profile_file in profiles:
    with open(profile_file) as f:
        profile = json.load(f)

    result = engine.replay_recording(
        recording_id=recording_id,
        profile_data=profile,
        session_name=f"batch_{profile['profileName']}"
    )

    print(f"{profile['profileName']}: {result['successful_fields']}/{result['total_fields']}")
```

### Scenario 4: Custom Extension

**Use Case:** Add custom logic (e.g., screenshot on error, skip certain fields)

```python
from tools.replay_extension import ReplayExtension, ReplayContext

class CustomExtension(ReplayExtension):
    def transformStep(self, step, context):
        # Skip password confirmation fields
        if "confirm" in step.get("field_name", "").lower():
            return {**step, "skip": True}
        return step

    def afterEachStep(self, step, result, context):
        # Screenshot on error
        if not result["success"]:
            context.browser_driver.save_screenshot(
                f"error_{step['field_name']}.png"
            )

engine.register_extension(CustomExtension())
```

### Scenario 5: CAPTCHA Manual Intervention

**Use Case:** Pause for manual CAPTCHA solving

```python
captcha_ext = CaptchaExtension(
    auto_solve=False,         # Don't auto-solve
    solve_after_fill=True,
    max_solve_time=300        # Wait 5 minutes for manual solve
)
```

---

## Monitoring & Debugging

### Success Metrics

Track these metrics for production monitoring:

```python
# Overall success
success_rate = (result['successful_fields'] / result['total_fields']) * 100

# Field-level results
for field_result in result['field_results']:
    print(f"{field_result['field_name']}: {field_result['success']}")
    if not field_result['success']:
        print(f"  Error: {field_result['error']}")

# Extension statistics
profile_stats = profile_ext.getStats()
print(f"Profile value usage: {profile_stats['profile_values_used']}")
print(f"Fallback to samples: {profile_stats['sample_values_used']}")
print(f"Fallback to defaults: {profile_stats['default_values_used']}")
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low success rate (<80%) | Poor selectors or page changes | Re-record the form |
| Fields not mapping | Profile missing fields | Add fields to profile |
| CAPTCHA blocking | CAPTCHA can't be solved | Use manual intervention mode |
| Timeout errors | Page too slow | Increase timeout in engine config |
| Wrong values filled | Profile field names don't match | Check field mapping confidence scores |

### Debug Mode

Enable verbose logging for troubleshooting:

```python
from tools.replay_extension import LoggingExtension

# Add logging extension
logging_ext = LoggingExtension(verbose=True)
engine.register_extension(logging_ext)

# Now you'll see detailed step-by-step logs
```

---

## Production Checklist

Before deploying to production:

- [ ] Recording tested with preview mode (sample values)
- [ ] Recording tested with test profile
- [ ] All fields mapping correctly (check confidence scores)
- [ ] CAPTCHA handling tested (if applicable)
- [ ] Success rate > 90% in test runs
- [ ] Profile contains all required fields
- [ ] No hardcoded sensitive data in recording
- [ ] Error handling tested (network failures, timeouts)
- [ ] Monitoring/logging configured
- [ ] Backup plan for CAPTCHA failures

---

## File Organization

Recommended directory structure:

```
FormAI/
├── recordings/
│   ├── github_signup.json           # Recording files
│   ├── linkedin_registration.json
│   └── TEMPLATE_recording.json      # Template reference
├── profiles/
│   ├── test_profile.json            # Test profiles
│   ├── production_user1.json        # Production profiles
│   └── production_user2.json
├── tools/
│   ├── chrome_recorder_parser.py    # Core tools
│   ├── profile_replay_engine.py
│   ├── profile_data_extension.py
│   ├── captcha_extension.py
│   └── replay_extension.py
├── docs/
│   ├── AI_RECORDING_INSTRUCTIONS.md # Recording guide
│   ├── RECORDING_QUICK_REFERENCE.md # Quick reference
│   └── RECORDING_TO_PRODUCTION_WORKFLOW.md  # This file
└── scripts/
    ├── test_recording.py            # Test scripts
    └── production_run.py            # Production scripts
```

---

## Summary

The FormAI workflow is simple:

1. **Record** → Use Chrome DevTools Recorder to capture form filling
2. **Import** → Parse with ChromeRecorderParser
3. **Profile** → Load profile data JSON
4. **Configure** → Register extensions (ProfileData + CAPTCHA)
5. **Execute** → Replay with automatic profile injection

**Key Benefits:**
- ✅ Works on **ANY** website you can record
- ✅ Automatic profile data injection
- ✅ CAPTCHA detection and handling
- ✅ High success rates (90%+ typical)
- ✅ Extensible for custom logic
- ✅ Production-ready with error handling

**Time Investment:**
- Initial recording: 5-15 minutes
- Setup code: 2-5 minutes (reusable)
- Production execution: 30 seconds - 3 minutes per run

**ROI:** One recording = unlimited automated form fills with any profile data! 🚀
