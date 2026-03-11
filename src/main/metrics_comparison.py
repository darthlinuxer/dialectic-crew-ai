"""Metrics stability checks for self-improve validation."""

from __future__ import annotations

from dialectic.metrics import MetricsStore


def metrics_stable(
    store: MetricsStore,
    baseline: dict,
    retention: float,
) -> tuple[bool, str]:
    """Compare current metrics against baseline; reject significant regressions."""
    for metric_type in ("prd_score", "task_score"):
        old = baseline.get(metric_type, {})
        if old.get("count", 0) < 3:
            continue

        new = store.trend(metric_type, window=10)
        if new["count"] < 3:
            continue

        if new["mean"] < old["mean"] * retention:
            return False, (
                f"{metric_type} regressed: {old['mean']:.1f} → {new['mean']:.1f} "
                f"(retention threshold: {retention:.0%})"
            )

    return True, "metrics stable"