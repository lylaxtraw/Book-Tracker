# Secrets and Keys Management

This document explains how to manage sensitive configuration for Book Tracker.

## Never Commit Secrets

⚠️ **CRITICAL**: Never commit `.env`, passwords, API keys, or secrets to Git.

Verify `.gitignore` includes:
```
.env
.env.local
.env.*.local
```

## Local Development

### 1. Create `.env` from Template

```bash
cp .env.example .env
```

### 2. Generate SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output and paste into `.env`:
```
SECRET_KEY=output-goes-here
```

### 3. Set Admin Credentials

Edit `.env`:
```
OWNER_USERNAME=your-username
OWNER_PASSWORD=your-password
```

⚠️ Never use simple passwords. Use something like `correct-horse-battery-staple`.

### 4. Database URL (Optional)

For local development, SQLite is fine:
```
DATABASE_URL=sqlite:///./books.db
```

For PostgreSQL:
```
DATABASE_URL=postgresql://user:password@localhost:5432/booktracker
```

### 5. Security Settings

For local development:
```
SECURE_COOKIES=false    # HTTP is OK locally
DEBUG=true
```

## Production Deployment

### Fly.io

Use Fly secrets (never hardcoded):

```bash
flyctl secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  OWNER_USERNAME="your-username" \
  OWNER_PASSWORD="your-password" \
  SECURE_COOKIES="true" \
  DEBUG="false" \
  --app book-tracker
```

View secrets:
```bash
flyctl secrets list --app book-tracker
```

### Render.com

Add secrets in Render dashboard:
1. Services → book-tracker → Environment
2. Add environment variables
3. Render masks secrets in logs automatically

```
SECRET_KEY=your-generated-key
OWNER_USERNAME=your-username
OWNER_PASSWORD=your-password
SECURE_COOKIES=true
DEBUG=false
DATABASE_URL=postgresql://...  # if using Postgres add-on
```

### GitHub Secrets (For CI/CD)

⚠️ **ADVANCED**: Only if deploying via GitHub Actions.

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secrets:
   - `FLY_API_TOKEN` - for Fly.io deployments
   - `RENDER_DEPLOY_KEY` - for Render deployments

Usage in workflows:
```yaml
env:
  FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

## Rotating Secrets

### When to Rotate

- After accidental exposure
- Quarterly (best practice)
- When someone with access leaves
- After security incident

### How to Rotate SECRET_KEY

1. Generate new key: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Update in all environments (local, Fly, Render, GitHub)
3. Existing sessions will be invalidated (users must log in again)

### How to Rotate OWNER_PASSWORD

1. Log in locally with old password
2. Go to Settings → Change Password
3. Update in `.env`
4. On production: Update with `flyctl secrets set OWNER_PASSWORD="..."`

## API Keys (Future)

If integrating with external services:

- **Open Library** - No key required currently
- **Email notifications** - SMTP credentials
- **Analytics** - Service-specific API keys

Always store in environment variables, never hardcode.

## Security Checklist

- [ ] `.env` is in `.gitignore`
- [ ] No `.env` file is committed to Git
- [ ] Different passwords for dev and production
- [ ] SECRET_KEY is long and random
- [ ] `SECURE_COOKIES=true` on production
- [ ] `DEBUG=false` on production
- [ ] All secrets stored in environment variables (never code)
- [ ] Secrets rotated every 3 months or after exposure
- [ ] Only trusted developers have access to secrets

## If You Accidentally Commit a Secret

1. **Stop immediately** — don't push if not yet pushed
2. Remove the file: `git rm --cached .env`
3. Add to `.gitignore`: `echo ".env" >> .gitignore`
4. Commit: `git commit -m "security: remove .env from tracking"`
5. If already pushed to GitHub:
   - Rotate all secrets immediately
   - Contact GitHub support for history purge
   - Treat as potential compromise

## Testing with Secrets

For tests that need credentials, use fixtures:

```python
# In conftest.py
TEST_USERNAME = "test-user"
TEST_PASSWORD = "test-password"

@pytest.fixture
def auth(client):
    client.post("/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    return client
```

Tests never touch `.env` — they use in-memory databases and mock external APIs.

## References

- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Fly.io Secrets](https://fly.io/docs/reference/secrets/)
- [Render Secrets](https://render.com/docs/environment-variables)
- [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
