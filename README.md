# Boocker

A personal book tracker for managing your reading life: track books you own, want to read, are reading, and have finished. Built with Python FastAPI backend and an installable progressive web app frontend.

**[📱 Open Live App](#live-app)** | **[📚 Documentation](./docs/)** | **[🤝 Contributing](./docs/CONTRIBUTING.md)** | **[📄 License](./LICENSE)**

---

## Features

✨ **Track Your Books**
- Add books from Open Library or manually
- Mark status (want to read, reading, finished, DNF)
- Organize with tags and categories
- See your reading statistics

📱 **Progressive Web App**
- Install on mobile devices without an app store
- Works offline with service worker caching
- Syncs across devices via the server
- Fast, lightweight, and responsive

🔐 **Simple & Secure**
- Single-user design (perfect for personal use)
- Session-based authentication
- No signup required — just set a password
- All your data stays under your control

📊 **Reading Insights**
- Track pages read per year
- Set and monitor yearly reading goals
- See reading trends over time

---

## Live App

**Currently Deploying:** https://boocker.fly.dev/

To set up your own live instance:

1. **Choose a hosting provider** (Fly.io recommended)
   - See [Deployment Guide](./docs/DEPLOYMENT.md)
   
2. **Clone and deploy**
   ```bash
   git clone https://github.com/lylaxtraw/Book-Tracker.git
   cd "Book Tracker"
   flyctl launch --no-deploy
   flyctl volumes create data --size 1
   flyctl deploy
   ```

3. **Access your app**
   - Visit your deployed URL
   - Create your admin password
   - Start tracking!

For detailed setup instructions, see [Deployment Guide](./docs/DEPLOYMENT.md).

---

## Install on Mobile

Bookmark is a Progressive Web App (PWA), which means you can install it directly on your device **without visiting an app store**.

### iOS (iPhone/iPad)

1. Open **Safari** and navigate to your Bookmark instance
2. Tap the **Share** button (square with arrow)
3. Scroll down and tap **"Add to Home Screen"**
4. Enter a name (or use the default "Bookmark")
5. Tap **"Add"**
6. The app will now appear on your home screen like a native app

### Android (Phone/Tablet)

1. Open **Chrome** or **Edge** and navigate to your Bookmark instance
2. Tap the **menu icon** (three dots) in the top-right corner
3. Tap **"Install app"** (or **"Create shortcut"** on some devices)
4. Confirm the app details
5. The app will install and appear on your home screen

### Desktop (Windows/Mac/Linux)

1. Open **Chrome**, **Edge**, or **Brave** browser
2. Navigate to your Bookmark instance
3. Click the **install icon** in the address bar (usually on the right side)
4. Or use the menu: **Menu → "Install [App Name]"**
5. The app will install like a native desktop application

### Features of the Installed App

- **Offline Access** — Works offline using cached data (changes sync when back online)
- **App Window** — Runs in its own window, not a browser tab
- **Fast Loading** — Instant startup, no browser chrome
- **Notifications Ready** — Can receive push notifications (feature in development)

---

## Architecture

The app consists of:

- **Backend**: FastAPI (Python) with SQLAlchemy ORM
- **Database**: SQLite (local) or PostgreSQL (production)
- **Frontend**: Progressive Web App (vanilla JavaScript)
- **Hosting**: Containerized with Docker

For detailed architecture documentation, see [Architecture Guide](./docs/ARCHITECTURE.md).

---

## Tag System

Seven preset tags organized by type and color:

| Category | Behavior | Tags |
|---|---|---|
| **Status** | One per book | Did Not Finish (red), Reading (orange), Want to Read (yellow), Read (blue) |
| **Shelf** | Multiple per book | Owned (green), Lent Out (indigo), Favourite (violet) |

All tags are editable — rename them, change colors, add new categories, or delete presets. The system tracks tag *roles* internally, so renaming "Read" to "Leído" won't break your statistics.

---

## Search & Add Books

Search for books from **Open Library** (requires no API key or login):

1. **Quick Search**: Type title, author, or ISBN
2. **Advanced Search**: Filter by title, author, subject, publisher, year
3. **Results**: Scored by relevance — the best match is highlighted
4. **Add Manually**: If Open Library doesn't have the book, fill in the details yourself

---

## API Documentation

For developers integrating with Book Tracker:

- **Interactive Docs**: Available at `/api/docs` when running locally
- **Full Reference**: See [API Documentation](./docs/API.md)
- **Example Endpoints**:
  - `GET /api/books/` — List your books
  - `POST /api/books/` — Add a book
  - `GET /api/stats/` — Get reading statistics

---

## Documentation

- **[Getting Started](./docs/DEPLOYMENT.md)** — Deploy to Fly.io or Render
- **[Mobile Installation](./docs/MOBILE.md)** — Install as an app on your phone
- **[Architecture](./docs/ARCHITECTURE.md)** — How the app is structured
- **[API Docs](./docs/API.md)** — Complete endpoint reference
- **[Contributing](./docs/CONTRIBUTING.md)** — Report bugs, request features, contribute code

For developers setting up a local environment, see [Developer Setup](./.dev/SETUP.md).

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

You're free to use, modify, and deploy Book Tracker for personal or commercial use, as long as you provide attribution.

---

## Getting Help

- 📖 Check the [Documentation](./docs/)
- 🐛 Found a bug? [Report it](https://github.com/lylaxtraw/Book-Tracker/issues)
- 💡 Have an idea? [Request a feature](https://github.com/lylaxtraw/Book-Tracker/issues)
- 🤝 Want to contribute? See [Contributing Guide](./docs/CONTRIBUTING.md)

---

Made with love for you, my shrimptastic boy <3

<!--
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
--->
