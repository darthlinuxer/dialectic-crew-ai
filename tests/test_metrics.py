"""Tests for dialectic.metrics -- SQLite-backed passive metrics store."""

from pathlib import Path

import pytest

from dialectic.metrics import (
    _default_metrics_db_path,
    MetricRecord,
    MetricsStore,
    emit,
    get_metrics_store,
    _reset_metrics_store,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_metrics_store()
    yield
    _reset_metrics_store()


@pytest.fixture
def store(tmp_path):
    return MetricsStore(db_path=tmp_path / "test_metrics.db")


class TestMetricRecord:
    def test_defaults(self):
        r = MetricRecord(metric_type="prd_score", value=9.2)
        assert r.metric_type == "prd_score"
        assert r.value == 9.2
        assert r.timestamp  # auto-populated
        assert r.context == {}

    def test_with_context(self):
        r = MetricRecord(
            metric_type="task_score",
            value=7.5,
            context={"task_id": "T-001", "success": True},
        )
        assert r.context["task_id"] == "T-001"


class TestMetricsStore:
    def test_default_path_uses_hidden_runtime_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("dialectic.metrics.resolve_project_root", lambda: tmp_path)
        monkeypatch.delenv("DIALECTIC_METRICS_DB", raising=False)

        assert _default_metrics_db_path() == tmp_path / ".dialectic" / "metrics.db"

    def test_default_path_honors_env_override(self, monkeypatch):
        monkeypatch.setenv("DIALECTIC_METRICS_DB", "~/custom-metrics.db")

        assert _default_metrics_db_path() == Path("~/custom-metrics.db").expanduser()

    def test_creates_parent_directory_for_db(self, tmp_path):
        db = tmp_path / "nested" / "metrics" / "custom.db"
        store = MetricsStore(db_path=db)

        assert db.parent.exists()
        store.close()

    def test_record_and_query(self, store):
        store.record(MetricRecord(metric_type="prd_score", value=8.5))
        store.record(MetricRecord(metric_type="prd_score", value=9.0))
        store.record(MetricRecord(metric_type="other", value=1.0))

        results = store.query("prd_score")
        assert len(results) == 2
        assert all(r.metric_type == "prd_score" for r in results)

    def test_query_since_filter(self, store):
        store.record(
            MetricRecord(
                metric_type="score", value=5.0, timestamp="2025-01-01T00:00:00"
            )
        )
        store.record(
            MetricRecord(
                metric_type="score", value=8.0, timestamp="2026-06-01T00:00:00"
            )
        )
        results = store.query("score", since="2026-01-01T00:00:00")
        assert len(results) == 1
        assert results[0].value == 8.0

    def test_query_limit(self, store):
        for i in range(20):
            store.record(MetricRecord(metric_type="x", value=float(i)))
        results = store.query("x", limit=5)
        assert len(results) == 5

    def test_query_empty(self, store):
        assert store.query("nonexistent") == []

    def test_trend(self, store):
        for v in [6.0, 7.0, 8.0, 9.0, 10.0]:
            store.record(MetricRecord(metric_type="score", value=v))
        t = store.trend("score", window=5)
        assert t["count"] == 5
        assert t["min"] == 6.0
        assert t["max"] == 10.0
        assert t["mean"] == 8.0

    def test_trend_empty(self, store):
        t = store.trend("empty")
        assert t["count"] == 0
        assert t["mean"] == 0.0

    def test_context_roundtrip(self, store):
        store.record(
            MetricRecord(
                metric_type="ctx",
                value=1.0,
                context={"nested": {"key": "val"}, "list": [1, 2]},
            )
        )
        results = store.query("ctx")
        assert results[0].context["nested"]["key"] == "val"
        assert results[0].context["list"] == [1, 2]

    def test_close_and_reopen(self, tmp_path):
        db = tmp_path / "reopen.db"
        s1 = MetricsStore(db_path=db)
        s1.record(MetricRecord(metric_type="a", value=1.0))
        s1.close()

        s2 = MetricsStore(db_path=db)
        assert len(s2.query("a")) == 1
        s2.close()


class TestEmitHelper:
    def test_emit_records_metric(self, tmp_path, monkeypatch):
        db = tmp_path / "emit.db"
        monkeypatch.setattr(
            "dialectic.metrics._store", MetricsStore(db_path=db)
        )
        emit("prd_score", 9.5, feature="Login")
        store = get_metrics_store()
        results = store.query("prd_score")
        assert len(results) == 1
        assert results[0].context["feature"] == "Login"

    def test_emit_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(
            "dialectic.metrics._store",
            None,
        )
        monkeypatch.setattr(
            "dialectic.metrics.get_metrics_store",
            lambda db_path=None: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        emit("bad", 0.0)
