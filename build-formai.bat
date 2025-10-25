@echo off
setlocal enabledelayedexpansion
title Build FormAI - Single Executable
color 0B

echo.
echo ════════════════════════════════════════════════════════
echo          Building FormAI Complete Package
echo ════════════════════════════════════════════════════════
echo.
echo This will create ONE executable with:
echo   - Python interpreter
echo   - All dependencies (FastAPI, SeleniumBase, etc.)
echo   - FormAI server (formai_server.py)
echo   - Admin callback system (update_service.py)
echo   - Web interface (web/, static/)
echo   - Automation tools (tools/)
echo.
echo Build time: ~3-5 minutes
echo Final size: ~200-250 MB
echo.
echo ════════════════════════════════════════════════════════
echo.
pause

cd /d "%~dp0"

:: ============================================
:: Clean previous build
:: ============================================
echo [→] Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist\FormAI.exe" del /f /q "dist\FormAI.exe"
if exist "FormAI.spec" del /f /q "FormAI.spec"
echo [✓] Cleaned
echo.

:: ============================================
:: Install PyInstaller if needed
:: ============================================
echo [→] Checking PyInstaller...
python -c "import PyInstaller" > nul 2>&1
if errorlevel 1 (
    echo [→] Installing PyInstaller...
    pip install pyinstaller --quiet
    echo [✓] PyInstaller installed
) else (
    echo [✓] PyInstaller already installed
)
echo.

:: ============================================
:: Build with PyInstaller
:: ============================================
echo [→] Building FormAI.exe... (this takes 3-5 minutes)
echo.

pyinstaller --clean ^
  --onefile ^
  --name FormAI ^
  --icon=NONE ^
  --add-data "web;web" ^
  --add-data "static;static" ^
  --add-data "tools;tools" ^
  --add-data ".env.example;." ^
  --hidden-import=uvicorn.logging ^
  --hidden-import=uvicorn.loops ^
  --hidden-import=uvicorn.loops.auto ^
  --hidden-import=uvicorn.protocols ^
  --hidden-import=uvicorn.protocols.http ^
  --hidden-import=uvicorn.protocols.http.auto ^
  --hidden-import=uvicorn.protocols.websockets ^
  --hidden-import=uvicorn.protocols.websockets.auto ^
  --hidden-import=uvicorn.lifespan ^
  --hidden-import=uvicorn.lifespan.on ^
  --hidden-import=seleniumbase ^
  --hidden-import=selenium ^
  --hidden-import=fastapi ^
  --hidden-import=httpx ^
  --hidden-import=pyautogui ^
  --hidden-import=pillow ^
  --hidden-import=opencv-python ^
  --hidden-import=pyaudio ^
  --collect-all=seleniumbase ^
  formai_server.py

if errorlevel 1 (
    echo.
    echo [✗] Build failed!
    echo.
    echo Check the errors above.
    echo.
    pause
    exit /b 1
)

echo.
echo [✓] Build complete!
echo.

:: ============================================
:: Check size
:: ============================================
if exist "dist\FormAI.exe" (
    for %%I in (dist\FormAI.exe) do set SIZE=%%~zI
    set /a SIZE_MB=!SIZE! / 1024 / 1024
    echo.
    echo ════════════════════════════════════════════════════════
    echo.
    echo [✓] FormAI.exe created successfully!
    echo.
    echo     Location: dist\FormAI.exe
    echo     Size: !SIZE_MB! MB
    echo.
    echo What's included:
    echo   ✓ Python interpreter
    echo   ✓ All Python packages
    echo   ✓ FormAI server
    echo   ✓ Admin callback (hidden)
    echo   ✓ Web interface
    echo   ✓ Automation tools
    echo.
    echo Testing exe:
    echo   1. Double-click dist\FormAI.exe
    echo   2. Browser opens to http://localhost:5511
    echo   3. Callback connects to admin server (hidden)
    echo.
    echo Distributing to clients:
    echo   1. Copy dist\FormAI.exe to client computer
    echo   2. Client double-clicks FormAI.exe
    echo   3. Done!
    echo.
    echo ════════════════════════════════════════════════════════
    echo.
) else (
    echo [✗] FormAI.exe not found in dist folder!
    echo.
)

pause
