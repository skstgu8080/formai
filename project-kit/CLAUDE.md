# [Project Name]

## Overview
- **Type**: [e.g., Next.js 15 + Convex, Express API, React Native app]
- **Stack**: [e.g., React 19, TypeScript, Tailwind CSS]
- **Architecture**: [e.g., App Router, REST API, Monorepo]
- **Repository**: [GitHub URL]

This CLAUDE.md is the authoritative source for development guidelines.

---

## Universal Rules

### MUST
- **MUST** explore codebase before making changes
- **MUST** run tests before committing
- **MUST** update CHANGELOG.md after significant changes
- **MUST** ensure all pages/endpoints are properly typed
- **MUST** follow existing code patterns and conventions

### SHOULD
- **SHOULD** use the documentation checklist after features
- **SHOULD** write tests for new functionality
- **SHOULD** keep functions small and focused

### MUST NOT
- **MUST NOT** commit secrets, API keys, or tokens
- **MUST NOT** bypass TypeScript errors with `@ts-ignore`
- **MUST NOT** push directly to main/master branch

---

## Core Commands

### Development
```bash
npm run dev              # Start development server
npm run build            # Production build
npm run start            # Production server
npm run lint             # Run linter
```

### Testing
```bash
npm run test             # Run tests
npm run test:watch       # Watch mode
npm run test:coverage    # Coverage report
```

### Database (if applicable)
```bash
npm run db:migrate       # Run migrations
npm run db:seed          # Seed data
npm run db:reset         # Reset database
```

---

## Project Structure

```
[project-name]/
├── src/                 # Source code
│   ├── app/            # Pages/routes
│   ├── components/     # UI components
│   ├── lib/            # Utilities
│   ├── hooks/          # Custom hooks
│   └── types/          # TypeScript types
├── public/             # Static assets
├── tests/              # Test files
├── docs/               # Documentation
│   ├── ARCHITECTURE.md # System architecture
│   ├── features/       # Feature specs
│   ├── bugs/           # Bug analysis
│   └── business/       # Business docs
└── .claude/            # Claude Code config
    ├── Agents/         # Subagent templates
    └── commands/       # Custom commands
```

---

## Key Patterns

### [Pattern Name 1]
```typescript
// Example code pattern used throughout the project
```

### [Pattern Name 2]
```typescript
// Another common pattern
```

### Authentication (if applicable)
```typescript
// How auth is handled
```

### Data Fetching (if applicable)
```typescript
// How data is fetched
```

---

## Environment Variables

```env
# Required
DATABASE_URL=
API_KEY=

# Optional
DEBUG=false
LOG_LEVEL=info
```

---

## Deployment

| Target | Platform | Auto-deploy |
|--------|----------|-------------|
| Production | [Vercel/Railway/AWS] | main branch |
| Staging | [Platform] | develop branch |
| Database | [Convex/Supabase/Postgres] | automatic |

---

## Tool Permissions

| Action | Permission |
|--------|------------|
| Read any file | ✅ Allowed |
| Write code files | ✅ Allowed |
| Run tests, linters | ✅ Allowed |
| Edit .env files | ⚠️ Ask first |
| Force push | ❌ Ask first |
| Delete databases | ❌ Ask first |
| Run `rm -rf` | ❌ Blocked |

---

## Verification Standards

**NEVER claim something is working, running, or accessible unless you have actually verified it**

- Run the application/tests and confirm no errors
- Check actual outputs and behavior
- If verification fails, report the actual error - don't claim it works

Example: Don't say "Server is running on port 3000" unless you ran the start command and verified it started without errors.

---

## Security Guidelines

- **NEVER** commit tokens, API keys, or credentials
- Use `.env.local` for local secrets (gitignored)
- Validate all user input
- Use parameterized queries for database operations
- Review generated bash commands before execution

For comprehensive security guidelines, see:
@.claude/security.md

---

## Specialized Context

| Directory | Guide | Purpose |
|-----------|-------|---------|
| `docs/` | [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| `.claude/Agents/` | Role files | Subagent templates |
| `.claude/` | Modular guidelines | Detailed guidelines |

### Detailed Guidelines (Imported)

For comprehensive guidelines on specific topics:

@.claude/security.md - Security best practices (OWASP-based)
@.claude/testing.md - Testing workflow and requirements
@.claude/api-design.md - REST API conventions and logging
@.claude/database.md - Database and migration guidelines
@.claude/standards.md - Code quality and conventions

---

## Known Issues

- [Issue 1]: Description and workaround
- [Issue 2]: Description and workaround

---

## Git Workflow

- Branch from `main` for features: `feature/description`
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- PRs require: passing tests, type checks, lint
- Squash commits on merge

---

## Testing Requirements

- **Unit tests**: All business logic
- **Integration tests**: API endpoints
- **E2E tests**: Critical user paths
- Run `npm test` before committing
- Minimum 80% coverage for new code

For detailed testing guidelines, see:
@.claude/testing.md

---

## Recent Changes

See [CHANGELOG.md](CHANGELOG.md) for full history.

### [Current Month Year]
- [Recent feature or change]

---

## Adding New Features

### New Page/Route
1. Create file in appropriate directory
2. Add to navigation if needed
3. Ensure responsive design
4. Write tests

### New API Endpoint
1. Create route handler
2. Add input validation
3. Document in API docs
4. Write integration tests

### New Database Table/Model
1. Update schema
2. Run migrations
3. Update ARCHITECTURE.md
4. Create CRUD operations

---

## Documentation Guidelines

### When to Update Documentation

**MUST update CHANGELOG.md when:**
- Adding a new feature or page
- Removing functionality
- Changing database schema
- Modifying API endpoints
- Fixing significant bugs

**MUST update CLAUDE.md when:**
- Adding new routes (update Project Structure)
- Adding new major modules
- Changing environment variables
- Modifying deployment configuration
- Adding new commands or scripts

**MUST update docs/ARCHITECTURE.md when:**
- Adding new database tables
- Creating new major modules
- Changing data flows
- Modifying authentication/authorization
- Adding new integrations

### Documentation Checklist (After Each Feature)

Before committing, verify:
- [ ] CHANGELOG.md entry added with date and description
- [ ] CLAUDE.md updated if structure changed
- [ ] Feature-specific doc created in docs/features/ if complex
- [ ] Related docs updated

### Creating Feature Documentation

For significant features, create `docs/features/FEATURE_NAME.md`:
```markdown
# Feature Name

## Overview
Brief description

## Architecture
- Database tables affected
- Functions/modules created/modified
- UI components

## Usage
How users interact with the feature

## Technical Details
Implementation specifics

## Testing
How to test the feature
```

### Documentation Structure

```
docs/
├── ARCHITECTURE.md      # Full system architecture
├── features/            # Feature specifications
├── bugs/                # Bug analysis
├── business/            # Business docs
└── archive/             # Old documentation
```
