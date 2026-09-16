# REST API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://bookmark.example.com` (replace with your domain)

## Authentication

Most endpoints require a session cookie. Obtain one via the `/api/auth/login` endpoint.

## Endpoints

### Authentication (`/api/auth/`)

#### Login
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

Response: 200 OK
Set-Cookie: session=...
```

#### Logout
```
POST /api/auth/logout
Response: 204 No Content
```

#### Change Password
```
POST /api/auth/password
Content-Type: application/json

{
  "old_password": "string",
  "new_password": "string"
}

Response: 204 No Content
```

#### Get Session Info
```
GET /api/auth/session
Response: 200 OK
{
  "username": "string",
  "authenticated": true
}
```

### Books (`/api/books/`)

#### List Books
```
GET /api/books/?skip=0&limit=100&tags=tag1,tag2
Response: 200 OK
[
  {
    "id": 1,
    "title": "string",
    "author": "string",
    "pages": integer,
    "isbn": "string",
    "finished_on": "YYYY-MM-DD" | null,
    "tags": ["string", ...]
  },
  ...
]
```

#### Create Book
```
POST /api/books/
Content-Type: application/json

{
  "title": "string",
  "author": "string",
  "pages": integer,
  "isbn": "string",
  "tags": ["string", ...]
}

Response: 201 Created
```

#### Get Book
```
GET /api/books/{book_id}
Response: 200 OK
{ ... book object ... }
```

#### Update Book
```
PUT /api/books/{book_id}
Content-Type: application/json

{
  "title": "string",
  "author": "string",
  "pages": integer,
  "isbn": "string",
  "finished_on": "YYYY-MM-DD" | null,
  "tags": ["string", ...]
}

Response: 200 OK
```

#### Delete Book
```
DELETE /api/books/{book_id}
Response: 204 No Content
```

### Tags (`/api/tags/`)

#### List Tags
```
GET /api/tags/
Response: 200 OK
{
  "categories": [...],
  "tags": [...]
}
```

#### Create Tag
```
POST /api/tags/
Content-Type: application/json

{
  "name": "string",
  "category_id": integer
}

Response: 201 Created
```

#### Delete Tag
```
DELETE /api/tags/{tag_id}
Response: 204 No Content
```

### Search (`/api/search/`)

#### Search Open Library
```
GET /api/search/?query=harry+potter&field=title
Response: 200 OK
[
  {
    "title": "string",
    "author": "string",
    "isbn": "string",
    "pages": integer
  },
  ...
]
```

### Stats (`/api/stats/`)

#### Get Reading Statistics
```
GET /api/stats/
Response: 200 OK
{
  "total_books": integer,
  "finished_books": integer,
  "pages_read": integer,
  "yearly_goal": integer,
  "yearly_progress": integer
}
```

### Backup (`/api/backup/`)

#### Export Books (CSV/JSON)
```
GET /api/backup/?format=csv|json
Response: 200 OK
[CSV data or JSON array]
```

#### Import Books (CSV/JSON)
```
POST /api/backup/
Content-Type: multipart/form-data

file: [CSV or JSON file]

Response: 200 OK
{
  "imported": integer,
  "failed": integer
}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `204 No Content` - Request successful, no content to return
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Rate Limiting

Currently no rate limiting is implemented. This may be added in future versions.
