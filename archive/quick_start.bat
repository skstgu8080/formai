@echo off
title FormAI Server - SeleniumBase Edition
cls

echo ==========================================
echo     FormAI v2.0 - SeleniumBase Edition
echo ==========================================
echo.

REM Kill any existing Python processes
echo Cleaning up existing processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM chrome.exe >nul 2>&1
taskkill /F /IM chromedriver.exe >nul 2>&1
timeout /t 1 >nul

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Install/Update dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check

REM Install SeleniumBase browser drivers
echo.
echo Setting up browser drivers...
seleniumbase install chromedriver --quiet

REM Install PyAutoGUI dependencies (for Windows)
pip install pyperclip --quiet

REM Build CSS if needed
if exist "package.json" (
    if not exist "static\css\tailwind.css" (
        echo Building CSS...
        npm run build-css
    )
)

REM Create necessary directories
if not exist "profiles" mkdir profiles
if not exist "field_mappings" mkdir field_mappings
if not exist "recordings" mkdir recordings
if not exist "saved_urls" mkdir saved_urls

REM Start the server
echo.
echo ==========================================
echo Starting FormAI Server...
echo ==========================================
echo.
echo Server will be available at:
echo   http://localhost:5511
echo.
echo Press Ctrl+C to stop the server
echo ==========================================
echo.

REM Run the FastAPI server
python formai_server.py

REM Cleanup on exit
echo.
echo Server stopped.
pause