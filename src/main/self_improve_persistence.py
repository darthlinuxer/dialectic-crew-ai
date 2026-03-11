"""Persistence and artifact-tracking helpers for self-improve cycles."""

from __future__ import annotations

from pathlib import Path
from typing import Type

from schemas import ImprovementOpportunity, SelfImprovementRecord


SELF_IMPROVE_STATE_DIR = Path(".dialectic") / "self_improve"


def record_prd_artifacts(record: SelfImprovementRecord, flow) -> str:
    record.prd_flow_id = getattr(flow, "flow_id", "") or getattr(flow.state, "id", "") or ""
    record.prd_path_json = flow.state.prd_path_json or ""
    record.prd_path_md = flow.state.prd_path_md or ""
    return record.prd_path_json


def record_plan_artifacts(record: SelfImprovementRecord, plan_result: dict) -> str:
    record.plan_path_json = plan_result.get("plan_path_json", "") or ""
    record.plan_path_md = plan_result.get("plan_path_md", "") or ""
    return record.plan_path_json


def record_execution_artifacts(record: SelfImprovementRecord, exec_result: dict) -> None:
    record.execution_run_id = exec_result.get("run_id", "") or ""
    record.execution_task_flow_ids = exec_result.get("task_flow_ids", {}) or {}
    record.execution_output_path = exec_result.get("output_path", "") or ""
    record.execution_report_path = exec_result.get("report_path", "") or ""


def self_improve_record_path(
    project_root: Path,
    cycle_id: str,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> Path:
    path = project_root / state_dir / f"{cycle_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_self_improve_record(
    project_root: Path,
    record: SelfImprovementRecord,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> None:
    path = self_improve_record_path(project_root, record.cycle_id, state_dir=state_dir)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


def load_self_improve_record(
    project_root: Path,
    cycle_id: str,
    *,
    state_dir: Path = SELF_IMPROVE_STATE_DIR,
) -> SelfImprovementRecord:
    path = self_improve_record_path(project_root, cycle_id, state_dir=state_dir)
    if not path.exists():
        raise FileNotFoundError(f"Self-improve snapshot not found: {path}")
    return SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))


def resolve_resume_context(record: SelfImprovementRecord) -> tuple[list[ImprovementOpportunity], dict]:
    return list(record.selected_opportunities), dict(record.baseline_metrics)


def summarize_resume_state(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> dict[str, str | list[str]]:
    reused: list[str] = []
    if record.prd_generated and record.prd_path_json:
        reused.append(f"PRD: {record.prd_path_json}")
    if record.plan_generated and record.plan_path_json:
        reused.append(f"Plan: {record.plan_path_json}")
    if record.execution_run_id:
        reused.append(f"Execution run: {record.execution_run_id}")

    if not record.prd_generated:
        next_stage = "PRD generation"
    elif not record.plan_generated:
        next_stage = "planning"
    elif (
        not record.execution_attempted
        or not record.execution_output_path
        or not record.execution_report_path
        or last_failure_reason.startswith("Execution failed:")
    ):
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
    records_dir = project_root / state_dir
    if not records_dir.exists():
        return []

    rows: list[dict[str, str]] = []
    for path in records_dir.glob("*.json"):
        try:
            record = SelfImprovementRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
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
    if not path:
        raise error_cls(failure_reason)
    return path