@echo off
setlocal enabledelayedexpansion
title FormAI - Browser Automation Platform
color 0B

:: ============================================
:: Change to script directory
:: ============================================
cd /d "%~dp0"

:: ============================================
:: FormAI Simple Launcher
:: No installation, no build, just works!
:: ============================================

echo.
echo ════════════════════════════════════════════════════════
echo                     FormAI
echo          Browser Automation Platform
echo ════════════════════════════════════════════════════════
echo.

:: ============================================
:: Check Python Installation
:: ============================================
echo [→] Checking Python...

:: Check for bundled Python first
if exist "python-embed\python.exe" (
    set "PYTHON=python-embed\python.exe"
    set "PIP=python-embed\python.exe -m pip"
    for /f "tokens=2" %%i in ('%PYTHON% --version 2^>^&1') do set PYVER=%%i
    echo [✓] Using bundled Python %PYVER%
    echo     ^(Portable - no system Python needed^)
) else (
    :: Fall back to system Python
    python --version > nul 2>&1
    if errorlevel 1 (
        echo [✗] Python not found!
        echo.
        echo This package needs Python. Two options:
        echo.
        echo Option 1 - Bundle Python (Recommended):
        echo   1. Run: setup-portable-python.bat
        echo   2. This downloads Python into this folder
        echo   3. Package becomes fully standalone
        echo.
        echo Option 2 - Install Python:
        echo   1. Download from https://www.python.org/downloads/
        echo   2. Check "Add Python to PATH" during install
        echo   3. Restart this script
        echo.
        pause
        exit /b 1
    )

    set "PYTHON=python"
    set "PIP=pip"
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo [✓] Using system Python %PYVER%
)

echo.

:: ============================================
:: Check/Install Dependencies
:: ============================================
echo [→] Checking dependencies...

:: Check if requirements are already installed (quick check)
%PYTHON% -c "import fastapi, uvicorn, seleniumbase" > nul 2>&1
if errorlevel 1 (
    echo [→] Installing dependencies ^(first run only, ~2-3 minutes^)...
    echo     This only happens once!
    echo.

    :: Check if requirements.txt exists
    if exist "requirements.txt" (
        echo [→] Installing from requirements.txt...
        %PIP% install -r requirements.txt --quiet --disable-pip-version-check
    ) else (
        echo [!] requirements.txt not found, installing core dependencies...
        %PIP% install seleniumbase==4.32.0 fastapi==0.115.0 uvicorn[standard]==0.32.0 python-multipart==0.0.9 websockets aiofiles==24.1.0 pyautogui==0.9.54 pillow pyperclip numpy pydantic python-dotenv httpx beautifulsoup4 lxml colorama --quiet --disable-pip-version-check
    )

    if errorlevel 1 (
        echo.
        echo [✗] Failed to install dependencies!
        echo.
        echo Troubleshooting:
        echo   1. Check internet connection
        echo   2. Make sure pip is updated: python -m pip install --upgrade pip
        echo   3. Try manual install: pip install fastapi uvicorn seleniumbase
        echo.
        echo Current directory: %CD%
        echo Python: %PYVER%
        echo.
        pause
        exit /b 1
    )

    echo.
    echo [✓] Dependencies installed successfully!
) else (
    echo [✓] Dependencies already installed
)

echo.

:: ============================================
:: Check if Already Running
:: ============================================
echo [→] Checking if already running...

netstat -ano | findstr ":5511" > nul 2>&1
if not errorlevel 1 (
    echo [!] FormAI is already running on port 5511
    echo.
    echo     Opening browser to existing instance...
    echo.
    start http://localhost:5511
    timeout /t 2 > nul
    exit /b 0
)

echo [✓] Port 5511 is available
echo.

:: ============================================
:: Create Data Directories
:: ============================================
if not exist "profiles" mkdir "profiles" 2>nul
if not exist "recordings" mkdir "recordings" 2>nul
if not exist "recordings\imports" mkdir "recordings\imports" 2>nul
if not exist "field_mappings" mkdir "field_mappings" 2>nul
if not exist "downloaded_files" mkdir "downloaded_files" 2>nul
if not exist "training_data" mkdir "training_data" 2>nul
if not exist "logs" mkdir "logs" 2>nul

:: ============================================
:: Setup Configuration
:: ============================================
if not exist ".env" (
    if exist ".env.example" (
        echo [→] Creating default configuration...
        copy /y ".env.example" ".env" > nul 2>&1
        echo [✓] Configuration created ^(.env^)
        echo.
    )
)

:: ============================================
:: Start Callback (Hidden Background)
:: ============================================
if exist "dist\FormAI-Callback.exe" (
    start "" "dist\FormAI-Callback.exe"
)

:: ============================================
:: Start Server
:: ============================================
echo ════════════════════════════════════════════════════════
echo.
echo [✓] Starting FormAI server...
echo.
echo     Server URL: http://localhost:5511
echo     Browser will open automatically in 3 seconds...
echo.
echo     Press Ctrl+C to stop the server
echo.
echo ════════════════════════════════════════════════════════
echo.

:: Wait a moment then open browser
start /min cmd /c "timeout /t 3 > nul && start http://localhost:5511"

:: Start the Python server
%PYTHON% formai_server.py

:: Kill callback on exit
taskkill /F /IM FormAI-Callback.exe >nul 2>&1

:: If we get here, server stopped
echo.
echo.
echo ════════════════════════════════════════════════════════
echo.
echo [→] FormAI has stopped.
echo.
pause
