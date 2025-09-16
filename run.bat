@echo off
title FormAI Simple

echo Starting FormAI...
echo.
echo Server will be available at: http://localhost:5511
echo.

:: Kill any existing processes
taskkill /F /IM python.exe >nul 2>&1

:: Start simple server
python simple_server.py

pause