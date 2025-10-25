#!/usr/bin/env python3
"""
Browser-Use Integration for FormAI
Wrapper around browser-use library for AI-powered form filling
"""
import asyncio
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

try:
    from browser_use import Agent, Browser
    from langchain_openai import ChatOpenAI
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    print("Warning: browser-use not installed. Run: pip install browser-use playwright langchain-openai")


class BrowserUseAutomation:
    """AI-powered browser automation using browser-use library"""

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize browser-use automation

        Args:
            openai_api_key: OpenAI API key (optional, will use env var if not provided)
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError("browser-use library not installed")

        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or parameters")

    def _profile_to_task_prompt(self, profile: Dict[str, Any], url: str) -> str:
        """
        Convert FormAI profile to browser-use task prompt

        Args:
            profile: FormAI profile dictionary
            url: Target URL to fill

        Returns:
            Task prompt string for browser-use Agent
        """
        # Extract profile data
        profile_info = {}

        # Handle both flat and nested profile structures
        if "personal_info" in profile:
            # Nested structure
            personal = profile.get("personal_info", {})
            contact = profile.get("contact_info", {})
            address = profile.get("address", {})

            profile_info.update({
                "first_name": personal.get("first_name", ""),
                "last_name": personal.get("last_name", ""),
                "email": contact.get("email", ""),
                "phone": contact.get("phone", ""),
                "address": address.get("street", ""),
                "city": address.get("city", ""),
                "state": address.get("state", ""),
                "zip": address.get("zip", ""),
                "country": address.get("country", ""),
            })
        else:
            # Flat structure
            profile_info = {k: v for k, v in profile.items() if v}

        # Build task prompt
        task = f"""
Fill out the form at {url} with the following information:

{json.dumps(profile_info, indent=2)}

Instructions:
- Navigate to the URL and wait for the page to load
- Identify all form fields on the page
- Match the profile information to the appropriate form fields
- Fill out each field with the corresponding data
- If a field is required but not in the profile, make a reasonable guess or skip it
- Submit the form when all required fields are filled
- Return a summary of what was filled and whether submission succeeded

IMPORTANT:
- Only fill fields that clearly match the profile data
- Don't submit if critical information is missing
- Report any errors or issues encountered
"""
        return task.strip()

    async def fill_form(
        self,
        url: str,
        profile: Dict[str, Any],
        headless: bool = False,
        max_steps: int = 50
    ) -> Dict[str, Any]:
        """
        Use AI to automatically fill a form

        Args:
            url: Target URL to fill
            profile: FormAI profile data
            headless: Run browser in headless mode
            max_steps: Maximum number of steps for the agent

        Returns:
            Results dictionary with:
            - success: bool
            - actions_taken: list of actions
            - final_result: summary from agent
            - error: error message if failed
        """
        try:
            # Create task prompt
            task = self._profile_to_task_prompt(profile, url)

            # Initialize LLM
            llm = ChatOpenAI(
                model="gpt-4o",
                api_key=self.openai_api_key
            )

            # Initialize browser
            browser = Browser(
                headless=headless,
                # disable_security=True,  # May help with some sites
            )

            # Create and run agent
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_steps=max_steps,
            )

            # Run the agent
            history = await agent.run()

            # Extract results
            actions_taken = []
            for step in history.history:
                if hasattr(step, 'action'):
                    actions_taken.append({
                        "type": step.action.__class__.__name__,
                        "description": str(step.action),
                    })

            return {
                "success": True,
                "url": url,
                "actions_taken": actions_taken,
                "total_steps": len(history.history),
                "final_result": history.final_result(),
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "actions_taken": [],
                "total_steps": 0,
                "final_result": None,
                "error": str(e)
            }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test browser-use setup

        Returns:
            Test results
        """
        try:
            # Simple test task
            llm = ChatOpenAI(
                model="gpt-4o",
                api_key=self.openai_api_key
            )

            browser = Browser(headless=True)

            agent = Agent(
                task="Navigate to google.com and return the page title",
                llm=llm,
                browser=browser,
                max_steps=3,
            )

            history = await agent.run()

            return {
                "success": True,
                "message": "Browser-use is working correctly",
                "result": history.final_result()
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Browser-use test failed: {str(e)}",
                "result": None
            }


# Async wrapper for FastAPI
class AsyncBrowserUseAutomation:
    """Async wrapper for BrowserUseAutomation"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.automation = BrowserUseAutomation(openai_api_key)

    async def fill_form(
        self,
        url: str,
        profile: Dict[str, Any],
        headless: bool = False,
        max_steps: int = 50
    ) -> Dict[str, Any]:
        """Fill form async"""
        return await self.automation.fill_form(url, profile, headless, max_steps)

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection async"""
        return await self.automation.test_connection()
