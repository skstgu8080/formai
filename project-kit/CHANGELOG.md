# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modular `.claude/` guideline files (security.md, testing.md, api-design.md, database.md, standards.md)
- OWASP-based security guidelines with checklists
- Comprehensive testing requirements and workflows
- Agent role templates (code-reviewer, architect, debugger, refactorer)
- Custom command templates (review, test, docs, debug)
- GETTING_STARTED.md quick-start guide
- `.cursorrules.template` for Cursor AI users
- `setup.ps1` PowerShell script for Windows users
- Verification standards section in CLAUDE.md

### Changed
- (Changes to existing features go here)

### Deprecated
- (Features that will be removed in future versions)

### Removed
- (Features removed in this release)

### Fixed
- (Bug fixes go here)

### Security
- (Security fixes go here)

---

## [1.0.0] - YYYY-MM-DD

### Added
- Initial release
- Core feature 1
- Core feature 2
- Core feature 3

### Technical
- Tech stack: [list technologies]
- Database schema v1
- Authentication setup

---

<!--
## Template for new releases:

## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature (files: path/to/file.ts)

### Changed
- Updated X to do Y

### Fixed
- Fixed bug where X happened

### Removed
- Removed deprecated feature X
-->

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | YYYY-MM-DD | Initial release |

---

## How to Update This File

1. **Adding a feature**: Add entry under `### Added` with brief description
2. **Fixing a bug**: Add entry under `### Fixed`
3. **Breaking change**: Bump major version, add under `### Changed`
4. **New release**: Move `[Unreleased]` items to new version section

### Good Changelog Entry Examples

```markdown
### Added
- User authentication with email/password and OAuth (Google, GitHub)
- Dashboard analytics showing user growth metrics
- Export data to CSV feature on /dashboard/reports

### Changed
- Improved search performance by 40% using database indexes
- Updated user profile page to support avatar uploads

### Fixed
- Fixed issue where users couldn't reset password on mobile
- Resolved race condition in real-time notifications

### Removed
- Removed legacy v1 API endpoints (deprecated since v2.0)
```

### Bad Changelog Entry Examples (Avoid These)

```markdown
- Fixed bug          # Too vague
- Updated stuff      # Not descriptive
- Changes            # Says nothing
- WIP                # Not a real change
```
