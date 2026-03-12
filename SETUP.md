# Setup Guide

For a fast path to running the app, see [QUICKSTART.md](QUICKSTART.md).

---

## Prerequisites

- **Python 3.10+** — python.org
- **Node.js 18+** — nodejs.org
- **MongoDB Community** — the only required external service
- **Stockfish** — required for chess analysis

Docker is not required.

---

## Install MongoDB

Download MongoDB Community from mongodb.com/try/download/community.

**Windows**: Run the MSI installer. Check "Install MongoDB as a Service" — this means it starts automatically and you never need to run `mongod` manually.

**macOS**: `brew tap mongodb/brew && brew install mongodb-community && brew services start mongodb-community`

**Linux**: Follow the distro-specific instructions at mongodb.com/docs/manual/installation/

Verify it's running:
```bash
mongosh --eval "db.adminCommand('ping')"
```

---

## Install Stockfish

Download a prebuilt binary from stockfishchess.org/download. Unzip it anywhere.

`run_local.py` checks several common locations automatically:
- Project root (`stockfish.exe`)
- `C:\Program Files\Stockfish\stockfish.exe`
- `C:\stockfish\stockfish.exe`
- `/opt/homebrew/bin/stockfish` (macOS Homebrew)
- `/usr/bin/stockfish`, `/usr/games/stockfish` (Linux)

If it's somewhere else, pass `--stockfish "path/to/stockfish"` at runtime.

---

## Install dependencies

```bash
# Python
pip install -r backend/requirements.txt

# Node
cd frontend && npm install && cd ..
```

---

## Run

```bash
python run_local.py
# or with explicit Stockfish path:
python run_local.py --stockfish "C:/path/to/stockfish.exe"
# backend only (skip frontend):
python run_local.py --no-frontend
# custom MongoDB URL:
python run_local.py --mongo-url mongodb://localhost:27017/chessmirror
```

`run_local.py` will:
1. Check MongoDB connectivity (exits with instructions if unreachable)
2. Locate Stockfish (warns but continues if not found)
3. Start the FastAPI backend at `http://localhost:8000` using SQLite
4. Start the Next.js frontend at `http://localhost:3000`

Press `Ctrl+C` to stop both.

---

## What run_local.py replaces vs Docker

| Docker service | Local equivalent |
|---|---|
| PostgreSQL | SQLite (`backend/chessmirror.db`, auto-created) |
| Redis | Eliminated — analysis runs inside FastAPI via BackgroundTasks |
| Celery worker | Eliminated — same as above |
| MongoDB | Still required — install locally (see above) |
| Stockfish | Binary on your machine (see above) |

---

## Environment variables

No `.env` file is required. `run_local.py` sets all necessary variables automatically:

| Variable | Value set by run_local.py |
|---|---|
| `DATABASE_URL` | `sqlite:///backend/chessmirror.db` |
| `MONGODB_URL` | `mongodb://localhost:27017/chessmirror` (or `--mongo-url`) |
| `USE_CELERY` | `false` |
| `STOCKFISH_PATH` | detected or `--stockfish` argument |
| `JWT_SECRET` | `local-dev-secret-not-for-production` |

For production, set these as real environment variables before starting the server.

---

## Troubleshooting

**MongoDB connection failed at startup**
- Check the service is running: Windows → Services → MongoDB → Start
- Or: `brew services start mongodb-community` (macOS)

**Stockfish not found**
- Pass the path explicitly: `python run_local.py --stockfish "C:/path/to/stockfish.exe"`
- Analysis jobs will fail without it; everything else still works

**`psycopg2` install error**
- `psycopg2-binary` is in `requirements.txt` but is unused when running locally with SQLite
- If it fails to install, you can remove it from `requirements.txt` — it won't affect local operation

**Port already in use**
- Backend default: 8000 — kill any existing uvicorn process
- Frontend default: 3000 — kill any existing Next.js process
