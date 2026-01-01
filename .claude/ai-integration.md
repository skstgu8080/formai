# AI Integration

> How FormAI uses Ollama and other AI services

## Overview

FormAI uses AI for:
1. **Form Analysis** - Understanding form structure
2. **Field Mapping** - Matching fields to profile data
3. **CAPTCHA Solving** - Vision-based CAPTCHA handling
4. **Smart Decisions** - Handling edge cases

---

## Ollama Configuration

### Environment

```env
OLLAMA_HOST=http://localhost:11434  # Default
```

### Required Model

```bash
ollama pull llama3.2  # Primary model
```

### Model Selection

| Task | Model | Why |
|------|-------|-----|
| Form analysis | `llama3.2` | Fast, good at JSON |
| Field mapping | `llama3.2` | Pattern recognition |
| CAPTCHA | `llava` | Vision capability |

---

## Form Analysis Prompt

**File:** `tools/seleniumbase_agent.py:78-103`

### Prompt Template

```python
AI_FIELD_ANALYSIS_PROMPT = """Analyze this form and return field mappings as JSON.

FORM HTML:
{form_html}

PROFILE FIELDS AVAILABLE:
{profile_fields}

TASK: Map each form field to the correct profile field.

RESPONSE FORMAT (JSON array):
[
  {"selector": "#email", "profile_field": "email", "type": "text", "confidence": 0.95},
  {"selector": "#firstName", "profile_field": "firstName", "type": "text", "confidence": 0.9},
  {"selector": "#country", "profile_field": "country", "type": "select", "confidence": 0.85}
]

Rules:
1. Use CSS selectors (prefer #id, then [name=...])
2. Map to exact profile field names
3. Include confidence score 0.0-1.0
4. Set type: text, select, checkbox, password
5. Only include fillable fields (not buttons, hidden)
6. For password confirmation fields, use profile_field: "password"

Return ONLY valid JSON array. No explanation.
"""
```

### Variables

| Variable | Content |
|----------|---------|
| `{form_html}` | Extracted form HTML (cleaned) |
| `{profile_fields}` | Available profile keys: `[email, firstName, lastName, ...]` |

---

## Ollama API Call

**File:** `tools/seleniumbase_agent.py:184-218`

```python
async def analyze_form_with_ai(sb, profile: dict) -> List[Dict]:
    # Extract form HTML
    form_html = sb.execute_script("""
        var form = document.querySelector('form');
        return form ? form.outerHTML : document.body.innerHTML;
    """)

    # Build prompt
    profile_fields = list(profile.keys())
    prompt = AI_FIELD_ANALYSIS_PROMPT.format(
        form_html=form_html[:5000],  # Limit size
        profile_fields=profile_fields
    )

    # Call Ollama
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low for consistency
                    "num_predict": 1000
                }
            },
            timeout=30.0
        )

    # Parse response
    result = response.json()
    content = result.get("response", "")

    # Extract JSON
    start = content.find('[')
    end = content.rfind(']') + 1
    if start >= 0 and end > start:
        return json.loads(content[start:end])

    return []
```

### Response Example

```json
[
  {"selector": "#email", "profile_field": "email", "type": "text", "confidence": 0.95},
  {"selector": "#password", "profile_field": "password", "type": "password", "confidence": 0.95},
  {"selector": "#firstName", "profile_field": "firstName", "type": "text", "confidence": 0.9},
  {"selector": "#lastName", "profile_field": "lastName", "type": "text", "confidence": 0.9},
  {"selector": "select[name='country']", "profile_field": "country", "type": "select", "confidence": 0.85}
]
```

---

## CAPTCHA Vision Analysis

**File:** `tools/captcha_solver.py`

### Screenshot + Vision Model

```python
async def solve_image_captcha(self, sb, captcha_selector: str):
    # Take screenshot of CAPTCHA element
    element = sb.find_element(captcha_selector)
    screenshot = element.screenshot_as_base64

    # Send to vision model
    response = await self._analyze_captcha_image(screenshot)

    return response.get("solution")
```

### Vision Prompt

```python
CAPTCHA_VISION_PROMPT = """Look at this CAPTCHA image.

What text or characters do you see?

Rules:
1. Return ONLY the characters/text
2. No explanation
3. Case sensitive
4. Include numbers and special characters

Response:"""
```

---

## 2Captcha Integration

**File:** `tools/captcha_solver.py`

### Environment

```env
TWOCAPTCHA_API_KEY=your_api_key_here
```

### API Flow

