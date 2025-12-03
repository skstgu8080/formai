# Project Kit

A documentation template system for software projects, designed to work seamlessly with Claude Code (AI-assisted development).

## What's Included

```
project-kit/
├── CLAUDE.md                    # Development guidelines (main config)
├── CHANGELOG.md                 # Change tracking template
├── README.md                    # This file
├── GETTING_STARTED.md           # Quick-start guide
├── setup.sh                     # Unix/Mac setup script
├── setup.ps1                    # Windows PowerShell setup script
├── .cursorrules.template        # Cursor AI template
│
├── docs/
│   ├── ARCHITECTURE.md          # System architecture template
│   ├── features/
│   │   └── _TEMPLATE.md         # Feature documentation template
│   ├── bugs/
│   │   └── _TEMPLATE.md         # Bug analysis template
│   ├── business/                # Business docs (pricing, plans)
│   └── archive/                 # Old documentation
│
└── .claude/
    ├── security.md              # OWASP-based security guidelines
    ├── testing.md               # Testing workflow & requirements
    ├── api-design.md            # REST API conventions & logging
    ├── database.md              # Database & migration guidelines
    ├── standards.md             # Code quality & conventions
    ├── Agents/                  # Subagent role templates
    │   ├── code-reviewer.md     # Security-focused code review
    │   ├── architect.md         # System design expert
    │   ├── debugger.md          # Bug investigation
    │   └── refactorer.md        # Code cleanup specialist
    ├── commands/                # Custom slash commands
    │   ├── review.md            # Code review command
    │   ├── test.md              # Test generation command
    │   ├── docs.md              # Documentation command
    │   └── debug.md             # Debug command
    └── plans/                   # Planning documents
```

## Quick Start

### 1. Copy to Your Project

**Unix/Mac:**
```bash
# Use the setup script
./setup.sh my-project /path/to/your-project/

# Or copy manually
cp -r project-kit/* /path/to/your-project/
```

**Windows PowerShell:**
```powershell
.\setup.ps1 -ProjectName "my-project" -TargetDir "C:\path\to\your-project"
```

**For Cursor AI users:**
```bash
cp .cursorrules.template /path/to/your-project/.cursorrules
```

### 2. Customize CLAUDE.md

Open `CLAUDE.md` and replace:
- `[Project Name]` with your project name
- `[e.g., Next.js 15 + Convex...]` with your actual tech stack
- Update all `[bracketed placeholders]` with real values

### 3. Customize ARCHITECTURE.md

Open `docs/ARCHITECTURE.md` and:
- Fill in your system diagram
- Document your database schema
- List your API endpoints
- Describe your authentication flow

### 4. Start Your Changelog

Open `CHANGELOG.md` and:
- Set the initial version date
- Document your starting features

## New: Modular Guidelines

The `.claude/` directory now includes comprehensive guidelines:

| File | Purpose |
|------|---------|
| `security.md` | OWASP-based security rules (input validation, auth, encryption) |
| `testing.md` | Test-first workflow, coverage requirements, test types |
| `api-design.md` | REST conventions, error handling, logging |
| `database.md` | Schema design, migrations, query safety |
| `standards.md` | Code quality, naming conventions, git workflow |

These are automatically imported by CLAUDE.md using the `@.claude/filename.md` syntax.

### Agent Roles & Commands

Pre-built agent templates in `.claude/Agents/`:
- **code-reviewer.md** - Security-focused code review
- **architect.md** - System design and architecture
- **debugger.md** - Bug investigation workflow
- **refactorer.md** - Code cleanup specialist

Custom commands in `.claude/commands/`:
- **/review** - Code review
- **/test** - Test generation
- **/docs** - Documentation generation
- **/debug** - Bug investigation

---

## How This System Works

### The Three Core Files

| File | Purpose | Update When |
|------|---------|-------------|
| `CLAUDE.md` | Development rules & project structure | Adding routes, changing commands, new patterns |
| `docs/ARCHITECTURE.md` | System design & technical reference | Adding tables, changing flows, new integrations |
| `CHANGELOG.md` | What changed and when | Every significant change |

