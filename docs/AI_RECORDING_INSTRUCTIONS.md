# AI Instructions: Recording Website Forms for FormAI Automation

## Mission Overview

Your task is to visit websites, record form-filling interactions using Chrome DevTools Recorder, and save those recordings for automated playback with FormAI's extension system.

## Required Tools

- Chrome or Chromium-based browser with DevTools Recorder
- Access to target website
- Text editor or file system access to save JSON files

## Step-by-Step Recording Process

### Phase 1: Preparation

1. **Open Chrome DevTools**
   - Navigate to the target website
   - Press `F12` or `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Option+I` (Mac)
   - OR right-click on page → "Inspect"

2. **Open the Recorder Panel**
   - In DevTools, click on the `>>` (more tools) icon in the top toolbar
   - Select "Recorder" from the dropdown menu
   - OR press `Ctrl+Shift+P` and type "Show Recorder"

3. **Create New Recording**
   - Click the "Create a new recording" button (red circle icon)
   - Give the recording a descriptive name (e.g., "github_signup", "amazon_checkout", "linkedin_registration")
   - Click "Start recording" button

### Phase 2: Recording the Form Fill

**IMPORTANT RULES:**
- Fill forms **SLOWLY and DELIBERATELY** - do NOT rush
- Fill **ALL fields** on the form, not just some
- Use **REALISTIC sample data** that matches the field types
- Do **NOT click submit** unless instructed to capture CAPTCHA behavior
- Wait 1-2 seconds between field fills for clear recording

4. **Navigate to the Form (if needed)**
   - If not already on the form page, navigate to it
   - The Recorder will capture the navigation step
   - Wait for the page to fully load

5. **Fill Each Form Field**

   For each field on the form:

   a. **Click into the field**
      - Click the input box to focus it
      - Wait for focus indicator to appear

   b. **Enter the value**
      - Type realistic sample data appropriate for the field type:
        - **First Name**: Use a real first name (e.g., "John", "Sarah")
        - **Last Name**: Use a real last name (e.g., "Smith", "Johnson")
        - **Email**: Use a realistic email format (e.g., "john.smith@example.com")
        - **Phone**: Use a properly formatted phone number (e.g., "(555) 123-4567")
        - **Password**: Use a strong password (e.g., "SecurePass123!")
        - **Address**: Use a complete realistic address
        - **City**: Use a real city name
        - **State/Province**: Use real state/province
        - **Zip/Postal Code**: Use a valid format
        - **Country**: Select appropriate country
        - **Credit Card**: Use test card number (e.g., "4111111111111111")
        - **Date**: Use realistic dates in correct format
        - **Dropdown/Select**: Choose a realistic option
        - **Checkbox**: Check/uncheck as needed
        - **Radio button**: Select appropriate option

   c. **Wait after each field**
      - Pause 1-2 seconds after filling each field
      - This creates cleaner recordings and mimics human behavior

6. **Handle Special Field Types**

   **Dropdowns/Select boxes:**
   - Click the dropdown to open it
   - Wait for options to appear
   - Click the desired option
   - Verify selection is shown

   **Checkboxes:**
   - Click each checkbox you want to check
   - Note which ones should be checked by default

   **Radio buttons:**
   - Click the appropriate radio button option
   - Only one can be selected per group

   **Multi-select:**
   - Hold Ctrl/Cmd and click multiple options
   - OR use Shift for range selection

   **Date pickers:**
   - Click the date field to open picker
   - Navigate to correct month/year
   - Click the specific date

   **File uploads:**
   - Note: File upload recordings may not work well
   - Skip file uploads or note them separately

### Phase 3: CAPTCHA Handling (Optional)

7. **If CAPTCHA is present:**

   **Option A: Skip CAPTCHA (Recommended for most recordings)**
   - Do NOT click the CAPTCHA checkbox
   - Do NOT click the submit button
   - Stop recording before submission
   - The FormAI CaptchaExtension will handle it during playback

   **Option B: Record CAPTCHA interaction (for testing)**
   - Click the CAPTCHA checkbox
   - Wait for verification
   - Note: CAPTCHA solving is handled by FormAI's CaptchaExtension
   - This records the interaction but won't solve CAPTCHAs automatically

### Phase 4: Stop and Export Recording

8. **Stop the Recording**
   - Click the "End recording" button (square icon)
   - The recording will appear in the Recorder panel
   - Review the steps captured

9. **Review the Recording**
   - Expand the recording steps
   - Verify all fields were captured
   - Check that selectors look reasonable
   - Ensure no sensitive data was recorded

