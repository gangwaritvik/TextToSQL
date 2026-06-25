"""
Text-to-SQL Entry Point
Run this file to start BOTH the FastAPI backend and the React frontend.

Set the environment variable RUN_FRONTEND=0 to start the backend only.
"""

import os
import uvicorn
import logging
import sys
import shutil
import subprocess
import atexit
import signal
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env.local
env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

# Suppress FAISS loader INFO messages (they're just about trying different SIMD versions)
logging.getLogger("faiss.loader").setLevel(logging.WARNING)

from backend.app import app

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Track the frontend process so we can shut it down cleanly
_frontend_process: "subprocess.Popen | None" = None


def start_frontend() -> "subprocess.Popen | None":
    """Start the React dev server (npm start) in a child process.

    Returns the process handle, or None if the frontend could not be started
    (npm missing, dependencies not installed, etc.). Failing here must never
    stop the backend from running.
    """
    # npm is npm.cmd on Windows; shutil.which resolves the right executable.
    npm = shutil.which("npm")
    if npm is None:
        print("⚠️  Frontend skipped: 'npm' was not found on PATH.")
        return None

    if not FRONTEND_DIR.exists():
        print(f"⚠️  Frontend skipped: directory not found at {FRONTEND_DIR}")
        return None

    if not (FRONTEND_DIR / "node_modules").exists():
        print("⚠️  Frontend dependencies missing. Run 'npm install' in the frontend folder.")
        return None

    # BROWSER=none stops CRA from opening a browser tab on every (re)start.
    env = {**os.environ, "BROWSER": "none"}

    try:
        process = subprocess.Popen(
            [npm, "start"],
            cwd=str(FRONTEND_DIR),
            env=env,
            shell=False,
        )
        print("🎨 Frontend starting on: http://localhost:3000")
        return process
    except Exception as exc:  # noqa: BLE001 - never let frontend break the backend
        print(f"⚠️  Failed to start frontend: {exc}")
        return None


def stop_frontend() -> None:
    """Terminate the frontend process (and its child node processes) if running."""
    global _frontend_process
    if _frontend_process is None or _frontend_process.poll() is not None:
        return

    print("🛑 Stopping frontend...")
    try:
        if os.name == "nt":
            # taskkill /T also kills the node child the npm wrapper spawned.
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(_frontend_process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            _frontend_process.terminate()
            _frontend_process.wait(timeout=10)
    except Exception:  # noqa: BLE001 - best effort cleanup
        pass
    finally:
        _frontend_process = None


if __name__ == "__main__":
    # Only launch the frontend in the main process, not in uvicorn's reload
    # worker (which re-imports this module). RUN_FRONTEND=0 disables it entirely.
    run_frontend = os.getenv("RUN_FRONTEND", "1") != "0"

    if run_frontend:
        _frontend_process = start_frontend()
        atexit.register(stop_frontend)
        # Ensure Ctrl+C / termination also tears down the frontend.
        signal.signal(signal.SIGINT, lambda *_: (stop_frontend(), sys.exit(0)))
        signal.signal(signal.SIGTERM, lambda *_: (stop_frontend(), sys.exit(0)))

    print("🚀 Starting Text-to-SQL Backend...")
    print("📊 Server running on: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")

    try:
        uvicorn.run(
            "backend.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
        )
    finally:
        stop_frontend()
