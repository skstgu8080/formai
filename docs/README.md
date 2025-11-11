# FormAI Documentation

Complete documentation for recording and automating website forms with FormAI's extension system.

## 📚 Documentation Files

### 🎯 For AI Agents Recording Forms

**[MCP_AUTOMATED_RECORDING.md](MCP_AUTOMATED_RECORDING.md)** (NEW - Automated Method)
- **Purpose:** Fully automated recording using Chrome DevTools MCP
- **When to use:** When you want AI agents to generate recordings automatically
- **Length:** Quick guide (~10 min read)
- **Covers:**
  - DOM inspection via Chrome DevTools MCP (NO screenshots!)
  - Automatic field discovery with JavaScript
  - Intelligent sample data generation
  - Chrome Recorder JSON export
  - < 1 minute recording time vs 5-15 minutes manual
- **Benefits:** Fastest method, 100% field coverage, fully automated

**[AI_RECORDING_INSTRUCTIONS.md](AI_RECORDING_INSTRUCTIONS.md)** (Manual Method)
- **Purpose:** Detailed step-by-step instructions for manual recording with Chrome DevTools
- **When to use:** When MCP is not available or you need manual control
- **Length:** Comprehensive (~15 min read)
- **Covers:**
  - How to use Chrome DevTools Recorder manually
  - Field-by-field recording instructions
  - CAPTCHA handling strategies
  - Sample data guidelines
  - Quality checklist
  - Export and save procedures

**[RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md)** (Quick Guide)
- **Purpose:** Fast reference card for experienced users
- **When to use:** When you already know the process and need a quick reminder
- **Length:** Quick reference (~2 min read)
- **Covers:**
  - 5-step quick start
  - Sample data table
  - Recording workflow diagram
  - Common scenarios
  - Troubleshooting

### 🚀 For Using Recordings in Production

**[RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)** (Production Guide)
- **Purpose:** Complete workflow from recording to production execution
- **When to use:** When you want to understand the entire FormAI system
- **Length:** Comprehensive (~20 min read)
- **Covers:**
  - 5-phase workflow (Record → Import → Profile → Configure → Execute)
  - Extension system explanation
  - Code examples for each phase
  - Advanced scenarios (headless, batch, custom extensions)
  - Monitoring and debugging
  - Production checklist

### 📋 Reference Files

**[../recordings/TEMPLATE_recording.json](../recordings/TEMPLATE_recording.json)** (JSON Template)
- **Purpose:** Example recording showing expected JSON structure
- **When to use:** Reference when creating or validating recordings
- **Contents:**
  - Complete recording structure
  - Field mapping reference
  - Metadata examples
  - Usage examples

## 🎓 Quick Start Guide

### For Recording a New Form

**Option 1: MCP Automated (Fastest - NEW!)**
1. **Read:** [MCP_AUTOMATED_RECORDING.md](MCP_AUTOMATED_RECORDING.md) (10 minutes)
2. **Run:** `python test_mcp_recording.py` to see demo
3. **Use:** MCP tools to navigate + discover fields + generate JSON
4. **Time:** < 1 minute per recording

**Option 2: Manual Recording (Traditional)**
1. **Read:** [RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md) (2 minutes)
2. **Follow:** The 5-step workflow
3. **Reference:** [AI_RECORDING_INSTRUCTIONS.md](AI_RECORDING_INSTRUCTIONS.md) for details
4. **Validate:** Check against [TEMPLATE_recording.json](../recordings/TEMPLATE_recording.json)
5. **Time:** 5-15 minutes per recording

### For Running in Production

1. **Read:** [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)
2. **Follow:** The 5-phase workflow
3. **Test:** Run in preview mode first
4. **Deploy:** Execute with production profile

## 🔑 Key Concepts

### Extension System

FormAI uses an extension-based architecture inspired by Puppeteer Replay:

- **ProfileDataExtension** - Automatic profile data injection
- **CaptchaExtension** - CAPTCHA detection and solving
- **LoggingExtension** - Verbose logging
- **ScreenshotExtension** - Screenshot capture
- **Custom Extensions** - Build your own

### Field Mapping

Automatic field detection and mapping:

```
Form Field          →  Profile Field
-----------------------------------------
firstName           →  profile.firstName
email              →  profile.email
phone              →  profile.phone
address            →  profile.address1
```

Confidence scoring (0.0-1.0):
- ID selectors: 1.0
- Name selectors: 0.8
- Class selectors: 0.5
- XPath selectors: 0.3

### CAPTCHA Handling

Automatic detection and solving:

1. Detect CAPTCHA type (reCAPTCHA, hCaptcha, etc.)
2. Attempt automatic solving using UC Mode
3. Fall back to manual intervention if needed
4. Track statistics (detected, solved, failed)

