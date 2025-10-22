@echo off
echo ===========================
echo Testing Python Installation
echo ===========================
echo.

echo Step 1: Checking Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo.
echo Step 2: Testing Python import...
python -c "import sys; print('Python works!')"
if %errorlevel% neq 0 (
    echo ERROR: Python import failed!
    pause
    exit /b 1
)

echo.
echo Step 3: Checking packages...
python -c "import seleniumbase, fastapi, uvicorn; print('All packages installed!')" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Packages not installed. Install now? (Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        echo Installing packages...
        python -m pip install -r requirements.txt
    )
)

echo.
echo ===========================
echo All checks complete!
echo ===========================
pause
