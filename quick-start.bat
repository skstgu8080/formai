@echo off
setlocal enabledelayedexpansion
title FormAI Quick Start

:: Set encoding for Windows
chcp 65001 > nul 2>&1
set PYTHONIOENCODING=utf-8

echo.
echo ===============================================
echo           FormAI Quick Start
echo ===============================================
echo.

:: Color codes for better output
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

:: Track if we have all dependencies
set "DEPS_OK=1"

echo %BLUE%Checking dependencies...%RESET%
echo.

:: Check Python
python --version > nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
    echo %GREEN%✓ Python !PYTHON_VER! found%RESET%
) else (
    echo %RED%✗ Python not found or not in PATH%RESET%
    echo   Please install Python from https://python.org
    set "DEPS_OK=0"
)

:: Check Node.js
node --version > nul 2>&1
if !errorlevel! equ 0 (
    for /f %%i in ('node --version 2^>^&1') do set NODE_VER=%%i
    echo %GREEN%✓ Node.js !NODE_VER! found%RESET%
) else (
    echo %RED%✗ Node.js not found or not in PATH%RESET%
    echo   Please install Node.js from https://nodejs.org
    set "DEPS_OK=0"
)

:: Check Rust
cargo --version > nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2" %%i in ('cargo --version 2^>^&1') do set RUST_VER=%%i
    echo %GREEN%✓ Rust/Cargo !RUST_VER! found%RESET%
) else (
    echo %RED%✗ Rust/Cargo not found or not in PATH%RESET%
    echo   Please install Rust from https://rustup.rs
    set "DEPS_OK=0"
)

:: Check Chrome/Chromium
set "CHROME_FOUND=0"
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME_FOUND=1"

if !CHROME_FOUND! equ 1 (
    echo %GREEN%✓ Chrome browser found%RESET%
) else (
    echo %YELLOW%⚠ Chrome not found in standard locations%RESET%
    echo   FormAI will still work, but may need browser setup
)

echo.

:: Exit if critical dependencies missing
if !DEPS_OK! equ 0 (
    echo %RED%Missing critical dependencies. Please install them and try again.%RESET%
    echo.
    pause
    exit /b 1
)

echo %GREEN%All dependencies found!%RESET%
echo.

:: Kill any existing processes
echo %BLUE%Cleaning up existing processes...%RESET%
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM formai-rust.exe >nul 2>&1
taskkill /F /IM cargo.exe >nul 2>&1

:: Check if CSS needs building
echo %BLUE%Checking CSS build status...%RESET%
if not exist "static\css\tailwind.css" (
    echo %YELLOW%CSS not built. Building Tailwind CSS...%RESET%
    if not exist "node_modules" (
        echo %BLUE%Installing Node.js dependencies...%RESET%
        call npm install
        if !errorlevel! neq 0 (
            echo %RED%Failed to install Node.js dependencies%RESET%
            pause
            exit /b 1
        )
    )

    echo %BLUE%Building CSS...%RESET%
    call npm run build-css
    if !errorlevel! neq 0 (
        echo %RED%Failed to build CSS%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✓ CSS built successfully%RESET%
) else (
    echo %GREEN%✓ CSS already built%RESET%
)

echo.
echo %BLUE%Starting FormAI Enhanced Python Server...%RESET%
echo.
echo %GREEN%Server will start at: http://localhost:5511%RESET%
echo %GREEN%Dashboard will open automatically in your browser%RESET%
echo.
echo %YELLOW%Press Ctrl+C to stop the server%RESET%
echo.

:: Start server and open browser
start "Opening Browser" timeout /t 3 /nobreak >nul && start http://localhost:5511
python -u formai_enhanced_server.py

echo.
echo %YELLOW%FormAI server stopped.%RESET%
pause