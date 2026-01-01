"""
Ollama Agent - The Brain for AI Form Filling.

Communicates with local Ollama to decide what actions to take
based on current page state and profile data.
"""

import json
import logging
import httpx
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ollama-agent")

SYSTEM_PROMPT = """You are an AI form-filling agent with FULL browser control. You see everything like DevTools.

AVAILABLE TOOLS:

BASIC ACTIONS:
- fill(selector, value) - Fill an input field
- click(selector) - Click an element
- select(selector, value) - Select dropdown option
- check(selector) - Check a checkbox
- submit() - Submit the form (verifies 200 response)
- done() - Form completed successfully
- skip(reason) - Cannot fill, skip to next

POWER TOOLS:
- type_human_like(selector, value) - Type with delays (anti-bot)
- scroll_to_element(selector) - Scroll into view
- hover(selector) - Hover to reveal elements
- press_key(key) - Press Enter, Tab, Escape
- wait_for_network() - Wait for AJAX to complete
- get_element_text(selector) - Read text content
- get_dropdown_options(selector) - List all dropdown options

ANALYSIS TOOLS:
- analyze_form() - Deep form structure analysis
- detect_errors() - Find validation errors

DYNAMIC TOOLS (You can create your own!):
- create_tool(name, js_code, description) - Create custom JS tool
- run_tool(name, ...args) - Run your custom tool
- execute_js(code) - Run any JavaScript

WHAT YOU CAN SEE:
- Full page HTML and DOM
- Network responses (200/400/500 status codes)
- Console logs and errors
- Form validation messages
- Success/failure after submit

RULES:
1. Fill ONE field at a time
2. Match profile fields intelligently
3. Check network responses for 200 success
4. If you see form errors, fix them
5. Use power tools when basic ones fail
6. Create custom tools for unusual widgets

RESPONSE FORMAT - JSON only:
{"tool": "fill", "selector": "#email", "value": "john@example.com", "profile_field": "email"}
{"tool": "select", "selector": "#country", "value": "United States", "profile_field": "country"}
{"tool": "type_human_like", "selector": "#phone", "value": "555-1234"}
{"tool": "press_key", "key": "Tab"}
{"tool": "execute_js", "code": "document.querySelector('#date').value = '2024-01-15'"}
{"tool": "create_tool", "name": "fillDatePicker", "code": "(date) => {...}", "description": "Custom date picker"}
{"tool": "submit"}
{"tool": "done"}

FIELD MAPPING INTELLIGENCE:
- firstName, first_name, fname, givenName → profile.firstName
- lastName, last_name, lname, surname, familyName → profile.lastName
- email, emailAddress, mail → profile.email
- phone, phoneNumber, tel, mobile → profile.phone
- address, street, streetAddress → profile.address
- city, locality → profile.city
- state, region, province → profile.state
- zip, zipCode, postalCode → profile.zipCode
- country, countryCode → profile.country
- company, organization, companyName → profile.company
- jobTitle, title, position → profile.jobTitle

Only respond with a single JSON action. No explanations."""


