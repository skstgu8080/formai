# Automation Engine

> The 7-phase pipeline that powers FormAI's form filling

## Overview

FormAI uses **two automation engines**:

| Engine | File | Use Case |
|--------|------|----------|
| **SeleniumBaseAgent** | `tools/seleniumbase_agent.py` | Protected sites, Cloudflare, AI-powered |
| **SimpleAutofill** | `tools/simple_autofill.py` | Fast, simple forms |

---

## Entry Points

### Web API

```python
# Start automation
POST /api/automation/start
{
    "profile_id": "user-123",
    "url": "https://example.com/signup",
    "use_stealth": true
}

# Stop automation
POST /api/automation/stop
POST /api/automation/stop/{session_id}
```

### CLI

```bash
python cli.py fill <site_id>    # Fill single site
python cli.py fill-all          # Fill all sites
python cli.py sites             # List sites
python cli.py profiles          # List profiles
```

### WebSocket

```
WS /ws  # Real-time progress updates
```

---

## SeleniumBaseAgent - 7-Phase Pipeline

**File:** `tools/seleniumbase_agent.py:557-941`

```
┌─────────────────────────────────────┐
│  PHASE 1: NAVIGATE                  │
│  → UC Mode (Undetected Chrome)      │
│  → Handle Cloudflare                │
├─────────────────────────────────────┤
│  PHASE 2: CLEAR                     │
│  → Close popups, modals             │
│  → Remove cookie banners            │
├─────────────────────────────────────┤
│  PHASE 3: DETECT                    │
│  → Load saved mappings OR           │
│  → AI analysis OR                   │
│  → Pattern matching                 │
├─────────────────────────────────────┤
│  PHASE 4: FILL                      │
│  → Map profile → fields             │
│  → Handle special types             │
├─────────────────────────────────────┤
│  PHASE 5: CAPTCHA                   │
│  → Detect reCAPTCHA/hCaptcha        │
│  → Solve via API or manual          │
├─────────────────────────────────────┤
│  PHASE 6: SUBMIT                    │
│  → Find submit button               │
│  → Click and wait                   │
│  → Handle multi-step forms          │
├─────────────────────────────────────┤
│  PHASE 7: LEARN                     │
│  → Save mappings to database        │
│  → "Learn Once, Replay Many"        │
└─────────────────────────────────────┘
```

---

## Phase 1: Navigate

**File:** `tools/seleniumbase_agent.py:605-680`

```python
with SB(uc=True, headless=True) as sb:
    # UC Mode = Undetected Chrome (anti-bot bypass)
    sb.uc_open_with_reconnect(url, reconnect_time=4)
```

### Features

- **UC Mode** - Bypasses bot detection
- **Cloudflare** - Handled automatically
- **Reconnect** - Retries on failure

### Browser Options

```python
SB(
    uc=True,           # Undetected Chrome
    headless=True,     # No visible window
    agent=user_agent,  # Custom user agent
    incognito=True,    # Private mode
)
```

---

## Phase 2: Clear

**File:** `tools/seleniumbase_agent.py:682-750`

```python
def _close_popups(self, sb):
    popup_selectors = [
        '[class*="modal"]',
        '[class*="popup"]',
        '[class*="overlay"]',
        '[class*="cookie"]',
        '[aria-label*="close"]',
        'button[class*="close"]',
    ]

    for selector in popup_selectors:
        try:
            if sb.is_element_visible(selector):
                sb.click(selector)
        except:
            continue
```

### What Gets Closed

- Modal dialogs
- Cookie consent banners
- Newsletter popups
- Overlay elements
- Chat widgets

---

## Phase 3: Detect

**File:** `tools/seleniumbase_agent.py:752-890`

### Three Detection Layers

```python
# Layer 1: Saved mappings (fastest)
if store.has_mappings(domain):
    mappings = store.get_mappings(domain)
    # Skip AI entirely!

# Layer 2: AI analysis
elif self.use_ai:
    mappings = await analyze_form_with_ai(sb, profile)

# Layer 3: Pattern matching (fallback)
else:
    mappings = self._detect_fields_by_patterns(sb)
```

### Field Extraction (JavaScript)

```javascript
document.querySelectorAll('input, select, textarea').forEach(el => {
    fields.push({
        selector: el.id ? `#${el.id}` : `[name="${el.name}"]`,
        type: el.type,
        label: getLabelFor(el),
        placeholder: el.placeholder,
        required: el.required
    });
});
```

---

## Phase 4: Fill

**File:** `tools/seleniumbase_agent.py:892-1100`

```python
def _fill_fields(self, sb, fields, profile):
    flat_profile = self._normalize_profile(profile)
    filled = 0

    for field in fields:
        selector = field['selector']
        profile_key = field['profile_field']
        value = flat_profile.get(profile_key)

        if not value:
            continue

        if field['type'] == 'select':
            sb.select_option_by_text(selector, value)
        elif field['type'] == 'checkbox':
            if not sb.is_selected(selector):
                sb.click(selector)
        else:
            sb.type(selector, value)

        filled += 1

    return filled
