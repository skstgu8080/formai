# Recording Quick Reference Card

## 🎯 Quick Start (5 Steps)

1. **F12** → Open DevTools
2. **Recorder Panel** → Create new recording
3. **Fill ALL fields SLOWLY** → Use realistic test data
4. **Stop & Export** → Save as JSON
5. **Save to** `recordings/{site}_{type}.json`

## 🚫 Critical Rules

- ❌ **DO NOT** rush through fields
- ❌ **DO NOT** skip fields
- ❌ **DO NOT** use real sensitive data
- ❌ **DO NOT** click submit (unless testing CAPTCHA)
- ✅ **DO** fill ALL fields
- ✅ **DO** use realistic sample data
- ✅ **DO** wait 1-2 seconds between fields

## 📋 Sample Data Reference

| Field Type | Example Value |
|-----------|---------------|
| First Name | John |
| Last Name | Smith |
| Email | john.smith@example.com |
| Phone | (555) 123-4567 |
| Password | SecurePass123! |
| Address | 123 Main St |
| City | New York |
| State | NY |
| Zip | 10001 |
| Country | USA |
| Credit Card | 4111111111111111 |
| CVV | 123 |
| Expiration | 12/25 |

## 🎬 Recording Workflow

```
Open DevTools (F12)
    ↓
Open Recorder Panel
    ↓
Click "Create new recording"
    ↓
Name it: {site}_{type}
    ↓
Click "Start recording"
    ↓
Navigate to form (if needed)
    ↓
Fill EACH field SLOWLY
    ↓
Wait 1-2 sec between fields
    ↓
Skip CAPTCHA/Submit
    ↓
Click "End recording"
    ↓
Review steps captured
    ↓
Click "Export" → JSON
    ↓
Save to recordings/
    ↓
DONE! ✅
```

## 🏃 Fast Recording Template

**For quick recordings, follow this pattern:**

1. **Start**: F12 → Recorder → New
2. **Fill**: All fields with sample data
3. **Stop**: End recording
4. **Export**: JSON format
5. **Save**: `recordings/{site}_{type}.json`

## 🎯 Field Mapping Auto-Detection

FormAI automatically detects these patterns:

- `firstName`, `first_name`, `fname` → profile.firstName
- `lastName`, `last_name`, `lname` → profile.lastName
- `email`, `emailAddress` → profile.email
- `phone`, `phoneNumber` → profile.phone
- `address`, `street` → profile.address1
- `city` → profile.city
- `state`, `province` → profile.state
- `zip`, `zipCode` → profile.zip

## ⚡ Common Scenarios

### Registration Form
1. Navigate to signup page
2. Fill: First Name, Last Name, Email, Password
3. Skip CAPTCHA
4. Export as `{site}_registration.json`

### Checkout Form
1. Navigate to checkout
2. Fill: Shipping address, payment info
3. Skip "Place Order" button
4. Export as `{site}_checkout.json`

### Contact Form
1. Navigate to contact page
2. Fill: Name, Email, Message
3. Skip submit
4. Export as `{site}_contact.json`

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Fields not captured | Fill slower, wait between fields |
| Too many steps | Normal, FormAI handles it |
| CAPTCHA blocks | Don't submit, FormAI handles CAPTCHA |
| Wrong selectors | FormAI normalizes automatically |

## ✅ Quality Checklist

Before saving:
- [ ] All fields filled (100%)
- [ ] Sample data is realistic
- [ ] No real sensitive data
- [ ] Descriptive filename
- [ ] Saved in `recordings/` folder
- [ ] JSON is valid

## 🚀 Using the Recording

```python
# Import and parse
from tools.chrome_recorder_parser import ChromeRecorderParser
import json

with open("recordings/your_file.json") as f:
    data = json.load(f)

parser = ChromeRecorderParser()
recording = parser.parse_chrome_recording_data(data)

# Save to FormAI
from tools.recording_manager import RecordingManager
manager = RecordingManager()
recording_id = manager.save_recording(recording)

# Replay with profile
from tools.profile_replay_engine import ProfileReplayEngine
from tools.profile_data_extension import ProfileDataExtension
from tools.captcha_extension import CaptchaExtension

with open("profiles/your_profile.json") as f:
    profile = json.load(f)

engine = ProfileReplayEngine(use_stealth=True, headless=False)
engine.register_extension(ProfileDataExtension())
engine.register_extension(CaptchaExtension(auto_solve=True))

result = engine.replay_recording(
    recording_id=recording_id,
    profile_data=profile
)
```

## 📝 File Naming Convention

**Pattern:** `{website}_{form_type}.json`

**Examples:**
- `github_signup.json`
- `amazon_checkout.json`
- `linkedin_registration.json`
- `salesforce_lead.json`
- `shopify_registration.json`

## 🎓 Pro Tips

1. **Slower is better** - 1-2 seconds between fields
2. **All fields matter** - Don't skip any
3. **Test data only** - Never use real credentials
4. **Review before save** - Check all steps captured
5. **Descriptive names** - Make filenames clear

---

**Remember:** Quality recordings = Successful automation! 🎯
