# Database Guidelines

## Schema Design

### Naming Conventions
- Use snake_case for table and column names
- Use plural for table names (`users`, `posts`, `comments`)
- Use singular for foreign key references (`user_id`, not `users_id`)
- Prefix boolean columns with `is_` or `has_` (`is_active`, `has_verified`)

### Standard Columns
Every table should include:
```sql
id          -- Primary key (UUID or auto-increment)
created_at  -- Timestamp of creation
updated_at  -- Timestamp of last update
```

### Soft Deletes (Optional)
```sql
deleted_at  -- NULL if not deleted, timestamp if deleted
```

---

## Migrations

### Rules
- NEVER modify migrations once committed to main branch
- Create new migrations for schema changes
- Test both up AND down migrations
- Keep migrations small and focused

### Naming Convention
```
YYYYMMDDHHMMSS_description.sql
20240115103000_create_users_table.sql
20240116140000_add_email_to_users.sql
```

### Migration Template
```sql
-- Up Migration
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Down Migration
DROP TABLE users;
```

---

## Query Safety

### ALWAYS
- Use parameterized queries (NEVER concatenate user input)
- Use transactions for multi-step operations
- Add appropriate indexes for frequently queried columns
- Limit result sets to prevent memory issues

### Examples

**Bad (SQL Injection vulnerable):**
```javascript
// ❌ NEVER do this
const query = `SELECT * FROM users WHERE email = '${email}'`;
```

**Good (Parameterized):**
```javascript
// ✅ Always use parameters
const query = 'SELECT * FROM users WHERE email = $1';
const result = await db.query(query, [email]);
```

---

## Indexing Guidelines

### When to Add Indexes
- Primary keys (automatic)
- Foreign keys
- Columns used in WHERE clauses frequently
- Columns used in ORDER BY
- Columns used in JOIN conditions

### Index Types
```sql
-- Single column
CREATE INDEX idx_users_email ON users(email);

-- Composite (order matters)
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at);

-- Unique
CREATE UNIQUE INDEX idx_users_email_unique ON users(email);
```

---

## Transactions

### When to Use
- Multiple related writes
- Operations that must succeed or fail together
- Financial operations

### Example
```javascript
const client = await pool.connect();
try {
  await client.query('BEGIN');
  await client.query('UPDATE accounts SET balance = balance - $1 WHERE id = $2', [amount, fromId]);
  await client.query('UPDATE accounts SET balance = balance + $1 WHERE id = $2', [amount, toId]);
  await client.query('COMMIT');
} catch (e) {
  await client.query('ROLLBACK');
  throw e;
} finally {
  client.release();
}
```

---

## Connection Management

### Rules
- Use connection pooling
- Set appropriate pool sizes (start with 10-20)
- Handle connection errors gracefully
- Close connections when done

### Pool Configuration
```javascript
const pool = new Pool({
  max: 20,              // Maximum connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

---

## Backup & Recovery

### Rules
- Automate regular backups
- Test restore procedures periodically
- Keep backups in separate location
- Document recovery steps

---

## Environment Separation

| Environment | Database |
|-------------|----------|
| Development | Local or dev instance |
| Testing | Isolated test database |
| Staging | Staging-specific database |
| Production | Production database |

NEVER use production data in development without anonymization.
