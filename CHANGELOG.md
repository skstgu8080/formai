# Changelog

All notable changes to FormAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.10] - 2025-12-26

### Fixed
- **CAPTCHA Methods** - Use correct SeleniumBase UC Mode methods
  - `uc_gui_handle_cf()` for Cloudflare/Turnstile
  - `uc_gui_handle_rc()` for reCAPTCHA
  - `uc_gui_handle_captcha()` as generic fallback
- **Repository URLs** - Updated all docs to use skstgu8080/formai

---

## [1.0.9] - 2025-12-26

### Added
- **Import Profile Button** - Import JSON profile files directly from the Profiles page
- **Gender Field Fallback** - Autofill engine checks multiple profile field names (sex, gender, genderA)
- **Gender Value Normalization** - Converts m/male to MALE, f/female to FEMALE for dropdown compatibility

### Changed
- **CAPTCHA Solving** - Now uses SeleniumBase built-in methods only (no paid APIs)
- **Release Workflow** - Removed retired macOS-13 Intel build, now builds for:
  - Windows x64
  - macOS Apple Silicon (ARM64)
  - Linux x64

### Removed
- **Paid CAPTCHA APIs** - Removed 2Captcha and Anti-Captcha integration
  - Deleted `tools/captcha_solver.py` (672 lines)
  - Removed CAPTCHA API endpoints from server
  - Removed CAPTCHA service config from Settings page

---

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

### Changed
- Added Edit button to recording cards on Recorder page

---

## [Unreleased]

### Added
- **One-Line Installation** - Install FormAI with a single curl/PowerShell command
  - `curl -sSL https://raw.githubusercontent.com/skstgu8080/formai/master/install.sh | bash` (macOS/Linux)
  - `irm https://raw.githubusercontent.com/skstgu8080/formai/master/install.ps1 | iex` (Windows)
- **Cross-Platform Releases** - Pre-built executables for Windows, macOS ARM, Linux
- **GitHub Actions CI/CD** - Automated release builds on version tags

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
| 1.0.10 | 2025-12-26 | Fix CAPTCHA methods, update repo URLs |
| 1.0.9 | 2025-12-26 | Remove paid CAPTCHA APIs, fix gender field, add profile import |
| 1.0.8 | 2025-12-03 | Recording Editor, Form Validation |
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
