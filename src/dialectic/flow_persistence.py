"""Helpers for CrewAI flow persistence configuration."""

from __future__ import annotations

import os
from pathlib import Path

from crewai.flow.persistence import SQLiteFlowPersistence

from dialectic.vision import resolve_project_root

FLOW_DB_ENV_VAR = "DIALECTIC_FLOW_DB"
DEFAULT_FLOW_DB_PATH = ".dialectic/flows.db"


def get_flow_persistence_db_path() -> str:
    """Return the configured SQLite path for persisted CrewAI flow state."""
    raw_path = os.getenv(FLOW_DB_ENV_VAR, DEFAULT_FLOW_DB_PATH).strip() or DEFAULT_FLOW_DB_PATH
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = resolve_project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def build_sqlite_flow_persistence() -> SQLiteFlowPersistence:
    """Build a SQLite persistence backend using the repository flow DB path."""
    return SQLiteFlowPersistence(db_path=get_flow_persistence_db_path())