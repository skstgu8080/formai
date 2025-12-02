# FormAI Installer for Windows (PowerShell)
# Usage: irm https://raw.githubusercontent.com/KoodosBots/formai/master/install.ps1 | iex

$ErrorActionPreference = "Stop"

# Configuration
$INSTALL_DIR = "$env:LOCALAPPDATA\FormAI"
$GITHUB_REPO = "skstgu8080/formai"
$VERSION = if ($env:FORMAI_VERSION) { $env:FORMAI_VERSION } else { "latest" }

function Write-Banner {
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║         " -NoNewline -ForegroundColor Cyan
    Write-Host "FormAI Installer" -NoNewline -ForegroundColor Green
    Write-Host "              ║" -ForegroundColor Cyan
    Write-Host "  ╚═══════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Get-Architecture {
    $arch = [System.Environment]::GetEnvironmentVariable("PROCESSOR_ARCHITECTURE")
    switch ($arch) {
        "AMD64" { return "x64" }
        "x86"   { return "x86" }
        "ARM64" { return "arm64" }
        default {
            Write-Host "Unsupported architecture: $arch" -ForegroundColor Red
            exit 1
        }
    }
}

function Get-LatestVersion {
    if ($VERSION -eq "latest") {
        try {
            $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/$GITHUB_REPO/releases/latest" -Headers @{ "User-Agent" = "FormAI-Installer" }
            return $releases.tag_name
        } catch {
            Write-Host "Could not detect latest version, using v1.0.0" -ForegroundColor Yellow
            return "v1.0.0"
        }
    }
    return $VERSION
}

function Install-FormAI {
    param (
        [string]$Version,
        [string]$Arch
    )

    $downloadUrl = "https://github.com/$GITHUB_REPO/releases/download/$Version/formai-windows-$Arch.zip"

    Write-Host "  Downloading FormAI $Version for Windows $Arch..." -ForegroundColor Blue

    # Create temp directory
    $tempDir = New-Item -ItemType Directory -Path "$env:TEMP\formai-install-$(Get-Random)" -Force

    try {
        # Download
        $zipPath = Join-Path $tempDir "formai.zip"
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        } catch {
            Write-Host "Failed to download from: $downloadUrl" -ForegroundColor Red
            Write-Host "Release may not exist yet. Please check: https://github.com/$GITHUB_REPO/releases" -ForegroundColor Yellow
            exit 1
        }

        # Create install directory
        if (Test-Path $INSTALL_DIR) {
            Write-Host "  Removing existing installation..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $INSTALL_DIR
        }
        New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null

        # Extract
        Write-Host "  Installing to $INSTALL_DIR..." -ForegroundColor Blue
        Expand-Archive -Path $zipPath -DestinationPath $INSTALL_DIR -Force

    } finally {
        # Cleanup temp
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

function Add-ToPath {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")

    if ($userPath -notlike "*$INSTALL_DIR*") {
        $newPath = "$userPath;$INSTALL_DIR"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "  Added $INSTALL_DIR to PATH" -ForegroundColor Green

        # Update current session
        $env:Path = "$env:Path;$INSTALL_DIR"
    }
}

function New-Shortcut {
    param (
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$Description
    )

    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.Description = $Description
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.Save()
}

function Create-Shortcuts {
    # Desktop shortcut
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $desktopShortcut = Join-Path $desktopPath "FormAI.lnk"

    $exePath = Join-Path $INSTALL_DIR "FormAI.exe"
    if (-not (Test-Path $exePath)) {
        $exePath = Join-Path $INSTALL_DIR "formai.exe"
    }

    if (Test-Path $exePath) {
        New-Shortcut -ShortcutPath $desktopShortcut -TargetPath $exePath -Description "FormAI - Form Automation"
        Write-Host "  Created desktop shortcut" -ForegroundColor Green

        # Start Menu shortcut
        $startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
        $startMenuShortcut = Join-Path $startMenuPath "FormAI.lnk"
        New-Shortcut -ShortcutPath $startMenuShortcut -TargetPath $exePath -Description "FormAI - Form Automation"
        Write-Host "  Created Start Menu shortcut" -ForegroundColor Green
    }
}

function Write-Success {
    Write-Host ""
    Write-Host "  ✓ FormAI installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  To start FormAI:" -ForegroundColor Cyan
    Write-Host "    formai" -ForegroundColor Yellow -NoNewline
    Write-Host "  (from any terminal)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Or double-click:" -ForegroundColor Cyan
    Write-Host "    Desktop shortcut or Start Menu" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Dashboard:" -ForegroundColor Cyan
    Write-Host "    http://localhost:5511" -ForegroundColor Yellow
    Write-Host ""
}

function Start-FormAINow {
    $response = Read-Host "  Start FormAI now? [Y/n]"

    if ($response -ne "n" -and $response -ne "N") {
        Write-Host "  Starting FormAI..." -ForegroundColor Green

        $exePath = Join-Path $INSTALL_DIR "FormAI.exe"
        if (-not (Test-Path $exePath)) {
            $exePath = Join-Path $INSTALL_DIR "formai.exe"
        }

        if (Test-Path $exePath) {
            Start-Process -FilePath $exePath -WorkingDirectory $INSTALL_DIR

            # Wait and open browser
            Start-Sleep -Seconds 3
            Start-Process "http://localhost:5511"
        } else {
            Write-Host "  Could not find FormAI executable" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Run 'formai' to start FormAI later." -ForegroundColor Yellow
    }
}

# Main
function Main {
    Write-Banner

    $arch = Get-Architecture
    Write-Host "  Detected: Windows $arch" -ForegroundColor Cyan

    $version = Get-LatestVersion
    Write-Host "  Version: $version" -ForegroundColor Cyan
    Write-Host ""

    Install-FormAI -Version $version -Arch $arch
    Add-ToPath
    Create-Shortcuts
    Write-Success
    Start-FormAINow
}

Main
