"""
Introspection engine -- 4-lens analysis of the app's current state.

Lenses:
  1. **VISION gap** -- parses SELF_VISION.md checkboxes to find incomplete items
  2. **Metric trends** -- queries MetricsStore for declining scores / rising retries
  3. **Code health** -- counts TODOs, test inventory via pytest --co -q
  4. **Past failures** -- analyses guardrail rejection patterns and failed tasks

Produces an IntrospectionReport with ranked ImprovementOpportunity items.
"""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dialectic.metrics import MetricsStore, get_metrics_store
from dialectic.vision import VisionContext, get_vision_path, resolve_project_root
from schemas import ImprovementOpportunity, IntrospectionReport

logger = logging.getLogger(__name__)

_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}


def _vision_gap_lens(
    vision_path: Path,
) -> list[ImprovementOpportunity]:
    """Parse ``[ ]`` / ``[x]`` checkboxes in the vision document."""
    if not vision_path.exists():
        return []
    text = vision_path.read_text(encoding="utf-8")
    opportunities: list[ImprovementOpportunity] = []
    incomplete_items: list[str] = []
    total_checkboxes = 0

    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^- \[[ x]\]", stripped):
            total_checkboxes += 1
            if stripped.startswith("- [ ]"):
                label = stripped[5:].strip()
                incomplete_items.append(label)

    if not incomplete_items:
        return []

    for idx, item in enumerate(incomplete_items):
        impact = "high" if idx < 3 else "medium"
        opportunities.append(
            ImprovementOpportunity(
                id=f"vision-gap-{idx+1}",
                category="vision_gap",
                title=f"Incomplete roadmap item: {item[:80]}",
                description=item,
                evidence=[
                    f"{len(incomplete_items)}/{total_checkboxes} roadmap items remain unchecked"
                ],
                estimated_impact=impact,
            )
        )
    return opportunities


def _metric_trends_lens(
    store: MetricsStore,
    window: int = 10,
) -> list[ImprovementOpportunity]:
    """Detect declining quality scores or rising retry / rejection counts."""
    opportunities: list[ImprovementOpportunity] = []

    score_trend = store.trend("prd_score", window=window)
    if score_trend["count"] >= 3 and score_trend["mean"] < 8.0:
        opportunities.append(
            ImprovementOpportunity(
                id="metric-prd-score-low",
                category="metric_regression",
                title="PRD quality scores are below target",
                description=(
                    f"Mean PRD score over last {score_trend['count']} runs is "
                    f"{score_trend['mean']:.1f} (target: >= 9.0)"
                ),
                evidence=[
                    f"mean={score_trend['mean']:.1f}",
                    f"min={score_trend['min']:.1f}",
                    f"max={score_trend['max']:.1f}",
                ],
                estimated_impact="high",
            )
        )

    retry_trend = store.trend("prd_retry_count", window=window)
    if retry_trend["count"] >= 3 and retry_trend["mean"] > 2.0:
        opportunities.append(
            ImprovementOpportunity(
                id="metric-prd-retries-high",
                category="metric_regression",
                title="PRD retry counts are elevated",
                description=(
                    f"Mean retries: {retry_trend['mean']:.1f} "
                    f"(indicating prompt or agent quality issues)"
                ),
                evidence=[f"mean_retries={retry_trend['mean']:.1f}"],
                estimated_impact="medium",
            )
        )

    reject_trend = store.trend("guardrail_reject", window=50)
    if reject_trend["count"] >= 5:
        opportunities.append(
            ImprovementOpportunity(
                id="metric-guardrail-rejections",
                category="metric_regression",
                title="Frequent guardrail rejections",
                description=(
                    f"{reject_trend['count']} guardrail rejections in recent history"
                ),
                evidence=[f"total_rejections={reject_trend['count']}"],
                estimated_impact="medium",
            )
        )

    task_trend = store.trend("task_score", window=window)
    if task_trend["count"] >= 3 and task_trend["mean"] < 7.0:
        opportunities.append(
            ImprovementOpportunity(
                id="metric-task-score-low",
                category="metric_regression",
                title="Task execution scores are below threshold",
                description=(
                    f"Mean task score: {task_trend['mean']:.1f} (target: >= 7.5)"
                ),
                evidence=[
                    f"mean={task_trend['mean']:.1f}",
                    f"min={task_trend['min']:.1f}",
                ],
                estimated_impact="high",
            )
        )

    return opportunities


