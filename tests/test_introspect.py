"""Tests for dialectic.introspect -- 4-lens introspection engine."""

import textwrap

import pytest

from dialectic.introspect import (
    _code_health_lens,
    _failure_patterns_lens,
    _metric_trends_lens,
    _vision_gap_lens,
    run_introspection,
)
from dialectic.metrics import MetricRecord, MetricsStore, _reset_metrics_store


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_metrics_store()
    yield
    _reset_metrics_store()


@pytest.fixture(name="metrics_store")
def _metrics_store(tmp_path):
    return MetricsStore(db_path=tmp_path / "test_introspect.db")


class TestVisionGapLens:
    def test_finds_incomplete_items(self, tmp_path):
        vision = tmp_path / "VISION.md"
        vision.write_text(textwrap.dedent("""\
            # Roadmap
            - [x] Completed item
            - [ ] Incomplete item A
            - [ ] Incomplete item B
            - [x] Another done
        """))
        results = _vision_gap_lens(vision)
        assert len(results) == 2
        assert results[0].category == "vision_gap"
        assert "Incomplete item A" in results[0].title

    def test_all_complete(self, tmp_path):
        vision = tmp_path / "VISION.md"
        vision.write_text("- [x] Done\n- [x] Also done\n")
        assert _vision_gap_lens(vision) == []

    def test_no_checkboxes(self, tmp_path):
        vision = tmp_path / "VISION.md"
        vision.write_text("# Just a heading\nSome text.\n")
        assert _vision_gap_lens(vision) == []

    def test_missing_file(self, tmp_path):
        assert _vision_gap_lens(tmp_path / "nonexistent.md") == []

    def test_impact_ranking(self, tmp_path):
        vision = tmp_path / "VISION.md"
        items = "\n".join(f"- [ ] Item {i}" for i in range(5))
        vision.write_text(items)
        results = _vision_gap_lens(vision)
        assert results[0].estimated_impact == "high"
        assert results[3].estimated_impact == "medium"

    def test_run_introspection_uses_roadmap_for_self_mode(self, tmp_path, metrics_store, monkeypatch):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        roadmap = tmp_path / "internal" / "ROADMAP.md"
        vision.parent.mkdir(parents=True)
        vision.write_text("# Anti-drift only\nNo checkboxes live here anymore.\n")
        roadmap.write_text(textwrap.dedent("""\
            # Roadmap
            - [x] Completed item
            - [ ] Move introspection checklist source to ROADMAP
        """))

        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        report = run_introspection(store=metrics_store)

        assert any(
            "Move introspection checklist source to ROADMAP" in opportunity.title
            for opportunity in report.opportunities
        )


class TestMetricTrendsLens:
    def test_low_prd_scores_detected(self, metrics_store):
        for v in [6.0, 7.0, 7.5]:
            metrics_store.record(MetricRecord(metric_type="prd_score", value=v))
        results = _metric_trends_lens(metrics_store)
        assert any(o.id == "metric-prd-score-low" for o in results)

    def test_high_retries_detected(self, metrics_store):
        for _ in range(3):
            metrics_store.record(MetricRecord(metric_type="prd_retry_count", value=3.0))
        results = _metric_trends_lens(metrics_store)
        assert any(o.id == "metric-prd-retries-high" for o in results)

    def test_guardrail_rejections_detected(self, metrics_store):
        for _ in range(5):
            metrics_store.record(MetricRecord(metric_type="guardrail_reject", value=1.0))
        results = _metric_trends_lens(metrics_store, window=10)
        assert any(o.id == "metric-guardrail-rejections" for o in results)

    def test_healthy_metrics_no_opportunities(self, metrics_store):
        for _ in range(5):
            metrics_store.record(MetricRecord(metric_type="prd_score", value=9.5))
            metrics_store.record(MetricRecord(metric_type="prd_retry_count", value=1.0))
        assert _metric_trends_lens(metrics_store) == []

    def test_empty_store_no_opportunities(self, metrics_store):
        assert _metric_trends_lens(metrics_store) == []


class TestCodeHealthLens:
    def test_counts_todos(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "example.py").write_text(
            "# TODO: fix this\n# FIXME: another one\ndef ok(): pass\n"
        )
        results = _code_health_lens(tmp_path)
        assert results == []  # only 2 TODOs, threshold is >5

    def test_many_todos_flagged(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        lines = "\n".join(f"# TODO: item {i}" for i in range(10))
        (src / "example.py").write_text(lines)
        results = _code_health_lens(tmp_path)
        assert len(results) >= 1
        assert results[0].category == "code_health"

    def test_no_src_dir(self, tmp_path):
        assert _code_health_lens(tmp_path) == []


class TestFailurePatternsLens:
    def test_recurring_rejections(self, metrics_store):
        for _ in range(5):
            metrics_store.record(MetricRecord(
                metric_type="guardrail_reject",
                value=1.0,
                context={"guardrail": "prd", "reason": "invalid_schema"},
            ))
        results = _failure_patterns_lens(metrics_store)
        assert len(results) == 1
        assert "prd" in results[0].title
        assert results[0].category == "failure_pattern"

    def test_no_rejections(self, metrics_store):
        assert _failure_patterns_lens(metrics_store) == []

    def test_below_threshold(self, metrics_store):
        for _ in range(2):
            metrics_store.record(MetricRecord(
                metric_type="guardrail_reject",
                value=1.0,
                context={"guardrail": "quality", "reason": "bad"},
            ))
        assert _failure_patterns_lens(metrics_store) == []


class TestRunIntrospection:
    def test_produces_report(self, tmp_path, metrics_store, monkeypatch):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True)
        vision.write_text("- [ ] Unfinished feature\n- [x] Done feature\n")

        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        report = run_introspection(store=metrics_store)
        assert report.timestamp
        assert isinstance(report.baseline_metrics, dict)
        assert "prd_score" in report.baseline_metrics

    def test_opportunities_sorted_by_impact(self, tmp_path, metrics_store, monkeypatch):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True)
        items = "\n".join(f"- [ ] Item {i}" for i in range(5))
        vision.write_text(items)

        for v in [5.0, 6.0, 6.5]:
            metrics_store.record(MetricRecord(metric_type="prd_score", value=v))

        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        report = run_introspection(store=metrics_store)
        impacts = [o.estimated_impact for o in report.opportunities]
        assert impacts == sorted(impacts, key=lambda i: {"high": 0, "medium": 1, "low": 2}[i])
