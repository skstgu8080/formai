# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session History

**IMPORTANT**: Before starting work on this project, read `sessions.md` for context on recent development sessions, including:
- Recent bug fixes and feature implementations
- API endpoint additions and modifications
- Profile system enhancements and normalization fixes
- Project structure reorganization
- Error resolutions and workarounds

This file tracks the evolution of the FormAI project and will help you understand what has been recently modified or fixed.

## Essential Commands

### Development Server
- `python formai_server.py` - **RECOMMENDED: Start the Python server (port 5511)**
- `start-python.bat` - Windows batch script to start the server
- `uvicorn formai_server:app --host 127.0.0.1 --port 5511` - Start with uvicorn directly

### Build System
- `npm run build-css` - Build Tailwind CSS from input.css to tailwind.css
- `npm run watch-css` - Watch and rebuild CSS automatically

### Browser Setup
- `scripts/install-browser.bat` - Install SeleniumBase browsers for automation

## Architecture Overview

FormAI is a **high-performance browser automation platform** built with Python and SeleniumBase:

### Primary Architecture
**Python Server** (`formai_server.py`)
- **Primary and recommended backend**
- FastAPI web framework with WebSocket support
- Runs on port 5511
- Full browser automation with SeleniumBase
- AI-powered form field mapping
- Real-time progress updates via WebSocket
- Anti-bot detection bypass with UC (Undetected Chrome) mode

### Automation Engine
**SeleniumBase** (`selenium_automation.py`)
- UC mode for undetected Chrome browser automation
- CDP (Chrome DevTools Protocol) mode for enhanced stealth
- PyAutoGUI integration for CAPTCHA assistance
- Smart form field detection and mapping
- Profile-based auto-fill
- Human-like interaction delays

### Frontend Structure
- **Web Pages**: `web/` directory contains HTML pages (index.html, profiles.html, automation.html, etc.)
- **Static Assets**: `static/` directory with CSS, JS, and images
- **CSS Build**: Uses Tailwind CSS with input.css → tailwind.css compilation
- **JavaScript**: Modular JS files in `static/js/` for different features

### Data Storage
- **Profiles**: JSON files in `profiles/` directory (auto-loaded on startup)
- **Field Mappings**: Stored in `field_mappings/` directory
- **Saved URLs**: Managed in `saved_urls/` directory
- **Recordings**: Browser recordings stored in `recordings/` directory

## Key Python Modules

- `formai_server.py` - FastAPI server setup and routing
- `selenium_automation.py` - SeleniumBase automation engine
- `gui_automation.py` - PyAutoGUI helper utilities
- `recording_manager.py` - Chrome recorder import and replay
- `profile_replay_engine.py` - Profile-based automation replay
- `enhanced_field_mapper.py` - Smart field detection and mapping
- `chrome_recorder_parser.py` - Chrome DevTools recorder JSON parser

## Browser Automation

- Uses **SeleniumBase** with UC mode for undetected Chrome
- CDP mode for enhanced stealth and anti-detection
- **PyAutoGUI** for GUI automation and CAPTCHA assistance
- Headless and headed (visible) browser modes
- Anti-bot detection bypass capabilities
- Form field detection and intelligent mapping
- Real-time progress updates via WebSocket

## Development Workflow

1. **Starting Server**: Run `python formai_server.py` or `start-python.bat`
2. **CSS Changes**: Run `npm run watch-css` for live CSS rebuilding
3. **Testing**: Access via http://localhost:5511

## Project Dependencies

### Python Dependencies
- `fastapi` - Web framework with async support
- `uvicorn` - ASGI server
- `seleniumbase` - Browser automation with anti-detection
- `pyautogui` - GUI automation for CAPTCHA handling
- `websockets` - Real-time communication
- `pydantic` - Data validation
- `colorama` - Terminal colors (Windows support)

### Node.js Dependencies
- `tailwindcss` - CSS framework
- Shadcn UI components

## Configuration Files

- `requirements.txt` - Python dependencies
- `package.json` - Node.js scripts and dependencies
- `tailwind.config.js` - Tailwind CSS configuration

## Important Notes

- **Primary backend is Python** - use `python formai_server.py` to start the server
- CSS must be built with `npm run build-css` after Tailwind changes
- SeleniumBase browsers are automatically managed
- Profile data is stored as JSON files, not in a traditional database
- WebSocket communication provides real-time automation updates
- The system includes anti-bot detection bypass with UC mode
- AI models configured in `static/Models.json` for intelligent form field mapping

## Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Run the server**: `python formai_server.py` or double-click `start-python.bat`
3. **Open dashboard**: Go to http://localhost:5511
4. **Start automation**: Profiles are automatically loaded from `profiles/` directory - just start using the web interface

## Features

- **Undetected Chrome**: UC mode bypasses most bot detection systems
- **CDP Mode**: Chrome DevTools Protocol for enhanced stealth
- **Smart Field Detection**: Automatically detects and maps form fields
- **Profile Management**: Save and reuse profile data across sites
- **Recording Replay**: Import Chrome DevTools recordings and replay with profiles
- **WebSocket Updates**: Real-time progress tracking during automation
- **PyAutoGUI Integration**: Manual CAPTCHA solving assistance
