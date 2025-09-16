@echo off
echo Starting FormAI Enhanced Server...
echo.

REM Kill any existing processes
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM formai-rust.exe >nul 2>&1

echo Starting Python server...
REM Start the enhanced Python server and keep it visible
python -u formai_enhanced_server.py