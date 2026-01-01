#Requires -Version 5.1
<#
.SYNOPSIS
    FormAI One-Line Installer
.DESCRIPTION
    Install FormAI with one command:
    irm https://raw.githubusercontent.com/skstgu8080/formai/master/install.ps1 | iex
.NOTES
    - Downloads FormAI from GitHub
    - Sets up portable Python (no system install needed)
    - Installs all dependencies
    - Sets up Ollama AI automatically on first run
    - Creates desktop shortcut
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Faster downloads

# Configuration
$repo = "skstgu8080/formai"
$branch = "master"
$installDir = "$env:LOCALAPPDATA\FormAI"
$pythonVersion = "3.11.9"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"

# Colors
function Write-Step { param($msg) Write-Host "[>] $msg" -ForegroundColor Cyan }
function Write-OK { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

# Banner
Clear-Host
Write-Host ""
Write-Host "  ___                      _    ___" -ForegroundColor Magenta
Write-Host " | __|__ _ _ _ _ __  __ _ | |  |_ _|" -ForegroundColor Magenta
Write-Host " | _/ _ \ '_| '  \/ _' || |   | |" -ForegroundColor Magenta
Write-Host " |_|\___/_| |_|_|_\__,_||_|  |___|" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Browser Automation Platform" -ForegroundColor White
Write-Host "  One-Line Installer" -ForegroundColor Gray
Write-Host ""

# Check if already installed
if (Test-Path "$installDir\formai_server.py") {
    Write-Warn "FormAI already installed at $installDir"
    Write-Host ""
    try {
        $response = Read-Host "  Reinstall? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host ""
            Write-Host "  To start FormAI: $installDir\FormAI.bat" -ForegroundColor Cyan
            Write-Host ""
            exit 0
        }
    } catch {
        # Non-interactive, skip reinstall
        Write-Host "  To start FormAI: $installDir\FormAI.bat" -ForegroundColor Cyan
        exit 0
    }
    Write-Host ""
}

# Create install directory
Write-Step "Creating installation directory..."
if (Test-Path $installDir) {
    Remove-Item -Recurse -Force $installDir -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Write-OK "Directory: $installDir"

# Download FormAI from GitHub
Write-Step "Downloading FormAI from GitHub..."
$zipUrl = "https://github.com/$repo/archive/refs/heads/$branch.zip"
$zipPath = "$env:TEMP\formai-download.zip"
$extractPath = "$env:TEMP\formai-extract"

try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    Write-OK "Downloaded from GitHub"
} catch {
    Write-Err "Failed to download: $_"
    exit 1
}

# Extract
Write-Step "Extracting files..."
if (Test-Path $extractPath) {
    Remove-Item -Recurse -Force $extractPath
}
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
$sourceFolder = Get-ChildItem $extractPath -Directory | Select-Object -First 1
Copy-Item -Path "$($sourceFolder.FullName)\*" -Destination $installDir -Recurse -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
Write-OK "Extracted to $installDir"

# Download portable Python
Write-Step "Setting up portable Python $pythonVersion..."
$pythonDir = "$installDir\python-embed"
$pythonZip = "$env:TEMP\python-embed.zip"

try {
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip -UseBasicParsing
    New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
    Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force
    Remove-Item $pythonZip -Force

    # Enable pip in embedded Python (uncomment import site)
    $pthFile = Get-ChildItem "$pythonDir\python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName
        $content = $content -replace "#import site", "import site"
        Set-Content $pthFile.FullName $content
    }

    Write-OK "Python $pythonVersion ready"
} catch {
    Write-Err "Failed to setup Python: $_"
    exit 1
}

# Install pip
Write-Step "Installing pip..."
$python = "$pythonDir\python.exe"
try {
    $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $getPipPath = "$pythonDir\get-pip.py"
    Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -UseBasicParsing
    & $python $getPipPath --no-warn-script-location 2>$null | Out-Null
    Remove-Item $getPipPath -Force -ErrorAction SilentlyContinue
    Write-OK "pip installed"
} catch {
    Write-Warn "pip installation had issues, continuing..."
}

