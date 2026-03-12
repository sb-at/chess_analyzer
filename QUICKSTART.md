# ChessMirror — Quick Start

## What you need

| Requirement | Notes |
|---|---|
| Python 3.10+ | python.org |
| Node.js 18+ | nodejs.org (includes npm) |
| MongoDB Community | mongodb.com/try/download/community — check "Install as a Service" during setup |
| Stockfish | stockfishchess.org/download — download and unzip anywhere |

No Docker. No `.env` file. No OAuth credentials.

---

## One-time setup

```bash
git clone <repo-url>
cd chess_analyzer

pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

---

## Run

```bash
python run_local.py --stockfish "C:/path/to/stockfish.exe"
```

This starts:
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:3000`

SQLite is used automatically in place of PostgreSQL. Analysis runs in-process — no Celery or Redis needed.

---

## Using the app

1. Open `http://localhost:3000`
2. Enter your Lichess or Chess.com username — no account needed
3. Select the time control you want to analyze
4. Choose how many games (25 / 50 / 100 / 250 / 500)
5. Wait for analysis to complete
6. Click any pattern or opening to play over your mistakes in an interactive board

---

## Troubleshooting

**MongoDB connection failed**
- Make sure MongoDB is installed and the service is running
- On Windows: search "Services", find "MongoDB", click Start
- Or run `mongod` manually in a terminal

**Stockfish not found**
- Pass the explicit path: `python run_local.py --stockfish "C:/path/to/stockfish.exe"`
- Analysis will fail without Stockfish but the rest of the app still works

**npm not found**
- Install Node.js from nodejs.org (includes npm)