```

### Field Type Handling

| Type | Method |
|------|--------|
| `text`, `email` | `sb.type(selector, value)` |
| `password` | `sb.type(selector, value)` |
| `select` | `sb.select_option_by_text()` |
| `checkbox` | `sb.click()` if not selected |
| `radio` | `sb.click()` matching value |

---

## Phase 5: CAPTCHA

**File:** `tools/seleniumbase_agent.py:1102-1165`

```python
def _handle_captcha(self, sb):
    # Detect CAPTCHA type
    if sb.is_element_visible('[class*="recaptcha"]'):
        captcha_type = 'recaptcha'
    elif sb.is_element_visible('[class*="hcaptcha"]'):
        captcha_type = 'hcaptcha'
    else:
        return True  # No CAPTCHA

    # Try auto-solve
    if self.captcha_solver:
        solved = await self.captcha_solver.solve(sb, captcha_type)
        return solved

    # Manual solve fallback
    return False
```

### CAPTCHA Solvers

| Solver | File | Method |
|--------|------|--------|
| 2Captcha API | `tools/captcha_solver.py` | Send image, get solution |
| Ollama Vision | `tools/ollama_agent.py` | Screenshot → AI analysis |
| Manual | - | User solves in browser |

---

## Phase 6: Submit

**File:** `tools/seleniumbase_agent.py:1167-1250`

```python
def _submit_form(self, sb):
    submit_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:contains("Submit")',
        'button:contains("Sign Up")',
        'button:contains("Register")',
        'button:contains("Create")',
        '[class*="submit"]',
    ]

    for selector in submit_selectors:
        try:
            if sb.is_element_visible(selector):
                sb.click(selector)
                sb.sleep(2)  # Wait for response
                return True
        except:
            continue

    return False
```

### Multi-Step Forms

**File:** `tools/seleniumbase_agent.py:1252-1320`

```python
# Phase 6.5: Handle multi-step
if self._is_multi_step_form(sb):
    while self._has_next_step(sb):
        # Fill current step
        self._fill_fields(sb, step_fields, profile)
        # Click next
        sb.click('[class*="next"]')
        sb.sleep(1)
```

---

## Phase 7: Learn

**File:** `tools/seleniumbase_agent.py:1322-1380`

```python
def _save_learned_mappings(self, domain, mappings):
    store = FieldMappingStore()
    store.save_mappings(
        domain=domain,
        mappings=mappings,
        fields_count=len(mappings)
    )
    print(f"[Learn] Saved {len(mappings)} mappings for {domain}")
```

### "Learn Once, Replay Many"

```
First visit:
  Phase 3: AI analysis (5 sec)
  Phase 7: Save mappings

Next visits:
  Phase 3: Load saved (instant)
  Phase 7: Skip
```

---

## SimpleAutofill Engine

**File:** `tools/simple_autofill.py`

Lightweight alternative using Playwright:

```python
class SimpleAutofill:
    async def fill(self, url: str, profile: dict) -> FillResult:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            # Detect and fill
            fields = await self._detect_fields(page)
            filled = await self._fill_fields(page, fields, profile)

            return FillResult(
                success=True,
                fields_filled=filled
            )
```

### When to Use Each

| SimpleAutofill | SeleniumBaseAgent |
|----------------|-------------------|
| Simple forms | Complex forms |
| No bot protection | Cloudflare/bot detection |
| Speed priority | Accuracy priority |
| Headless only | Visible browser option |

---

## WebSocket Updates

**File:** `formai_server.py:1863-1920`

Real-time progress via WebSocket:

```python
async def broadcast_progress(session_id, phase, progress):
    await manager.broadcast({
        "type": "automation_progress",
        "session_id": session_id,
        "phase": phase,          # "navigate", "fill", "submit"
        "progress": progress,    # 0-100
        "message": f"Phase {phase}..."
    })
```

### Message Types

```json
{"type": "automation_started", "session_id": "abc123"}
{"type": "automation_progress", "phase": "fill", "progress": 50}
{"type": "fields_filled", "count": 12}
{"type": "captcha_detected", "type": "recaptcha"}
{"type": "automation_completed", "success": true}
{"type": "automation_error", "error": "Timeout"}
```

---

## Error Handling

```python
try:
    result = await agent.fill_site(url, profile)
except TimeoutError:
    # Page load timeout
    return {"success": False, "error": "timeout"}
except ElementNotFound:
    # Form field not found
    return {"success": False, "error": "element_not_found"}
except CaptchaFailed:
    # CAPTCHA not solved
    return {"success": False, "error": "captcha_failed"}
except Exception as e:
    # Unknown error
    logger.error(f"Automation failed: {e}")
    return {"success": False, "error": str(e)}
```

---

## Performance Tuning

### Timeouts

```python
PAGE_LOAD_TIMEOUT = 30      # seconds
ELEMENT_WAIT_TIMEOUT = 10   # seconds
CAPTCHA_TIMEOUT = 60        # seconds
SUBMIT_WAIT = 2             # seconds after submit
```

### Retries

```python
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries
```

### Headless vs Visible

```python
# Headless (faster, no UI)
SB(headless=True, uc=True)

# Visible (debugging, CAPTCHA)
SB(headless=False, uc=True)
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `tools/seleniumbase_agent.py` | Main 7-phase engine |
| `tools/simple_autofill.py` | Lightweight Playwright engine |
| `tools/captcha_solver.py` | CAPTCHA handling |
| `tools/field_mapping_store.py` | Save/load learned mappings |
| `formai_server.py` | API endpoints, WebSocket |
| `cli.py` | Command-line interface |
