#!/usr/bin/env python3
"""
Chrome DevTools MCP Replay Engine
Replays recordings using Chrome DevTools MCP tools
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path


class ChromeDevToolsReplay:
    """Replay recordings using Chrome DevTools MCP"""

    def __init__(self, mcp_tools: Dict[str, Callable]):
        """
        Initialize replay engine with MCP tools

        Args:
            mcp_tools: Dictionary of MCP tool functions (navigate_page, fill, click, etc.)
        """
        self.mcp_tools = mcp_tools
        self.progress_callback = None
        self.replay_stats = {
            "start_time": None,
            "end_time": None,
            "recording_id": None,
            "total_fields": 0,
            "successful_fields": 0,
            "failed_fields": 0,
            "errors": [],
            "execution_times": [],
            "field_results": []
        }

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    async def _send_progress_update(self, status: str, message: str, progress: float = 0, field_data: Dict = None):
        """Send progress update to callback if available"""
        if self.progress_callback:
            update = {
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
                "field_data": field_data or {},
                "stats": self.replay_stats.copy()
            }
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(update)
            else:
                self.progress_callback(update)

    async def replay_recording(
        self,
        recording: Dict[str, Any],
        profile: Optional[Dict[str, Any]] = None,
        use_recorded_values: bool = True
    ) -> Dict[str, Any]:
        """
        Replay a recording using Chrome DevTools MCP

        Args:
            recording: Recording data with steps
            profile: Optional profile data for production mode
            use_recorded_values: If True, use values from recording; if False, use profile

        Returns:
            Dict with replay results
        """
        try:
            self.replay_stats["start_time"] = datetime.now().isoformat()
            self.replay_stats["recording_id"] = recording.get("recording_id", "unknown")

            recording_name = recording.get("recording_name") or recording.get("title", "Unknown Recording")
            await self._send_progress_update("loading", f"Loaded recording: {recording_name}")

            # Get steps from recording
            steps = recording.get("steps", [])
            if not steps:
                raise Exception("No steps found in recording")

            self.replay_stats["total_fields"] = len([s for s in steps if s.get("type") == "change"])

            # Navigate to starting URL
            start_url = recording.get("url")
            if not start_url:
                raise Exception("No URL found in recording")

            await self._send_progress_update("navigating", f"Navigating to {start_url}...", 5)

            # Use Chrome DevTools MCP to navigate
            navigate_result = await self.mcp_tools["navigate_page"](url=start_url)

            await self._send_progress_update("navigated", "Page loaded successfully", 10)

            # Wait a bit for page to load
            await asyncio.sleep(2)

            # Take snapshot to see page structure
            await self._send_progress_update("analyzing", "Analyzing page structure...", 15)
            snapshot = await self.mcp_tools["take_snapshot"]()

            # Replay each step
            total_steps = len(steps)
            for idx, step in enumerate(steps):
                step_progress = 15 + (idx / total_steps * 75)

                step_type = step.get("type")

                if step_type == "navigate":
                    # Already handled initial navigation
                    continue

                elif step_type == "change":
                    # Fill form field
                    await self._replay_fill_step(step, profile, use_recorded_values, step_progress)

                elif step_type == "click":
                    # Click element
                    await self._replay_click_step(step, step_progress)

                # Small delay between steps for human-like behavior
                await asyncio.sleep(0.5)

            # Replay completed successfully
            self.replay_stats["end_time"] = datetime.now().isoformat()
            await self._send_progress_update("completed", "Replay completed successfully!", 100)

            return {
                "success": True,
                "stats": self.replay_stats,
                "message": "Replay completed successfully"
            }

        except Exception as e:
            error_msg = str(e)
            self.replay_stats["errors"].append(error_msg)
            self.replay_stats["end_time"] = datetime.now().isoformat()
            await self._send_progress_update("error", f"Replay failed: {error_msg}", 0)

            return {
                "success": False,
                "stats": self.replay_stats,
                "error": error_msg
            }

    async def _replay_fill_step(
        self,
        step: Dict[str, Any],
        profile: Optional[Dict[str, Any]],
        use_recorded_values: bool,
        progress: float
    ):
        """Replay a fill/change step"""
        try:
            field_mapping = step.get("field_mapping", {})
            form_field = field_mapping.get("form_field", "unknown")
            profile_field = field_mapping.get("profile_field", "")

            # Determine which value to use
            if use_recorded_values:
                # Use the recorded value (preview mode)
                value = step.get("value", "")
                mode = "preview"
            else:
                # Use profile value (production mode)
                if not profile:
                    raise Exception("No profile provided for production mode")
                value = profile.get(profile_field, "")
                mode = "production"

            await self._send_progress_update(
                "filling",
                f"Filling {form_field} ({mode} mode)...",
                progress,
                {"field": form_field, "mode": mode}
            )

            # Get selectors - try aria label first, then CSS
            selectors = step.get("selectors", [])

            # Try to find element using selectors
            element_found = False
            for selector_list in selectors:
                if not selector_list:
                    continue

                selector = selector_list[0] if isinstance(selector_list, list) else selector_list

                # For aria selectors, extract the label
                if selector.startswith("aria/"):
                    aria_label = selector.replace("aria/", "")

                    # Use Chrome DevTools MCP to fill the field
                    try:
                        # First, take snapshot to find element UID
                        snapshot = await self.mcp_tools["take_snapshot"]()

                        # Search for element in snapshot by aria label or text
                        # This is simplified - in reality we'd parse the snapshot
                        # For now, we'll use a heuristic to find the element

                        # Try to fill using aria label directly
                        # Note: This is a simplified approach
                        # In production, we'd parse the snapshot to find the exact UID

                        await self.mcp_tools["fill"](
                            uid=f"aria_{aria_label.lower().replace(' ', '_')}",
                            value=value
                        )

                        element_found = True
                        break
                    except Exception as e:
                        # Try next selector
                        continue

            if element_found:
                self.replay_stats["successful_fields"] += 1
                self.replay_stats["field_results"].append({
                    "field": form_field,
                    "status": "success",
                    "value": value[:20] + "..." if len(value) > 20 else value
                })
            else:
                self.replay_stats["failed_fields"] += 1
                self.replay_stats["field_results"].append({
                    "field": form_field,
                    "status": "failed",
                    "error": "Element not found"
                })

        except Exception as e:
            self.replay_stats["failed_fields"] += 1
            self.replay_stats["errors"].append(f"Field {form_field}: {str(e)}")
            await self._send_progress_update("warning", f"Failed to fill {form_field}: {str(e)}", progress)

    async def _replay_click_step(self, step: Dict[str, Any], progress: float):
        """Replay a click step"""
        try:
            target = step.get("target", "unknown")
            await self._send_progress_update("clicking", f"Clicking {target}...", progress)

            # Get selectors
            selectors = step.get("selectors", [])

            # Try to click using selectors
            for selector_list in selectors:
                if not selector_list:
                    continue

                selector = selector_list[0] if isinstance(selector_list, list) else selector_list

                if selector.startswith("aria/"):
                    aria_label = selector.replace("aria/", "")

                    try:
                        await self.mcp_tools["click"](
                            element=aria_label,
                            uid=f"aria_{aria_label.lower().replace(' ', '_')}"
                        )
                        break
                    except Exception as e:
                        continue

        except Exception as e:
            self.replay_stats["errors"].append(f"Click {target}: {str(e)}")
            await self._send_progress_update("warning", f"Failed to click {target}: {str(e)}", progress)
