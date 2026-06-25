"""
Created-Database Registry

Tracks databases that were created through the file-upload feature so they can be
treated as temporary. The uploaded data lives only for the session it was created
in, and the database itself is dropped on the next backend startup.

A small JSON file is used so the registry survives across restarts (the process
that created the database has already stopped by the time cleanup runs).
"""

import json
import logging
from typing import List

from sqlalchemy import text

from backend.db.db import get_engine
from backend.paths import CREATED_DATABASES_FILE

logger = logging.getLogger(__name__)

# Registry file lives under the project-level data/ directory
_REGISTRY_PATH = CREATED_DATABASES_FILE

# Databases that must NEVER be dropped, regardless of registry contents
_PROTECTED = {"postgres", "template0", "template1"}


def _read() -> List[str]:
    """Read the list of created database names from disk (best-effort)."""
    try:
        if _REGISTRY_PATH.exists():
            with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [str(x) for x in data]
    except Exception as e:
        logger.warning(f"Could not read created-DB registry: {e}")
    return []


def _write(names: List[str]) -> None:
    """Persist the list of created database names to disk (best-effort)."""
    try:
        with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(set(names)), f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write created-DB registry: {e}")


def register_created_database(name: str) -> None:
    """Record that a database was created via the upload feature."""
    names = _read()
    if name not in names:
        names.append(name)
        _write(names)
        logger.info(f"Registered temporary database for later cleanup: {name}")


def get_created_databases() -> List[str]:
    """Return the list of databases created via the upload feature."""
    return _read()


def clear_created_databases() -> None:
    """Forget all registered created databases."""
    _write([])


def drop_created_databases() -> List[str]:
    """Drop every database registered as created-via-upload.

    Only databases recorded in the registry are touched, so pre-existing
    databases (e.g. Sample, fastapi_db, postgres) are never affected. System
    databases are additionally protected as defense-in-depth.

    Returns the list of database names that were actually dropped.
    """
    registered = _read()
    dropped: List[str] = []

    if not registered:
        return dropped

    # Connect to the default maintenance database to drop the others
    admin_engine = get_engine()  # defaults to the configured default DB (postgres)
    try:
        for db_name in registered:
            if db_name in _PROTECTED:
                logger.warning(f"Skipping protected database: {db_name}")
                continue
            try:
                # DROP DATABASE cannot run in a transaction block -> AUTOCOMMIT.
                with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    # Terminate any lingering connections to the target DB so the
                    # drop is not blocked by an open session.
                    conn.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                            "WHERE datname = :name AND pid <> pg_backend_pid()"
                        ),
                        {"name": db_name},
                    )
                    # db_name comes from our own sanitizer ([a-z0-9_] only), so
                    # quoting the identifier is safe here.
                    conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
                logger.info(f"🗑️  Dropped temporary database: {db_name}")
                dropped.append(db_name)
            except Exception as e:
                logger.error(f"Failed to drop temporary database {db_name}: {e}")
    finally:
        admin_engine.dispose()

    # Keep only entries that still need attention (failed drops are retried next
    # time); drop protected and successfully-removed ones from the registry.
    remaining = [d for d in registered if d not in dropped and d not in _PROTECTED]
    _write(remaining)
    return dropped
