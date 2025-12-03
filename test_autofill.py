#!/usr/bin/env python3
"""Test the AutofillEngine with Reebok registration form."""

import asyncio
import json
import logging
from pathlib import Path

# Configure logging to DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from tools.autofill_engine import AutofillEngine

async def main():
    # Load recording
    recording_path = Path("recordings/reebok_chrome.json")
    with open(recording_path, 'r', encoding='utf-8') as f:
        recording = json.load(f)

    # Load profile
    profile_path = Path("profiles/demo-profile.json")
    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)

    print(f"\n=== Testing AutofillEngine ===")
    print(f"Recording: {recording.get('title', 'Unknown')}")
    print(f"Profile: {profile.get('name', 'Unknown')}")
    print(f"Profile data keys: {list(profile.get('data', profile).keys())}")

    # Create engine (headless=False so we can see it)
    engine = AutofillEngine(headless=False)

    # Test parsing first
    fields, checkboxes, radios, submit = engine._parse_recording(recording)
    print(f"\n=== Parsed Recording ===")
    print(f"Fields ({len(fields)}):")
    for f in fields:
        print(f"  - {f}")
    print(f"Checkboxes ({len(checkboxes)}):")
    for c in checkboxes:
        print(f"  - {c}")
    print(f"Radios ({len(radios)}): {radios}")
    print(f"Submit: {submit}")

    # Execute
    print("\nExecuting autofill...")
    result = await engine.execute(recording=recording, profile=profile)

    print(f"\n=== Result ===")
    print(f"Success: {result.success}")
    print(f"Fields filled: {result.fields_filled}")
    print(f"Checkboxes checked: {result.checkboxes_checked}")
    print(f"Radios selected: {result.radios_selected}")
    print(f"Submitted: {result.submitted}")
    if result.error:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
