# Bookmark

A personal book tracker: manage everything owned, wanted, read, and more.
Python FastAPI backend with an installable progressive web app frontend.

**Live App:** https://bookmark.example.com (replace with your deployment URL)

---

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit it -- at minimum SECRET_KEY and OWNER_PASSWORD
uvicorn app.main:app --reload
```

Open http://localhost:8000 and sign in with `OWNER_USERNAME` / `OWNER_PASSWORD`
from your `.env`.

For local development set `SECURE_COOKIES=false`. A Secure-only cookie is never
sent back over plain `http://`, so leaving it on means the login appears to
succeed and then immediately forgets you.

### Testing

```bash
pytest                 # run the full test suite
pytest -v              # with verbose output
pytest tests/test_books.py::test_progress_is_derived_from_pages
```

Tests never touch the network — Open Library is mocked with `respx` — and use a
throwaway database in a temp directory, so they cannot disturb your real data.

---

## How the pieces fit

```
app/
  main.py          FastAPI app, static mounting, SPA fallback
  config.py        settings from the environment
  database.py      engine + session
  models.py        Book, Tag, TagCategory, ReadingGoal, Preference, User
  schemas.py       request/response validation
  auth.py          argon2 hashing, signed session cookie
  seed.py          the seven rainbow presets
  openlibrary.py   search client + fuzzy match scoring
  routers/         auth_routes, books, tags, search, stats, backup
static/            index.html, style.css, app.js, manifest, service worker, icons
tests/             pytest suite
```

Interactive API docs run at `/api/docs` while the server is up.

### Tags

Seven presets, one per colour of the rainbow, split across two categories:

| Category | Exclusive | Tags |
|---|---|---|
| Status | yes — one per book | Did Not Finish (red), Reading (orange), Want to Read (yellow), Read (blue) |
| Shelf | no | Owned (green), Lent Out (indigo), Favourite (violet) |

Status is exclusive so a book sorts onto exactly one shelf. Shelf is not,
because a book can be owned, lent out and beloved at the same time. Genre and
Mood arrive empty, waiting for whatever the reader wants to put there.

Every one of these is an ordinary database row. Rename them, recolour them,
move them between categories, delete them, add new categories with their own
exclusivity rule — all from the Tags screen, presets included.

Behaviour keys on a hidden `role` field rather than the tag's name, so renaming
"Read" to "Leído" doesn't break the statistics or the automatic finish dates.

### Adding books

One flow, two doors. A quick search box, and an Advanced Search panel that
folds down to expose title, author, subject, publisher, ISBN, language and a
year range — filled fields are ANDed together. Results come back scored against
what was typed, with the closest one marked and a confidence percentage, to
confirm or reject. If Open Library is down or has never heard of the book,
there's a manual form, and the app says so rather than showing an error.

Open Library needs no API key and no registration, which is what keeps the
whole "ship a book database" problem down to one HTTP request.

---

## Deployment as a PWA

The app is a progressive web app, installable on mobile devices without an app store.

**Installation on iOS:**
1. Deploy to a server with HTTPS.
2. Open the URL in Safari (not Chrome; only Safari can install PWAs on iOS).
3. Tap Share → Add to Home Screen.

**Key features:**
- The service worker caches the shell, so the app opens instantly.
- Library data syncs across devices via the server.
- No app store review process, no $99/year developer account.

### Hosting

Consider these factors when choosing a host:

- **Persistent disk:** SQLite requires a persistent disk. Most free tiers don't include one.
- **Always-on:** Free tiers may spin down during idle periods.
- **Alternative:** Use a hosted Postgres database instead of SQLite. No code changes needed — add
  `psycopg[binary]` to `requirements.txt` and point `DATABASE_URL` at your Postgres instance.

Popular options:
- **Fly.io** — `fly launch --no-deploy`, then `fly volumes create bookmark_data --size 1`.
- **Render** — Free tier lacks persistent disk; consider paid disk or Postgres.
- **Railway** — Runs on monthly credit.

Environment variables for deployment:

```
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
OWNER_USERNAME=<username>
OWNER_PASSWORD=<strong password>
SECURE_COOKIES=true
```

The password is hashed with argon2 on first boot and never stored in plaintext. Users can change it
from Settings after login.

---

## GitHub

```bash
git init
git add .
git commit -m "Bookmark: first shelf"
git branch -M main
git remote add origin git@github.com:<you>/bookmark.git
git push -u origin main
```

`.gitignore` already excludes `.env`, `.venv/` and every `*.db` file. Nobody's
library or password ends up in the repo.

---

## Notes for later

- `Base.metadata.create_all` handles the schema on boot, which is fine until
  you change a column on a database that already has books in it. Alembic is in
  `requirements.txt` for when that day comes.
- One uvicorn worker, deliberately. SQLite dislikes concurrent writers, and for
  one reader there is nothing to gain from more.
- Bump `CACHE` in `static/sw.js` whenever the front end changes, or returning
  phones keep serving the old shell from cache.
- Covers are hotlinked from Open Library rather than copied. They load over the
  network and are not part of a backup.
