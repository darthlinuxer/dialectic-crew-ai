"""Persistence and artifact-tracking helpers for self-improve cycles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Type, cast

from pydantic import ValidationError

from schemas import ImprovementOpportunity, SelfImprovementRecord

from .git_helpers import git_branch_exists

SELF_IMPROVE_STATE_DIR = Path(".dialectic") / "self_improve"
SELF_IMPROVE_STATE_DIR_ENV_VAR = "DIALECTIC_SELF_IMPROVE_STATE_DIR"
SELF_IMPROVE_PRD_DIR = Path("prd_output") / "self"
_POST_EXECUTION_RESUME_STAGES = frozenset(
    {
        "quality gate",
        "quality remediation",
        "quality gate (remediation exhausted)",
        "test validation",
        "metrics validation",
        "PR creation",
    }
)


def _normalize_story_id(story_id: str) -> str:
    cleaned = story_id.strip().upper()
    if cleaned.isdigit():
        return f"US{int(cleaned)}"
    if cleaned.startswith("US"):
        suffix = cleaned[2:].lstrip("-_ ")
        if suffix.isdigit():
            return f"US{int(suffix)}"
    return cleaned


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _plan_source_matches_prd(payload: dict[str, Any], prd_path: Path) -> bool:
    source_prd_path = payload.get("source_prd_path")
    if not isinstance(source_prd_path, str) or not source_prd_path.strip():
        return False
    try:
        resolved_source = Path(source_prd_path).expanduser().resolve()
    except OSError:
        return False
    return resolved_source == prd_path


def _plan_marks_story_completed(payload: dict[str, Any]) -> bool:
    if payload.get("status") == "completed":
        return True
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return False
    return all(
        isinstance(task, dict) and task.get("status") == "completed" for task in tasks
    )


def _story_ids_from_prd_payload(user_stories: list[Any]) -> list[str]:
    return [
        story["id"].strip()
        for story in user_stories
        if isinstance(story, dict)
        and isinstance(story.get("id"), str)
        and story.get("id", "").strip()
    ]


def _user_stories_from_prd_payload(
    payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if payload is None:
        return []

    raw_user_stories = payload.get("user_stories")
    if not isinstance(raw_user_stories, list):
        return []

    return [story for story in raw_user_stories if isinstance(story, dict)]


def _is_prd_payload(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return (
        isinstance(payload.get("feature_name"), str)
        and isinstance(payload.get("objective"), str)
        and isinstance(payload.get("user_stories"), list)
    )


def _completed_story_ids_from_plan_artifacts(prd_path: Path) -> set[str]:
    completed_story_ids: set[str] = set()
    for candidate_path in prd_path.parent.glob("exec_*.json"):
        candidate = _load_json_object(candidate_path)
        if candidate is None or not _plan_source_matches_prd(candidate, prd_path):
            continue
        if not _plan_marks_story_completed(candidate):
            continue
        story_id = candidate.get("user_story_id")
        if isinstance(story_id, str) and story_id.strip():
            completed_story_ids.add(_normalize_story_id(story_id))
    return completed_story_ids


def completed_story_ids_for_prd(prd_path: str) -> list[str]:
    """Return completed PRD user story ids in PRD order using exported plan artifacts."""
    resolved_prd_path = Path(prd_path).expanduser().resolve()
    payload = _load_json_object(resolved_prd_path)
    user_stories = cast(list[dict[str, Any]], _user_stories_from_prd_payload(payload))
    if not user_stories:
        return []

    ordered_story_ids = _story_ids_from_prd_payload(user_stories)
    completed_story_ids = _completed_story_ids_from_plan_artifacts(resolved_prd_path)

    return [
        story_id
        for story_id in ordered_story_ids
        if _normalize_story_id(story_id) in completed_story_ids
    ]


def next_available_story_for_prd(prd_path: str) -> str | None:
    """Return the first unfinished PRD story id using exported plan artifacts as truth."""
    resolved_prd_path = Path(prd_path).expanduser().resolve()
    payload = _load_json_object(resolved_prd_path)
    user_stories = cast(list[dict[str, Any]], _user_stories_from_prd_payload(payload))
    if not user_stories:
        return None

    completed_story_ids = {
        _normalize_story_id(story_id)
        for story_id in completed_story_ids_for_prd(str(resolved_prd_path))
    }
    for story in cast(list[dict[str, Any]], user_stories):
        story_id = story.get("id")
        if isinstance(story_id, str) and story_id.strip():
            if _normalize_story_id(story_id) not in completed_story_ids:
                return story_id.strip()
    return None


def latest_self_prd_path(project_root: Path) -> str | None:
    """Return the newest valid SELF-scope PRD artifact path, if one exists."""
    prd_dir = project_root / SELF_IMPROVE_PRD_DIR
    if not prd_dir.exists():
        return None

    candidates: list[Path] = []
    for path in prd_dir.glob("*.json"):
        payload = _load_json_object(path)
        if _is_prd_payload(payload):
            candidates.append(path)

    if not candidates:
        return None
    return str(max(candidates, key=lambda candidate: candidate.stat().st_mtime))


def latest_unfinished_self_prd_path(project_root: Path) -> str | None:
    """Return the newest valid SELF PRD that still has an unfinished story."""
    prd_dir = project_root / SELF_IMPROVE_PRD_DIR
    if not prd_dir.exists():
        return None

    candidates: list[Path] = []
    for path in prd_dir.glob("*.json"):
        payload = _load_json_object(path)
        if not _is_prd_payload(payload):
            continue
        if next_available_story_for_prd(str(path)) is None:
            continue
        candidates.append(path)

    if not candidates:
        return None
    return str(max(candidates, key=lambda candidate: candidate.stat().st_mtime))


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
    resolved_state_dir = (
        Path(raw_state_dir).expanduser() if raw_state_dir else state_dir
    )
    if not resolved_state_dir.is_absolute():
        resolved_state_dir = project_root / resolved_state_dir
    return resolved_state_dir


def record_prd_artifacts(record: SelfImprovementRecord, flow) -> str:
    """Copy exported PRD artifact metadata from the flow state into the cycle record."""
    record.prd_flow_id = (
        getattr(flow, "flow_id", "") or getattr(flow.state, "id", "") or ""
    )
    record.prd_path_json = flow.state.prd_path_json or ""
    record.prd_path_md = flow.state.prd_path_md or ""
    return record.prd_path_json


def record_plan_artifacts(record: SelfImprovementRecord, plan_result: dict) -> str:
    """Copy exported planning artifact metadata into the cycle record."""
    record.plan_path_json = plan_result.get("plan_path_json", "") or ""
    record.plan_path_md = plan_result.get("plan_path_md", "") or ""
    return record.plan_path_json


def record_execution_artifacts(
    record: SelfImprovementRecord, exec_result: dict
) -> None:
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


def _next_resume_stage(
    record: SelfImprovementRecord,
    *,
    execution_reusable: bool,
    quality_gate_completed: bool,
) -> str:
    next_stage = "completed"
    if not record.prd_generated:
        next_stage = "PRD generation"
    elif not record.plan_generated:
        next_stage = "planning"
    elif not execution_reusable:
        next_stage = "execution"
    elif not quality_gate_completed:
        if record.quality_remediation_exhausted:
            next_stage = "quality gate (remediation exhausted)"
        elif record.quality_remediation_attempted:
            next_stage = "quality remediation"
        else:
            next_stage = "quality gate"
    elif not record.tests_passed:
        next_stage = "test validation"
    elif not record.metrics_stable:
        next_stage = "metrics validation"
    elif not record.pr_created:
        next_stage = "PR creation"
    return next_stage


def summarize_resume_state(
    record: SelfImprovementRecord,
    last_failure_reason: str = "",
) -> dict[str, str | list[str]]:
    """Summarize what a resumed cycle can reuse and which stage remains."""
    reused: list[str] = []
    execution_reusable = execution_result_reusable(record, last_failure_reason)
    quality_gate_completed = (
        record.quality_gate_passed
        or record.tests_passed
        or record.metrics_stable
        or record.pr_created
    )
    if record.prd_generated and record.prd_path_json:
        reused.append(f"PRD: {record.prd_path_json}")
    if record.plan_generated and record.plan_path_json:
        reused.append(f"Plan: {record.plan_path_json}")
    if execution_reusable and record.execution_run_id:
        reused.append(f"Execution run: {record.execution_run_id}")
    next_stage = _next_resume_stage(
        record,
        execution_reusable=execution_reusable,
        quality_gate_completed=quality_gate_completed,
    )

    return {
        "last_failure": last_failure_reason or "unknown",
        "next_stage": next_stage,
        "reused": reused,
    }


def has_meaningful_self_improve_progress(record: SelfImprovementRecord) -> bool:
    """Return whether a saved cycle progressed far enough to be worth resuming."""
    return any(
        (
            bool(record.selected_opportunities),
            record.opportunities_found > 0,
            record.opportunities_attempted > 0,
            record.prd_generated,
            record.plan_generated,
            record.execution_attempted,
            record.quality_gate_passed,
            record.tests_passed,
            record.metrics_stable,
            record.pr_created,
            bool(record.branch_name),
            bool(record.feature_request),
        )
    )


def _resume_stage_requires_live_branch(next_stage: str) -> bool:
    return next_stage in _POST_EXECUTION_RESUME_STAGES


def _record_is_listable_resumable_cycle(
    project_root: Path,
    record: SelfImprovementRecord,
    *,
    next_stage: str,
) -> bool:
    if next_stage == "completed":
        return False
    if not has_meaningful_self_improve_progress(record):
        return False
    if not _resume_stage_requires_live_branch(next_stage):
        return True
    if not record.branch_name:
        return False
    return git_branch_exists(record.branch_name, project_root)


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
            record = SelfImprovementRecord.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError):
            continue
        summary = summarize_resume_state(record, record.failure_reason)
        next_stage = str(summary["next_stage"])
        if not _record_is_listable_resumable_cycle(
            project_root,
            record,
            next_stage=next_stage,
        ):
            continue
        rows.append(
            {
                "cycle_id": record.cycle_id,
                "timestamp": record.timestamp,
                "next_stage": next_stage,
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
    "SELF_IMPROVE_PRD_DIR",
    "completed_story_ids_for_prd",
    "latest_self_prd_path",
    "latest_unfinished_self_prd_path",
    "next_available_story_for_prd",
    "list_resumable_cycles",
    "load_self_improve_record",
    "execution_result_reusable",
    "has_meaningful_self_improve_progress",
    "record_execution_artifacts",
    "record_plan_artifacts",
    "record_prd_artifacts",
    "require_artifact",
    "resolve_resume_context",
    "save_self_improve_record",
    "self_improve_record_path",
    "summarize_resume_state",
]
