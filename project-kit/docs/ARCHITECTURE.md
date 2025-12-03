# [Project Name] - System Architecture

> **Last Updated:** [YYYY-MM-DD]
> **Version:** 1.0.0

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [System Diagram](#system-diagram)
- [Directory Structure](#directory-structure)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Authentication & Authorization](#authentication--authorization)
- [External Integrations](#external-integrations)
- [Deployment Architecture](#deployment-architecture)
- [Statistics Summary](#statistics-summary)

---

## Overview

[Brief description of what the project does and its main features]

**Key Features:**
- Feature 1
- Feature 2
- Feature 3

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | [React/Vue/Next.js] |
| Styling | [Tailwind/CSS Modules/styled-components] |
| Backend | [Node.js/Python/Go] |
| Database | [PostgreSQL/MongoDB/Convex] |
| Authentication | [Clerk/Auth0/NextAuth] |
| Deployment | [Vercel/Railway/AWS] |

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              [PROJECT NAME]                                  │
│                          System Architecture                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                CLIENTS                                       │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│       WEB BROWSER        │      MOBILE APP          │        API            │
│                          │      (if applicable)     │      CONSUMERS        │
│  ┌────────────────────┐  │  ┌────────────────────┐  │  ┌─────────────────┐  │
│  │ Public Pages       │  │  │ React Native /     │  │  │ Third-party     │  │
│  │ • Landing          │  │  │ Flutter App        │  │  │ integrations    │  │
│  │ • Marketing        │  │  │                    │  │  │                 │  │
│  │ • Docs             │  │  └────────────────────┘  │  └─────────────────┘  │
│  ├────────────────────┤  │                          │                       │
│  │ Protected Pages    │  │                          │                       │
│  │ • Dashboard        │  │                          │                       │
│  │ • Settings         │  │                          │                       │
│  │ • Admin            │  │                          │                       │
│  └────────────────────┘  │                          │                       │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────┐    ┌────────────────────────────────────┐   │
│  │      AUTH PROVIDER         │    │           MIDDLEWARE               │   │
│  │  [Clerk/Auth0/NextAuth]    │───▶│  • Route protection                │   │
│  │  • Sign in/up              │    │  • Role-based access               │   │
│  │  • Session management      │    │  • API key validation              │   │
│  └────────────────────────────┘    └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REST ENDPOINTS                        GRAPHQL (if applicable)              │
│  ───────────────                       ────────────────────────             │
│  GET    /api/resource                  query { resources { ... } }          │
│  POST   /api/resource                  mutation { createResource }          │
│  PUT    /api/resource/:id                                                   │
│  DELETE /api/resource/:id                                                   │
│                                                                              │
│  WEBHOOKS                              REAL-TIME (if applicable)            │
│  ────────                              ─────────────────────────            │
│  POST /api/webhooks/[provider]         WebSocket connections                │
│                                        Server-sent events                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND SERVICES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CORE MODULES                   UTILITIES                   INTEGRATIONS    │
│  ────────────                   ─────────                   ────────────    │
│  • users                        • email                     • stripe        │
│  • auth                         • logging                   • analytics     │
│  • [domain-1]                   • validation                • storage       │
│  • [domain-2]                   • caching                   • [other]       │
│  • [domain-3]                                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CORE TABLES                    FEATURE TABLES              SYSTEM TABLES   │
│  ───────────                    ──────────────              ─────────────   │
│  • users                        • [feature_1]               • events        │
│  • sessions                     • [feature_2]               • audit_logs    │
│  • [core_table]                 • [feature_3]               • settings      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
[project-name]/
├── src/
│   ├── app/                    # Routes/pages
│   │   ├── (public)/          # Public pages
│   │   ├── dashboard/         # Protected user pages
│   │   ├── admin/             # Admin pages
│   │   └── api/               # API routes
│   │
│   ├── components/            # UI components
│   │   ├── ui/               # Base components
│   │   ├── forms/            # Form components
│   │   └── layouts/          # Layout components
│   │
│   ├── lib/                   # Utilities
│   │   ├── db/               # Database utilities
│   │   ├── auth/             # Auth utilities
│   │   └── utils/            # General utilities
│   │
│   ├── hooks/                 # Custom React hooks
│   │
│   └── types/                 # TypeScript types
│
├── public/                    # Static assets
├── tests/                     # Test files
├── docs/                      # Documentation
└── scripts/                   # Build/deploy scripts
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │       │  [table_2]  │       │  [table_3]  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │       │ id (PK)     │
│ email       │  │    │ user_id(FK) │───────│ [field]     │
│ name        │  └───▶│ [field]     │       │ [field]     │
│ created_at  │       │ created_at  │       │ created_at  │
└─────────────┘       └─────────────┘       └─────────────┘
```

### Table Definitions

**users**
```typescript
{
  id: string,           // Primary key
  email: string,        // Unique
  name: string,
  role: 'user' | 'admin',
  created_at: timestamp,
  updated_at: timestamp
}
```

**[table_name]**
```typescript
{
  id: string,
  // ... fields
}
```

---

## API Reference

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | User registration |

### Protected Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/user/profile` | Get user profile | User |
| PUT | `/api/user/profile` | Update profile | User |
| GET | `/api/admin/users` | List all users | Admin |

### Webhooks

| Provider | Endpoint | Events |
|----------|----------|--------|
| [Provider] | `/api/webhooks/[provider]` | event.created, event.updated |

---

## Data Flow Diagrams

### User Authentication Flow

```
User Signs Up/In → Auth Provider → Webhook → Database → Session Created
                                      │
                                      ▼
                              User Redirected to Dashboard
```

### [Feature Name] Flow

```
[Step 1] → [Step 2] → [Step 3] → [Step 4]
              │
              ▼
        [Side Effect]
```

---

## Authentication & Authorization

### Authentication
- Provider: [Clerk/Auth0/NextAuth]
- Session storage: [JWT/Cookie/Database]
- Token expiry: [Duration]

### Authorization Levels

| Role | Access |
|------|--------|
| Public | Landing, docs, auth pages |
| User | Dashboard, profile, [features] |
| Admin | All user access + admin panel |

### Protected Routes

Routes protected by middleware:
- `/dashboard/*` - Requires authentication
- `/admin/*` - Requires admin role
- `/api/protected/*` - Requires valid token

---

## External Integrations

### [Integration 1 Name]
- **Purpose**: [What it does]
- **Documentation**: [Link]
- **Webhook**: `/api/webhooks/[name]`

### [Integration 2 Name]
- **Purpose**: [What it does]
- **Documentation**: [Link]

---

## Deployment Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   FRONTEND   │    │   BACKEND    │    │   DATABASE   │
│   [Vercel]   │───▶│  [Railway]   │───▶│  [Provider]  │
│              │    │              │    │              │
│ Auto-deploy  │    │ Auto-deploy  │    │  Managed     │
│ from main    │    │ from main    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Environments

| Environment | URL | Branch |
|-------------|-----|--------|
| Production | https://[domain].com | main |
| Staging | https://staging.[domain].com | develop |
| Preview | https://[pr-id].[domain].com | PR branches |

---

## Statistics Summary

| Metric | Count |
|--------|-------|
| Total Routes | [X] |
| API Endpoints | [X] |
| Database Tables | [X] |
| Components | [X] |

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guidelines
- [CHANGELOG.md](../CHANGELOG.md) - Change history
- [docs/features/](./features/) - Feature documentation

---

## Maintenance Notes

### How to Update This Document

1. **Adding a new table**: Add to Database Schema section
2. **Adding an API endpoint**: Add to API Reference section
3. **Adding an integration**: Add to External Integrations section
4. **Changing architecture**: Update System Diagram

### Review Schedule
- Review monthly for accuracy
- Update immediately after major changes
