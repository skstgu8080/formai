# Security Guidelines

> **Based on OWASP Application Security Verification Standard (ASVS)**

## Quick Reference - Critical Security Rules

### ALWAYS
- Use parameterized queries for all database operations
- Validate AND sanitize all user input
- Use context-appropriate output encoding (HTML, JavaScript, URL)
- Hash passwords with bcrypt/scrypt/Argon2 (minimum 10 rounds)
- Use cryptographically secure random generation for security tokens
- Implement CSRF protection on state-changing requests
- Set secure session cookie flags (httpOnly, secure, sameSite)
- Enforce HTTPS in production
- Return generic error messages to users
- Log security events with proper metadata

### NEVER
- Store passwords, API keys, or secrets in plain text
- Use eval() or dynamic code execution with user input
- Trust client-side validation alone
- Expose stack traces or internal errors to users
- Commit secrets to version control

---

## Input Validation & Sanitization

### Injection Prevention
- **SQL Injection**: Use parameterized queries or ORM methods (NEVER concatenate user input)
- **XSS Prevention**: Sanitize HTML output using libraries like DOMPurify
- **Command Injection**: Use parameterized APIs for OS commands, avoid system() with user input

### Validation Rules
- Validate input type (string, number, email, etc.)
- Validate input length (min/max characters)
- Validate input format using regex or validation libraries (zod, joi, yup)
- Validate file upload types by checking MIME type, not just extension
- Limit file upload sizes appropriately

---

## Authentication & Authorization

### Password Policy
- Minimum 8 characters (15+ recommended)
- Validate against common passwords list
- Allow paste functionality in password fields
- Use bcrypt/Argon2 for hashing (minimum 10 rounds)

### Session Management
- Regenerate session IDs after login
- Use secure cookie flags:
  - `httpOnly: true` (prevent JavaScript access)
  - `secure: true` (HTTPS only)
  - `sameSite: 'strict'` (CSRF protection)
- Implement session timeout (inactivity + absolute)

### Authorization
- Verify permissions server-side for ALL protected resources
- Follow principle of least privilege
- Re-authenticate before sensitive account changes

---

## HTTP Security Headers

Set these headers on all responses:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'
```

---

## CORS Configuration

- NEVER use '*' wildcard in production
- Explicitly whitelist allowed origins
- Set appropriate Access-Control-Allow-Methods

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Login | 5 attempts / 15 min |
| Password reset | 3 attempts / 15 min |
| Registration | 5 attempts / hour |
| API (authenticated) | 100 requests / min |
| API (public) | 20 requests / min |

---

## Error Handling & Logging

### Error Messages
- Return generic messages to users ("Invalid credentials", not "Password incorrect")
- Log detailed errors server-side only
- Never expose stack traces, internal paths, or database structure

### Security Event Logging
Log these events with timestamp, user ID, IP address:
- Authentication attempts (success/failure)
- Authorization failures
- Rate limit violations
- Input validation failures
- CSRF token failures

---

## Environment & Secrets

- Use environment variables for all secrets
- Use different credentials per environment (dev/staging/prod)
- Keep `.env.example` updated with placeholder values
- Validate required env vars at startup

---

## Security Checklist

Before deploying, verify:

- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection on state-changing requests
- [ ] Passwords hashed with bcrypt/Argon2
- [ ] Session cookies have secure flags
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Rate limiting on auth endpoints
- [ ] Secrets in environment variables
- [ ] Error messages are generic
- [ ] Security events are logged
