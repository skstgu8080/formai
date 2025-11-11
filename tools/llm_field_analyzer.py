#!/usr/bin/env python3
"""
LLM Field Analyzer - Uses AI models to intelligently analyze form fields
Supports OpenAI, Anthropic, Google AI, and OpenRouter
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx


class LLMFieldAnalyzer:
    """
    Uses LLM APIs to analyze form fields intelligently
    Falls back to pattern matching if no API keys configured
    """

    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.default_provider = self._get_default_provider()

    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from api_keys directory"""
        api_keys = {}
        api_keys_dir = Path("api_keys")

        if api_keys_dir.exists():
            for file in api_keys_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        key_data = json.load(f)
                        service_name = file.stem
                        api_key = key_data.get("api_key")
                        if api_key:
                            api_keys[service_name] = api_key
                except Exception as e:
                    print(f"Error loading API key for {file.stem}: {e}")

        return api_keys

    def _get_default_provider(self) -> Optional[str]:
        """Get the first configured provider"""
        # Priority order: Ollama (free/local), OpenAI, Anthropic, Google, OpenRouter
        priority = ['ollama', 'openai', 'anthropic', 'google', 'openrouter']
        for provider in priority:
            if provider in self.api_keys:
                return provider
        return None

    async def analyze_form_with_llm(
        self,
        snapshot: str,
        profile_fields: List[str],
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze form fields and map to profile

        Args:
            snapshot: Accessibility tree snapshot
            profile_fields: Available profile fields
            provider: Which AI provider to use (default: auto)

        Returns:
            Field mappings with confidence scores
        """
        if not provider:
            provider = self.default_provider

        if not provider or provider not in self.api_keys:
            return {
                "error": "No AI provider configured",
                "mappings": []
            }

        # Create analysis prompt
        prompt = self._create_analysis_prompt(snapshot, profile_fields)

        # Call appropriate provider
        if provider == 'ollama':
            return await self._analyze_with_ollama(prompt)
        elif provider == 'openai':
            return await self._analyze_with_openai(prompt)
        elif provider == 'anthropic':
            return await self._analyze_with_anthropic(prompt)
        elif provider == 'google':
            return await self._analyze_with_google(prompt)
        elif provider == 'openrouter':
            return await self._analyze_with_openrouter(prompt)
        else:
            return {
                "error": f"Unsupported provider: {provider}",
                "mappings": []
            }

    def _create_analysis_prompt(self, snapshot: str, profile_fields: List[str]) -> str:
        """Create prompt for LLM analysis"""
        return f"""Analyze this form accessibility tree and map fields to profile data.

FORM SNAPSHOT:
{snapshot[:2000]}  # Limit snapshot size

AVAILABLE PROFILE FIELDS:
{', '.join(profile_fields)}

TASK:
1. Identify all input fields in the form
2. For each field, determine which profile field it should map to
3. Return JSON with field mappings

RESPONSE FORMAT (JSON only, no explanation):
{{
    "mappings": [
        {{
            "field_label": "Email Address",
            "field_selector": "input[name='email']",
            "profile_field": "email",
            "confidence": 0.95
        }}
    ]
}}
"""

    async def _analyze_with_ollama(self, prompt: str) -> Dict[str, Any]:
        """Analyze using Ollama (local models)"""
        base_url = self.api_keys.get('ollama', 'http://localhost:11434')
        if not base_url:
            return {"error": "Ollama base URL not configured", "mappings": []}

        # Load model preference from environment or use default
        model = os.getenv('OLLAMA_MODEL', 'llama3.2')

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Ollama uses OpenAI-compatible API
                response = await client.post(
                    f"{base_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a form analysis expert. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "format": "json"
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']

                    # Try to parse JSON from response
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # Try to extract JSON from markdown code blocks
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            return json.loads(content[json_start:json_end])
                        return {"error": "Invalid JSON in response", "mappings": []}
                else:
                    return {
                        "error": f"Ollama API error: {response.status_code} - Is Ollama running? Run 'ollama serve'",
                        "mappings": []
                    }

        except httpx.ConnectError:
            return {
                "error": "Cannot connect to Ollama. Install from https://ollama.com/download and run 'ollama serve'",
                "mappings": []
            }
        except Exception as e:
            return {
                "error": f"Ollama request failed: {str(e)}",
                "mappings": []
            }

    async def _analyze_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Analyze using OpenAI API"""
        api_key = self.api_keys.get('openai')
        if not api_key:
            return {"error": "OpenAI API key not configured", "mappings": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a form analysis expert. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return json.loads(content)
                else:
                    return {
                        "error": f"OpenAI API error: {response.status_code}",
                        "mappings": []
                    }

        except Exception as e:
            return {
                "error": f"OpenAI request failed: {str(e)}",
                "mappings": []
            }

    async def _analyze_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Analyze using Anthropic Claude API"""
        api_key = self.api_keys.get('anthropic')
        if not api_key:
            return {"error": "Anthropic API key not configured", "mappings": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['content'][0]['text']
                    # Extract JSON from response
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        return json.loads(content[json_start:json_end])
                    return {"error": "No JSON in response", "mappings": []}
                else:
                    return {
                        "error": f"Anthropic API error: {response.status_code}",
                        "mappings": []
                    }

        except Exception as e:
            return {
                "error": f"Anthropic request failed: {str(e)}",
                "mappings": []
            }

    async def _analyze_with_google(self, prompt: str) -> Dict[str, Any]:
        """Analyze using Google AI API"""
        api_key = self.api_keys.get('google')
        if not api_key:
            return {"error": "Google AI API key not configured", "mappings": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "response_mime_type": "application/json"
                        }
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return json.loads(content)
                else:
                    return {
                        "error": f"Google AI API error: {response.status_code}",
                        "mappings": []
                    }

        except Exception as e:
            return {
                "error": f"Google AI request failed: {str(e)}",
                "mappings": []
            }

    async def _analyze_with_openrouter(self, prompt: str) -> Dict[str, Any]:
        """Analyze using OpenRouter API"""
        api_key = self.api_keys.get('openrouter')
        if not api_key:
            return {"error": "OpenRouter API key not configured", "mappings": []}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-exp:free",
                        "messages": [
                            {"role": "system", "content": "You are a form analysis expert. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    return json.loads(content)
                else:
                    return {
                        "error": f"OpenRouter API error: {response.status_code}",
                        "mappings": []
                    }

        except Exception as e:
            return {
                "error": f"OpenRouter request failed: {str(e)}",
                "mappings": []
            }


# Singleton instance
_llm_analyzer = None

def get_llm_analyzer() -> LLMFieldAnalyzer:
    """Get or create LLM analyzer instance"""
    global _llm_analyzer
    if _llm_analyzer is None:
        _llm_analyzer = LLMFieldAnalyzer()
    return _llm_analyzer
