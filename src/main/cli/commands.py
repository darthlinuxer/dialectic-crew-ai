"""Command handlers for the CLI entrypoint."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TypedDict, cast

from dialectic import run_dialectic_flow
from dialectic.prd_flow import get_prd_resume_state
from dialectic.vision import VisionContext, ensure_vision_path, resolve_project_root
from execution.dialectic_execution import run_dialectic_execution
from execution.runner import run_execution
from execution.status import mark_task, show_status
from execution.verify import verify_task, verify_user_story
from planning.flow import run_user_story_planning
from schemas import SelfImprovementRecord

from ..self_improve import _list_resumable_cycles, run_self_improve
from ..self_improve.persistence import (
    list_unfinished_self_prds,
    load_self_improve_record,
)


SELF_IMPROVE_AUTO_RESUME = "__AUTO_RESUME__"


def _has_meaningful_self_improve_progress(record: SelfImprovementRecord) -> bool:
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


def _select_auto_resume_cycle(
    project_root: Path,
    rows: list[dict[str, str]],
) -> str:
    for row in rows:
        cycle_id = row["cycle_id"]
        try:
            record = load_self_improve_record(project_root, cycle_id)
        except (FileNotFoundError, OSError, ValueError):
            continue
        if _has_meaningful_self_improve_progress(record):
            return cycle_id

    return rows[0]["cycle_id"]


def _looks_like_prd_artifact(artifact_path: str) -> bool:
    try:
        payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("user_stories"), list)


def _validate_prd_artifact_mode_request(
    artifact_path: str | None,
    resume_cycle_id: str | None,
    enabled: bool,
    mode_flag: str,
) -> None:
    if not enabled:
        return
    if resume_cycle_id:
        print(f"Provide either {mode_flag} or --resume, not both.")
        sys.exit(1)
    if artifact_path is None:
        return
    if not _looks_like_prd_artifact(artifact_path):
        print(f"{mode_flag} requires a PRD JSON artifact with user_stories.")
        sys.exit(1)


def _build_self_improve_run_kwargs(
    artifact_path: str | None,
    next_roadmap_item: bool,
    next_available_story: bool,
    continue_prd: bool,
    selected_story_ref: str | None = None,
) -> dict[str, object]:
    run_kwargs: dict[str, object] = {
        "artifact_path": artifact_path,
        "next_roadmap_item": next_roadmap_item,
    }
    if next_available_story:
        run_kwargs["next_available_story"] = True
    if continue_prd:
        run_kwargs["continue_prd"] = True
    if selected_story_ref:
        run_kwargs["selected_story_ref"] = selected_story_ref
    return run_kwargs


def _validate_story_continuation_mode_conflict(
    next_available_story: bool,
    continue_prd: bool,
) -> None:
    if next_available_story and continue_prd:
        print("Provide either --continue-prd or --next-available-story, not both.")
        sys.exit(1)


def _self_improve_prompt_supported() -> bool:
    stdin = getattr(sys, "stdin", None)
    stdout = getattr(sys, "stdout", None)
    if stdin is None or stdout is None:
        return False
    return bool(getattr(stdin, "isatty", lambda: False)()) and bool(
        getattr(stdout, "isatty", lambda: False)()
    )


def _prompt_for_choice(
    prompt: str,
    valid_choices: set[str],
    *,
    default: str,
) -> str:
    while True:
        response = input(prompt).strip() or default
        if response in valid_choices:
            return response
        print(
            f"Invalid choice: {response}. "
            f"Choose one of {', '.join(sorted(valid_choices))}."
        )


def _prompt_for_story_selection(
    unfinished_prds: list[dict[str, Any]],
) -> tuple[str, str]:
    story_options: list[tuple[str, str, str, str]] = []
    print("\nAvailable unfinished stories:")
    for summary in unfinished_prds:
        prd_path = str(summary["path"])
        feature_name = str(summary.get("feature_name") or Path(prd_path).name)
        prd_name = Path(prd_path).name
        for story_ref in list(summary["unfinished_story_refs"]):
            story_options.append((prd_path, str(story_ref), feature_name, prd_name))

    for index, (_, story_ref, feature_name, prd_name) in enumerate(story_options, 1):
        print(f"  {index}. {story_ref} — {feature_name} ({prd_name})")

    selected = _prompt_for_choice(
        f"Select story [1-{len(story_options)}]: ",
        {str(index) for index in range(1, len(story_options) + 1)},
        default="1",
    )
    prd_path, story_ref, _, _ = story_options[int(selected) - 1]
    return prd_path, story_ref


def _prompt_for_smart_self_improve_mode(
    unfinished_prds: list[dict[str, Any]],
) -> dict[str, object]:
    latest = unfinished_prds[0]
    print("\nUnfinished SELF PRDs detected:")
    for index, summary in enumerate(unfinished_prds, 1):
        prd_path = str(summary["path"])
        feature_name = str(summary.get("feature_name") or Path(prd_path).name)
        print(
            f"  {index}. {feature_name} ({Path(prd_path).name}) — completed "
            f"{summary['completed_story_count']}/{summary['total_story_count']}, "
            f"next {summary['next_story_ref']}"
        )

    print("\nChoose how to proceed:")
    print("  1. Continue the next unfinished story from the latest PRD")
    print("  2. Continue all remaining stories from the latest PRD")
    print("  3. Choose a specific unfinished story")
    print("  4. Start a new self-improve cycle")

    choice = _prompt_for_choice(
        "Select [1-4] (default 1): ",
        {"1", "2", "3", "4"},
        default="1",
    )
    if choice == "1":
        return {
            "artifact_path": str(latest["path"]),
            "next_available_story": True,
            "continue_prd": False,
            "selected_story_ref": None,
        }
    if choice == "2":
        return {
            "artifact_path": str(latest["path"]),
            "next_available_story": False,
            "continue_prd": True,
            "selected_story_ref": None,
        }
    if choice == "3":
        prd_path, story_ref = _prompt_for_story_selection(unfinished_prds)
        return {
            "artifact_path": prd_path,
            "next_available_story": False,
            "continue_prd": False,
            "selected_story_ref": story_ref,
        }
    return {
        "artifact_path": None,
        "next_available_story": False,
        "continue_prd": False,
        "selected_story_ref": None,
    }


class PrdFlowKwargs(TypedDict):
    """Keyword arguments shared by PRD CLI dispatch helpers."""

    file_paths: list[str] | None
    vision_context: VisionContext
    resume_id: str | None
    max_retries: int | None
    consensus_min_score: float | None


def _build_prd_flow_kwargs(
    file_paths: list[str] | None,
    vision_context: VisionContext,
    resume_id: str | None,
    max_retries: int | None,
    consensus_min_score: float | None,
) -> PrdFlowKwargs:
    """Build the shared PRD dispatch kwargs used by CLI seams and command handlers."""
    return {
        "file_paths": file_paths,
        "vision_context": vision_context,
        "resume_id": resume_id,
        "max_retries": max_retries,
        "consensus_min_score": consensus_min_score,
    }


def _check_vision_exists(context: VisionContext = VisionContext.PROJECT) -> None:
    try:
        ensure_vision_path(context)
    except FileNotFoundError as exc:
        print("  Vision document not found!")
        print(f"  {exc}")
        sys.exit(1)


def cmd_prd(
    feature_request: str | None,
    file_paths: list[str] | None = None,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_id: str | None = None,
    max_retries: int | None = None,
    consensus_min_score: float | None = None,
    get_prd_resume_state_fn=get_prd_resume_state,
) -> None:
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Generate or resume a PRD flow from the CLI surface."""
    if not resume_id and not feature_request:
        print("Provide the feature: python main.py prd 'your feature here'")
        sys.exit(1)

    if resume_id and not get_prd_resume_state_fn(resume_id):
        print(f"Persisted PRD flow not found: {resume_id}")
        sys.exit(1)

    result = run_dialectic_flow(
        feature_request,
        **_build_prd_flow_kwargs(
            file_paths=file_paths,
            vision_context=vision_context,
            resume_id=resume_id,
            max_retries=max_retries,
            consensus_min_score=consensus_min_score,
        ),
    )
    print("\n" + "=" * 60)
    print("DIALECTIC PROCESS COMPLETE!")
    print("=" * 60)
    print(f"Flow ID: {result['flow_id']}")
    print(f"Quality Score: {result['quality_score']}/10.0")
    print(f"Total rounds: {result['iterations']}")
    print(f"Consensus: {result['consensus_reached']}")
    if result["consensus_reached"] and result["quality_score"] < 9.0:
        print(
            "Hint: consensus was reached below the hard approval threshold; "
            "rerun with '--consensus-min-score SCORE' to allow consensus-aware early stopping."
        )
    if not result["consensus_reached"] and result["quality_score"] < 9.0:
        print(
            "Hint: try a higher retry budget with '--max-retries N' "
            "to give the dialectic more rounds."
        )
    print("=" * 60)


