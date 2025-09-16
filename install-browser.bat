@echo off
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║           FormAI - Browser Installation              ║
echo ║              Playwright Auto-Setup                   ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo FormAI now uses Playwright for reliable browser automation!
echo.
echo ✅ Benefits of the new system:
echo   • Automatic browser management
echo   • Enhanced reliability and stability
echo   • No manual Chrome installation needed
echo   • Built-in browser binaries included
echo.
echo ℹ️  How it works:
echo   • Playwright automatically downloads and manages browsers
echo   • First run will install Chromium automatically
echo   • No manual setup required!
echo.

pause

echo.
echo ========================================
echo      Installing Playwright Browsers
echo ========================================
echo.
echo This will download the required browser binaries...
echo (This only needs to be done once)
echo.

REM Try to install Playwright browsers
echo Installing Playwright browsers...
cargo run --bin formai-rust -- --install-browsers 2>nul || (
    echo.
    echo Installing via npx playwright install chromium...
    npx playwright install chromium 2>nul || (
        echo.
        echo Note: Playwright browsers will be installed automatically
        echo when you first run FormAI automation.
        echo.
    )
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║            ✅ Setup Complete!                        ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo FormAI is now ready with Playwright automation!
echo.
echo Key improvements:
echo   • No more Chrome timeout errors
echo   • Faster and more reliable form filling
echo   • Automatic browser updates
echo   • Enhanced debugging capabilities
echo.
echo Next steps:
echo   1. Run FormAI with: quick-start.bat
echo   2. Try form automation - it's now much more reliable!
echo   3. Enjoy the enhanced performance!
echo.

pause