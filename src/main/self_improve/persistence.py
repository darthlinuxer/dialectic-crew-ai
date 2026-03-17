"""Persistence and artifact-tracking helpers for self-improve cycles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Type

from pydantic import ValidationError

from schemas import ImprovementOpportunity, SelfImprovementRecord


SELF_IMPROVE_STATE_DIR = Path(".dialectic") / "self_improve"
SELF_IMPROVE_STATE_DIR_ENV_VAR = "DIALECTIC_SELF_IMPROVE_STATE_DIR"


def execution_result_reusable(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> bool:
    """Return whether the saved execution can be safely reused on resume."""
    if (
        not record.execution_attempted
        or not record.execution_output_path
        or not record.execution_report_path
    ):
        return False
    if last_failure_reason.startswith("Execution failed:"):
        return False
    if record.execution_story_status in {"failed", "partially_completed"}:
        return False
    return True


def _resolve_state_dir(project_root: Path, state_dir: Path) -> Path:
    """Resolve the effective snapshot directory, honoring an env override when present."""
    raw_state_dir = os.getenv(SELF_IMPROVE_STATE_DIR_ENV_VAR, "").strip()
    resolved_state_dir = Path(raw_state_dir).expanduser() if raw_state_dir else state_dir
    if not resolved_state_dir.is_absolute():
        resolved_state_dir = project_root / resolved_state_dir
    return resolved_state_dir


def record_prd_artifacts(record: SelfImprovementRecord, flow) -> str:
    """Copy exported PRD artifact metadata from the flow state into the cycle record."""
    record.prd_flow_id = getattr(flow, "flow_id", "") or getattr(flow.state, "id", "") or ""
    record.prd_path_json = flow.state.prd_path_json or ""
    record.prd_path_md = flow.state.prd_path_md or ""
    return record.prd_path_json


def record_plan_artifacts(record: SelfImprovementRecord, plan_result: dict) -> str:
    """Copy exported planning artifact metadata into the cycle record."""
    record.plan_path_json = plan_result.get("plan_path_json", "") or ""
    record.plan_path_md = plan_result.get("plan_path_md", "") or ""
    return record.plan_path_json


def record_execution_artifacts(record: SelfImprovementRecord, exec_result: dict) -> None:
    """Copy exported execution artifact metadata into the cycle record."""
    record.execution_run_id = exec_result.get("run_id", "") or ""
    record.execution_task_flow_ids = exec_result.get("task_flow_ids", {}) or {}
    record.execution_story_status = exec_result.get("story_status", "") or ""
    record.execution_output_path = exec_result.get("output_path", "") or ""
    record.execution_report_path = exec_result.get("report_path", "") or ""


def self_improve_record_path(
    project_root: Path,
    cycle_id: str,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> Path:
    """Return the snapshot path for a self-improve cycle and ensure its parent exists."""
    path = _resolve_state_dir(project_root, state_dir) / f"{cycle_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_self_improve_record(
    project_root: Path,
    record: SelfImprovementRecord,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> None:
    """Persist a self-improve cycle snapshot to disk."""
    path = self_improve_record_path(project_root, record.cycle_id, state_dir=state_dir)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


def load_self_improve_record(
    project_root: Path,
    cycle_id: str,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> SelfImprovementRecord:
    """Load a persisted self-improve cycle snapshot from disk."""
    path = self_improve_record_path(project_root, cycle_id, state_dir=state_dir)
    if not path.exists():
        raise FileNotFoundError(f"Self-improve snapshot not found: {path}")
    return SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))


def resolve_resume_context(
    record: SelfImprovementRecord,
) -> tuple[list[ImprovementOpportunity], dict]:
    """Extract the saved opportunities and baseline metrics for resume handling."""
    return list(record.selected_opportunities), dict(record.baseline_metrics)


def summarize_resume_state(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> dict[str, str | list[str]]:
    """Summarize what a resumed cycle can reuse and which stage remains."""
    reused: list[str] = []
    execution_reusable = execution_result_reusable(record, last_failure_reason)
    if record.prd_generated and record.prd_path_json:
        reused.append(f"PRD: {record.prd_path_json}")
    if record.plan_generated and record.plan_path_json:
        reused.append(f"Plan: {record.plan_path_json}")
    if execution_reusable and record.execution_run_id:
        reused.append(f"Execution run: {record.execution_run_id}")

    if not record.prd_generated:
        next_stage = "PRD generation"
    elif not record.plan_generated:
        next_stage = "planning"
    elif not execution_reusable:
        next_stage = "execution"
    elif not record.tests_passed:
        next_stage = "test validation"
    elif not record.metrics_stable:
        next_stage = "metrics validation"
    elif not record.pr_created:
        next_stage = "PR creation"
    else:
        next_stage = "completed"

    return {
        "last_failure": last_failure_reason or "unknown",
        "next_stage": next_stage,
        "reused": reused,
    }


def list_resumable_cycles(
    project_root: Path,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> list[dict[str, str]]:
    """List persisted self-improve cycles that can be resumed."""
    records_dir = _resolve_state_dir(project_root, state_dir)
    if not records_dir.exists():
        return []

    rows: list[dict[str, str]] = []
    for path in records_dir.glob("*.json"):
        try:
            record = SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            continue
        summary = summarize_resume_state(record, record.failure_reason)
        rows.append(
            {
                "cycle_id": record.cycle_id,
                "timestamp": record.timestamp,
                "next_stage": str(summary["next_stage"]),
                "last_failure": str(summary["last_failure"]),
            }
        )

    rows.sort(key=lambda row: (row["timestamp"], row["cycle_id"]), reverse=True)
    return rows


def require_artifact(
    path: str,
    failure_reason: str,
    *,
    error_cls: Type[Exception] = RuntimeError,
) -> str:
    """Require a non-empty artifact path or raise the configured error type."""
    if not path:
        raise error_cls(failure_reason)
    return path

__all__ = [
    "SELF_IMPROVE_STATE_DIR",
    "SELF_IMPROVE_STATE_DIR_ENV_VAR",
    "list_resumable_cycles",
    "load_self_improve_record",
    "execution_result_reusable",
    "record_execution_artifacts",
    "record_plan_artifacts",
    "record_prd_artifacts",
    "require_artifact",
    "resolve_resume_context",
    "save_self_improve_record",
    "self_improve_record_path",
    "summarize_resume_state",
]

