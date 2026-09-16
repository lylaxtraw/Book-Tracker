# Contributing to Book Tracker

Thank you for your interest in contributing to Book Tracker! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.13+
- Git
- A GitHub account

### Setup Development Environment

1. **Fork and Clone**
```bash
git clone https://github.com/yourusername/Book-Tracker.git
cd "Book Tracker"
```

2. **Create Virtual Environment**
```bash
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup Database**
```bash
python3 -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

5. **Run Tests**
```bash
pytest
```

6. **Start Development Server**
```bash
python3 -m uvicorn app.main:app --reload
```

Visit `http://localhost:8000` in your browser.

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
# Or for bug fixes:
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation updates
- `chore/` — Maintenance, tooling, dependencies
- `test/` — Test improvements

### 2. Make Changes

- Write code following the project style
- Add or update tests for your changes
- Run tests locally: `pytest`
- Run linter: `ruff check app/ tests/`

### 3. Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description

Optional detailed explanation if needed.

Closes #123  (if applicable)
```

Examples:
- `feat(books): add bulk import from CSV`
- `fix(auth): validate password length`
- `docs(deployment): add Render.com guide`
- `test(search): add Open Library API tests`

Types:
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation
- `test` — Test updates
- `chore` — Maintenance, dependencies
- `refactor` — Code restructuring

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

On GitHub:
1. Click "Compare & pull request"
2. Fill out PR template
3. Reference any related issues: `Closes #123`
4. Request review from maintainers

## Pull Request Guidelines

### PR Description Should Include

- **What**: Brief description of changes
- **Why**: Motivation for the change
- **How**: Implementation approach
- **Testing**: How to verify the changes work
- **Related Issues**: Link any related issues

### Checklist Before Submitting

- [ ] Code follows project style
- [ ] Tests added or updated
- [ ] Tests pass: `pytest`
- [ ] Linter passes: `ruff check app/ tests/`
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow Conventional Commits
- [ ] No sensitive data in code (passwords, API keys, etc.)

## Code Style

### Python Style

We follow PEP 8 with these tools:

**Linting:**
```bash
ruff check app/ tests/
ruff check --fix app/ tests/  # Auto-fix issues
```

**Type Checking:**
```bash
mypy app/
```

### Key Guidelines

- Use type hints for all function parameters and returns
- Keep functions small and focused
- Add docstrings to public functions
- Use meaningful variable names
- Limit line length to 88 characters (Ruff default)

### Example Function

```python
def calculate_pages_this_year(user_id: int) -> int:
    """
    Calculate total pages read this calendar year.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Total pages read this year
    """
    db = SessionLocal()
    today = date.today()
    books = db.query(Book).filter(
        Book.user_id == user_id,
        Book.finished_on >= date(today.year, 1, 1)
    ).all()
    return sum(book.pages for book in books)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_books.py

# Run specific test function
pytest tests/test_books.py::test_create_book

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app
```

### Writing Tests

Tests go in `tests/` directory with filename pattern `test_*.py`.

Example test:

```python
def test_create_book(auth):
    """Test creating a new book."""
    response = auth.post(
        "/api/books/",
        json={
            "title": "1984",
            "author": "George Orwell",
            "pages": 328,
            "tags": ["finished"]
        }
    )
    assert response.status_code == 201
    assert response.json()["title"] == "1984"
```

### Test Fixtures

Available fixtures from `conftest.py`:
- `client` — Unauthenticated test client
- `auth` — Authenticated test client (logged-in user)
- `tags` — Pre-seeded tag data
- `make_book(auth, ...)` — Helper to create test books

## Documentation

### Updating Docs

Documentation files are in `docs/`:
- `API.md` — API endpoint documentation
- `ARCHITECTURE.md` — Project structure and design
- `DEPLOYMENT.md` — Deployment guides
- `CONTRIBUTING.md` — This file

When adding features, update relevant docs:

```bash
# Add endpoint to API.md
# Update ARCHITECTURE.md if changing structure
# Add deployment notes if needed
```

## Reporting Issues

### Bug Reports

Click "Issues" → "New issue" → "Bug report"

Include:
- **Description**: What happened?
- **Expected Behavior**: What should happen?
- **Steps to Reproduce**: How to trigger the bug
- **Environment**: OS, Python version, browser (if frontend)
- **Logs**: Any error messages or stack traces

### Feature Requests

Click "Issues" → "New issue" → "Feature request"

Include:
- **Description**: What feature would you like?
- **Use Case**: Why do you need this?
- **Solution Ideas**: How might this be implemented?
- **Examples**: Real-world examples if applicable

## Code Review Process

### What to Expect

1. **Automated Checks**
   - Tests must pass
   - Linter checks must pass
   - Code coverage maintained

2. **Human Review**
   - Maintainer reviews code quality
   - Feedback on implementation approach
   - Suggestions for improvement

3. **Approval & Merge**
   - Once approved, PR can be merged
   - Branch is deleted after merge

### Review Feedback

- Be open to suggestions
- Discuss disagreements respectfully
- Request clarification if needed
- Update code based on feedback

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

Maintained in `app/__init__.py`:
```python
__version__ = "1.0.0"
```

## Getting Help

- **Questions**: Open an issue with label `question`
- **Documentation**: Check `docs/` directory
- **Chat**: Discussions tab on GitHub

## Code of Conduct

Be respectful, inclusive, and professional:
- Welcome all contributions regardless of background
- Be kind in code reviews
- Respect different perspectives
- Report harassment or inappropriate behavior

## License

By contributing, you agree your code will be licensed under the project's license.

---

**Thank you for contributing to Book Tracker!** 🎉
