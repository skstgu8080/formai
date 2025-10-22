@echo off
title FormAI Admin Server
color 0B

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║         FormAI Admin Monitoring Server           ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  Monitor and control all FormAI installations       ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo Please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

:: Auto-open browser after delay
start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5512"

:: Start admin server
echo Starting Admin Server on port 5512...
echo.
python admin_server.py

pause
