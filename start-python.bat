@echo off
setlocal enabledelayedexpansion
title FormAI - Starting...

:: Set encoding for Windows
chcp 65001 > nul 2>&1
set PYTHONIOENCODING=utf-8

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║              FormAI - Python Server                  ║
echo ╠══════════════════════════════════════════════════════╣
echo ║  SeleniumBase + PyAutoGUI Browser Automation         ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Color codes for better output
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "RESET=[0m"

:: Track setup status
set "SETUP_NEEDED=0"
set "ERROR_OCCURRED=0"

echo %CYAN%Checking system requirements...%RESET%
echo.

:: ============================================
:: Detect Python Installation
:: ============================================
set "PYTHON_CMD="

:: Check for Miniconda/Anaconda (preferred)
if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON_CMD=%USERPROFILE%\miniconda3\python.exe"
    echo %GREEN%✓ Using Miniconda Python%RESET%
) else if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_CMD=%USERPROFILE%\anaconda3\python.exe"
    echo %GREEN%✓ Using Anaconda Python%RESET%
) else (
    :: Fall back to system Python
    python --version > nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
        echo %GREEN%✓ Using system Python%RESET%
    ) else (
        echo %RED%✗ Python not found%RESET%
        echo   Please install Python from https://python.org or Miniconda
        set "ERROR_OCCURRED=1"
        goto :error_exit
    )
)

:: Display Python version
for /f "tokens=2" %%i in ('"%PYTHON_CMD%" --version 2^>^&1') do set PYTHON_VER=%%i
echo %CYAN%  Python !PYTHON_VER!%RESET%

:: ============================================
:: Install Python Dependencies
:: ============================================
echo %BLUE%Installing Python dependencies...%RESET%
echo %YELLOW%  (This will be quick if already installed)%RESET%
echo.

"%PYTHON_CMD%" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo %RED%✗ Failed to install Python dependencies%RESET%
    echo %RED%  Make sure requirements.txt is in the same folder as this script%RESET%
    set "ERROR_OCCURRED=1"
    goto :error_exit
)

echo.
echo %GREEN%✓ Python dependencies ready%RESET%

:: ============================================
:: Check Node.js (optional for CSS building)
:: ============================================
echo %BLUE%Checking Node.js...%RESET%
node --version > nul 2>&1
if !errorlevel! equ 0 (
    for /f %%i in ('node --version 2^>^&1') do set NODE_VER=%%i
    echo %GREEN%✓ Node.js !NODE_VER! found%RESET%

    :: Check if node_modules exists
    if not exist "node_modules" (
        echo %YELLOW%⚠ Node.js dependencies not installed%RESET%
        echo %BLUE%Installing Node.js dependencies...%RESET%
        call npm install
        if !errorlevel! neq 0 (
            echo %YELLOW%⚠ Failed to install Node.js dependencies%RESET%
            echo   (CSS building may not work, but server will still run)
        ) else (
            echo %GREEN%✓ Node.js dependencies installed%RESET%
            set "SETUP_NEEDED=1"
        )
    ) else (
        echo %GREEN%✓ Node.js dependencies installed%RESET%
    )

    :: Check if Tailwind CSS is built
    if not exist "static\css\tailwind.css" (
        echo %YELLOW%⚠ Tailwind CSS not built%RESET%
        echo %BLUE%Building CSS...%RESET%
        call npm run build-css
        if !errorlevel! neq 0 (
            echo %YELLOW%⚠ Failed to build CSS%RESET%
            echo   (Using fallback styles)
        ) else (
            echo %GREEN%✓ CSS built successfully%RESET%
        )
    ) else (
        echo %GREEN%✓ Tailwind CSS built%RESET%
    )
) else (
    echo %YELLOW%⚠ Node.js not found%RESET%
    echo   Node.js is optional but recommended for UI customization
    echo   Install from https://nodejs.org if you want to modify styles
)

:: ============================================
:: Check SeleniumBase Browsers
:: ============================================
echo %BLUE%Checking browser drivers...%RESET%

:: Check if SeleniumBase browsers are installed
"%PYTHON_CMD%" -c "from pathlib import Path; import sys; sys.exit(0 if (Path.home() / '.cache' / 'selenium').exists() else 1)" > nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✓ Browser drivers found%RESET%
) else (
    echo %YELLOW%⚠ Browser drivers not installed%RESET%
    echo.
    echo   SeleniumBase needs to install browser drivers for automation.
    echo.
    choice /C YN /M "   Install browser drivers now"
    if !errorlevel! equ 1 (
        echo.
        echo %BLUE%Installing browser drivers...%RESET%
        if exist "scripts\install-browser.bat" (
            call scripts\install-browser.bat
        ) else (
            sbase get chromedriver
        )
        echo %GREEN%✓ Browser drivers installed%RESET%
    ) else (
        echo %YELLOW%⚠ Skipping browser driver installation%RESET%
        echo   You can install later by running: scripts\install-browser.bat
    )
)

echo.

:: ============================================
:: Display Setup Summary
:: ============================================
if !SETUP_NEEDED! equ 1 (
    echo %GREEN%═══════════════════════════════════════════════════════%RESET%
    echo %GREEN%  Setup completed successfully!%RESET%
    echo %GREEN%═══════════════════════════════════════════════════════%RESET%
    echo.
)

:: ============================================
:: Start Server
:: ============================================
echo %CYAN%Starting FormAI Python Server...%RESET%
echo.
echo %GREEN%Server will start at: http://localhost:5511%RESET%
echo %YELLOW%Press Ctrl+C to stop the server%RESET%
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
echo %YELLOW%FormAI server stopped.%RESET%
pause
