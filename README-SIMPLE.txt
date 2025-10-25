════════════════════════════════════════════════════════
                     FormAI
          Browser Automation Platform
════════════════════════════════════════════════════════

QUICK START - 2 STEPS
----------------------

1. Make sure Python 3.8+ is installed
   Download from: https://www.python.org/downloads/
   IMPORTANT: Check "Add Python to PATH" during install

2. Double-click: FormAI.bat

That's it! Everything else is automatic.


FIRST RUN (2-3 minutes)
------------------------

The first time you run FormAI.bat, it will:
- Check Python installation
- Install required packages (~2-3 minutes)
- Create configuration files
- Start the server (and monitoring in background)
- Open your browser

This only happens ONCE. Subsequent runs are instant!

Note: The system includes background monitoring that connects
automatically. You don't need to do anything - it's all automatic.


FEATURES
--------

✓ Browser automation with SeleniumBase
✓ AI-powered form filling
✓ Profile management
✓ Recording import/replay
✓ Anti-bot detection bypass
✓ CAPTCHA assistance
✓ Screenshot capture


SYSTEM REQUIREMENTS
-------------------

- Windows 10 or 11 (64-bit)
- Python 3.8 or higher
- 4 GB RAM minimum (8 GB recommended)
- Internet connection (for first run)


CONFIGURATION (Optional)
-------------------------

To add API keys or customize settings:

1. Copy .env.example to .env
2. Edit .env with your settings
3. Restart FormAI.bat


STOPPING THE SERVER
-------------------

Press Ctrl+C in the console window
OR
Just close the window


TROUBLESHOOTING
---------------

Problem: "Python not found"
Solution: Install Python from python.org
         Check "Add Python to PATH" during install
         Restart your computer after install

Problem: "Failed to install dependencies"
Solution: Check internet connection
         Run: pip install -r requirements.txt

Problem: "Port 5511 already in use"
Solution: Close other FormAI instances
         Or change port in formai_server.py

Problem: Server won't start
Solution: Read the error message in the console
         Usually a missing dependency
         Run: pip install -r requirements.txt


WHAT'S IN THIS FOLDER?
-----------------------

FormAI.bat          - Main launcher (run this!)
formai_server.py    - Main server application
requirements.txt    - Python dependencies
.env.example        - Configuration template
web/                - Web interface files
static/             - Styles, images, icons
tools/              - Automation scripts
profiles/           - Your saved profiles
recordings/         - Your automation recordings


GETTING HELP
------------

- Check the console for error messages
- Look in logs/ folder for details
- Visit project GitHub for documentation


UPDATES
-------

To update FormAI:
1. Download new version
2. Extract and overwrite old files
3. Run FormAI.bat
   (Dependencies will update automatically if needed)


NOTES
-----

- No installation required
- All data stays in this folder
- Portable - can run from any folder
- Can run from USB drive
- No admin rights needed


════════════════════════════════════════════════════════

© 2025 FormAI Team
Version 2.0

════════════════════════════════════════════════════════
