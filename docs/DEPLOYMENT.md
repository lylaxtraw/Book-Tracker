# Deployment Guide

This guide covers deploying Book Tracker to Fly.io or Render.com.

## Prerequisites

- Docker installed locally
- Git and GitHub repository set up
- Fly.io CLI or Render account

## Environment Setup

### Create .env.production

```bash
DATABASE_URL=sqlite:///./data/books.db
DEBUG=false
SECRET_KEY=your-super-secret-random-key-here
```

**Important**: Generate a strong SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Add this file to `.gitignore` (already done):
```
.env.production
```

## Deployment to Fly.io

### 1. Install Fly CLI

```bash
brew install flyctl
```

### 2. Authenticate

```bash
flyctl auth login
```

### 3. Create Fly App

```bash
flyctl apps create
# Choose an app name (e.g., book-tracker)
```

### 4. Create Persistent Volume

```bash
flyctl volumes create data --size 1 --app book-tracker
```

This stores the SQLite database persistently across deployments.

### 5. Set Environment Variables

```bash
flyctl secrets set DATABASE_URL="sqlite:///data/books.db" --app book-tracker
flyctl secrets set SECRET_KEY="your-secret-key-here" --app book-tracker
flyctl secrets set DEBUG="false" --app book-tracker
```

### 6. Deploy

```bash
flyctl deploy --app book-tracker
```

Monitor deployment:
```bash
flyctl logs --app book-tracker
```

### 7. View Live App

```bash
flyctl open --app book-tracker
```

Your app will be available at: `https://book-tracker.fly.dev` (or your chosen app name)

## Deployment to Render

### 1. Connect GitHub Repository

- Go to [render.com](https://render.com)
- Create new Web Service
- Connect your GitHub account and select the Book Tracker repository

### 2. Configure Service

- **Name**: book-tracker
- **Environment**: Docker
- **Branch**: main (or dev for staging)
- **Region**: Select closest to your location

### 3. Set Environment Variables

In Render dashboard under "Environment":

```
DATABASE_URL=sqlite:///data/books.db
DEBUG=false
SECRET_KEY=your-secret-key-here
```

### 4. Add Persistent Disk

- Under "Disks" section: Add disk
- **Mount Path**: `/data`
- **Size**: 1 GB minimum

### 5. Deploy

- Click "Create Web Service"
- Render automatically deploys from your GitHub repository

### 6. Auto-Deploy on Push

Enable auto-deploy:
- Settings → GitHub Integration
- Select "Automatically deploy new commits"

Your app will be available at: `https://book-tracker.onrender.com`

## Post-Deployment

### 1. Initialize Database

If the database doesn't exist, create it:

```bash
# For Fly.io
flyctl ssh console --app book-tracker

# Or for Render, use the shell in dashboard
python3
>>> from app.database import engine
>>> from app.models import Base
>>> Base.metadata.create_all(bind=engine)
>>> exit()
```

### 2. Create Initial User

```bash
# SSH into the running container
flyctl ssh console --app book-tracker

# Run Python
python3
>>> from app.database import SessionLocal
>>> from app.models import User
>>> from app.auth import hash_password
>>> db = SessionLocal()
>>> user = User(username="admin", password_hash=hash_password("your-password"))
>>> db.add(user)
>>> db.commit()
>>> exit()
```

### 3. Verify Live App

- Visit your deployed URL
- Log in with your created credentials
- Add a test book
- Verify functionality

## Updating Deployments

### Update to Fly.io

```bash
# Make code changes and commit
git add .
git commit -m "Update: feature description"
git push origin main

# Deploy
flyctl deploy --app book-tracker

# View logs
flyctl logs --app book-tracker -f
```

### Update to Render

Render automatically redeploys when you push to the configured branch.

Monitor deployment:
- Render Dashboard → Services → book-tracker → Activity

## Database Backup

### Fly.io

```bash
# Download database backup
flyctl ssh console --app book-tracker
# Then copy /data/books.db to your local machine
```

### Render

Access via dashboard:
- Services → book-tracker → Shell
- Copy database file to local machine

## Troubleshooting

### App Won't Start

Check logs for errors:

**Fly.io:**
```bash
flyctl logs --app book-tracker --level err
```

**Render:**
- Dashboard → Services → book-tracker → Logs

### Database Connection Error

Ensure:
1. Volume/disk is created
2. DATABASE_URL points to correct path
3. Database file has write permissions

### Static Files Not Serving

Check that `static/` folder exists in Docker image:
```bash
flyctl ssh console --app book-tracker
ls -la /app/static/
```

### High Memory Usage

SQLite can be memory-intensive. If issues persist:
1. Migrate to PostgreSQL (Render: Use add-on)
2. Increase allocated RAM
3. Optimize database queries

## Monitoring

### Fly.io Monitoring

```bash
# View real-time metrics
flyctl status --app book-tracker

# View detailed logs
flyctl logs --app book-tracker --level info
```

### Render Monitoring

- Dashboard → Services → book-tracker
- View CPU, memory, and disk usage
- Check "Logs" for application output

## Scale Up

### Fly.io

```bash
# Increase machine size
flyctl scale vm dedicated-cpu-1x --app book-tracker

# Add more instances
flyctl scale count 2 --app book-tracker
```

### Render

- Services → book-tracker → Settings
- Increase "Instance Type" or enable "Auto-scaling"

## Security Notes

- Keep SECRET_KEY secret—use environment variables
- Database credentials should never be in code
- Regularly update dependencies
- Monitor logs for suspicious activity
- Use HTTPS only (automatic with both platforms)

## Support

For issues with:
- **Fly.io**: [fly.io docs](https://fly.io/docs/)
- **Render**: [render.com docs](https://render.com/docs)
- **FastAPI**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
