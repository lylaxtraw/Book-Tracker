# Development Notes

Personal notes, TODOs, and ideas for Book Tracker development.

## Current Focus

- ✅ Project structure organized
- ✅ GitHub Actions CI/CD workflows set up
- ✅ Documentation created
- 🟡 27 test failures in stats and transfer modules (deferred to dev branch)
- 🟡 20 line-length style issues (ruff --fix can auto-fix)

## Priority TODOs

### High Priority
- [ ] Fix test_stats.py failures (10 tests)
  - Root cause: API response key mismatch
  - Affected endpoints: `/api/stats/`
  
- [ ] Fix test_transfer.py failures (16 tests)
  - Root cause: CSV/JSON import-export endpoint issues
  - Affected endpoints: `/api/backup/`

- [ ] Auto-fix line-length violations
  ```bash
  ruff check --fix app/ tests/
  ```

### Medium Priority
- [ ] Add mypy support (workspace path issue)
- [ ] Add pre-commit hooks for linting
- [ ] Improve test coverage
- [ ] Add deployment status badges to README

### Low Priority
- [ ] Add email notification support
- [ ] Add reading recommendations
- [ ] Add social features (sharing)
- [ ] Performance optimization

## Known Issues

### Python 3.14 Incompatibility
- ✅ RESOLVED: Downgraded to Python 3.13
- pydantic-core doesn't support Python 3.14 yet (PyO3 limitation)

### HTTP 204 Endpoints
- ✅ RESOLVED: Added `response_model=None` to 5 endpoints
- FastAPI 0.115.6 validates response models for status codes

### Test Fixture Mismatch
- ✅ RESOLVED: Fixed auth/client fixture usage in test_stats.py and test_transfer.py

### Undefined Variables
- ✅ RESOLVED: Fixed `client` variable in test_transfer.py upload() function

## Testing Notes

### Test Commands
```bash
# Run all tests
pytest

# Run specific file with verbose output
pytest tests/test_books.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run failing tests
pytest tests/test_stats.py tests/test_transfer.py -v
```

### Test Database
- Tests use temporary SQLite database
- Each test gets fresh database
- No data persists between tests
- Open Library API mocked with respx

## Deployment Notes

### Fly.io Setup
```bash
flyctl apps create book-tracker
flyctl volumes create data --size 1 --app book-tracker
flyctl secrets set SECRET_KEY="..." --app book-tracker
flyctl deploy --app book-tracker
```

### Environment Variables
- `SECRET_KEY`: Generated with `secrets.token_urlsafe(48)`
- `OWNER_USERNAME`: Admin username
- `OWNER_PASSWORD`: Admin password (hashed on first boot)
- `DATABASE_URL`: SQLite or PostgreSQL
- `SECURE_COOKIES`: `true` for HTTPS, `false` for HTTP
- `DEBUG`: `false` for production

## GitHub Actions

### Workflows
- `test.yml` - Run pytest on push/PR
- `lint.yml` - Run ruff & mypy checks
- `deploy.yml` - Deploy to Fly.io on main branch push

### Secrets Needed
- `FLY_API_TOKEN` - For Fly.io deployments

## Code Quality

### Linting
```bash
ruff check app/ tests/               # Check for issues
ruff check --fix app/ tests/         # Auto-fix issues
ruff format app/ tests/              # Format code
```

### Type Checking
```bash
mypy app/ --ignore-missing-imports
```

### Style Guide
- PEP 8 with line-length limit of 88 characters
- Type hints on all public functions
- Docstrings on classes and public functions

## Open Questions

- [ ] Should we add PostgreSQL support for large databases?
- [ ] Add full-text search capability?
- [ ] Multi-user support (different shelves per user)?
- [ ] Book review/rating system?

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [pytest Guide](https://docs.pytest.org/)
- [Fly.io Deployment](https://fly.io/docs/)

## Session History

### 2026-09-16
- Organized project structure (app/, static/, tests/)
- Fixed Python version (3.13 instead of 3.14)
- Fixed HTTP 204 endpoint issues
- Fixed test fixtures
- Created comprehensive docs
- Set up GitHub Actions
- Created .dev/ folder for dev docs

---

*Last updated: 2026-09-16*
