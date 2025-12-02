#!/bin/bash
# FormAI Build Script for macOS/Linux
# Builds formai executable using PyInstaller
#
# Usage:
#   ./scripts/build.sh        - Interactive mode
#   ./scripts/build.sh --ci   - CI mode (no prompts)

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Run Python build script
python3 scripts/build.py "$@"
