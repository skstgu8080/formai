# CDP Replay with AI Value Replacement

## Overview

The CDP (Chrome DevTools Protocol) Replay system provides native Chrome recording replay using Playwright, combined with AI-powered intelligent mapping of profile data to form fields.

This solves the date field issue and other form filling inconsistencies by:
1. Using AI to intelligently map profile fields to form fields
2. Replaying recordings exactly like Chrome DevTools does (using Playwright)
3. Ensuring date formats and values match profile data correctly

## Architecture

```
┌─────────────────┐
│   Recording     │ (Chrome DevTools format)
│  + Profile Data │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Value       │ (OpenRouter/DeepSeek)
│  Replacer       │ - Maps fields intelligently
│                 │ - Handles date components
│                 │ - Converts formats
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Modified        │ (Recording with profile values)
│ Recording       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Playwright     │ (Native CDP replay)
│  Replay Engine  │ - Executes steps natively
│                 │ - Handles all selector types
│                 │ - Works like Chrome replay
└─────────────────┘
```

## Features

### AI Value Replacement (`tools/ai_value_replacer.py`)

**Smart Field Mapping:**
- Pattern-based matching for common fields (firstname, lastname, email, etc.)
- AI-powered matching for complex fields using OpenRouter API
- Intelligent date field detection and construction
- Month name to number conversion (e.g., "Feb" → "02")
- Format detection from sample values (ISO, US, European)

**Date Handling:**
The system handles date fields specially:
- Detects date fields from selectors: `#birthdate`, `dob`, `birth-date`, etc.
- Constructs dates from profile components: `birthMonth`, `birthDay`, `birthYear`
- Matches format to expected format: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`
- Converts month names: "Feb" → "02", "January" → "01", etc.

Example:
```python
Profile: { "birthMonth": "Feb", "birthDay": "11", "birthYear": "1989" }
Sample:  "1998-01-15" (ISO format)
Result:  "1989-02-11" (ISO format with profile data)
```

### CDP Replay Engine (`tools/chrome_devtools_replay.py`)

**Native Playwright Replay:**
- Initializes real Chrome browser via Playwright
- Executes recording steps exactly like Chrome DevTools
- Supports all step types: navigate, change, click, keyDown, keyUp, scroll
- Handles multiple selector types: ARIA, CSS, XPath, Pierce (shadow DOM)
- Real-time progress updates via WebSocket

**Selector Fallback:**
Chrome recordings include multiple selectors in priority order:
1. ARIA labels (most reliable)
2. CSS IDs and classes
3. XPath selectors
4. Pierce selectors (for shadow DOM)

The replay engine tries each selector until one succeeds.

## Usage

### Web UI

1. **Go to Recorder page**: http://localhost:5511/recorder
2. **Select a recording**
3. **Click "Replay"** button
4. **Select a profile** from dropdown
5. **Choose replay mode:**
   - **"Replay (Selenium)"** - Original Selenium-based replay
   - **"Replay (CDP+AI)"** - New Playwright + AI replay ✨

### API Endpoint

```bash
POST /api/recordings/{recording_id}/replay-cdp

Body:
{
  "profile_id": "profile-123",
  "headless": false
}

Response:
{
  "session_id": "session-456",
  "message": "CDP replay started (AI-powered)",
  "recording_name": "Reebok Registration",
  "profile_name": "John Doe",
  "mode": "cdp"
}
```

### Programmatic Usage

```python
import asyncio
from tools.chrome_devtools_replay import replay_recording_with_profile

# Load recording and profile
recording = {...}  # Chrome DevTools recording
profile = {...}    # User profile data
api_key = "your-openrouter-api-key"

# Run replay
result = await replay_recording_with_profile(
    recording=recording,
    profile=profile,
    api_key=api_key,
    headless=False
)

