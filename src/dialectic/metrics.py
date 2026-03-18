"""
SQLite-backed passive metrics store.

Records timestamped metric events from PRD flows, task execution,
and guardrail rejections.  Emit-only integration -- callers fire and
forget; no behaviour is altered.

Usage:
    from dialectic.metrics import get_metrics_store

    store = get_metrics_store()
    store.record(MetricRecord(
        metric_type="prd_score",
        value=9.2,
        context={"feature": "Login with 2FA", "vision_context": "project"},
    ))
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dialectic.vision import resolve_project_root

logger = logging.getLogger(__name__)

_DEFAULT_DB_NAME = "metrics.db"
_DEFAULT_DB_DIR = ".dialectic"
_METRICS_DB_ENV_VAR = "DIALECTIC_METRICS_DB"


def _default_metrics_db_path() -> Path:
    """Return the default metrics database path."""
    configured = os.getenv(_METRICS_DB_ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser()
    return resolve_project_root() / _DEFAULT_DB_DIR / _DEFAULT_DB_NAME


class MetricRecord(BaseModel):
    """Single metric data point."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metric_type: str
    value: float
    context: dict[str, Any] = Field(default_factory=dict)


class MetricsStore:
    """Thread-safe SQLite store for metric records."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = _default_metrics_db_path()
        db_path = Path(db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._local = threading.local()
        self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def _ensure_table(self) -> None:
        self._conn().execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL,
                metric_type TEXT   NOT NULL,
                value      REAL   NOT NULL,
                context    TEXT   NOT NULL DEFAULT '{}'
            )
            """
        )
        self._conn().commit()

    def record(self, metric: MetricRecord) -> None:
        try:
            self._conn().execute(
                "INSERT INTO metrics (timestamp, metric_type, value, context) "
                "VALUES (?, ?, ?, ?)",
                (
                    metric.timestamp,
                    metric.metric_type,
                    metric.value,
                    json.dumps(metric.context, ensure_ascii=False),
                ),
            )
            self._conn().commit()
        except Exception:
            logger.debug(
                "Failed to record metric %s", metric.metric_type, exc_info=True
            )

    def query(
        self,
        metric_type: str,
        since: str | None = None,
        limit: int = 500,
    ) -> list[MetricRecord]:
        sql = "SELECT timestamp, metric_type, value, context FROM metrics WHERE metric_type = ?"
        params: list[Any] = [metric_type]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn().execute(sql, params).fetchall()
        return [
            MetricRecord(
                timestamp=r[0],
                metric_type=r[1],
                value=r[2],
                context=json.loads(r[3]),
            )
            for r in rows
        ]

    def trend(self, metric_type: str, window: int = 10) -> dict[str, Any]:
        records = self.query(metric_type, limit=window)
        if not records:
            return {"count": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "latest": 0.0}
        values = [r.value for r in records]
        return {
            "count": len(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[0],
        }

    def close(self) -> None:
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


_store: MetricsStore | None = None
_store_lock = threading.Lock()


def get_metrics_store(db_path: str | Path | None = None) -> MetricsStore:
    """Return the singleton MetricsStore (lazy-init)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = MetricsStore(db_path)
    return _store


def _reset_metrics_store() -> None:
    """Reset the singleton (testing only)."""
    global _store
    if _store is not None:
        _store.close()
    _store = None


def emit(metric_type: str, value: float, **ctx: Any) -> None:
    """Fire-and-forget metric emission."""
    try:
        store = get_metrics_store()
        store.record(MetricRecord(metric_type=metric_type, value=value, context=ctx))
    except Exception:
        logger.debug("emit(%s) failed", metric_type, exc_info=True)