### Documentation Flow

```
New Feature Request
       │
       ▼
┌─────────────────┐
│ Plan & Implement │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│            Documentation Checklist               │
├─────────────────────────────────────────────────┤
│ □ CHANGELOG.md - Added entry for this feature   │
│ □ CLAUDE.md - Updated if structure changed      │
│ □ ARCHITECTURE.md - Updated if schema changed   │
│ □ docs/features/ - Created spec if complex      │
└─────────────────────────────────────────────────┘
         │
         ▼
      Commit
```

## Templates Included

### Feature Template (`docs/features/_TEMPLATE.md`)

Use for documenting significant features:
- User stories
- Database changes
- API endpoints
- Implementation details
- Testing checklist

### Bug Template (`docs/bugs/_TEMPLATE.md`)

Use for analyzing bugs:
- Reproduction steps
- Root cause analysis
- Fix implementation
- Prevention strategies

## Best Practices

### Keep CLAUDE.md Accurate

This is the first file Claude (or any developer) reads. If it's wrong, everything else will be harder.

```markdown
✅ Good: Specific, actionable rules
- **MUST** run `npm test` before committing
- **MUST** use `api.users.create` for new users

❌ Bad: Vague guidelines
- Try to test things
- Use the API correctly
```

### Keep CHANGELOG.md Updated

Update it immediately after completing work, not "later":

```markdown
✅ Good: Update right after merging
## [2024-01-15]
### Added
- User avatar upload feature (files: components/Avatar.tsx, api/upload.ts)

❌ Bad: Batch updates weeks later
## [Sometime in January]
### Added
- Various features
- Some fixes
```

### Keep ARCHITECTURE.md Visual

Use diagrams and tables, not walls of text:

```markdown
✅ Good: Visual representation
┌─────────┐     ┌─────────┐
│  User   │────▶│  API    │────▶ Database
└─────────┘     └─────────┘

❌ Bad: Dense paragraphs
The user connects to the API which then connects to the database
and the API processes the request and returns data to the user...
```

## Folder Organization

### docs/features/
One file per major feature. Use the template.
```
docs/features/
├── _TEMPLATE.md           # Copy this for new features
├── authentication.md      # Auth system docs
├── payment-integration.md # Stripe integration
└── real-time-chat.md     # WebSocket chat feature
```

### docs/bugs/
One file per significant bug investigation. Great for post-mortems.
```
docs/bugs/
├── _TEMPLATE.md
├── 2024-01-memory-leak.md
└── 2024-02-auth-bypass.md
```

### docs/business/
Non-technical documentation.
```
docs/business/
├── pricing-strategy.md
├── feature-roadmap.md
└── competitor-analysis.md
```

### docs/archive/
Old docs you don't want to delete but aren't actively using.

## Integration with Claude Code

This kit is designed to work with Claude Code's context system:

1. **CLAUDE.md** is automatically read at the start of sessions
2. **Specialized Context** table in CLAUDE.md points to other important docs
3. **Documentation Guidelines** section tells Claude when to update docs
4. **.claude/** folder contains agent roles and custom commands

## Customization Tips

### For Different Tech Stacks

**Next.js + Convex:**
- Keep the real-time sections in ARCHITECTURE.md
- Add Convex function patterns to CLAUDE.md

**Express + PostgreSQL:**
- Simplify to REST API patterns
- Add migration workflow to CLAUDE.md

**Mobile Apps:**
- Add platform-specific sections (iOS/Android)
- Include app store deployment info

### For Team Size

**Solo Developer:**
- Simplify CHANGELOG to just dates and changes
- Skip detailed feature docs for small features

**Large Team:**
- Add PR template references
- Include code review checklists
- Add team-specific conventions

## License

MIT - Use this however you want.

---

## Contributing

Found a way to improve these templates? Feel free to suggest changes!

## Credits

Created based on documentation patterns from DominoInsta project.
