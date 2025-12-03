# Changelog

All notable changes to FormAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.8] - 2025-12-03

### Added
- **Recording Editor UI** - Visual editor to modify selectors and field mappings
  - Edit CSS/XPath selectors for form fields
  - Re-map profile fields to form fields
  - View alternative selectors from original recording
  - Apply suggested mappings with one click
- **Form Validation** - Validate profile data before form submission
  - Email format validation
  - Phone number format validation
  - Password strength checking
  - Required field detection
  - Pre-replay validation with warnings
- **CAPTCHA Solving Integration** - Support for solving CAPTCHAs automatically
  - 2Captcha API support
  - Anti-Captcha API support
  - reCAPTCHA v2/v3 solving
  - hCaptcha solving
  - Image CAPTCHA solving
  - API key configuration in Settings page

### Changed
- Added Edit button to recording cards on Recorder page
- Enhanced Settings page with CAPTCHA service configuration

---

## [Unreleased]

### Added
- **One-Line Installation** - Install FormAI with a single curl/PowerShell command
  - `curl -sSL https://raw.githubusercontent.com/KoodosBots/formai/master/install.sh | bash` (macOS/Linux)
  - `irm https://raw.githubusercontent.com/KoodosBots/formai/master/install.ps1 | iex` (Windows)
- **Cross-Platform Releases** - Pre-built executables for Windows, macOS (Intel/ARM), Linux
- **GitHub Actions CI/CD** - Automated release builds on version tags
- **Bulk Autofill Engine** - SeleniumBase-based form filling replaces Puppeteer step-by-step replay
- Project-kit documentation structure adoption
- Modular `.claude/` guideline files (security.md, testing.md, api-design.md, database.md, standards.md)
- Agent templates (code-reviewer, debugger, refactorer)
- Custom slash commands (review, test, debug)
- docs/ARCHITECTURE.md for system design
- Documentation templates for features and bugs

### Changed
- Dashboard recording replay now uses fast bulk autofill instead of slow step-by-step Puppeteer
- Restructured CLAUDE.md with project-kit format
- Updated README.md with accurate Python-based setup instructions
- Refactored build-formai.bat to use cross-platform Python build script

### Removed
- Puppeteer-based step-by-step replay (replaced with SeleniumBase AutofillEngine)
- Outdated Rust/cargo references from README
- Unrelated Archon project content from CLAUDE.md

---

## [1.0.0] - 2025-12-01 (Baseline)

### Added
- **Dual-Server Architecture**
  - Client server (port 5511) - Main automation server
  - Admin server (port 5512) - Central monitoring

- **Browser Automation**
  - SeleniumBase with UC (Undetected Chrome) mode
  - CDP (Chrome DevTools Protocol) support
  - Anti-bot detection bypass
  - Human-like interaction delays

- **AI-Powered Form Filling**
  - Smart field detection and mapping
  - Profile-based auto-fill
  - Multiple AI provider support (OpenRouter, Ollama)

- **Recording System**
  - Chrome DevTools recording import
  - Recording replay with profile data
  - Template creation from recordings

- **Profile Management**
  - Create, edit, delete profiles
  - Flat and nested profile format support
  - Profile normalization for field mapping

- **Admin Features**
  - Client heartbeat monitoring
  - Remote command execution
  - Screenshot collection
  - Statistics aggregation

### Technical
- Python 3.x with FastAPI
- SeleniumBase for browser automation
- WebSocket for real-time updates
- JSON file storage (no database required)
- Tailwind CSS for frontend styling

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-12-01 | Baseline - Python-based FormAI with dual-server architecture |

---

## How to Update This File

1. **Adding a feature**: Add entry under `### Added` in `[Unreleased]`
2. **Fixing a bug**: Add entry under `### Fixed`
3. **Breaking change**: Bump major version, add under `### Changed`
4. **New release**: Move `[Unreleased]` items to new version section

### Good Changelog Entry Examples

```markdown
### Added
- Profile export to CSV format on /profiles page
- Batch automation for multiple URLs simultaneously
- Real-time progress tracking via WebSocket

### Changed
- Improved field detection accuracy by 40%
- Updated recording parser to handle Chrome 120+ format

### Fixed
- Fixed issue where profiles with special characters failed to save
- Resolved WebSocket disconnection on long-running automations

### Removed
- Removed deprecated v1 recording format support
```

### Bad Changelog Entry Examples (Avoid These)

```markdown
- Fixed bug          # Too vague
- Updated stuff      # Not descriptive
- Changes            # Says nothing
- WIP                # Not a real change
```
