# Ollama Setup Guide

Run AI models locally for free! Ollama lets you use powerful AI models without paying for API access.

## What is Ollama?

Ollama is a free, open-source tool that lets you run large language models (LLMs) on your own computer. Perfect for:
- **Privacy**: Your data never leaves your machine
- **Cost**: Completely free, no API charges
- **Offline**: Works without internet connection
- **Speed**: Local inference can be faster than API calls

## Installation

### Windows

1. **Download Ollama**
   - Visit: https://ollama.com/download
   - Download the Windows installer
   - Run the installer and follow the prompts

2. **Verify Installation**
   ```bash
   ollama --version
   ```

3. **Start Ollama Service**
   ```bash
   ollama serve
   ```

   Or just run Ollama from Start Menu - it runs in the background.

### macOS

1. **Download Ollama**
   ```bash
   # Using Homebrew
   brew install ollama

   # Or download from https://ollama.com/download
   ```

2. **Start Ollama**
   ```bash
   ollama serve
   ```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

## Recommended Models for Form Filling

### Llama 3.2 (Recommended - Fast & Accurate)
```bash
ollama pull llama3.2
```
- **Size**: 2GB
- **Speed**: Very fast
- **Accuracy**: Excellent for form analysis
- **Best for**: General use

### Llama 3.1 8B (More powerful)
```bash
ollama pull llama3.1:8b
```
- **Size**: 4.7GB
- **Speed**: Fast
- **Accuracy**: Excellent
- **Best for**: Complex forms

### Mistral (Alternative)
```bash
ollama pull mistral
```
- **Size**: 4.1GB
- **Speed**: Fast
- **Accuracy**: Very good
- **Best for**: Alternative to Llama

### Qwen 2.5 Coder (Specialized)
```bash
ollama pull qwen2.5-coder
```
- **Size**: 4.7GB
- **Speed**: Fast
- **Accuracy**: Excellent for web forms
- **Best for**: Technical forms

## Configuration in FormAI

1. **Go to Settings** → **AI API Keys**

2. **Configure Ollama**
   - Ollama Base URL: `http://localhost:11434` (default)
   - Click **Save**

3. **Set Model in .env**
   ```bash
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

4. **Test It**
   - Go to Automation page
   - Select a profile
   - Click "AI Auto-Fill (No Recording)"
   - Enter a form URL
   - AI will use Ollama to analyze and fill the form!

## Troubleshooting

### "Cannot connect to Ollama"

**Solution**: Make sure Ollama is running
```bash
ollama serve
```

### "Model not found"

**Solution**: Pull the model first
```bash
ollama pull llama3.2
```

### "Ollama is slow"

**Solutions**:
1. Use smaller model: `llama3.2` instead of `llama3.1:70b`
2. Check GPU support: Ollama uses GPU automatically if available
3. Close other applications to free up RAM

### Check Running Models

```bash
ollama list
```

### Check Ollama Status

```bash
# Test Ollama API
curl http://localhost:11434/api/tags
```

## System Requirements

### Minimum
- **RAM**: 8GB
- **Storage**: 5GB free
- **CPU**: Modern processor (2015+)

### Recommended
- **RAM**: 16GB+
- **Storage**: 10GB+ free
- **GPU**: NVIDIA/AMD GPU (optional, for faster inference)
- **CPU**: Multi-core processor

## Model Performance Comparison

| Model | Size | Speed | Accuracy | RAM Required |
|-------|------|-------|----------|--------------|
| llama3.2 | 2GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | 8GB |
| llama3.1:8b | 4.7GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 12GB |
| mistral | 4.1GB | ⚡⚡ | ⭐⭐⭐⭐ | 12GB |
| qwen2.5-coder | 4.7GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 12GB |

## Advanced Configuration

### Use GPU Acceleration

Ollama automatically uses GPU if available. Check GPU usage:
```bash
nvidia-smi  # For NVIDIA GPUs
```

### Change Default Port

```bash
OLLAMA_HOST=0.0.0.0:8080 ollama serve
```

Then update FormAI `.env`:
```bash
OLLAMA_BASE_URL=http://localhost:8080
```

### Run Multiple Models

```bash
# Pull multiple models
ollama pull llama3.2
ollama pull mistral
ollama pull qwen2.5-coder

# Switch models in .env
OLLAMA_MODEL=mistral  # Use Mistral instead
```

## Benefits of Local AI

### Privacy
- Your form data never leaves your computer
- No data sent to third-party APIs
- Complete control over your data

### Cost
- **$0** - Completely free
- No API rate limits
- Unlimited usage

### Speed
- Local inference can be faster than API calls
- No network latency
- Instant responses

### Offline
- Works without internet
- No dependency on external services
- Always available

## Comparison with Cloud AI

| Feature | Ollama (Local) | Cloud API |
|---------|----------------|-----------|
| **Cost** | Free | $0.01 - $0.10 per request |
| **Privacy** | ✅ Private | ❌ Sent to cloud |
| **Speed** | Fast (with GPU) | Variable (network) |
| **Offline** | ✅ Yes | ❌ No |
| **Setup** | 5 minutes | 1 minute |
| **Quality** | Excellent | Excellent |

## Getting Help

- **Ollama Docs**: https://github.com/ollama/ollama
- **Model Library**: https://ollama.com/library
- **Discord**: https://discord.gg/ollama

## Next Steps

1. ✅ Install Ollama
2. ✅ Pull llama3.2 model
3. ✅ Configure in FormAI Settings
4. ✅ Test with AI Auto-Fill
5. 🎉 Enjoy free AI-powered form filling!
