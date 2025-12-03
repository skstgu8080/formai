<#
.SYNOPSIS
    Project Kit Setup Script for Windows

.DESCRIPTION
    Sets up project documentation templates for use with Claude Code and other AI assistants.

.PARAMETER ProjectName
    Name of your project (default: "my-project")

.PARAMETER TargetDir
    Target directory for setup (default: current directory)

.EXAMPLE
    .\setup.ps1 -ProjectName "my-app" -TargetDir "C:\Projects\my-app"
#>

param(
    [string]$ProjectName = "my-project",
    [string]$TargetDir = "."
)

Write-Host "`n🚀 Setting up Project Kit for: $ProjectName" -ForegroundColor Cyan
Write-Host "   Target directory: $TargetDir`n"

# Create target directory if needed
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "📁 Created directory: $TargetDir" -ForegroundColor Green
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Copy files
Write-Host "📁 Copying documentation templates..." -ForegroundColor Yellow

# Copy main files
Copy-Item "$ScriptDir\CLAUDE.md" -Destination $TargetDir -Force
Copy-Item "$ScriptDir\CHANGELOG.md" -Destination $TargetDir -Force

# Copy docs directory
if (Test-Path "$ScriptDir\docs") {
    Copy-Item "$ScriptDir\docs" -Destination $TargetDir -Recurse -Force
}

# Copy .claude directory
if (Test-Path "$ScriptDir\.claude") {
    Copy-Item "$ScriptDir\.claude" -Destination $TargetDir -Recurse -Force
} else {
    # Create .claude structure
    New-Item -ItemType Directory -Path "$TargetDir\.claude\Agents" -Force | Out-Null
    New-Item -ItemType Directory -Path "$TargetDir\.claude\commands" -Force | Out-Null
    New-Item -ItemType Directory -Path "$TargetDir\.claude\plans" -Force | Out-Null
}

# Copy .gitignore template
if (Test-Path "$ScriptDir\.gitignore.template") {
    Copy-Item "$ScriptDir\.gitignore.template" -Destination "$TargetDir\.gitignore" -Force
}

# Replace placeholders in CLAUDE.md
Write-Host "✏️  Customizing CLAUDE.md..." -ForegroundColor Yellow
$claudeFile = "$TargetDir\CLAUDE.md"
if (Test-Path $claudeFile) {
    $content = Get-Content $claudeFile -Raw
    $content = $content -replace '\[Project Name\]', $ProjectName
    Set-Content $claudeFile -Value $content
}

# Replace in ARCHITECTURE.md
$archFile = "$TargetDir\docs\ARCHITECTURE.md"
if (Test-Path $archFile) {
    $content = Get-Content $archFile -Raw
    $content = $content -replace '\[Project Name\]', $ProjectName
    $content = $content -replace '\[project-name\]', $ProjectName
    Set-Content $archFile -Value $content
}

# Set current date in CHANGELOG
$changelogFile = "$TargetDir\CHANGELOG.md"
if (Test-Path $changelogFile) {
    $currentDate = Get-Date -Format "yyyy-MM-dd"
    $content = Get-Content $changelogFile -Raw
    $content = $content -replace 'YYYY-MM-DD', $currentDate
    Set-Content $changelogFile -Value $content
}

Write-Host "`n✅ Project Kit setup complete!" -ForegroundColor Green
Write-Host "`n📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Edit CLAUDE.md to add your tech stack and project details"
Write-Host "   2. Edit docs/ARCHITECTURE.md to document your system"
Write-Host "   3. Update CHANGELOG.md with your initial features"
Write-Host "`n📚 Files created:" -ForegroundColor Cyan
Write-Host "   - CLAUDE.md (development guidelines)"
Write-Host "   - CHANGELOG.md (change tracking)"
Write-Host "   - docs/ARCHITECTURE.md (system architecture)"
Write-Host "   - docs/features/_TEMPLATE.md (feature doc template)"
Write-Host "   - docs/bugs/_TEMPLATE.md (bug analysis template)"
Write-Host "   - .claude/ (Claude Code configuration)"
Write-Host ""
