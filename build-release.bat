@echo off
echo.
echo ========================================
echo     FormAI - One-Time Build Setup
echo ========================================
echo.
echo This will create a fast-starting executable.
echo You only need to run this once!
echo.

REM Kill any existing processes
echo Stopping any running instances...
taskkill /F /IM cargo.exe >nul 2>&1
taskkill /F /IM formai-rust.exe >nul 2>&1
timeout /t 2 >nul

REM Clean any lock files
if exist "target\.rustc_info.json" del "target\.rustc_info.json" >nul 2>&1
if exist "target\CACHEDIR.TAG" del "target\CACHEDIR.TAG" >nul 2>&1

REM Build CSS if needed
if exist package.json (
    if not exist node_modules (
        echo Installing dependencies...
        call npm install
    )
    echo Building CSS...
    call npm run build-css
)

echo.
echo Building optimized executable...
echo This may take 2-3 minutes but only happens once.
echo.

cargo build --release

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    ✅ BUILD SUCCESSFUL!
echo ========================================
echo.
echo FormAI has been compiled successfully!
echo.
echo From now on, you can start FormAI instantly using:
echo    - start-fast.bat (instant startup)
echo    - Or directly: target\release\formai-rust.exe
echo.
echo The application will start in under 1 second!
echo.
pause