"""Command handlers for the CLI entrypoint."""

from __future__ import annotations

import os
import sys

from dialectic.prd_flow import get_prd_resume_state
from dialectic.vision import VisionContext, ensure_vision_path, resolve_project_root
from execution.dialectic_execution import run_dialectic_execution
from execution.runner import run_execution
from execution.status import mark_task, show_status
from execution.verify import verify_task, verify_user_story
from main.self_improve import _list_resumable_cycles, run_self_improve
from planning.flow import run_user_story_planning
from dialectic import run_dialectic_flow


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
    get_prd_resume_state_fn=get_prd_resume_state,
) -> None:
    if resume_id and not get_prd_resume_state_fn(resume_id):
        print(f"Persisted PRD flow not found: {resume_id}")
        sys.exit(1)

    result = run_dialectic_flow(
        feature_request,
        file_paths=file_paths,
        vision_context=vision_context,
        resume_id=resume_id,
    )
    print("\n" + "=" * 60)
    print("DIALECTIC PROCESS COMPLETE!")
    print("=" * 60)
    print(f"Flow ID: {result['flow_id']}")
    print(f"Quality Score: {result['quality_score']}/10.0")
    print(f"Total rounds: {result['iterations']}")
    print(f"Consensus: {result['consensus_reached']}")
    print("=" * 60)


def cmd_plan(
    prd_path: str | None,
    us_ref: str | None,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> None:
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
    try:
        show_status(plan_path)
    except FileNotFoundError as exc:
        print(f"  {exc}")
        sys.exit(1)


def cmd_mark(task_id: str, status: str, plan_path: str | None) -> None:
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


def cmd_self_improve(
    dry_run: bool = False,
    max_improvements: int = 1,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
    list_resumable: bool = False,
) -> None:
    _check_vision_exists(VisionContext.SELF)
    if list_resumable:
        rows = _list_resumable_cycles(resolve_project_root())
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

    record = run_self_improve(
        max_improvements=max_improvements,
        dry_run=dry_run,
        stash_dirty=stash_dirty,
        resume_cycle_id=resume_cycle_id,
    )
    if record.pr_created:
        print("\nSelf-improvement cycle completed successfully.")
    elif record.failure_reason == "dry_run":
        print("\nDry run complete. No changes made.")
    elif record.failure_reason:
        print(f"\nSelf-improvement cycle ended: {record.failure_reason}")


def cmd_help(help_text: str) -> None:
    print(help_text.strip())
