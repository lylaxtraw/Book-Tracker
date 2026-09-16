# GitHub Actions & Deployment Issues

This document tracks issues with CI/CD workflows.

## Recent Workflow Failures

### Test Workflow Issue: Python 3.13 Not Available on Ubuntu

**Problem**: GitHub Actions' `ubuntu-latest` may not have Python 3.13 pre-installed.

**Solution**: Add setup step with `actions/setup-python@v4`:

The workflow already includes this, but if issues persist:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.13'
    cache: 'pip'
```

### Dependencies Installation Fails

**Problem**: Some packages may not have wheels for Linux or require compilation.

**Solution**: 
1. Ensure requirements.txt pins versions
2. Add build tools to CI: `apt-get install build-essential`
3. Use pre-built wheels: `pip install --only-binary :all: package-name`

### Tests Fail on CI but Pass Locally

**Reasons**:
- Different Python minor version (3.13.0 vs 3.13.1)
- Environment variables not set
- Database path issues
- Timezone differences

**Debug**:
```bash
# Check Python version
python --version

# Check environment
env | grep -i database
env | grep -i secret

# Run same test locally
pytest tests/test_books.py -v
```

## Fixing Workflows

### Enable Detailed Logging

Add to workflow step:

```yaml
- name: Run pytest
  run: pytest -vv --tb=long
  env:
    PYTHONUNBUFFERED: 1
```

### Test Locally Against Workflow Environment

```bash
# Install Docker
docker run -it python:3.13 bash

# Inside container
git clone https://github.com/lylaxtraw/Book-Tracker.git
cd Book-Tracker
pip install -r requirements.txt
pytest
```

### View Full Workflow Logs

1. Go to GitHub repository
2. Click "Actions" tab
3. Click failed workflow
4. Expand failed job
5. See full output with error details

## CI/CD Secrets Setup

### For Fly.io Deployment

1. Generate API token on Fly.io dashboard
2. Go to GitHub repo → Settings → Secrets and variables → Actions
3. Add secret: `FLY_API_TOKEN` = your-token-here
4. Workflow uses: `FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}`

### For Render Deployment

1. Get deploy key from Render dashboard
2. Add GitHub secret: `RENDER_DEPLOY_KEY`
3. Add GitHub secret: `RENDER_SERVICE_ID`

Uncomment in `.github/workflows/deploy.yml`:
```yaml
- name: Deploy to Render
  run: |
    curl https://api.render.com/deploy/srv-${{ secrets.RENDER_SERVICE_ID }}?key=${{ secrets.RENDER_DEPLOY_KEY }} -d ""
```

## Debugging Workflow Steps

### Print Environment Variables

```yaml
- name: Debug environment
  run: |
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
    echo "Current directory: $(pwd)"
    echo "Files: $(ls -la)"
```

### Skip Failing Job

Temporarily skip to unblock other jobs:

```yaml
- name: Run tests
  if: false  # Set to true to enable
  run: pytest
```

### Run Specific Workflow Locally

```bash
# Install act (GitHub Actions local runner)
brew install act

# Run workflow locally
act -j test
```

## Common Fixes

### Cache Not Working

Ensure cache key is consistent:

```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### Timezone Issues in Tests

Some tests may assume timezone. Fix with:

```yaml
env:
  TZ: UTC
```

### Insufficient Disk Space

If getting "no space" errors:

```yaml
- name: Free up disk space
  run: |
    df -h
    sudo apt-get clean
    sudo rm -rf /usr/share/dotnet
```

## Monitoring Deployments

### Check Deployment Status

**Fly.io:**
```bash
flyctl status --app book-tracker
flyctl logs --app book-tracker -f
```

**Render:**
- Dashboard → Services → book-tracker → Activity
- Click deployment to see logs

### Rollback Failed Deployment

**Fly.io:**
```bash
flyctl releases --app book-tracker
flyctl releases rollback <version> --app book-tracker
```

**Render:**
- Click "Redeploy" on previous successful deployment

## Preventing Workflow Failures

1. **Test locally before push**: `pytest && ruff check app/`
2. **Use consistent Python versions**: Always 3.13
3. **Pin dependencies**: `pip freeze > requirements.txt`
4. **Check log before committing**: `git status` and `git diff`
5. **Use pre-commit hooks**: Run linter automatically

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Debugging Workflows](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/about-workflow-runs)
- [act - Local Runner](https://github.com/nektos/act)
