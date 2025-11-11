"""
Python wrapper for Puppeteer Replay (exact Chrome DevTools replay)

This module calls the Node.js Puppeteer Replay script which uses
the EXACT same @puppeteer/replay library that Chrome DevTools uses.
"""

import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import asyncio

logger = logging.getLogger(__name__)


class PuppeteerReplayWrapper:
    """
    Wrapper for Puppeteer Replay - uses EXACT Chrome DevTools replay engine
    """

    def __init__(self):
        """Initialize the Puppeteer Replay wrapper"""
        self.replay_script = Path(__file__).parent / "puppeteer_replay.js"
        self.progress_callback = None

        if not self.replay_script.exists():
            raise FileNotFoundError(f"Puppeteer replay script not found: {self.replay_script}")

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    async def _send_progress(self, status: str, message: str, progress: float = 0):
        """Send progress update"""
        if self.progress_callback:
            update = {
                "status": status,
                "message": message,
                "progress": progress
            }
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(update)
            else:
                self.progress_callback(update)

    async def replay_recording(
        self,
        recording: Dict[str, Any],
        profile_values: Dict[str, str] = None,
        headless: bool = False,
        step_delay: int = 1000,
        random_variation: int = 500,
        auto_close: bool = True,
        close_delay: int = 2000
    ) -> Dict[str, Any]:
        """
        Replay recording using Puppeteer Replay (exact Chrome DevTools behavior)

        Args:
            recording: Chrome DevTools recording
            profile_values: Dict mapping selectors to profile values
            headless: Run in headless mode
            step_delay: Delay between steps in milliseconds (default: 1000)
            random_variation: Random variation in delay (default: 500)
            auto_close: Automatically close browser after replay (default: True)
            close_delay: Delay before closing browser in milliseconds (default: 2000)

        Returns:
            Result dict with success status
        """
        try:
            await self._send_progress("preparing", "Preparing Puppeteer Replay...", 5)

            # Save recording to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                encoding='utf-8'
            ) as rec_file:
                json.dump(recording, rec_file, indent=2)
                recording_path = rec_file.name

            # Save profile values to temp file if provided
            profile_path = None
            if profile_values:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.json',
                    delete=False,
                    encoding='utf-8'
                ) as prof_file:
                    json.dump(profile_values, prof_file, indent=2)
                    profile_path = prof_file.name

            await self._send_progress("starting", "Starting Puppeteer Replay (exact Chrome behavior)...", 10)

            # Build command
            cmd = ['node', str(self.replay_script), recording_path]

            if profile_path:
                cmd.append(profile_path)

            if headless:
                cmd.append('--headless')

            # Add delay options
            cmd.append(f'--stepdelay={step_delay}')
            cmd.append(f'--variation={random_variation}')

            # Add auto-close options
            if auto_close:
                cmd.append('--autoclose')
            cmd.append(f'--closedelay={close_delay}')

            # Run Puppeteer Replay
            logger.info(f"Executing: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(Path(__file__).parent.parent)
            )

            # Stream output and capture all lines
            output_lines = []
            async for line in process.stdout:
                line_text = line.decode('utf-8').strip()
                if line_text:
                    output_lines.append(line_text)
                    logger.info(f"[Puppeteer] {line_text}")
                    print(f"[Puppeteer] {line_text}")  # Also print to console

                    # Parse progress from output
                    if '[Puppeteer Replay] Starting replay' in line_text:
                        await self._send_progress("replaying", "Starting replay...", 15)
                    elif '[Value Replaced]' in line_text:
                        await self._send_progress("filling", line_text, 50)
                    elif '[Step Complete]' in line_text:
                        await self._send_progress("progress", line_text, 70)
                    elif 'Replay completed successfully' in line_text:
                        await self._send_progress("completed", "Replay completed!", 100)

            # Wait for process to complete
            await process.wait()

            # Clean up temp files
            try:
                Path(recording_path).unlink()
                if profile_path:
                    Path(profile_path).unlink()
            except:
                pass

            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "Puppeteer Replay completed successfully"
                }
            else:
                error_msg = f"Puppeteer Replay failed with exit code {process.returncode}"
                if output_lines:
                    # Include last few lines of output for debugging
                    error_msg += f"\n\nLast output:\n" + "\n".join(output_lines[-10:])

                logger.error(error_msg)
                print(f"\n[ERROR] {error_msg}\n")

                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Puppeteer Replay error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


async def replay_with_profile(
    recording: Dict[str, Any],
    profile: Dict[str, Any],
    api_key: str,
    headless: bool = False,
    step_delay: int = 1000,
    random_variation: int = 500,
    auto_close: bool = True,
    close_delay: int = 2000
) -> Dict[str, Any]:
    """
    Convenience function to replay with AI value mapping + Puppeteer Replay

    Args:
        recording: Chrome DevTools recording
        profile: User profile data
        api_key: OpenRouter API key for AI mapping
        headless: Run in headless mode
        step_delay: Delay between steps in milliseconds (default: 1000)
        random_variation: Random variation in delay (default: 500)
        auto_close: Automatically close browser after replay (default: True)
        close_delay: Delay before closing browser in milliseconds (default: 2000)

    Returns:
        Replay result
    """
    from .ai_value_replacer import AIValueReplacer

    # Step 1: Use AI to map profile values to selectors
    logger.info("Using AI to map profile values to form fields...")
    replacer = AIValueReplacer(api_key)
    modified_recording = replacer.replace_recording_values(recording, profile)

    # Step 2: Extract profile values as selector → value mappings
    profile_values = {}
    for step in modified_recording.get('steps', []):
        if step.get('type') == 'change' and step.get('selectors'):
            # Get first selector as identifier
            selectors = step.get('selectors', [[]])
            if selectors and selectors[0]:
                selector = selectors[0][0]
                value = step.get('value', '')
                if value:
                    profile_values[selector] = value

    # Step 3: Replay with Puppeteer (exact Chrome behavior)
    logger.info("Replaying with Puppeteer (exact Chrome DevTools replay)...")
    wrapper = PuppeteerReplayWrapper()
    result = await wrapper.replay_recording(
        recording=recording,  # Use original recording, let Puppeteer extension replace values
        profile_values=profile_values,
        headless=headless,
        step_delay=step_delay,
        random_variation=random_variation,
        auto_close=auto_close,
        close_delay=close_delay
    )

    return result


def test_puppeteer_replay():
    """Test Puppeteer Replay with a simple recording"""
    test_recording = {
        "title": "Test Recording",
        "steps": [
            {
                "type": "navigate",
                "url": "https://www.google.com"
            }
        ]
    }

    async def run_test():
        wrapper = PuppeteerReplayWrapper()
        result = await wrapper.replay_recording(test_recording, headless=False)
        print(f"Test result: {result}")

    asyncio.run(run_test())


if __name__ == "__main__":
    test_puppeteer_replay()
