# AI Provider Options for Form Filling

FormAI supports multiple AI providers for intelligent form analysis and filling. Choose the one that best fits your needs.

## Quick Comparison

| Provider | Cost | Privacy | Speed | Setup Time | Quality |
|----------|------|---------|-------|------------|---------|
| **Ollama** | 🟢 Free | 🟢 100% Private | ⚡ Fast | 5 min | ⭐⭐⭐⭐ |
| **OpenAI** | 🔴 $0.01-0.10/req | 🔴 Cloud | ⚡⚡ Very Fast | 1 min | ⭐⭐⭐⭐⭐ |
| **Anthropic** | 🔴 $0.01-0.15/req | 🔴 Cloud | ⚡⚡ Very Fast | 1 min | ⭐⭐⭐⭐⭐ |
| **Google AI** | 🟡 Free tier* | 🔴 Cloud | ⚡⚡ Very Fast | 2 min | ⭐⭐⭐⭐ |
| **OpenRouter** | 🟡 Varies | 🔴 Cloud | ⚡⚡ Fast | 2 min | ⭐⭐⭐⭐ |

*Google AI has free tier with limitations

## 1. Ollama (Recommended for Privacy)

**Perfect for**: Privacy-conscious users, offline work, unlimited usage

### Setup
```bash
# 1. Install Ollama
# Download from: https://ollama.com/download

# 2. Pull a model
ollama pull llama3.2

# 3. Start Ollama
ollama serve

# 4. Configure in FormAI Settings
# Ollama Base URL: http://localhost:11434
```

### Pros
- ✅ Completely free
- ✅ 100% private - data never leaves your machine
- ✅ Works offline
- ✅ No rate limits
- ✅ Multiple models available

### Cons
- ❌ Requires installation
- ❌ Uses local resources (RAM, CPU/GPU)
- ❌ Initial setup takes 5 minutes

### Recommended Models
- `llama3.2` - Fast, 2GB (Best for most users)
- `llama3.1:8b` - More powerful, 4.7GB
- `qwen2.5-coder` - Excellent for forms, 4.7GB

### Cost
**$0** - Completely free, unlimited usage

---

## 2. OpenAI (Best Overall Quality)

**Perfect for**: Maximum accuracy, occasional use, willing to pay

### Setup
1. Get API key: https://platform.openai.com/api-keys
2. Go to FormAI Settings → AI API Keys
3. Enter OpenAI API key
4. Click Save

### Pros
- ✅ Highest quality responses
- ✅ Very fast
- ✅ Easy setup
- ✅ Reliable infrastructure

### Cons
- ❌ Costs money per request
- ❌ Data sent to OpenAI servers
- ❌ Requires internet

### Models Used
- GPT-4 Mini (default) - Best balance of speed/cost/quality
- GPT-3.5 Turbo - Faster, cheaper, good quality

### Cost
- **GPT-4 Mini**: ~$0.01 per form
- **GPT-3.5 Turbo**: ~$0.002 per form

---

## 3. Anthropic Claude (Best Reasoning)

**Perfect for**: Complex forms, high accuracy, advanced reasoning

### Setup
1. Get API key: https://console.anthropic.com/
2. Go to FormAI Settings → AI API Keys
3. Enter Anthropic API key
4. Click Save

### Pros
- ✅ Excellent reasoning
- ✅ Very accurate
- ✅ Great for complex forms
- ✅ Fast responses

### Cons
- ❌ Costs money
- ❌ Data sent to Anthropic servers
- ❌ Requires internet

### Models Used
- Claude 3.5 Sonnet (default) - Best quality
- Claude 3 Haiku - Faster, cheaper

### Cost
- **Claude Sonnet**: ~$0.015 per form
- **Claude Haiku**: ~$0.003 per form

---

## 4. Google AI (Free Tier Available)

**Perfect for**: Budget users, testing, occasional use

### Setup
1. Get API key: https://makersuite.google.com/app/apikey
2. Go to FormAI Settings → AI API Keys
3. Enter Google AI API key
4. Click Save

### Pros
- ✅ Free tier available (60 requests/minute)
- ✅ Fast responses
- ✅ Good quality
- ✅ Easy setup