```python
class CaptchaSolver:
    async def solve_recaptcha(self, site_key: str, page_url: str) -> str:
        # Step 1: Submit CAPTCHA
        response = await self.client.post(
            "https://2captcha.com/in.php",
            data={
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url
            }
        )
        captcha_id = response.text.split("|")[1]

        # Step 2: Poll for solution
        for _ in range(60):  # Max 60 attempts
            await asyncio.sleep(5)
            result = await self.client.get(
                f"https://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}"
            )
            if "OK" in result.text:
                return result.text.split("|")[1]

        raise CaptchaTimeout("Solution not ready")
```

### Supported CAPTCHA Types

| Type | Method |
|------|--------|
| reCAPTCHA v2 | `userrecaptcha` |
| reCAPTCHA v3 | `userrecaptcha` + min_score |
| hCaptcha | `hcaptcha` |
| Image CAPTCHA | `base64` |
| Text CAPTCHA | `textcaptcha` |

---

## OpenRouter Integration

**File:** `tools/field_analyzer.py`

### Environment

```env
OPENROUTER_API_KEY=your_api_key_here
```

### API Call

```python
async def analyze_with_openrouter(form_html: str, profile: dict):
    response = await httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://formai.local",
            "X-Title": "FormAI"
        },
        json={
            "model": "anthropic/claude-3-haiku",
            "messages": [
                {"role": "system", "content": "You are a form analyzer..."},
                {"role": "user", "content": f"Analyze: {form_html}"}
            ]
        }
    )
    return response.json()
```

---

## Agent Memory

**File:** `tools/agent_memory.py`

Stores AI learning data for improved accuracy:

### Database Schema

```sql
CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    pattern TEXT,
    profile_field TEXT,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    last_used TIMESTAMP
);
```

### Usage

```python
memory = AgentMemory()

# Record successful mapping
memory.record_success(
    domain="amazon.com",
    pattern="email",
    profile_field="email"
)

# Get best mapping for pattern
best_field = memory.get_best_mapping(
    domain="amazon.com",
    pattern="email"
)  # Returns "email" with highest success rate
```

---

## Error Handling

### Ollama Errors

```python
try:
    mappings = await analyze_form_with_ai(sb, profile)
except httpx.ConnectError:
    logger.error("Ollama not running")
    # Fall back to pattern matching
    mappings = detect_fields_by_patterns(sb)
except httpx.TimeoutException:
    logger.error("Ollama timeout")
    mappings = detect_fields_by_patterns(sb)
except json.JSONDecodeError:
    logger.error("Invalid JSON from Ollama")
    mappings = []
```

### CAPTCHA Errors

```python
try:
    solution = await solver.solve_recaptcha(site_key, url)
except CaptchaTimeout:
    logger.warning("CAPTCHA timeout - manual solve needed")
    return {"needs_manual": True}
except InsufficientBalance:
    logger.error("2Captcha balance low")
    return {"error": "captcha_balance"}
```

---

## Performance Tuning

### Ollama Options

```python
{
    "temperature": 0.1,    # Low = consistent output
    "num_predict": 1000,   # Max tokens
    "top_k": 40,           # Top-k sampling
    "top_p": 0.9,          # Nucleus sampling
}
```

### Timeouts

```python
OLLAMA_TIMEOUT = 30      # seconds
CAPTCHA_TIMEOUT = 120    # seconds (2captcha can be slow)
OPENROUTER_TIMEOUT = 60  # seconds
```

### Caching

```python
# Cache AI responses for same form structure
@lru_cache(maxsize=100)
def get_cached_analysis(form_hash: str):
    return cached_mappings.get(form_hash)
```

---

## AI Decision Flow

```
┌─────────────────────────────────────┐
│  Form Detected                       │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Has Saved Mappings?                 │
│  → YES: Use saved (skip AI)          │
│  → NO: Continue                      │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Ollama Available?                   │
│  → YES: AI Analysis                  │
│  → NO: Pattern Matching              │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  AI Response Valid?                  │
│  → YES: Use mappings                 │
│  → NO: Fall back to patterns         │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  Save Successful Mappings            │
│  → Learn for next time               │
└─────────────────────────────────────┘
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `tools/seleniumbase_agent.py:78-218` | Ollama form analysis |
| `tools/ollama_agent.py` | Ollama client wrapper |
| `tools/captcha_solver.py` | CAPTCHA solving (2Captcha, vision) |
| `tools/field_analyzer.py` | OpenRouter integration |
| `tools/agent_memory.py` | AI learning database |
