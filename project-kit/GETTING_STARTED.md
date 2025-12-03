# Getting Started with Project Kit

Quick guide to using this documentation template system.

---

## Installation (2 minutes)

### Option 1: Copy Files

```bash
# Copy to your project
cp -r project-kit/* /path/to/your-project/

# Or selectively
cp project-kit/CLAUDE.md /path/to/your-project/
cp -r project-kit/docs /path/to/your-project/
cp -r project-kit/.claude /path/to/your-project/
```

### Option 2: Use Setup Script

```bash
# From project-kit directory
./setup.sh my-project /path/to/your-project/
```

### Option 3: Windows PowerShell

```powershell
.\setup.ps1 -ProjectName "my-project" -TargetDir "C:\path\to\your-project"
```

---

## Quick Customization

### Step 1: Update CLAUDE.md (Required)

Open `CLAUDE.md` and replace:

1. `[Project Name]` → Your project name
2. `[e.g., Next.js 15 + Convex...]` → Your tech stack
3. Update **Core Commands** section with your actual commands

### Step 2: Update ARCHITECTURE.md (Required)

Open `docs/ARCHITECTURE.md` and fill in:

1. System diagram
2. Database schema
3. API endpoints
4. Tech stack table

### Step 3: Review .claude/ Guidelines (Optional)

The `.claude/` directory contains modular guidelines:

| File | Purpose | Customize? |
|------|---------|------------|
| security.md | Security rules | Keep as-is or extend |
| testing.md | Testing workflow | Update test commands |
| api-design.md | API conventions | Adjust to your API style |
| database.md | DB guidelines | Update for your database |
| standards.md | Code quality | Add project-specific rules |

---

## Verify It Works

Start Claude Code in your project and ask:

```
What are our security guidelines?
What testing framework should I use?
Where should I put utility functions?
```

Claude should answer based on your CLAUDE.md and .claude/*.md files.

---

## How It Works

```
You start Claude Code
        │
        ▼
Claude reads CLAUDE.md automatically
        │
        ▼
Claude imports @.claude/*.md files
        │
        ▼
Claude follows these rules for entire session
```

**You never need to:**
- Paste guidelines into chat
- Remind Claude about rules
- Reference the files manually

---

## Directory Structure

After setup, your project should have:

```
your-project/
├── CLAUDE.md                 # Main AI config (customize this!)
├── CHANGELOG.md              # Track changes
├── docs/
│   ├── ARCHITECTURE.md       # System design
│   ├── features/             # Feature docs
│   │   └── _TEMPLATE.md
│   ├── bugs/                 # Bug analysis
│   │   └── _TEMPLATE.md
│   └── business/             # Business docs
└── .claude/
    ├── security.md           # Security guidelines
    ├── testing.md            # Testing requirements
    ├── api-design.md         # API conventions
    ├── database.md           # Database guidelines
    ├── standards.md          # Code quality
    ├── Agents/               # AI agent roles
    │   ├── code-reviewer.md
    │   ├── architect.md
    │   ├── debugger.md
    │   └── refactorer.md
    ├── commands/             # Custom commands
    │   ├── review.md
    │   ├── test.md
    │   ├── docs.md
    │   └── debug.md
    └── plans/                # Planning docs
```

---

## Tips for Better Guidelines

### Be Specific

```markdown
❌ Bad: "Write clean code"
✅ Good: "Keep functions under 50 lines"
```

### Use ALWAYS/NEVER

```markdown
- ALWAYS use parameterized queries
- NEVER commit secrets to repository
```

### Include Examples

```markdown
✅ Good commit message:
feat: Add user authentication with JWT

❌ Bad commit message:
fixed stuff
```

---

## Troubleshooting

### Claude ignores guidelines

- Make rules more specific
- Use stronger language (ALWAYS/NEVER)
- Check file is named exactly `CLAUDE.md`

### Too much context / slow

- Keep CLAUDE.md under 200 lines
- Remove unused .claude/*.md files

### Changes not taking effect

- Press `#` in Claude Code to reload
- Or start a new conversation

---

## Next Steps

1. ✅ Copy files to your project
2. ✅ Customize CLAUDE.md
3. ✅ Update ARCHITECTURE.md
4. ✅ Start your CHANGELOG
5. 🎯 Start coding with AI assistance!

---

## Resources

- [Claude Code Docs](https://docs.claude.com/en/docs/claude-code)
- [OWASP Security Guidelines](https://owasp.org/www-project-application-security-verification-standard/)
- [Keep a Changelog](https://keepachangelog.com/)