### Cons
- ❌ Free tier has limits
- ❌ Data sent to Google servers
- ❌ Requires internet

### Models Used
- Gemini 2.0 Flash (default) - Fast and accurate

### Cost
- **Free tier**: 60 requests/minute
- **Paid**: ~$0.005 per form

---

## 5. OpenRouter (Access Multiple Models)

**Perfect for**: Model flexibility, trying different AIs

### Setup
1. Get API key: https://openrouter.ai/keys
2. Go to FormAI Settings → AI API Keys
3. Enter OpenRouter API key
4. Click Save

### Pros
- ✅ Access to many models
- ✅ Flexible pricing
- ✅ Can use free models
- ✅ Single API for multiple providers

### Cons
- ❌ Quality varies by model
- ❌ Data sent to third parties
- ❌ Requires internet

### Models Available
- Gemini 2.0 Flash (Free)
- Llama 3.1 (Free)
- GPT-4 ($)
- Claude 3.5 ($)
- And many more

### Cost
- **Free models**: $0
- **Premium models**: Varies ($0.001 - $0.15 per form)

---

## Choosing the Right Provider

### For Privacy
→ **Ollama** - Your data never leaves your computer

### For Quality
→ **OpenAI GPT-4 Mini** or **Anthropic Claude Sonnet**

### For Free Usage
→ **Ollama** (unlimited) or **Google AI** (60/min free tier)

### For Budget
→ **OpenRouter** with free models or **Google AI**

### For Complex Forms
→ **Anthropic Claude** or **OpenAI GPT-4**

### For Offline Use
→ **Ollama** (only option that works offline)

---

## Setup Priority

We recommend trying providers in this order:

1. **Ollama** - Free, private, unlimited
   - If you have 8GB+ RAM
   - 5 minute setup

2. **Google AI** - Free tier
   - If you need cloud AI
   - Quick signup

3. **OpenRouter** - Flexible
   - If you want to try different models
   - Some free options

4. **OpenAI** - Best quality
   - If quality is priority
   - Willing to pay

5. **Anthropic** - Advanced reasoning
   - For complex forms
   - Premium option

---

## Automatic Provider Selection

FormAI automatically selects the first configured provider in this priority order:

1. **Ollama** (free local)
2. **OpenAI**
3. **Anthropic**
4. **Google AI**
5. **OpenRouter**

You can configure multiple providers and switch between them in Settings.

---

## Privacy Comparison

### 🟢 Ollama - Private
- Data never leaves your computer
- No tracking
- No data retention
- You control everything

### 🔴 Cloud Providers (OpenAI, Anthropic, Google, OpenRouter)
- Data sent to third-party servers
- Subject to their privacy policies
- May be used for training (check provider policies)
- Requires trust in the provider

**Recommendation**: Use Ollama if privacy is a concern.

---

## Cost Comparison (100 Forms/Month)

| Provider | Monthly Cost |
|----------|--------------|
| **Ollama** | $0 |
| **Google AI** (free tier) | $0 |
| **OpenRouter** (free models) | $0 |
| **OpenAI GPT-4 Mini** | ~$1.00 |
| **OpenAI GPT-3.5** | ~$0.20 |
| **Anthropic Claude Sonnet** | ~$1.50 |
| **Google AI** (paid) | ~$0.50 |

---

## Getting Started

1. **Start with Ollama** (free, private)
   - See [OLLAMA_SETUP.md](./OLLAMA_SETUP.md)
   - 5 minute setup
   - Works offline

2. **Or try Google AI** (cloud, free tier)
   - Quick signup
   - Good for testing

3. **Configure in Settings**
   - Go to Settings → AI API Keys
   - Enter your API key or URL
   - Click Save

4. **Test It**
   - Go to Automation
   - Select a profile
   - Click "AI Auto-Fill (No Recording)"
   - Enter a form URL
   - AI will analyze and fill the form!

---

## Support

Having trouble? Check our guides:
- [Ollama Setup Guide](./OLLAMA_SETUP.md)
- [Main Documentation](./README.md)

Or open an issue on GitHub.
