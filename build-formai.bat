@echo off
:: FormAI Build Script
:: Builds FormAI.exe using PyInstaller
::
:: Usage:
::   build-formai.bat        - Interactive mode
::   build-formai.bat --ci   - CI mode (no prompts)

setlocal

cd /d "%~dp0"

:: Check for CI mode
set CI_MODE=
if "%1"=="--ci" set CI_MODE=--ci

:: Run Python build script
python scripts\build.py %CI_MODE%

endlocal
