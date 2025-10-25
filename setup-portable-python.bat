@echo off
setlocal enabledelayedexpansion
title FormAI - Setup Portable Python
color 0B

echo.
echo ════════════════════════════════════════════════════════
echo          Setup Portable Python for FormAI
echo ════════════════════════════════════════════════════════
echo.
echo This will download and setup a portable Python installation
echo that can be distributed with FormAI.
echo.
echo Target computers will NOT need Python installed!
echo.
echo Download size: ~30 MB
echo Final package size: ~100-150 MB
echo.
echo ════════════════════════════════════════════════════════
echo.
pause

cd /d "%~dp0"

:: ============================================
:: Check if already exists
:: ============================================
if exist "python-embed" (
    echo [!] python-embed folder already exists
    echo.
    choice /C YN /M "Do you want to download it again"
    if errorlevel 2 goto :skip_download
    echo.
    echo [→] Removing old python-embed folder...
    rmdir /s /q "python-embed"
)

:: ============================================
:: Download Python Embeddable
:: ============================================
echo.
echo [1/5] Downloading Python 3.12.0 embeddable package...
echo [→] This is ~30 MB, please wait...
echo.

set "PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip"
set "PYTHON_ZIP=python-embed.zip"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing"

if not exist "%PYTHON_ZIP%" (
    echo [✗] Failed to download Python!
    echo.
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo [✓] Python downloaded

:: ============================================
:: Extract Python
:: ============================================
echo.
echo [2/5] Extracting Python...

mkdir "python-embed" 2>nul
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath 'python-embed' -Force"

if not exist "python-embed\python.exe" (
    echo [✗] Failed to extract Python!
    pause
    exit /b 1
)

echo [✓] Python extracted

:: Clean up zip
del "%PYTHON_ZIP%" 2>nul

:skip_download

:: ============================================
:: Configure Python
:: ============================================
echo.
echo [3/5] Configuring Python for packages...

:: Enable site-packages
(
echo python312.zip
echo .
echo.
echo # Uncommented to enable site-packages
echo import site
echo.
echo # Additional paths
echo Lib\site-packages
) > "python-embed\python312._pth"

echo [✓] Python configured

:: ============================================
:: Install pip
:: ============================================
echo.
echo [4/5] Installing pip...

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"

if exist "get-pip.py" (
    python-embed\python.exe get-pip.py
    del get-pip.py
    echo [✓] Pip installed
) else (
    echo [⚠] Could not download pip installer
    echo    You can install it manually later
)

:: ============================================
:: Install Dependencies
:: ============================================
echo.
echo [5/5] Pre-installing dependencies...
echo [→] This may take 2-3 minutes...
echo.

if exist "requirements.txt" (
    python-embed\python.exe -m pip install -r requirements.txt
    echo.
    echo [✓] Dependencies pre-installed
) else (
    echo [!] requirements.txt not found
    echo    Dependencies will be installed on first run
)

:: ============================================
:: Complete
:: ============================================
echo.
echo ════════════════════════════════════════════════════════
echo.
echo [✓] Portable Python setup complete!
echo.
echo What was created:
echo   python-embed\            Portable Python folder
echo   python-embed\python.exe  Python 3.12.0
echo   python-embed\Lib\        Python packages
echo.
echo Your FormAI distribution now includes Python!
echo.
echo Next steps:
echo   1. Test it: FormAI.bat
echo   2. ZIP the entire FormAI folder
echo   3. Share the ZIP with anyone
echo   4. They extract and run FormAI.bat
echo   5. Works on any Windows PC (no Python install needed!)
echo.
echo Package size: ~100-150 MB
echo.
echo ════════════════════════════════════════════════════════
echo.
pause
