@echo off
setlocal enabledelayedexpansion
title FormAI - Starting...

:: Set encoding for Windows
chcp 65001 > nul 2>&1
set PYTHONIOENCODING=utf-8

:: Color codes for error output
set "RED=[91m"
set "RESET=[0m"

:: Track setup status
set "ERROR_OCCURRED=0"

:: ============================================
:: Detect Python Installation
:: ============================================
set "PYTHON_CMD="

:: Check for Miniconda/Anaconda (preferred)
if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON_CMD=%USERPROFILE%\miniconda3\python.exe"
) else if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_CMD=%USERPROFILE%\anaconda3\python.exe"
) else (
    :: Fall back to system Python
    python --version > nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo %RED%ERROR: Python not found%RESET%
        echo Please install Python from https://python.org or Miniconda
        set "ERROR_OCCURRED=1"
        goto :error_exit
    )
)

:: ============================================
:: Install Python Dependencies
:: ============================================
"%PYTHON_CMD%" -m pip install -r requirements.txt --quiet --disable-pip-version-check > nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo %RED%✗ Failed to install Python dependencies%RESET%
    echo %RED%  Make sure requirements.txt is in the same folder as this script%RESET%
    set "ERROR_OCCURRED=1"
    goto :error_exit
)

:: ============================================
:: Check Node.js (optional for CSS building)
:: ============================================
node --version > nul 2>&1
if !errorlevel! equ 0 (
    :: Check if node_modules exists
    if not exist "node_modules" (
        call npm install > nul 2>&1
    )

    :: Check if Tailwind CSS is built
    if not exist "static\css\tailwind.css" (
        call npm run build-css > nul 2>&1
    )
)

:: ============================================
:: Check SeleniumBase Browsers (silent)
:: ============================================
"%PYTHON_CMD%" -c "from pathlib import Path; import sys; sys.exit(0 if (Path.home() / '.cache' / 'selenium').exists() else 1)" > nul 2>&1

:: ============================================
:: Kill any existing servers on port 5511
:: ============================================
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5511 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a > nul 2>&1
)
timeout /t 1 /nobreak > nul 2>&1

:: ============================================
:: Start Server
:: ============================================
echo FormAI Server v2.0 - Starting...
echo.

:: Auto-open browser after a short delay
start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5511"

:: Start the server
"%PYTHON_CMD%" formai_server.py

goto :end

:: ============================================
:: Error Handling
:: ============================================
:error_exit
echo.
echo %RED%═══════════════════════════════════════════════════════%RESET%
echo %RED%  Setup failed. Please fix the errors above.%RESET%
echo %RED%═══════════════════════════════════════════════════════%RESET%
echo.
pause
exit /b 1

:: ============================================
:: Normal Exit
:: ============================================
:end
echo.
echo FormAI server stopped.
pause
