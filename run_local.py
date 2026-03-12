#!/usr/bin/env python3
"""Run the full ChessMirror stack locally — no Docker required.

Requirements:
  - MongoDB running on localhost:27017 (the only mandatory service)
  - Stockfish binary (download from https://stockfishchess.org/download/)
  - Python packages:  pip install -r backend/requirements.txt
  - Node packages:    cd frontend && npm install

What this replaces vs Docker:
  - PostgreSQL  → SQLite (auto-created as backend/chessmirror.db)
  - Redis       → FastAPI BackgroundTasks (USE_CELERY=false)
  - Celery worker → runs inside the FastAPI process
  - MongoDB     → must still be running (only remaining external dependency)

Usage:
  python run_local.py
  python run_local.py --stockfish "C:/path/to/stockfish.exe"
  python run_local.py --mongo-url mongodb://localhost:27017/chessmirror
"""
import argparse
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")

# ── Defaults ──────────────────────────────────────────────────────────────────

SQLITE_URL = f"sqlite:///{os.path.join(BACKEND, 'chessmirror.db')}"
DEFAULT_MONGO = "mongodb://localhost:27017/chessmirror"

# Common Stockfish locations to probe automatically
STOCKFISH_CANDIDATES = [
    # Windows
    r"C:\Program Files\Stockfish\stockfish.exe",
    r"C:\stockfish\stockfish.exe",
    os.path.join(ROOT, "stockfish.exe"),
    os.path.join(ROOT, "stockfish", "stockfish.exe"),
    # macOS (Homebrew)
    "/opt/homebrew/bin/stockfish",
    "/usr/local/bin/stockfish",
    # Linux
    "/usr/games/stockfish",
    "/usr/bin/stockfish",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_stockfish() -> str | None:
    for path in STOCKFISH_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def check_mongodb(url: str) -> bool:
    try:
        from pymongo import MongoClient
        client = MongoClient(url, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return True
    except Exception:
        return False


def stream_output(proc, label: str, color: str):
    """Print subprocess output with a coloured label prefix."""
    RESET = "\033[0m"
    for line in iter(proc.stdout.readline, b""):
        print(f"{color}[{label}]{RESET} {line.decode(errors='replace').rstrip()}")


# ── Preflight checks ──────────────────────────────────────────────────────────

def preflight(mongo_url: str, stockfish_path: str | None) -> str:
    """Return resolved stockfish path or exit with helpful instructions."""
    print("\n── Preflight checks ────────────────────────────────────────────")

    # MongoDB
    print(f"  MongoDB ({mongo_url}) ... ", end="", flush=True)
    if check_mongodb(mongo_url):
        print("OK")
    else:
        print("FAILED")
        print("\nERROR: Cannot connect to MongoDB.")
        print("Install MongoDB Community: https://www.mongodb.com/try/download/community")
        print("Then start it with:  mongod  (or via the MongoDB Compass / service)")
        sys.exit(1)

    # Stockfish
    sf = stockfish_path or find_stockfish()
    print(f"  Stockfish ... ", end="", flush=True)
    if sf and os.path.isfile(sf):
        print(f"OK  ({sf})")
    else:
        print("NOT FOUND")
        print("\nWARNING: Stockfish binary not found.")
        print("Download from: https://stockfishchess.org/download/")
        print("Then either:")
        print("  • Place stockfish.exe in the project root")
        print("  • Pass --stockfish 'C:/path/to/stockfish.exe'")
        print("\nThe server will start but game analysis will fail without Stockfish.")
        sf = "stockfish"  # let it fail at runtime with a clear error

    # npm
    print(f"  npm ... ", end="", flush=True)
    result = subprocess.run(["npm", "--version"], capture_output=True)
    if result.returncode == 0:
        print(f"OK  (v{result.stdout.decode().strip()})")
    else:
        print("NOT FOUND")
        print("\nERROR: npm not found. Install Node.js: https://nodejs.org/")
        sys.exit(1)

    print("────────────────────────────────────────────────────────────────\n")
    return sf


# ── Start processes ───────────────────────────────────────────────────────────

def start_backend(mongo_url: str, stockfish_path: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "DATABASE_URL": SQLITE_URL,
        "MONGODB_URL": mongo_url,
        "USE_CELERY": "false",
        "STOCKFISH_PATH": stockfish_path,
        "JWT_SECRET": os.getenv("JWT_SECRET", "local-dev-secret-not-for-production"),
        # Silence Redis connection warnings from Celery config on startup
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    }
    cmd = [sys.executable, "-m", "uvicorn", "main:app",
           "--host", "0.0.0.0", "--port", "8000", "--reload"]
    return subprocess.Popen(
        cmd, cwd=BACKEND, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def start_frontend() -> subprocess.Popen:
    env = {
        **os.environ,
        "NEXT_PUBLIC_API_URL": "http://localhost:8000",
    }
    # On Windows, npm is a .cmd file and needs shell=True
    cmd = ["npm", "run", "dev"]
    return subprocess.Popen(
        cmd, cwd=FRONTEND, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        shell=(sys.platform == "win32"),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stockfish", metavar="PATH", help="Path to Stockfish executable")
    parser.add_argument("--mongo-url", default=DEFAULT_MONGO, metavar="URL",
                        help=f"MongoDB connection URL (default: {DEFAULT_MONGO})")
    parser.add_argument("--no-frontend", action="store_true",
                        help="Start backend only (skip npm run dev)")
    args = parser.parse_args()

    stockfish = preflight(args.mongo_url, args.stockfish)

    procs = []
    threads = []

    CYAN = "\033[96m"
    GREEN = "\033[92m"

    print("Starting backend on  http://localhost:8000")
    print("API docs at          http://localhost:8000/docs\n")
    backend = start_backend(args.mongo_url, stockfish)
    procs.append(backend)
    t = threading.Thread(target=stream_output, args=(backend, "backend", CYAN), daemon=True)
    t.start()
    threads.append(t)

    if not args.no_frontend:
        time.sleep(2)  # give the backend a moment to bind
        print("\nStarting frontend on http://localhost:3000\n")
        frontend = start_frontend()
        procs.append(frontend)
        t = threading.Thread(target=stream_output, args=(frontend, "frontend", GREEN), daemon=True)
        t.start()
        threads.append(t)

    print("\nPress Ctrl+C to stop all services.\n")

    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("Done.")


if __name__ == "__main__":
    main()