class OllamaAgent:
    """Ollama-powered agent that decides form filling actions."""

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.timeout = 60.0
        self.conversation_history: List[Dict[str, str]] = []

    async def decide_action(
        self,
        page_state: Dict[str, Any],
        profile: Dict[str, Any],
        last_action_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Decide the next action based on page state and profile.

        Args:
            page_state: Current page info (url, fields, etc.)
            profile: User profile data to fill
            last_action_result: Result of previous action (for context)

        Returns:
            Action dict: {"tool": "fill", "selector": "...", "value": "..."}
        """
        # Build the prompt
        prompt = self._build_prompt(page_state, profile, last_action_result)

        # Get response from Ollama
        response = await self._chat(prompt)

        # Parse the action
        action = self._parse_action(response)

        return action

    def _build_prompt(
        self,
        page_state: Dict[str, Any],
        profile: Dict[str, Any],
        last_action_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the prompt for Ollama."""
        # Use unfilled_fields if available, otherwise filter from all fields
        fields = page_state.get("unfilled_fields") or page_state.get("fields", [])
        filled_selectors = page_state.get("filled_selectors", [])

        relevant_fields = []
        for f in fields:
            if f.get("disabled"):
                continue
            relevant_fields.append({
                "selector": f.get("selector", ""),
                "type": f.get("type", "text"),
                "name": f.get("name", ""),
                "labels": f.get("labels", []),
                "placeholder": f.get("placeholder", ""),
                "value": f.get("value", ""),
                "required": f.get("required", False),
                "options": f.get("options", [])[:10]  # Limit dropdown options
            })

        # Build profile summary (only non-empty values)
        profile_summary = {k: v for k, v in profile.items() if v and k != "id"}

        prompt_parts = [
            f"PAGE URL: {page_state.get('url', 'unknown')}",
        ]

        # Show already filled fields
        if filled_selectors:
            prompt_parts.append(f"\nALREADY FILLED ({len(filled_selectors)} fields): {', '.join(filled_selectors[:10])}")
            prompt_parts.append("DO NOT fill these again!")

        prompt_parts.extend([
            f"\nUNFILLED FORM FIELDS ({len(relevant_fields)} remaining):",
            json.dumps(relevant_fields[:20], indent=2),  # Limit to 20 fields
            f"\nPROFILE DATA:",
            json.dumps(profile_summary, indent=2),
        ])

        # If no unfilled fields, tell AI to submit or finish
        if len(relevant_fields) == 0:
            prompt_parts.append("\nNo more fields to fill. Use 'submit' or 'done'.")

        if last_action_result:
            prompt_parts.append(f"\nLAST ACTION RESULT: {json.dumps(last_action_result)}")

        # Add learned mappings if available
        learned = page_state.get("learned_mappings", [])
        if learned:
            prompt_parts.append("\nLEARNED MAPPINGS (use these first!):")
            for m in learned[:10]:  # Top 10 mappings
                prompt_parts.append(f"  {m['selector']} → profile.{m['profile_field']} (score: {m.get('score', 0):.2f})")

        # Add site pattern if available
        site_pattern = page_state.get("site_pattern")
        if site_pattern and site_pattern.get("success_rate", 0) > 0.5:
            prompt_parts.append(f"\nSITE PATTERN: Previously {site_pattern['success_rate']*100:.0f}% success rate")
            if site_pattern.get("field_order"):
                prompt_parts.append(f"  Successful order: {', '.join(site_pattern['field_order'][:5])}")

        prompt_parts.append("\nWhat is the next action? Return JSON only.")

        return "\n".join(prompt_parts)

    async def _chat(self, user_message: str) -> str:
        """Send message to Ollama and get response."""
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Prepare messages with system prompt
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation_history[-10:]  # Keep last 10 messages for context
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistency
                            "num_predict": 200   # Short responses
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()

                assistant_message = result.get("message", {}).get("content", "")

                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                return assistant_message

        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return '{"tool": "skip", "reason": "AI timeout"}'
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return '{"tool": "skip", "reason": "AI error"}'

    def _parse_action(self, response: str) -> Dict[str, Any]:
        """Parse Ollama response into action dict."""
        # Clean up response
        response = response.strip()

        # Try to extract JSON from response
        # Sometimes model adds explanation before/after JSON
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            try:
                action = json.loads(json_str)
                # Validate action has required fields
                if "tool" in action:
                    return action
            except json.JSONDecodeError:
                pass

        # Fallback: try to parse common patterns
        response_lower = response.lower()
        if "done" in response_lower:
            return {"tool": "done"}
        if "skip" in response_lower:
            return {"tool": "skip", "reason": "Could not parse action"}
        if "submit" in response_lower:
            return {"tool": "submit"}

        # Default: skip if we can't parse
        logger.warning(f"Could not parse Ollama response: {response[:100]}")
        return {"tool": "skip", "reason": "Invalid AI response"}

    def reset_conversation(self):
        """Reset conversation history for new site."""
        self.conversation_history.clear()

    async def analyze_captcha(self, screenshot_base64: str) -> Dict[str, Any]:
        """
        Analyze CAPTCHA using vision model.

        Args:
            screenshot_base64: Base64 encoded screenshot

        Returns:
            Analysis result with solution if possible
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": "llava",  # Vision model
                        "prompt": "This is a CAPTCHA. Can you read what it says? If it's a text CAPTCHA, provide the text. If it's an image selection CAPTCHA, describe what needs to be selected. Be concise.",
                        "images": [screenshot_base64],
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()

                return {
                    "success": True,
                    "analysis": result.get("response", ""),
                    "can_solve": "select" not in result.get("response", "").lower()
                }

        except Exception as e:
            logger.error(f"CAPTCHA analysis error: {e}")
            return {
                "success": False,
                "error": str(e),
                "can_solve": False
            }

    async def check_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "").split(":")[0] for m in models]
                    return self.model.split(":")[0] in model_names
                return False
        except Exception:
            return False
