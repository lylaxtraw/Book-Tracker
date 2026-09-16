# Project Architecture

## Overview

Book Tracker is a full-stack web application for managing and tracking your personal book collection. The backend is built with FastAPI (Python) and provides REST API endpoints, while the frontend is a Progressive Web App (PWA) built with vanilla JavaScript.

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.6
- **Language**: Python 3.13
- **Database**: SQLite (with SQLAlchemy ORM)
- **Validation**: Pydantic 2.10.4
- **Testing**: pytest 8.3.4, respx (for mocking HTTP)
- **Authentication**: Session-based with Starlette middleware

### Frontend
- **Type**: Progressive Web App (PWA)
- **Language**: Vanilla JavaScript
- **Features**: Service worker, manifest for installability
- **Styling**: CSS3 with responsive design

### Deployment
- **Primary**: Fly.io (containerized with Docker)
- **Alternative**: Render.com
- **Database**: SQLite with persistent volume

## Directory Structure

```
Book Tracker/
├── app/
│   ├── __init__.py              # Package info
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration management
│   ├── database.py              # Database setup & sessions
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── auth.py                  # Authentication utilities
│   ├── openlibrary.py           # Open Library API client
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # Auth endpoints (/api/auth/)
│   │   ├── books.py             # Book CRUD (/api/books/)
│   │   ├── tags.py              # Tag management (/api/tags/)
│   │   ├── search.py            # Book search (/api/search/)
│   │   ├── stats.py             # Reading stats (/api/stats/)
│   │   └── backup.py            # Import/export (/api/backup/)
│
├── static/
│   ├── index.html               # Single page application
│   ├── manifest.webmanifest     # PWA manifest
│   ├── sw.js                    # Service worker
│   ├── js/
│   │   └── app.js               # Main application logic
│   ├── css/
│   │   └── style.css            # Application styling
│   └── icons/                   # Application icons
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── test_auth.py             # Authentication tests
│   ├── test_books.py            # Book operation tests
│   ├── test_tags.py             # Tag management tests
│   ├── test_search.py           # Search integration tests
│   ├── test_stats.py            # Statistics calculation tests
│   └── test_transfer.py         # Import/export tests
│
├── docs/
│   ├── README.md                # Documentation overview
│   ├── API.md                   # API endpoint documentation
│   ├── ARCHITECTURE.md          # This file
│   ├── DEPLOYMENT.md            # Deployment guides
│   └── CONTRIBUTING.md          # Contribution guidelines
│
├── .github/
│   ├── workflows/               # GitHub Actions CI/CD
│   └── ISSUE_TEMPLATE/          # Issue templates
│
├── requirements.txt             # Python dependencies
├── pytest.ini                   # pytest configuration
├── Dockerfile                   # Docker container definition
├── fly.toml                     # Fly.io configuration
├── render.yaml                  # Render.com configuration
└── README.md                    # Project README
```

## Key Components

### Backend Architecture

#### 1. **Authentication (app/auth.py)**
- Handles user password verification
- Provides session management via Starlette middleware
- All protected endpoints require valid session

#### 2. **Database Models (app/models.py)**
- `User`: Stores usernames and hashed passwords
- `Book`: Core book records with metadata
- `Tag`: Book categories and metadata tags
- `TagCategory`: Grouping for tags (role-based)

#### 3. **Schemas (app/schemas.py)**
- Pydantic models for request/response validation
- Separate schemas for input vs. output
- Ensures data consistency across API

#### 4. **Routers (app/routers/)**
- Each module handles a specific domain (auth, books, tags, etc.)
- Clean separation of concerns
- Mounted on FastAPI app with `/api/` prefix

#### 5. **External Integrations**
- **Open Library**: respx-mocked in tests, real HTTP in production
- **Static Files**: SPA served from `static/` directory with fallback routing

### Frontend Architecture

#### Single Page Application (SPA)
- `index.html`: Main HTML shell
- `app.js`: Application logic (routing, state, API calls)
- `style.css`: Responsive styling
- `sw.js`: Service worker for offline functionality

#### Progressive Web App Features
- Installable via manifest.webmanifest
- Works offline via service worker
- Mobile-friendly responsive design

## Data Flow

### User Login Flow
1. User enters credentials → POST `/api/auth/login`
2. FastAPI validates and sets session cookie
3. Frontend stores session (browser cookies)
4. All subsequent requests include session automatically

### Book Creation Flow
1. Frontend → POST `/api/books/` with book data
2. FastAPI validates with Pydantic schema
3. Database stores book record
4. Response includes created book with ID
5. Frontend updates UI

### Search Integration
1. Frontend → GET `/api/search/?query=...`
2. Backend calls Open Library API (real in prod, mocked in tests)
3. Results returned to frontend
4. User can add to collection

## Testing Strategy

### Unit Tests
- `test_auth.py`: Session management, login/logout
- `test_books.py`: CRUD operations
- `test_tags.py`: Tag management
- `test_search.py`: Open Library integration (mocked)

### Test Fixtures (conftest.py)
- `client`: Unauthenticated TestClient
- `auth`: Authenticated TestClient (logged-in user)
- `tags`: Pre-seeded tag data
- `make_book()`: Helper for creating test books

### Database Testing
- Each test uses fresh SQLite database in temp directory
- Tests are isolated and don't affect each other
- No network calls (respx mocks all external APIs)

## Configuration

### Environment Variables (.env)
```
DATABASE_URL=sqlite:///./test.db  # Or production database
DEBUG=false
SECRET_KEY=your-secret-key-here
```

### Constants (app/config.py)
- Preset tag roles and colors
- Session configuration
- CORS settings

## Performance Considerations

### Database
- SQLite suitable for single-user/small-scale deployments
- Migration to PostgreSQL recommended for multi-user scenarios
- Indexes on frequently queried columns (book title, author, tags)

### Frontend
- Service worker caches static assets
- Minimal JavaScript for fast startup
- Responsive images for various screen sizes

### API
- Pagination on book listing endpoints
- Tag filtering for efficient querying

## Deployment Architecture

### Docker Container
- Python 3.13 base image
- FastAPI app runs on port 8000
- SQLite database stored in persistent volume
- Static files mounted from `static/` directory

### Environment-Specific Configs
- **Development**: SQLite local file
- **Fly.io**: SQLite in persistent volume
- **Render**: SQLite or PostgreSQL in persistent storage

## Error Handling

- Pydantic validation errors → 400 Bad Request
- Missing authentication → 401 Unauthorized
- Resource not found → 404 Not Found
- Database errors → 500 Internal Server Error
- All errors include detail message for debugging

## Security

- Passwords hashed with bcrypt
- Session-based authentication (no JWT)
- CORS configured to allow frontend domain
- Environment variables for sensitive config
- Database queries use ORM (protection from SQL injection)
