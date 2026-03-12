"""Start Celery worker."""
import subprocess
import sys

try:
    print("Starting Celery worker...")
    result = subprocess.run(
        [sys.executable, "-m", "celery", "-A", "tasks", "worker", "--loglevel=info", "--pool=solo"],
        cwd=".",
        capture_output=False
    )
except KeyboardInterrupt:
    print("\nWorker stopped")
except Exception as e:
    print(f"Error starting worker: {e}")
