#!/usr/bin/env python3
"""
MCP Controller - Wrapper for Playwright MCP tool calls
Provides clean interface for browser automation via MCP
"""
import json
from typing import Dict, Any, List, Optional


class MCPController:
    """Controller for Playwright MCP browser automation"""

    def __init__(self):
        self.browser_started = False
        self.current_url = None

    async def navigate(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        """
        Navigate to URL using Playwright MCP

        Args:
            url: Target URL
            timeout: Navigation timeout in milliseconds

        Returns:
            Navigation result
        """
        try:
            # Use Playwright MCP navigate tool
            from mcp__playwright__browser_navigate import browser_navigate

            result = await browser_navigate(url=url, timeout=timeout)
            self.current_url = url
            self.browser_started = True

            return {
                "success": True,
                "url": url,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def take_snapshot(self) -> Dict[str, Any]:
        """
        Take accessibility tree snapshot of current page

        Returns:
            Snapshot data with form fields
        """
        try:
            from mcp__playwright__browser_snapshot import browser_snapshot

            snapshot = await browser_snapshot()

            return {
                "success": True,
                "snapshot": snapshot,
                "url": self.current_url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def fill_field(self, selector: str, value: str, field_name: str = None) -> Dict[str, Any]:
        """
        Fill a single form field

        Args:
            selector: CSS selector or ARIA selector
            value: Value to fill
            field_name: Human-readable field name for logging

        Returns:
            Fill result
        """
        try:
            from mcp__playwright__browser_type import browser_type

            result = await browser_type(
                element=field_name or selector,
                ref=selector,
                text=value,
                submit=False
            )

            return {
                "success": True,
                "field": field_name or selector,
                "value": value,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "field": field_name or selector,
                "error": str(e)
            }

    async def select_option(self, selector: str, value: str, field_name: str = None) -> Dict[str, Any]:
        """
        Select option from dropdown

        Args:
            selector: CSS selector for select element
            value: Option value to select
            field_name: Human-readable field name

        Returns:
            Selection result
        """
        try:
            from mcp__playwright__browser_select_option import browser_select_option

            result = await browser_select_option(
                element=field_name or selector,
                ref=selector,
                values=[value]
            )

            return {
                "success": True,
                "field": field_name or selector,
                "value": value,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "field": field_name or selector,
                "error": str(e)
            }

    async def click_element(self, selector: str, element_name: str = None) -> Dict[str, Any]:
        """
        Click an element (button, link, etc.)

        Args:
            selector: CSS selector
            element_name: Human-readable element name

        Returns:
            Click result
        """
        try:
            from mcp__playwright__browser_click import browser_click

            result = await browser_click(
                element=element_name or selector,
                ref=selector
            )

            return {
                "success": True,
                "element": element_name or selector,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "element": element_name or selector,
                "error": str(e)
            }

    async def take_screenshot(self, filename: str = None, full_page: bool = False) -> Dict[str, Any]:
        """
        Take screenshot of current page

        Args:
            filename: Optional filename to save to
            full_page: Take full page screenshot vs viewport

        Returns:
            Screenshot result with base64 image data
        """
        try:
            from mcp__playwright__browser_take_screenshot import browser_take_screenshot

            result = await browser_take_screenshot(
                filename=filename,
                fullPage=full_page
            )

            return {
                "success": True,
                "screenshot": result,
                "filename": filename,
                "url": self.current_url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def evaluate_script(self, script: str) -> Dict[str, Any]:
        """
        Execute JavaScript in page context

        Args:
            script: JavaScript code to execute

        Returns:
            Evaluation result
        """
        try:
            from mcp__playwright__browser_evaluate import browser_evaluate

            result = await browser_evaluate(function=script)

            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def fill_form(self, fields: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fill multiple form fields at once

        Args:
            fields: List of {name, ref, type, value} dicts

        Returns:
            Fill result with success count
        """
        try:
            from mcp__playwright__browser_fill_form import browser_fill_form

            result = await browser_fill_form(fields=fields)

            return {
                "success": True,
                "fields_filled": len(fields),
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "fields_attempted": len(fields)
            }

    async def close(self) -> Dict[str, Any]:
        """
        Close browser

        Returns:
            Close result
        """
        try:
            from mcp__playwright__browser_close import browser_close

            result = await browser_close()
            self.browser_started = False
            self.current_url = None

            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_mcp_controller = None

def get_mcp_controller() -> MCPController:
    """Get or create MCP controller instance"""
    global _mcp_controller
    if _mcp_controller is None:
        _mcp_controller = MCPController()
    return _mcp_controller