def _code_health_lens(project_root: Path) -> list[ImprovementOpportunity]:
    """Count TODOs in source and run test discovery."""
    opportunities: list[ImprovementOpportunity] = []
    src_dir = project_root / "src"
    todo_count = 0
    todo_files: list[str] = []

    if src_dir.exists():
        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                hits = [
                    line.strip()
                    for line in content.splitlines()
                    if "TODO" in line or "FIXME" in line or "HACK" in line
                ]
                if hits:
                    todo_count += len(hits)
                    todo_files.append(str(py_file.relative_to(project_root)))
            except OSError:
                pass

    if todo_count > 5:
        opportunities.append(
            ImprovementOpportunity(
                id="code-health-todos",
                category="code_health",
                title=f"{todo_count} TODO/FIXME/HACK markers in source code",
                description="Accumulated technical debt markers across source files",
                evidence=todo_files[:10],
                estimated_impact="low" if todo_count < 15 else "medium",
            )
        )

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--co", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
            test_count_line = lines[-1] if lines else ""
            match = re.search(r"(\d+)\s+test", test_count_line)
            test_count = int(match.group(1)) if match else 0
            if test_count < 20:
                opportunities.append(
                    ImprovementOpportunity(
                        id="code-health-low-tests",
                        category="code_health",
                        title=f"Only {test_count} tests discovered",
                        description="Test coverage may be insufficient",
                        evidence=[test_count_line.strip()],
                        estimated_impact="medium",
                    )
                )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug("pytest discovery failed", exc_info=True)

    return opportunities


def _failure_patterns_lens(
    store: MetricsStore,
) -> list[ImprovementOpportunity]:
    """Analyse guardrail rejection patterns for recurring issues."""
    opportunities: list[ImprovementOpportunity] = []

    rejections = store.query("guardrail_reject", limit=100)
    if not rejections:
        return []

    reason_counts: dict[str, int] = {}
    for r in rejections:
        reason = r.context.get("reason", "unknown")
        guardrail = r.context.get("guardrail", "unknown")
        key = f"{guardrail}:{reason}"
        reason_counts[key] = reason_counts.get(key, 0) + 1

    for key, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        if count >= 3:
            opportunities.append(
                ImprovementOpportunity(
                    id=f"failure-{key.replace(':', '-')}",
                    category="failure_pattern",
                    title=f"Recurring guardrail failure: {key}",
                    description=f"{count} rejections for pattern '{key}'",
                    evidence=[f"occurrences={count}"],
                    estimated_impact="medium" if count < 10 else "high",
                )
            )

    return opportunities


def run_introspection(
    store: MetricsStore | None = None,
    vision_context: VisionContext = VisionContext.SELF,
    metric_window: int = 10,
) -> IntrospectionReport:
    """Run all 4 lenses and return a sorted IntrospectionReport."""
    if store is None:
        store = get_metrics_store()

    vision_path = get_vision_path(vision_context)
    project_root = resolve_project_root()

    opportunities: list[ImprovementOpportunity] = []
    opportunities.extend(_vision_gap_lens(vision_path))
    opportunities.extend(_metric_trends_lens(store, window=metric_window))
    opportunities.extend(_code_health_lens(project_root))
    opportunities.extend(_failure_patterns_lens(store))

    opportunities.sort(key=lambda o: _IMPACT_ORDER.get(o.estimated_impact, 1))

    baseline = {
        "prd_score": store.trend("prd_score", window=metric_window),
        "task_score": store.trend("task_score", window=metric_window),
        "prd_retry_count": store.trend("prd_retry_count", window=metric_window),
        "guardrail_reject": store.trend("guardrail_reject", window=50),
    }

    return IntrospectionReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        opportunities=opportunities,
        baseline_metrics=baseline,
    )