print(result)
```

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# OpenRouter API key for AI field mapping
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key from: https://openrouter.ai/keys

### AI Model

Default model: `deepseek/deepseek-chat` (free tier available)

You can change the model in `tools/ai_value_replacer.py`:

```python
replacer = AIValueReplacer(
    api_key=api_key,
    model="deepseek/deepseek-chat"  # or "google/gemma-2-9b-it", etc.
)
```

Available free models:
- `deepseek/deepseek-chat` (recommended)
- `google/gemma-2-9b-it`
- `meta-llama/llama-3-8b-instruct`

## Testing

Run the test suite:

```bash
python test_cdp_replay.py
```

This tests:
1. **Date handling** - Verifies date component construction
2. **AI value replacement** - Tests field mapping with real profile
3. **CDP replay engine** - Validates Playwright replay setup

## Troubleshooting

### Issue: "OpenRouter API key not configured"

**Solution:** Add `OPENROUTER_API_KEY` to your `.env` file.

### Issue: Date fields still showing wrong dates

**Possible causes:**
1. Profile missing date components (`birthMonth`, `birthDay`, `birthYear`)
2. Month is in wrong format (use full name like "February" or short like "Feb")
3. Recording not imported correctly

**Solution:**
- Check profile has all three date fields
- Use month names, not numbers: "Feb" not "2"
- Re-import recording if needed

### Issue: "Could not find element"

**Possible causes:**
1. Page structure changed
2. Selectors in recording are outdated
3. Page loaded too slowly

**Solution:**
- Re-record the action in Chrome DevTools
- Increase timeout in replay settings
- Check if website has bot detection

### Issue: Replay is too fast/slow

**Solution:** Adjust delays in `chrome_devtools_replay.py`:

```python
# Line 134 - Between steps
await asyncio.sleep(0.3)  # Increase for slower replay

# Line 141 - After completion
await asyncio.sleep(2)  # Time to see results
```

## Comparison: Selenium vs CDP Replay

| Feature | Selenium (Old) | CDP+AI (New) |
|---------|---------------|--------------|
| **Engine** | SeleniumBase | Playwright |
| **Value Mapping** | Pattern-based | AI-powered |
| **Date Handling** | Manual construction | AI + format detection |
| **Replay Accuracy** | Simulated typing | Native browser replay |
| **Speed** | Slower | Faster |
| **Selector Support** | CSS, XPath | ARIA, CSS, XPath, Pierce |
| **Bot Detection** | Harder to bypass | Better stealth |

## Known Limitations

1. **API Key Required:** Requires OpenRouter API key (free tier available)
2. **Network Dependency:** Needs internet for AI mapping calls
3. **Complex Forms:** Very dynamic forms may still fail (same as Chrome replay)
4. **CAPTCHAs:** Cannot automatically solve CAPTCHAs (same as before)

## Future Improvements

- [ ] Cache AI mappings to reduce API calls
- [ ] Offline mode with local LLM (Ollama)
- [ ] Visual verification (screenshot comparison)
- [ ] Recording editing UI
- [ ] Template-based mapping (save mappings per site)

## Files Modified

1. `tools/ai_value_replacer.py` - NEW: AI value replacement engine
2. `tools/chrome_devtools_replay.py` - UPDATED: Playwright replay engine
3. `formai_server.py` - ADDED: `/api/recordings/{id}/replay-cdp` endpoint
4. `web/recorder.html` - ADDED: "Replay (CDP+AI)" button
5. `.env.example` - DOCUMENTED: `OPENROUTER_API_KEY`

## Contributing

To improve the AI mapping:

1. Add more field patterns in `ai_value_replacer.py` → `_try_direct_match()`
2. Adjust AI prompt in `_build_mapping_prompt()` for better results
3. Add new field type handlers (e.g., credit card, phone formatting)

## Support

For issues specific to:
- **Date fields:** Check `_construct_date_value()` in `ai_value_replacer.py`
- **Element finding:** Check `_find_element()` in `chrome_devtools_replay.py`
- **AI mapping:** Check `_map_field_with_ai()` in `ai_value_replacer.py`

## Credits

- **Chrome DevTools Protocol** - Google Chrome team
- **Playwright** - Microsoft
- **OpenRouter** - AI model routing
- **DeepSeek** - Default AI model