10. **Export the Recording**
    - Click the "Export" button (download icon) in the Recorder panel
    - Select "Export as JSON" from the dropdown
    - Choose "Puppeteer (JSON)" or "Puppeteer Replay" format
    - Save the file with a descriptive name

### Phase 5: Save to FormAI

11. **Save the Recording File**
    - Save the exported JSON to: `FormAI/recordings/`
    - Use a descriptive filename following this pattern:
      - `{website}_{form_type}.json`
      - Examples:
        - `github_signup.json`
        - `amazon_checkout.json`
        - `linkedin_registration.json`
        - `salesforce_lead_form.json`
        - `shopify_customer_registration.json`

12. **Verify Recording Format**

    The JSON file should have this structure:
    ```json
    {
      "title": "Descriptive Title",
      "steps": [
        {
          "type": "navigate",
          "url": "https://example.com/form"
        },
        {
          "type": "change",
          "selectors": [["#firstName"]],
          "value": "John"
        },
        {
          "type": "change",
          "selectors": [["#lastName"]],
          "value": "Smith"
        }
      ]
    }
    ```

13. **Add Metadata (Optional)**

    Edit the JSON file to add helpful metadata:
    ```json
    {
      "title": "GitHub Registration Form",
      "description": "Complete GitHub account registration with all fields",
      "url": "https://github.com/signup",
      "total_fields": 5,
      "has_captcha": true,
      "captcha_type": "reCAPTCHA v2",
      "steps": [...]
    }
    ```

## Quality Checklist

Before finalizing a recording, verify:

- [ ] All form fields were filled (not just some)
- [ ] Sample data is realistic and appropriate for field types
- [ ] Selectors are clean (prefer ID and name over XPath)
- [ ] No sensitive real data was recorded (use test data only)
- [ ] Recording has a descriptive title
- [ ] File is saved in `recordings/` directory
- [ ] Filename follows naming convention
- [ ] JSON is valid and properly formatted
- [ ] No unnecessary navigation steps
- [ ] CAPTCHA handling is documented (if present)

## Using the Recording with FormAI

After creating and saving the recording:

1. **Import to FormAI**
   ```python
   from tools.recording_manager import RecordingManager
   from tools.chrome_recorder_parser import ChromeRecorderParser
   import json

   # Load the recording
   with open("recordings/your_recording.json") as f:
       chrome_data = json.load(f)

   # Parse it
   parser = ChromeRecorderParser()
   recording = parser.parse_chrome_recording_data(chrome_data)

   # Save to FormAI
   manager = RecordingManager()
   recording_id = manager.save_recording(recording)
   print(f"Recording ID: {recording_id}")
   ```

2. **Replay with Profile Data**
   ```python
   from tools.profile_replay_engine import ProfileReplayEngine
   from tools.profile_data_extension import ProfileDataExtension
   from tools.captcha_extension import CaptchaExtension

   # Load profile
   with open("profiles/your_profile.json") as f:
       profile = json.load(f)

   # Create engine with extensions
   engine = ProfileReplayEngine(use_stealth=True, headless=False)
   engine.register_extension(ProfileDataExtension())
   engine.register_extension(CaptchaExtension(auto_solve=True))

   # Replay
   result = engine.replay_recording(
       recording_id=recording_id,
       profile_data=profile,
       session_name="production_run"
   )
   ```

3. **The Extension System Automatically:**
   - Maps form fields to profile data
   - Injects profile values instead of sample values
   - Detects and attempts to solve CAPTCHAs
   - Tracks success/failure statistics
   - Handles errors gracefully

## Field Mapping Reference

The FormAI system automatically maps these field patterns:

| Field Pattern | Profile Mapping | Sample Value |
|--------------|----------------|--------------|
| firstName, first_name, fname | profile.firstName | "John" |
| lastName, last_name, lname | profile.lastName | "Smith" |
| email, emailAddress | profile.email | "john@example.com" |
| phone, phoneNumber, mobile | profile.phone | "(555) 123-4567" |
| address, address1, street | profile.address1 | "123 Main St" |
| address2, apt, suite | profile.address2 | "Apt 4B" |
| city | profile.city | "New York" |
| state, province | profile.state | "NY" |
| zip, zipCode, postalCode | profile.zip | "10001" |
| country | profile.country | "USA" |
| company, companyName | profile.company | "Example Corp" |
| website, url | profile.website | "https://example.com" |
| jobTitle, title, position | profile.jobTitle | "Software Engineer" |
| password, pwd | (use sample value) | "SecurePass123!" |

