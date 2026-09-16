# Local Development Setup

## Prerequisites

- Python 3.13 or higher
- pip
- Git

## Step 1: Clone and Navigate

```bash
cd "Koy's Gifts/Book Tracker"
```

## Step 2: Create Virtual Environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate
# On Windows: .venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4: Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and change at minimum:
- `SECRET_KEY`: Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `OWNER_PASSWORD`: Your admin password

## Step 5: Initialize Database

```bash
python3 -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

This creates the SQLite database and tables.

## Step 6: Run the Application

```bash
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`

### Log In

Username: Value from `OWNER_USERNAME` in `.env` (default: admin)
Password: Value from `OWNER_PASSWORD` in `.env`

## Step 7: Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_books.py

# Run a specific test
pytest tests/test_books.py::test_create_book

# Run with coverage
pytest --cov=app
```

## Step 8: Run Linter & Type Checker

```bash
# Check for style issues
ruff check app/ tests/

# Auto-fix style issues
ruff check --fix app/ tests/

# Type checking
mypy app/ --ignore-missing-imports
```

## Development Workflow

1. Create a branch: `git checkout -b feature/my-feature`
2. Make changes and test: `pytest`
3. Lint your code: `ruff check --fix app/`
4. Commit with conventional commits: `git commit -m "feat: add new feature"`
5. Push and create a pull request

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Make sure you're in the project root directory and venv is activated:
```bash
pwd  # Should show ".../Book Tracker"
which python  # Should show ".venv/bin/python"
```

### "sqlite3.OperationalError: unable to open database file"

The database file doesn't exist. Run:
```bash
python3 -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

### Tests fail with "AssertionError: assert 401 == 201"

Authentication failed. Check that `.env` has correct credentials and database is initialized.

### Port 8000 already in use

Use a different port:
```bash
uvicorn app.main:app --reload --port 8001
```

### Changes don't reload

Make sure you're using `--reload` flag:
```bash
uvicorn app.main:app --reload
```

## IDE Setup

### VS Code

Install extensions:
- Python
- Pylance
- Pytest
- Ruff

Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.linting.ruffEnabled": true,
  "python.linting.ruffArgs": ["--select", "E,W,F"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestPath": ".venv/bin/pytest"
}
```

## Environment Variables Reference

See [SECRETS.md](./SECRETS.md) for detailed environment variable documentation.
