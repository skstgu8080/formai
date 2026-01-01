# Recording System

> Learn from Chrome DevTools recordings to automate form filling

## Overview

The Recording System enables **"Learn Once, Replay Many"** - record a form fill once in Chrome, extract field mappings, and use them forever.

**Key File:** `tools/recording_trainer.py`

---

## How It Works

```
Chrome DevTools Recording
        ↓
   RecordingTrainer
        ↓
   Extract Mappings
        ↓
   Save to Database
        ↓
   Instant Replay
```

---

## Creating a Chrome Recording

1. Open Chrome DevTools (F12)
2. Go to **Recorder** tab
3. Click **Create new recording**
4. Fill the form manually
5. Stop recording
6. Export as JSON

---

## Recording Format

Chrome recordings contain steps:

```json
{
  "title": "Example Form",
  "steps": [
    {
      "type": "navigate",
      "url": "https://example.com/signup"
    },
    {
      "type": "change",
      "selectors": [
        ["#email"],
        ["aria/Email address"]
      ],
      "value": "test@example.com"
    },
    {
      "type": "click",
      "selectors": [
        ["#submit-btn"]
      ]
    }
  ]
}
```

---

## RecordingTrainer Class

**File:** `tools/recording_trainer.py:71-643`

### Key Methods

| Method | Purpose |
|--------|---------|
| `extract_mappings(recording)` | Parse recording, return field mappings |
| `extract_domain(recording)` | Get domain from recording URL |
| `extract_url(recording)` | Get URL from recording |
| `train_from_recording(recording, store)` | Parse + save to database |
| `analyze_field(selector, sb)` | Analyze field on live page |

### Usage

```python
from tools.recording_trainer import RecordingTrainer
from tools.field_mapping_store import FieldMappingStore

trainer = RecordingTrainer()
store = FieldMappingStore()

# Load recording
with open("recording.json") as f:
    recording = json.load(f)

# Train
result = trainer.train_from_recording(recording, store)
# Returns: {"success": True, "domain": "example.com", "fields_learned": 8}
```

---

## Field Mapping Extraction

The trainer looks for `change` events (field fills) and maps:

### From Aria Labels (Priority 1)

```python
ARIA_TO_PROFILE = {
    'first name': 'firstName',
    'email': 'email',
    'phone number': 'phone',
    'address': 'address',
    'city': 'city',
    'zip code': 'zip',
    ...
}
```

### From Selector Patterns (Priority 2)

```python
SELECTOR_PATTERNS = {
    r'first[-_]?name': 'firstName',
    r'email': 'email',
    r'phone': 'phone',
    r'address': 'address',
    r'city': 'city',
    r'zip': 'zip',
    ...
}
```

---

## Field Normalization

Handles variations in field names:

```python
normalize_profile_field("suburb/City")  # → "city"
normalize_profile_field("postalCode")   # → "zip"
normalize_profile_field("first_name")   # → "firstName"
```

**Normalizations:**
- `firstname`, `fname` → `firstName`
- `lastname`, `surname` → `lastName`
- `suburb`, `town` → `city`
- `postcode`, `postal` → `zip`
- `telephone`, `mobile` → `phone`

---

## Selector Priority

When choosing CSS selector from recording:

1. **ID selectors** (`#email`) - Most reliable
2. **Pierce selectors** (`pierce/#email`) - Shadow DOM
3. **CSS selectors** (`.form-input`) - Good
4. **XPath** (`xpath/...`) - Last resort

---

## Live Field Analysis

For enhanced mappings, analyze fields on live page:

```python
enhanced = trainer.analyze_mappings_live(mappings, url, headless=True)
```

Returns fill strategies:

| Strategy | When Used |
|----------|-----------|
| `direct_type` | Text inputs, email, password |
| `dropdown_select` | `<select>` elements |
| `custom_dropdown` | Button-based dropdowns |
| `js_date_input` | HTML5 date inputs |
| `char_by_char` | Phone inputs with masks |
| `checkbox_click` | Checkbox fields |
| `radio_click` | Radio buttons |

---

## Batch Training

Process all recordings in a directory:

```bash
python -m tools.recording_trainer batch
```

Or programmatically:

```python
from tools.recording_trainer import batch_train_recordings

results = batch_train_recordings(
    recordings_dir="sites/recordings",
    mappings_dir="field_mappings"
)

print(f"Trained {results['successful']} recordings")
print(f"Domains: {len(results['domains_trained'])}")
```

---

## Integration with Automation

When SeleniumBaseAgent fills a site:

```python
# Phase 3: DETECT
if store.has_mappings(domain):
    # Use trained mappings (instant!)
    mappings = store.get_mappings(domain)
else:
    # Fall back to AI analysis
    mappings = await analyze_form_with_ai(...)
```

**Result:** Trained sites fill 10x faster (no AI needed).

---

## API Endpoint

Import recordings via web UI:

```
POST /api/recordings/import-chrome
Content-Type: application/json

{
  "recording": { ... Chrome recording JSON ... }
}
```

Response:
```json
{
  "success": true,
  "domain": "example.com",
  "fields_learned": 12
}
```

---

## Storage

Mappings saved to SQLite:

```sql
-- domain_mappings table
{
  "domain": "example.com",
  "url": "https://example.com/signup",
  "mappings": [
    {"selector": "#email", "profile_field": "email"},
    {"selector": "#firstName", "profile_field": "firstName"}
  ]
}
```
