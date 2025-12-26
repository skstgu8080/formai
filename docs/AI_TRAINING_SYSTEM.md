# AI Training System for FormAI

## Overview

The AI Training System allows FormAI to learn from your form-filling recordings and automatically improve field detection and mapping over time. This system uses **Ollama** (free, local AI) to analyze Chrome DevTools recordings and build a knowledge base that makes future form-filling smarter and more accurate.

## How It Works

### The Simple Workflow

1. **You record** - Fill out a form manually using Chrome DevTools Recorder
2. **Upload recording** - Import the JSON recording into FormAI
3. **AI analyzes** - Ollama automatically identifies field types and suggests profile mappings
4. **You confirm** - Review and confirm (or correct) the AI's suggestions
5. **System learns** - Your confirmations become training data for future improvements

### Why This is Powerful

- **No manual mapping** - AI automatically maps form fields to your profile
- **Gets smarter** - Each recording you upload improves the system
- **100% Private** - All AI processing happens locally via Ollama (no cloud)
- **Zero cost** - Ollama is completely free and unlimited

## Prerequisites

### 1. Install Ollama

**Option A: Auto-Install via FormAI**
1. Open FormAI at http://localhost:5511
2. Go to Settings → AI API Keys
3. Click "Install Ollama"
4. Wait for automatic installation

**Option B: Manual Installation**
1. Download from https://ollama.com/download
2. Run the installer
3. Open terminal and run:
   ```bash
   ollama pull llama3.2
   ollama serve
   ```

### 2. Configure FormAI

Create a `.env` file (copy from `.env.example`) and ensure these settings:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# AI Training Features
AI_RECORDING_ANALYSIS=true
CONFIDENCE_THRESHOLD=0.8
ASK_USER_ON_LOW_CONFIDENCE=true
```

### 3. Recommended Ollama Models

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `llama3.2` | 2GB | ⚡⚡⚡ | **Recommended** - General use, fast |
| `llama3.1:8b` | 4.7GB | ⚡⚡ | Complex forms, higher accuracy |
| `qwen2.5-coder` | 4.7GB | ⚡⚡ | Technical/developer forms |
| `mistral` | 4.1GB | ⚡⚡ | Alternative option |

**To install:**
```bash
ollama pull llama3.2  # or any model above
```

## Using the AI Training System

### Step 1: Create a Recording

**Using Chrome DevTools Recorder:**

1. Open Chrome
2. Press F12 → "Recorder" tab
3. Click "Create a new recording"
4. Name your recording (e.g., "Contact Form - Example.com")
5. Click "Start recording"
6. Fill out the form manually
7. Click "End recording"
8. Export as JSON (right-click → "Export as JSON")

### Step 2: Import Recording into FormAI

**Via UI:**
1. Open http://localhost:5511
2. Go to "Recordings" page
3. Click "Import Chrome Recording"
4. Upload or paste your JSON file
5. Click "Import"

**Via API:**
```bash
curl -X POST http://localhost:5511/api/recordings/import-chrome \
  -H "Content-Type: application/json" \
  -d @recording.json