def cmd_plan(
    prd_path: str | None,
    us_ref: str | None,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> None:
    """Generate a user-story execution plan from a PRD artifact."""
    if prd_path == "--latest":
        prd_path = None
    if prd_path and not os.path.exists(prd_path):
        print(f"PRD not found: {prd_path}")
        sys.exit(1)
    result = run_user_story_planning(prd_path, us_ref, vision_context=vision_context)
    print(f"Score: {result['quality_score']}/10.0")


def cmd_execute(
    plan_path: str | None,
    spec_only: bool = False,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_run_id: str | None = None,
) -> None:
    """Execute an approved plan or generate a spec-only artifact."""
    try:
        if spec_only:
            result = run_execution(plan_path=plan_path or "--latest")
            print(f"\nSpec generated: {result['output_path']}")
            print(f"   Plan: {result['plan_id']} -- {result['plan_title']}")
            return

        result = run_dialectic_execution(
            plan_path=plan_path or "--latest",
            vision_context=vision_context,
            resume_run_id=resume_run_id,
        )
        story_status = result.get("story_status", "unknown")
        print(f"\nExecution complete: {result['output_path']}")
        print(f"   Run ID: {result['run_id']}")
        print(f"   Plan: {result['plan_id']} -- {result['plan_title']}")
        print(f"   Story status: {story_status}")
        if result.get("verified_tasks"):
            print(f"   Verified: {', '.join(result['verified_tasks'])}")
        if result.get("failed_verification_tasks"):
            print(f"   Failed:   {', '.join(result['failed_verification_tasks'])}")
        if result.get("task_flow_ids"):
            for task_id, flow_id in sorted(result["task_flow_ids"].items()):
                print(f"   Task flow {task_id}: {flow_id}")
        print(f"   Report: {result['report_path']}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"{exc}")
        sys.exit(1)


def cmd_status(plan_path: str | None) -> None:
    """Show execution status for the requested plan."""
    try:
        show_status(plan_path)
    except FileNotFoundError as exc:
        print(f"  {exc}")
        sys.exit(1)


def cmd_mark(task_id: str, status: str, plan_path: str | None) -> None:
    """Update the status of an execution task."""
    valid = ("pending", "in_progress", "completed", "failed")
    if status not in valid:
        print(f"  Invalid status: '{status}'. Use: {', '.join(valid)}")
        sys.exit(1)
    try:
        mark_task(task_id, status, plan_path)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as exc:
        print(f"  {exc}")
        sys.exit(1)


def cmd_verify(task_id: str, plan_path: str | None, prd_path: str | None) -> None:
    """Run targeted verification for a single task."""
    try:
        result = verify_task(task_id, plan_path, prd_path)
        if result["verified"]:
            print(f"\n  Task {task_id} verified successfully!")
        else:
            print(f"\n  Task {task_id} did NOT pass verification.")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  {exc}")
        sys.exit(1)


def cmd_verify_story(plan_path: str | None, prd_path: str | None) -> None:
    """Run verification across all tasks for a user story."""
    try:
        result = verify_user_story(plan_path, prd_path)
        status = result["story_status"]
        verified = result["verified_tasks"]
        failed = result["failed_verification_tasks"]
        print(f"\n  Story status: {status}")
        if verified:
            print(f"  Verified tasks: {', '.join(verified)}")
        if failed:
            print(f"  Failed verification: {', '.join(failed)}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"  {exc}")
        sys.exit(1)


def cmd_self_improve(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
    simulate: bool = False,
    max_improvements: int = 1,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
    list_resumable: bool = False,
    skip_baseline_tests: bool = False,
    artifact_path: str | None = None,
    next_roadmap_item: bool = False,
    next_available_story: bool = False,
    continue_prd: bool = False,
) -> None:
    """Run or inspect the guarded self-improve workflow from the CLI."""
    selected_story_ref: str | None = None
    if max_improvements != 1:
        raise ValueError(
            "self-improve currently only supports max_improvements=1 while "
            "end-to-end reliability is being validated"
        )
    if artifact_path and resume_cycle_id:
        print("Provide either an artifact path or --resume, not both.")
        sys.exit(1)
    _validate_story_continuation_mode_conflict(
        next_available_story,
        continue_prd,
    )
    if artifact_path and not os.path.exists(artifact_path):
        print(f"Self-improve artifact not found: {artifact_path}")
        sys.exit(1)
    _validate_prd_artifact_mode_request(
        artifact_path,
        resume_cycle_id,
        next_available_story,
        "--next-available-story",
    )
    _validate_prd_artifact_mode_request(
        artifact_path,
        resume_cycle_id,
        continue_prd,
        "--continue-prd",
    )

    _check_vision_exists(VisionContext.SELF)
    project_root = resolve_project_root()
    has_explicit_mode = any(
        (
            simulate,
            stash_dirty,
            resume_cycle_id is not None,
            list_resumable,
            skip_baseline_tests,
            artifact_path is not None,
            next_roadmap_item,
            next_available_story,
            continue_prd,
        )
    )
    if not has_explicit_mode and _self_improve_prompt_supported():
        unfinished_prds = list_unfinished_self_prds(project_root)
        if unfinished_prds:
            smart_defaults = _prompt_for_smart_self_improve_mode(unfinished_prds)
            artifact_path = (
                cast(str | None, smart_defaults["artifact_path"]) or artifact_path
            )
            next_available_story = bool(smart_defaults["next_available_story"])
            continue_prd = bool(smart_defaults["continue_prd"])
            selected_story_ref = (
                cast(str | None, smart_defaults["selected_story_ref"]) or None
            )

    should_auto_resume = resume_cycle_id == SELF_IMPROVE_AUTO_RESUME
    if list_resumable:
        rows = _list_resumable_cycles(project_root)
        if not rows:
            print("\nNo resumable self-improve cycles found.")
            return
        print("\nResumable self-improve cycles:")
        for row in rows:
            print(
                f"- {row['cycle_id']} | {row['timestamp']} | next: {row['next_stage']} | "
                f"last failure: {row['last_failure']}"
            )
        return

    if should_auto_resume:
        rows = _list_resumable_cycles(project_root)
        if not rows:
            print("\nNo resumable self-improve cycles found.")
            return
        if not simulate and artifact_path is None:
            resume_cycle_id = _select_auto_resume_cycle(
                project_root,
                rows,
            )
            print(f"Auto-resuming latest resumable cycle: {resume_cycle_id}")

    run_kwargs = _build_self_improve_run_kwargs(
        artifact_path,
        next_roadmap_item,
        next_available_story,
        continue_prd,
        selected_story_ref,
    )

    record = run_self_improve(
        max_improvements,
        simulate,
        stash_dirty,
        resume_cycle_id,
        skip_baseline_tests,
        **run_kwargs,
    )
    if record.pr_created:
        print("\nSelf-improvement cycle completed successfully.")
    elif record.failure_reason == "simulated":
        print("\nSimulation complete. No branch or runtime artifacts were preserved.")
    elif record.failure_reason:
        print(f"\nSelf-improvement cycle ended: {record.failure_reason}")


__all__ = [
    "_build_prd_flow_kwargs",
    "_check_vision_exists",
    "SELF_IMPROVE_AUTO_RESUME",
    "cmd_execute",
    "cmd_mark",
    "cmd_plan",
    "cmd_prd",
    "cmd_self_improve",
    "cmd_status",
    "cmd_verify",
    "cmd_verify_story",
]
