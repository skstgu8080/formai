# Field Mapping System

> How FormAI extracts profile data and maps it to form fields

## Overview

FormAI uses a **three-layer** field detection system:
1. **Saved Mappings** - Previously learned (instant)
2. **AI Analysis** - Ollama analyzes form HTML (3-5 sec)
3. **Pattern Matching** - Fallback dictionary (instant)

---

## Profile Structure

### Database Schema (`database/db.py:30-51`)

```sql
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    name TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    password TEXT,
    birthdate TEXT,
    gender TEXT,
    address1 TEXT,
    address2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    company TEXT,
    data JSON,  -- Extra fields as JSON
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Supported Profile Fields

**Core Fields (columns):**
- `email`, `phone`, `password`, `gender`
- `firstName`, `lastName` (stored as `first_name`, `last_name`)
- `address1`, `address2`, `city`, `state`, `zip`, `country`
- `company`, `birthdate`, `name`

**Extended Fields (JSON blob):**
- Any custom fields stored in `data` column

---

## Profile Normalization

**File:** `tools/seleniumbase_agent.py:2111-2201`

The `_normalize_profile()` function converts any profile format into a flat, usable structure:

### Input → Output Example

**Input (nested):**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "personal": { "phone": "555-123-4567" },
  "address": { "city": "Austin", "state": "TX" }
}
```

**Output (flat + derived):**
```python
{
  "firstName": "John",
  "lastName": "Doe",
  "name": "John Doe",           # Derived
  "phone": "5551234567",        # Digits only
  "phone_raw": "5551234567",
  "city": "Austin",
  "state": "TX",
  "country": "United States",   # Default
  "password": "SecurePass123!", # Default
  "title": "Mr",                # Default
  "dob": "1990-01-15",          # Default
  "dob_year": "1990",           # Split
  "dob_month": "01",
  "dob_day": "15",
  "dob_year_int": 1990,         # Integer versions
  "dob_month_int": 1,
  "dob_day_int": 15
}
```

### Normalization Steps

1. **Flatten nested dicts** - `address.city` → `city`
2. **Derive full name** - `firstName` + `lastName` → `name`
3. **Set defaults** - password, title, dob, address, etc.
4. **Normalize phone** - Remove dashes/spaces, extract digits
5. **Split DOB** - Parse `YYYY-MM-DD` into components

---

## Pattern Dictionary

**File:** `tools/seleniumbase_agent.py:220-241`

```python
LABEL_PATTERNS = {
    # Email
    'email': ['email', 'e-mail', 'emailaddress', 'mail'],

    # Names
    'firstName': ['firstname', 'first name', 'fname', 'givenname'],
    'lastName': ['lastname', 'surname', 'familyname', 'lname'],
    'name': ['full name', 'fullname', 'your name'],

    # Password
    'password': ['password', 'passwd', 'pwd', 'newpassword'],

    # Phone
    'phone': ['phone', 'mobile', 'telephone', 'tel', 'cell'],

    # Address
    'address': ['address', 'street', 'address1', 'streetaddress'],
    'address2': ['address2', 'apt', 'suite', 'unit', 'apartment'],

    # Location
    'city': ['city', 'town', 'suburb', 'locality'],
    'state': ['state', 'province', 'region', 'county'],
    'zip': ['zip', 'zipcode', 'postal', 'postcode'],
    'country': ['country', 'nation', 'countrycode'],

    # Business
    'company': ['company', 'organization', 'business'],

    # Other
    'website': ['website', 'url', 'homepage'],
    'username': ['username', 'user', 'userid', 'login'],
    'dob': ['dob', 'dateofbirth', 'birthday', 'birthdate'],
    'title': ['title', 'salutation', 'prefix'],
}
```

### Special Patterns

**File:** `tools/seleniumbase_agent.py:243-261`

```python
# Confirm password fields
CONFIRM_PASSWORD_PATTERNS = [
    'confirm', 'verify', 'retype', 're-enter', 'repeat',
    'confirmpassword', 'password2', 'pwd2'
]

# Confirm email fields
CONFIRM_EMAIL_PATTERNS = [
    'confirm email', 'verify email', 'emailconfirm', 'email2'
]

# Split DOB detection
DOB_DAY_PATTERNS = ['_day', 'birth_day', 'dob_day']
DOB_MONTH_PATTERNS = ['_month', 'birthmonth', 'dob_month']
DOB_YEAR_PATTERNS = ['_year', 'birthyear', 'dob_year']

# Title/Salutation
TITLE_PATTERNS = ['title', 'salutation', 'prefix', 'honorific']
```

---

## Priority Matching Algorithm

**File:** `tools/seleniumbase_agent.py:1407-1449`

Fields are matched in **strict priority order**:

```
PRIORITY 1: Label Text (most reliable)
    ↓ no match
PRIORITY 2: Placeholder Text
    ↓ no match
PRIORITY 3: Other Attributes (name, id, aria-label, autocomplete)
```

### Why This Order?

1. **Label** - Visible text users see (99% accurate)
2. **Placeholder** - Hints like "Enter your email"
3. **Attributes** - Can be misleading (`name="user_input_1"`)

### Matching Code

```python
matched_key = None

# Priority 1: Check LABEL
if label:
    for profile_key, patterns in LABEL_PATTERNS.items():
        for pattern in patterns:
            if pattern in label.lower():
                matched_key = profile_key
                break

# Priority 2: Check PLACEHOLDER
if not matched_key and placeholder:
    for profile_key, patterns in LABEL_PATTERNS.items():
        for pattern in patterns:
            if pattern in placeholder.lower():
                matched_key = profile_key
                break

# Priority 3: Check OTHER ATTRIBUTES
if not matched_key:
    other_text = f"{name} {id} {aria_label} {autocomplete}".lower()
    for profile_key, patterns in LABEL_PATTERNS.items():
        for pattern in patterns:
            if pattern in other_text:
                matched_key = profile_key
                break
```

