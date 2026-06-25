"""
Centralized filesystem paths.

All generated/runtime artifacts (FAISS indices, query logs, the created-database
registry) live under a single top-level ``data/`` directory, kept separate from
source code and ignored by git. Importing this module guarantees those
directories exist.
"""

from pathlib import Path

# Project root = the directory that contains the ``backend`` package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Runtime data (git-ignored)
DATA_DIR = PROJECT_ROOT / "data"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
LOGS_DIR = DATA_DIR / "logs" / "queries"
CREATED_DATABASES_FILE = DATA_DIR / "created_databases.json"

# Make sure the runtime directories exist before anything writes to them.
for _directory in (DATA_DIR, EMBEDDINGS_DIR, LOGS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)
