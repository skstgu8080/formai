# CLI Usage

> Terminal commands for headless form automation

## Overview

The CLI (`cli.py`) provides terminal-based form filling without opening a browser UI.

**File:** `cli.py`

---

## Commands

### List Sites

```bash
python cli.py sites
```

Shows all 292+ sites with:
- ID, Name, Status, Fields filled
- Enabled/disabled status
- Total statistics

### List Profiles

```bash
python cli.py profiles
```

Shows all profiles with:
- ID, Name, Email

### Fill Single Site

```bash
python cli.py fill <site_id>
python cli.py fill <site_id> --profile <profile_id>
python cli.py fill <site_id> --no-submit
```

**Options:**
- `--profile, -p` - Specific profile to use (default: first profile)
- `--no-submit` - Fill fields only, don't click submit
- `--submit, -s` - Submit form after filling (default: True)

**Example:**
```bash
python cli.py fill abc123 --profile koodos
```

### Fill All Sites

```bash
python cli.py fill-all
python cli.py fill-all --profile <profile_id>
python cli.py fill-all --no-submit
```

Processes all enabled sites in batch.

### Setup Email

```bash
python cli.py setup-email
python cli.py setup-email --provider outlook
python cli.py setup-email --provider yahoo
```

Opens browser to sign into email. Session saved for verification.

**Providers:** `gmail` (default), `outlook`, `yahoo`

### Verify Email

```bash
python cli.py verify-email
python cli.py verify-email <search_term>
```

Opens email in browser to find verification links.

---

## Output Format

### Fill Result

```
============================================================
FILLING: Example Site
URL: https://example.com/signup
PROFILE: John Doe (john@example.com)
MODE: Headless + SUBMIT
============================================================

============================================================
RESULT: SUCCESS
============================================================
  Fields filled: 12
  Form submitted: Yes
  Duration: 4521ms
============================================================
```

### Batch Result

```
[1/10] Example Site 1...
  [OK] Filled 8 fields [SUBMITTED]
[2/10] Example Site 2...
  [FAIL] Element not found
...

============================================================
BATCH COMPLETE: 8 success, 2 failed
FORMS SUBMITTED: 8
============================================================
```

---

## Partial ID Matching

Both site IDs and profile IDs support partial matching:

```bash
# Full ID
python cli.py fill abc12345

# Partial ID (matches first site starting with "abc")
python cli.py fill abc
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (site not found, profile not found, etc.) |

---

## Fill History

All fill operations are logged to `fill_history` table:

```sql
SELECT * FROM fill_history ORDER BY created_at DESC LIMIT 10;
```

Fields logged:
- `site_id`, `profile_id`, `url`
- `success`, `fields_filled`, `error`
- `duration_ms`, `created_at`

---

## Integration with Sites Manager

The CLI uses `SitesManager` to:
- List all sites (`get_all_sites()`)
- Get enabled sites (`get_enabled_sites()`)
- Update status after fill (`update_site_status()`)

---

## Integration with SimpleAutofill

The CLI uses `SimpleAutofill` engine:

```python
engine = SimpleAutofill(headless=True, submit=True)
result = await engine.fill(url, profile)
```

Always runs headless for speed.

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `list_sites()` | Display all sites |
| `list_profiles()` | Display all profiles |
| `fill_site()` | Fill single site |
| `fill_all_sites()` | Batch fill all enabled |
| `setup_email()` | Email login session |
| `verify_email()` | Find verification links |