# Install Python dependencies
Write-Step "Installing dependencies (this takes 2-3 minutes)..."
$pip = "$pythonDir\Scripts\pip.exe"
try {
    & $pip install -r "$installDir\requirements.txt" --quiet --disable-pip-version-check 2>$null
    Write-OK "Dependencies installed"
} catch {
    Write-Warn "Some dependencies may have failed"
}

# Create optimized launcher
Write-Step "Creating launcher..."
$launcherContent = @'
@echo off
setlocal enabledelayedexpansion
title FormAI - Browser Automation
cd /d "%~dp0"

set "PYTHON=%~dp0python-embed\python.exe"

echo.
echo ========================================
echo        FormAI - Starting...
echo ========================================
echo.

REM Check/Setup Ollama AI
echo [^>] Checking AI setup...
"%PYTHON%" check_ollama_model.py
echo.

REM Check if already running
netstat -ano 2>nul | findstr ":5511.*LISTENING" > nul 2>&1
if not errorlevel 1 (
    echo [!] FormAI already running on port 5511
    echo     Opening browser...
    start http://localhost:5511
    timeout /t 2 > nul
    exit /b 0
)

REM Create directories if needed
if not exist "profiles" mkdir "profiles" 2>nul
if not exist "recordings" mkdir "recordings" 2>nul
if not exist "field_mappings" mkdir "field_mappings" 2>nul
if not exist "logs" mkdir "logs" 2>nul

echo [^>] Starting server on http://localhost:5511
echo     Press Ctrl+C to stop
echo.

REM Open browser after delay
start /min cmd /c "timeout /t 3 > nul && start http://localhost:5511"

REM Start server
"%PYTHON%" formai_server.py

echo.
echo FormAI stopped.
pause
'@

Set-Content -Path "$installDir\FormAI.bat" -Value $launcherContent -Encoding ASCII
Write-OK "Launcher created"

# Create desktop shortcut
Write-Step "Creating desktop shortcut..."
try {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = "$desktopPath\FormAI.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "$installDir\FormAI.bat"
    $shortcut.WorkingDirectory = $installDir
    $shortcut.Description = "FormAI - Browser Automation Platform"
    $shortcut.IconLocation = "shell32.dll,21"
    $shortcut.Save()
    Write-OK "Desktop shortcut created"
} catch {
    Write-Warn "Could not create shortcut: $_"
}

# Create Start Menu shortcut
try {
    $startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    $startShortcut = "$startMenuPath\FormAI.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($startShortcut)
    $shortcut.TargetPath = "$installDir\FormAI.bat"
    $shortcut.WorkingDirectory = $installDir
    $shortcut.Description = "FormAI - Browser Automation Platform"
    $shortcut.Save()
    Write-OK "Start Menu shortcut created"
} catch {
    # Silent fail for Start Menu
}

# Done!
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "    FormAI installed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location: $installDir" -ForegroundColor White
Write-Host ""
Write-Host "  To start FormAI:" -ForegroundColor White
Write-Host "    - Double-click 'FormAI' on your desktop" -ForegroundColor Cyan
Write-Host "    - Or run: $installDir\FormAI.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "  First run will:" -ForegroundColor Gray
Write-Host "    - Install Ollama AI automatically" -ForegroundColor Gray
Write-Host "    - Download AI model (~2GB)" -ForegroundColor Gray
Write-Host "    - Open http://localhost:5511" -ForegroundColor Gray
Write-Host ""

# Ask to launch
try {
    $launch = Read-Host "  Launch FormAI now? (Y/n)"
    if ($launch -ne "n" -and $launch -ne "N") {
        Write-Host ""
        Write-Host "  Starting FormAI..." -ForegroundColor Cyan
        Start-Process "$installDir\FormAI.bat" -WorkingDirectory $installDir
    }
} catch {
    # Non-interactive, auto-launch
    Write-Host ""
    Write-Host "  Starting FormAI..." -ForegroundColor Cyan
    Start-Process "$installDir\FormAI.bat" -WorkingDirectory $installDir
}