```

### Step 3: AI Analysis (Automatic)

FormAI automatically analyzes the recording with Ollama:

- Identifies field types (email, name, phone, etc.)
- Suggests profile field mappings
- Calculates confidence scores
- Categorizes the form (signup, checkout, contact, etc.)

**Manual Trigger:**
```bash
POST /api/ai/analyze-recording/{recording_id}?profile_id={profile_id}
```

### Step 4: Review and Confirm Mappings

**Via API:**
```bash
POST /api/ai/confirm-mapping
{
  "recording_id": "abc123",
  "field_index": 0,
  "confirmed_mapping": "email",
  "was_correct": true
}
```

**What Happens:**
- ✅ Correct mapping → System learns the pattern
- ❌ Incorrect mapping → High-value training data collected
- System improves for similar forms in the future

## API Reference

### Analyze Recording with AI

```http
POST /api/ai/analyze-recording/{recording_id}?profile_id={profile_id}
```

**Response:**
```json
{
  "success": true,
  "recording_id": "abc123",
  "ai_analysis": {
    "status": "analyzed",
    "model_used": "llama3.2",
    "form_category": "user_registration",
    "field_count": 5,
    "avg_confidence": 0.92,
    "fields": [
      {
        "field_name": "Email",
        "ai_field_type": "email",
        "ai_profile_mapping": "email",
        "ai_confidence": 0.95,
        "ai_reasoning": "Email input field detected by name attribute"
      }
    ],
    "requires_review": false,
    "training_value": "high"
  }
}
```

### Confirm Field Mapping

```http
POST /api/ai/confirm-mapping
{
  "recording_id": "abc123",
  "field_index": 0,
  "confirmed_mapping": "email",
  "was_correct": true
}
```

### Get Recording Library

```http
GET /api/ai/recording-library?category=signup&min_confidence=0.8
```

**Response:**
```json
{
  "recordings": [...],
  "stats": {
    "total_analyzed_recordings": 25,
    "categories": {
      "user_registration": 10,
      "checkout": 8,
      "contact_form": 7
    },
    "avg_confidence": 0.89,
    "high_value_recordings": 15
  }
}
```

### Get Training Examples (Few-Shot Learning)

```http
GET /api/ai/training-examples?limit=5
```

Returns best examples for few-shot learning prompts.

## Understanding AI Analysis Results

### Form Categories

- `user_registration` - Signup/register forms
- `login` - Login forms
- `checkout` - E-commerce checkout
- `shipping_address` - Address forms
- `business_contact` - B2B contact forms
- `contact_form` - General contact forms
- `general_form` - Unknown/other types

### Confidence Scores

- **0.9 - 1.0** - Very High (auto-fill safe)
- **0.8 - 0.9** - High (review recommended)
- **0.7 - 0.8** - Medium (manual confirmation needed)
- **< 0.7** - Low (requires review)

### Training Value

- **high** - Complex form with many fields, high confidence
- **medium** - Standard form, moderate complexity
- **low** - Simple form or low confidence

## Advanced: How the AI Learns

### Pattern Learning (Not Fine-Tuning)

This system uses **few-shot learning** rather than traditional fine-tuning:

1. **Recording Collection** - Your recordings become examples
2. **Pattern Database** - System builds a knowledge base of field patterns
3. **Few-Shot Prompts** - AI uses past examples to analyze new forms
4. **Active Learning** - User corrections improve future suggestions

### What Gets Learned

- Field name patterns (email, e-mail, email_address → email)
- Selector patterns (input[name='email'] → email field)
- Form structure patterns (what fields appear together)
- Domain-specific patterns (e-commerce vs. contact forms)

### Training Data Storage

All training data is stored locally:

```
recordings/
├── recording1.json      # Original recording
│   └── ai_analysis      # AI analysis results
│   └── user_confirmed   # User confirmations
├── recording2.json
└── recording3.json
```

## Best Practices

### For Better AI Analysis

1. **Use descriptive recording names** - "Shopify Checkout" vs. "Form 1"
2. **Record complete flows** - Fill all fields, don't skip
3. **Upload diverse examples** - Different form types improve learning
4. **Confirm mappings** - Even if correct, confirmation helps training
5. **Correct errors immediately** - High-value training data

### For Production Use

1. **Start with 10-20 recordings** - Build initial knowledge base
2. **Review low-confidence fields** - Don't auto-fill below 0.8
3. **Test on similar forms** - AI learns patterns, works best on similar types
4. **Update regularly** - Add new recordings as you encounter new forms

### For Privacy

- All AI runs locally (Ollama)
- No data sent to cloud
- Recordings stay on your machine
- Safe for sensitive forms (medical, financial, etc.)

## Troubleshooting

### Ollama Not Found

**Error:** `Connection refused to localhost:11434`

**Solution:**
1. Ensure Ollama is installed: `ollama --version`
2. Start Ollama: `ollama serve`
3. Verify: `curl http://localhost:11434/api/version`

### Low AI Confidence

**Problem:** AI shows confidence < 0.7 for most fields

**Solutions:**
1. Upload more example recordings (5-10 similar forms)
2. Use a better model: `ollama pull llama3.1:8b`
3. Manually confirm mappings to build training data

### Slow Analysis

**Problem:** AI analysis takes >30 seconds

**Solutions:**
1. Use faster model: `llama3.2` (2GB) instead of larger models
2. Check CPU usage - close other apps
3. Consider GPU acceleration (advanced)

### Wrong Field Mappings

**Problem:** AI consistently maps fields incorrectly

**Solutions:**
1. Correct and confirm - becomes training data
2. Check recording quality - ensure complete form fills
3. Upload more examples of this form type
4. Review field names/selectors in recording

## Next Steps

1. **Record 5-10 diverse forms** - Build initial training library
2. **Analyze and confirm** - Review AI suggestions
3. **Test replay** - Try replaying with a profile
4. **Iterate** - Add more recordings, improve accuracy

## Future Enhancements (Phase 2+)

- Multi-modal learning (screenshot + DOM analysis)
- Actual fine-tuning (LoRA) for specialized domains
- Behavioral timing analysis
- Integration with password managers
- Graph-based form understanding

## Support

- GitHub Issues: https://github.com/skstgu8080/formai/issues
- Documentation: `docs/` folder
- API Reference: This document

---

**Happy Training! The AI gets smarter with every recording you upload.** 🚀