## 📂 File Organization

```
FormAI/
├── docs/                                    ← You are here
│   ├── README.md                           ← This file
│   ├── AI_RECORDING_INSTRUCTIONS.md        ← Main recording guide
│   ├── RECORDING_QUICK_REFERENCE.md        ← Quick reference
│   └── RECORDING_TO_PRODUCTION_WORKFLOW.md ← Production guide
├── recordings/
│   ├── TEMPLATE_recording.json             ← JSON template
│   ├── github_signup.json                  ← Example recordings
│   └── signupgenius_registration.json
├── profiles/
│   └── koodos.json                         ← Profile examples
└── tools/
    ├── chrome_recorder_parser.py           ← Recording parser
    ├── profile_replay_engine.py            ← Replay engine
    ├── profile_data_extension.py           ← Profile injection
    ├── captcha_extension.py                ← CAPTCHA handling
    └── replay_extension.py                 ← Extension base class
```

## 🎯 Common Use Cases

### Use Case 1: First-Time User

**Goal:** Create your first recording and run it

**Steps:**
1. Read: [RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md)
2. Record: Follow the 5-step workflow
3. Test: Use the code example in [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)

**Time:** ~30 minutes total

### Use Case 2: Experienced User

**Goal:** Record a new form quickly

**Steps:**
1. Reference: [RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md)
2. Record: F12 → Recorder → Fill all fields → Export → Save
3. Run: Use existing production script

**Time:** ~10 minutes

### Use Case 3: Production Deployment

**Goal:** Deploy form automation to production

**Steps:**
1. Read: Production section of [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)
2. Test: Run with preview mode
3. Validate: Check success rate > 90%
4. Deploy: Execute with production profile

**Time:** ~1 hour including testing

### Use Case 4: Troubleshooting

**Goal:** Fix a failing recording

**Reference:**
- Troubleshooting section in [AI_RECORDING_INSTRUCTIONS.md](AI_RECORDING_INSTRUCTIONS.md)
- Monitoring & Debugging in [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)

**Common fixes:**
- Re-record if success rate < 80%
- Add missing fields to profile
- Enable manual CAPTCHA intervention
- Check selector quality scores

## 💡 Pro Tips

1. **Always fill ALL fields** - Incomplete recordings lead to failures
2. **Use realistic sample data** - Helps with field type detection
3. **Test before production** - Use preview mode first
4. **Monitor success rates** - Track and improve over time
5. **Handle CAPTCHAs appropriately** - Know when to auto-solve vs manual

## 🆘 Getting Help

### Documentation Hierarchy

```
Need quick reminder?
    → RECORDING_QUICK_REFERENCE.md

Need detailed recording instructions?
    → AI_RECORDING_INSTRUCTIONS.md

Need production workflow?
    → RECORDING_TO_PRODUCTION_WORKFLOW.md

Need JSON structure reference?
    → recordings/TEMPLATE_recording.json
```

### Common Questions

**Q: Which file should I read first?**
A: Start with [RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md), then dive into [AI_RECORDING_INSTRUCTIONS.md](AI_RECORDING_INSTRUCTIONS.md) for details.

**Q: How do I test a recording before production?**
A: See "Preview Mode" section in [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)

**Q: Why is my CAPTCHA not being solved?**
A: See CAPTCHA handling sections in all three guides. Modern CAPTCHAs often require manual intervention.

**Q: What if my recording has low success rate?**
A: See troubleshooting sections. Usually requires re-recording or profile field updates.

## 🚀 Next Steps

1. **New to FormAI?** → Read [RECORDING_QUICK_REFERENCE.md](RECORDING_QUICK_REFERENCE.md)
2. **Ready to record?** → Follow [AI_RECORDING_INSTRUCTIONS.md](AI_RECORDING_INSTRUCTIONS.md)
3. **Ready for production?** → Implement [RECORDING_TO_PRODUCTION_WORKFLOW.md](RECORDING_TO_PRODUCTION_WORKFLOW.md)

## 📊 Success Metrics

Track these metrics for your recordings:

- **Field Coverage:** 100% of fields captured
- **Success Rate:** > 90% fields filled successfully
- **CAPTCHA Resolution:** Detected and handled appropriately
- **Execution Time:** < 3 minutes typical
- **Profile Mapping:** > 0.8 average confidence score

## 🎉 You're Ready!

You now have everything you need to:
- ✅ Record any website form
- ✅ Import recordings to FormAI
- ✅ Configure the extension system
- ✅ Run automated form filling in production
- ✅ Handle CAPTCHAs automatically
- ✅ Monitor and debug issues

**Happy automating!** 🚀
