#!/usr/bin/env python3
"""
Simple Playwright MCP-based Recorder
Uses Playwright MCP server for browser automation and recording
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse


class PlaywrightRecorder:
    """Simple recorder using Playwright MCP server"""

    def __init__(self, recordings_dir: str = "recordings"):
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(exist_ok=True)

        self.recording_session_id = None
        self.is_recording = False
        self.start_url = None
        self.recorded_steps = []

    def start_recording(self, url: str) -> Dict[str, Any]:
        """
        Start a new recording session

        Note: This creates the session metadata. Actual browser actions
        should be performed via the Playwright MCP tools:
        - mcp__playwright__browser_navigate
        - mcp__playwright__browser_click
        - mcp__playwright__browser_type
        - etc.

        Args:
            url: Starting URL to navigate to

        Returns:
            Dict with session info
        """
        try:
            self.recording_session_id = str(uuid.uuid4())[:8]
            self.start_url = url
            self.recorded_steps = []
            self.is_recording = True

            # Add initial navigation step
            self._add_step({
                "type": "navigate",
                "url": url,
                "assertedEvents": [{
                    "type": "navigation",
                    "url": url,
                    "title": ""
                }]
            })

            return {
                "session_id": self.recording_session_id,
                "status": "recording",
                "start_url": url,
                "message": "Recording started. Use Playwright MCP tools to perform actions."
            }

        except Exception as e:
            raise Exception(f"Failed to start recording: {e}")

    def record_action(self, action_type: str, **kwargs) -> None:
        """
        Record an action performed via Playwright MCP

        Args:
            action_type: Type of action (navigate, click, type, etc.)
            **kwargs: Action-specific parameters
        """
        if not self.is_recording:
            raise Exception("No active recording session")

        step = {"type": action_type, **kwargs}
        self._add_step(step)

    def _add_step(self, step: Dict[str, Any]) -> None:
        """Add a step to the recording"""
        self.recorded_steps.append(step)

    def get_status(self) -> Dict[str, Any]:
        """Get current recording status"""
        return {
            "session_id": self.recording_session_id,
            "status": "recording" if self.is_recording else "stopped",
            "start_url": self.start_url,
            "steps_recorded": len(self.recorded_steps)
        }

    def stop_recording(self, recording_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop recording and save the session

        Args:
            recording_name: Optional name for the recording

        Returns:
            Dict with recording metadata and file path
        """
        try:
            if not self.is_recording:
                raise Exception("No active recording session")

            self.is_recording = False

            # Generate recording name
            if not recording_name:
                domain = urlparse(self.start_url).netloc or "unknown"
                recording_name = f"Playwright Recording - {domain} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            # Create Chrome Recorder format JSON
            chrome_recording = {
                "title": recording_name,
                "steps": self.recorded_steps
            }

            # Save recording
            recording_id = str(uuid.uuid4())[:12]
            recording_file = self.recordings_dir / f"{recording_id}.json"

            with open(recording_file, 'w', encoding='utf-8') as f:
                json.dump(chrome_recording, f, indent=2)

            return {
                "recording_id": recording_id,
                "recording_name": recording_name,
                "file_path": str(recording_file),
                "total_steps": len(self.recorded_steps),
                "start_url": self.start_url,
                "chrome_format": chrome_recording
            }

        except Exception as e:
            raise Exception(f"Failed to stop recording: {e}")

    def cancel_recording(self) -> None:
        """Cancel recording without saving"""
        self.is_recording = False
        self.recorded_steps = []
        self.recording_session_id = None


class PlaywrightActionConverter:
    """Convert Playwright MCP actions to Chrome Recorder format"""

    @staticmethod
    def convert_navigate(url: str) -> Dict[str, Any]:
        """Convert navigation action"""
        return {
            "type": "navigate",
            "url": url,
            "assertedEvents": [{
                "type": "navigation",
                "url": url,
                "title": ""
            }]
        }

    @staticmethod
    def convert_click(element: str, ref: str) -> Dict[str, Any]:
        """Convert click action"""
        return {
            "type": "click",
            "target": "main",
            "selectors": [[ref]],
            "offsetX": 0,
            "offsetY": 0,
            "button": "primary"
        }

    @staticmethod
    def convert_type(element: str, ref: str, text: str) -> Dict[str, Any]:
        """Convert type/fill action"""
        return {
            "type": "change",
            "target": "main",
            "selectors": [[ref]],
            "value": text
        }

    @staticmethod
    def convert_select(element: str, ref: str, values: List[str]) -> Dict[str, Any]:
        """Convert select action"""
        return {
            "type": "change",
            "target": "main",
            "selectors": [[ref]],
            "value": values[0] if values else ""
        }


# Async wrapper for FastAPI
class AsyncPlaywrightRecorder:
    """Async wrapper for PlaywrightRecorder"""

    def __init__(self, recordings_dir: str = "recordings"):
        self.recorder = PlaywrightRecorder(recordings_dir)

    async def start_recording(self, url: str, visible: bool = True) -> Dict[str, Any]:
        """Start recording async"""
        return self.recorder.start_recording(url)

    async def record_action(self, action_type: str, **kwargs) -> None:
        """Record action async"""
        self.recorder.record_action(action_type, **kwargs)

    async def stop_recording(self, recording_name: Optional[str] = None) -> Dict[str, Any]:
        """Stop recording async"""
        return self.recorder.stop_recording(recording_name)

    async def get_status(self) -> Dict[str, Any]:
        """Get status async"""
        return self.recorder.get_status()

    async def cancel_recording(self) -> None:
        """Cancel recording async"""
        self.recorder.cancel_recording()
