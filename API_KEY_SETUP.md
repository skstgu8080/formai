# API Key Setup Guide

## For Production Users

FormAI requires API keys to power its AI features. You need to provide your own API keys through the Settings page.

### How to Add Your API Keys

1. **Open FormAI** in your browser at `http://localhost:5511`
2. **Navigate to Settings** using the sidebar menu
3. **Scroll to the API Keys section**
4. **Enter your API keys** for one or more of the following services:

   - **OpenAI**: Get your key from [platform.openai.com](https://platform.openai.com/api-keys)
   - **Anthropic (Claude)**: Get your key from [console.anthropic.com](https://console.anthropic.com/)
   - **Google (Gemini)**: Get your key from [makersuite.google.com](https://makersuite.google.com/app/apikey)
   - **OpenRouter**: Get your key from [openrouter.ai](https://openrouter.ai/keys)

5. **Click Save** to store your API keys securely

### Security Notes

- API keys are stored locally in your `settings.json` file
- Never share your API keys with others
- Never commit API keys to version control
- Keep your API keys secure and rotate them regularly

### Which API Key Should I Use?

You only need ONE API key from any of the supported providers:

- **OpenRouter** (Recommended): Access to multiple AI models with one key
- **OpenAI**: GPT-4, GPT-3.5 models
- **Anthropic**: Claude models
- **Google**: Gemini models

## For Developers

If you're developing or testing FormAI, you can optionally use environment variables:

### Development Setup

1. Create a `.env.development` file in the root directory
2. Add your development API keys:

```env
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-key-here
OPENROUTER_API_KEY=your-openrouter-key-here
```

3. Set the environment variable:
```bash
set ENVIRONMENT=development  # Windows
export ENVIRONMENT=development  # Linux/Mac
```

**Important**: The `.env` file approach is ONLY for development. Production users must enter their API keys through the UI.

## System Status Indicators

The dashboard shows real-time status of your setup:

- **Browser Engine**: Active when browser automation is available
- **WebSocket**: Connected when real-time communication is established
- **AI Model**:
  - "Ready" - API key is configured
  - "No API Key" - You need to add an API key in Settings
- **Memory Usage**: Current memory consumption

## Troubleshooting

### "No API Key" Status
- Go to Settings and add at least one API key
- Save the settings
- Refresh the page

### API Key Not Working
- Verify your API key is correct and active
- Check if you have credits/quota with your provider
- Ensure your API key has the necessary permissions

### Need Help?
Visit the Settings page and follow the prompts to add your API keys.