---

## Special Field Handling

### Dropdowns (Country/State)

**File:** `tools/seleniumbase_agent.py:1168-1217`

```python
if field_type == 'select' and 'country' in all_text:
    country_value = profile.get('country', 'United States')

    # Strategy 1: Exact text match
    sb.select_option_by_text(selector, country_value)

    # Strategy 2: Value attribute (e.g., "US")
    sb.select_option_by_value(selector, country_value)

    # Strategy 3: Fuzzy match
    options = sb.get_select_options(selector)
    for opt in options:
        if country_value.lower() in opt.lower():
            sb.select_option_by_text(selector, opt)
            break
```

### Checkboxes (Terms/Privacy)

**File:** `tools/seleniumbase_agent.py:1219-1295`

```python
if field_type == 'checkbox':
    # Required patterns (check these)
    required = ['terms', 'agree', 'accept', 'privacy', 'consent', 'gdpr']

    # Skip patterns (don't check these)
    skip = ['newsletter', 'subscribe', 'mailinglist']

    if any(p in all_text for p in required):
        if not elem.is_selected():
            sb.click(selector)  # Check it
```

### Password Confirmation

**File:** `tools/seleniumbase_agent.py:1296-1314`

```python
if any(p in all_text for p in CONFIRM_PASSWORD_PATTERNS):
    # Use same password value
    sb.type(selector, profile['password'])
```

### Split DOB Fields

**File:** `tools/seleniumbase_agent.py:1316-1379`

```python
# Detect which DOB component
if '_day' in field_id:
    value = profile['dob_day_int']  # 15
elif '_month' in field_id:
    value = profile['dob_month_int']  # 6
elif '_year' in field_id:
    value = profile['dob_year_int']  # 1990

# Fill dropdown with multiple formats
for fmt in [str(value), str(value).zfill(2)]:
    try:
        sb.select_option_by_value(selector, fmt)
        break
    except:
        continue
```

### Title/Salutation

**File:** `tools/seleniumbase_agent.py:1381-1405`

```python
if 'title' in all_text and tag == 'select':
    title = profile.get('title', 'Mr')

    # Try formats: "Mr", "MR", "Mr.", "mr"
    for fmt in [title, title.upper(), f"{title}.", title.lower()]:
        try:
            sb.select_option_by_text(selector, fmt)
            break
        except:
            continue
```

---

## AI Analysis (Ollama)

**File:** `tools/seleniumbase_agent.py:78-103`

When pattern matching isn't enough, Ollama analyzes the form:

### Prompt Template

```python
AI_FIELD_ANALYSIS_PROMPT = """Analyze this form and return field mappings.

FORM HTML:
{form_html}

PROFILE FIELDS AVAILABLE:
{profile_fields}

Return JSON array:
[
  {"selector": "#email", "profile_field": "email", "confidence": 0.95},
  {"selector": "#firstName", "profile_field": "firstName", "confidence": 0.9}
]

Rules:
1. Use CSS selectors (prefer #id)
2. Map to exact profile field names
3. Include confidence 0.0-1.0
4. Set type: text, select, checkbox, password
"""
```

### Response Parsing

```python
response = await ollama.generate(prompt)
content = response["response"]

# Extract JSON array
start = content.find('[')
end = content.rfind(']') + 1
mappings = json.loads(content[start:end])
```

---

## Learn & Replay System

**File:** `tools/field_mapping_store.py:60-103`

### Save Mappings (After Successful Fill)

```python
store.save_mappings(
    domain="amazon.com",
    mappings=[
        {"selector": "#ap_email", "profile_field": "email"},
        {"selector": "#ap_password", "profile_field": "password"}
    ]
)
```

### Load Mappings (On Revisit)

```python
if store.has_mappings("amazon.com"):
    mappings = store.get_mappings("amazon.com")
    # Use directly - skip AI analysis!
```

### Database Table

```sql
CREATE TABLE domain_mappings (
    domain TEXT PRIMARY KEY,
    url TEXT,
    mappings JSON NOT NULL,
    fields_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Field Name Normalization

**File:** `tools/seleniumbase_agent.py:355-452`

Handles non-standard field names from AI:

```python
FIELD_NORMALIZATIONS = {
    'firstname': 'firstName',
    'lastname': 'lastName',
    'suburb': 'city',        # Australian
    'postalcode': 'zip',
    'postcode': 'zip',
    'phonenumber': 'phone',
}

def normalize_profile_field(field_name):
    lower = field_name.lower().replace(' ', '')
    return FIELD_NORMALIZATIONS.get(lower, field_name)
```

---

## Performance

| Scenario | Time |
|----------|------|
| Saved mappings (replay) | < 1 sec |
| Pattern matching only | 1-2 sec |
| AI analysis (Ollama) | 3-5 sec |
| Complex form + AI | 5-10 sec |

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `seleniumbase_agent.py` | 220-241 | Pattern dictionary |
| `seleniumbase_agent.py` | 1407-1449 | Priority matching |
| `seleniumbase_agent.py` | 2111-2201 | Profile normalization |
| `seleniumbase_agent.py` | 1168-1405 | Special field handling |
| `seleniumbase_agent.py` | 78-103 | AI prompt template |
| `field_mapping_store.py` | 60-103 | Save/load mappings |
| `field_analyzer.py` | 169-243 | DOM field extraction |
| `database/db.py` | 30-51 | Profile schema |