## Common Recording Scenarios

### Scenario 1: Simple Registration Form

**Fields to record:**
- First Name
- Last Name
- Email
- Password
- Confirm Password

**Steps:**
1. Start recording
2. Navigate to registration page
3. Fill all 5 fields slowly
4. Do NOT click submit (skip CAPTCHA)
5. Stop recording
6. Export as `{site}_registration.json`

### Scenario 2: Checkout Form

**Fields to record:**
- Shipping Address (5-7 fields)
- Billing Address (if different)
- Payment Method (card type, number, CVV, expiration)
- Contact Information (email, phone)

**Steps:**
1. Start recording
2. Navigate to checkout
3. Fill shipping address completely
4. Fill payment information (use test card)
5. Fill contact details
6. Do NOT click "Place Order"
7. Stop recording
8. Export as `{site}_checkout.json`

### Scenario 3: Multi-Step Form

**Approach:**
- Record EACH step as a separate recording
- OR record the entire flow in one recording
- Name appropriately: `{site}_step1.json`, `{site}_step2.json`

### Scenario 4: Form with Dynamic Fields

**Special handling:**
- Record all static fields first
- Then interact with dynamic elements
- Note any JavaScript-triggered fields in recording metadata

## Troubleshooting

### Recording Issues

**Problem: Some fields not captured**
- Solution: Fill fields more slowly, wait 1-2 seconds between fills

**Problem: Selectors are XPath instead of CSS**
- Solution: This is normal, FormAI will normalize them automatically

**Problem: Dropdown selections not recorded**
- Solution: Click the dropdown, wait for options, then click option (not keyboard selection)

**Problem: Recording has too many steps**
- Solution: Review and note which steps are essential; FormAI will replay all steps

**Problem: CAPTCHA blocks form submission**
- Solution: Don't submit the form; FormAI's CaptchaExtension handles this during playback

### Playback Issues

**Problem: Fields not filling during playback**
- Solution: Check that profile has matching field names (firstName, lastName, etc.)

**Problem: CAPTCHA not detected**
- Solution: Ensure CaptchaExtension is registered before replay

**Problem: Wrong values being filled**
- Solution: Check profile data structure and field mapping confidence scores

## Advanced Tips

1. **Selector Quality**: FormAI auto-scores selectors (ID=1.0, name=0.8, class=0.5, XPath=0.3)

2. **Field Confidence**: FormAI calculates confidence for each field mapping (0.0-1.0)

3. **Value Transformers**: Phone, ZIP, and SSN values are automatically formatted

4. **Extension System**: Create custom extensions for special handling:
   ```python
   class CustomExtension(ReplayExtension):
       def transformStep(self, step, context):
           # Custom logic here
           return step
   ```

5. **Preview Mode**: Test recordings with sample values before production:
   ```python
   ProfileDataExtension(use_recorded_values=True)
   ```

## Security Best Practices

- ⚠️ **NEVER record real passwords, credit cards, or sensitive data**
- ✅ Use test data only (test credit cards, fake emails, sample passwords)
- ✅ Review recordings before saving to ensure no sensitive data
- ✅ Use `.gitignore` to prevent committing sensitive recordings
- ✅ Store production profile data separately and securely

## Output File Structure

After recording, your FormAI directory should look like:

```
FormAI/
├── recordings/
│   ├── github_signup.json
│   ├── amazon_checkout.json
│   ├── linkedin_registration.json
│   └── your_new_recording.json
├── profiles/
│   ├── test_profile.json
│   └── production_profile.json
└── tools/
    ├── chrome_recorder_parser.py
    ├── profile_replay_engine.py
    ├── profile_data_extension.py
    └── captcha_extension.py
```

## Success Criteria

A successful recording should:
1. ✅ Capture ALL form fields (100% coverage)
2. ✅ Use realistic sample data appropriate for each field type
3. ✅ Have clean, descriptive naming
4. ✅ Be saved in proper JSON format
5. ✅ Contain no sensitive real data
6. ✅ Be reproducible (can replay successfully with profile data)
7. ✅ Handle CAPTCHAs appropriately (either skip or note for extension handling)

## Next Steps After Recording

1. Test the recording with a test profile
2. Verify all fields map correctly
3. Check CAPTCHA detection and handling
4. Run in production with real profile data
5. Monitor success rates and adjust as needed

---

**Remember**: The goal is to create high-quality recordings that FormAI's extension system can automatically replay with ANY profile data. Take your time, fill ALL fields, and use realistic sample data!
