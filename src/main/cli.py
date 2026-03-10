"""
Main entry point for Dialectic Crew AI.

Commands:
  python main.py prd "your feature request"   — generates PRD with dialectic
  python main.py plan [prd.json] [US-001]      — plans execution of a user story
  python main.py execute [plan.json|--latest]  — executes plan with auto-verify
  python main.py status [plan.json]            — shows story + task status
  python main.py verify-story [plan.json]      — re-verifies all tasks in a story
  python main.py mark <id> <status>            — manual task status override
  python main.py verify <id>                   — manual single-task re-check
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

from dialectic import DialecticFlow, run_dialectic_flow
from dialectic.state import DialecticState
from dialectic.prd_flow import OUTPUT_DIR, _get_persistence, get_prd_resume_state
from planning.flow import run_user_story_planning
from execution.runner import run_execution
from execution.dialectic_execution import run_dialectic_execution
from execution.verify import show_status, mark_task, verify_task, verify_user_story
from dialectic.vision import ensure_vision_path, VisionContext


BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     DIALECTIC CREW AI - PRD & Planning v1.3                       ║
║                                                                   ║
║     Dialectic: Thesis → Antithesis → Synthesis → Validation       ║
║     Commands: prd | plan | execute | status | verify-story | help ║
║              | self-improve                                        ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Usage:
  python main.py <command> [arguments...]
  dialectic-crew <command> [arguments...]

Commands:

    prd "your feature request" [--files file1.pdf file2.png ...] [--resume FLOW_ID]
      Generates a PRD (Product Requirement Document) using the dialectic method
      (thesis → antithesis → synthesis → validation). By default requires
      knowledge/VISION.md; use --self to run against internal/SELF_VISION.md.
      Saves to prd_output/ (JSON + Markdown).
            Use --resume FLOW_ID to continue a persisted PRD flow.
      Use --files to attach reference documents (PDF, images, text) for agents to analyze.
      Ex.: python main.py prd "Login with 2FA"
                     python main.py prd --resume <flow-id>
           python main.py prd "Dashboard redesign" --files wireframe.png spec.pdf

  plan [prd.json] [US-001|index]
      Plans the execution of a user story with dialectic. Generates a plan
      (UserStoryExecutionPlan) with tasks and score. By default uses the latest
      PRD in prd_output/ and the first user story.
      Saves to prd_output/ (exec_<US>_<timestamp>.json and .md).
      Ex.: python main.py plan
           python main.py plan prd_output/PRD_20260308_1640.json US1

    execute [plan.json|--latest] [--spec-only] [--resume-run RUN_ID]
      Executes the plan with CrewAI and dialectic per task. Each task goes through
      Thesis → Antithesis → Synthesis → Validation with automatic retries.
      After all tasks finish, a post-execution verification phase checks each
      completed task against PRD acceptance criteria and updates the user story
      status (completed, partially_completed, or failed) automatically.
      Use --spec-only to only generate a spec in Markdown (legacy behavior).
     Use --resume-run RUN_ID to continue an interrupted execution from the
     stored checkpoint in exec_output/<run_id>/checkpoint.json.
      By default uses the most recent plan in prd_output/ (exec_*.json).
      Saves to exec_output/<run_id>/ (report.json, outputs).
      Ex.: python main.py execute
           python main.py execute prd_output/exec_US1_20260308_1200.json
         python main.py execute --resume-run 20260310_120000
           python main.py execute --spec-only

  status [plan.json|--latest]
      Shows the status of the user story and all its tasks (pending, in_progress,
      completed, partially_completed, failed). By default uses the most recent plan.
      Ex.: python main.py status
           python main.py status prd_output/exec_US1_20260308_1750.json

  verify-story [plan.json] [--prd prd.json]
      Verifies all completed tasks in the plan against PRD acceptance criteria
      using LLM agents and updates the user story status. Useful for re-checking
      a story after manual changes or debugging.
      Ex.: python main.py verify-story
           python main.py verify-story --prd prd_output/PRD_20260308_1640.json

Manual overrides (the execute command handles these automatically):

  mark <task_id> <status> [plan.json]
      Manually overrides the status of a task. Useful for edge cases where a
      human decides a task is done or needs to be reset.
      Valid statuses: pending, in_progress, completed, failed
      Ex.: python main.py mark T0 completed
           python main.py mark T3 failed prd_output/exec_US1_20260308_1750.json

  verify <task_id> [plan.json] [--prd prd.json]
      Manually re-verifies a single task using an LLM agent. The execute command
      does this automatically for all tasks; use this for targeted re-checks.
      Ex.: python main.py verify T0
           python main.py verify T2 --prd prd_output/PRD_20260308_1640.json

        self-improve [--dry-run] [--max N] [--stash-dirty] [--resume CYCLE_ID] [--list-resumable]
      Runs one self-improvement cycle: introspect against internal/SELF_VISION.md,
      generate PRD, plan, and execute improvements, then validate with tests
      and metrics. Creates a PR for human review if all gates pass.
      --dry-run   Print the introspection report without making changes.
      --max N     Maximum number of improvements per cycle (default: 1).
            --resume CYCLE_ID
                                        Continue a previously interrupted self-improve cycle using
                                        the saved snapshot in .dialectic/self_improve/<cycle-id>.json.
            --list-resumable
                                    Print saved resumable self-improve cycles and exit.
            --stash-dirty
                                    Stash current-branch changes before creating the
                                    self-improve branch. The stash is left in the stash stack.
    CrewAI telemetry is disabled automatically by the CLI to avoid noisy
    exporter failures from external telemetry endpoints.
      If a prior run was interrupted on a `self-improve/*` branch, stale
      self-improve-only worktree changes are discarded automatically.
      Ex.: python main.py self-improve --dry-run
           python main.py self-improve --max 2
           python main.py self-improve --resume 20260310T120000
         python main.py self-improve --list-resumable

  --self (flag for prd, plan, execute)
      Run against the app's internal vision (internal/SELF_VISION.md) instead
      of the user's project vision (knowledge/VISION.md). Used to evolve the
      app itself using its own dialectic pipeline.
      Ex.: python main.py prd "Add memory support" --self
           python main.py plan --self
           python main.py execute --self

  help, -h, --help
      Shows this message.

Requirements:
    - knowledge/VISION.md (for prd, plan, and execute by default)
    - internal/SELF_VISION.md (when using --self or self-improve)
  - API key in .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY)
"""


def _check_api_key():
    has = bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )
    if not has:
        print("  Configure your API key first!")
        print("   Copy .env.example to .env and add the key\n")
    return has


def _extract_self_flag(args: list[str]) -> tuple[list[str], VisionContext]:
    if "--self" in args:
        remaining = [a for a in args if a != "--self"]
        return remaining, VisionContext.SELF
    return args, VisionContext.PROJECT


def _check_vision_exists(context: VisionContext = VisionContext.PROJECT):
    try:
        ensure_vision_path(context)
    except FileNotFoundError as exc:
        print(f"  Vision document not found!")
        print(f"  {exc}")
        sys.exit(1)


def _command_requires_api(sub: str, args: list[str]) -> bool:
    if sub in {"status", "mark"}:
        return False
    if sub == "execute" and "--spec-only" in args:
        return False
    return True


def _command_requires_vision(sub: str, args: list[str]) -> bool:
    if sub in {"prd", "plan", "verify", "verify-story"}:
        return True
    if sub == "execute" and "--spec-only" not in args:
        return True
    if sub == "self-improve":
        return False  # self-improve checks SELF vision internally
    return False


def cmd_prd(
    feature_request: str | None,
    file_paths: list[str] | None = None,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_id: str | None = None,
):
    if resume_id and not get_prd_resume_state(resume_id):
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


def cmd_plan(prd_path: str | None, us_ref: str | None, vision_context: VisionContext = VisionContext.PROJECT):
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
):
    try:
        if spec_only:
            result = run_execution(plan_path=plan_path or "--latest")
            print(f"\nSpec generated: {result['output_path']}")
            print(f"   Plan: {result['plan_id']} -- {result['plan_title']}")
        else:
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
    except FileNotFoundError as e:
        print(f"{e}")
        sys.exit(1)
    except ValueError as e:
        print(f"{e}")
        sys.exit(1)


def cmd_status(plan_path: str | None):
    try:
        show_status(plan_path)
    except FileNotFoundError as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_mark(task_id: str, status: str, plan_path: str | None):
    valid = ("pending", "in_progress", "completed", "failed")
    if status not in valid:
        print(f"  Invalid status: '{status}'. Use: {', '.join(valid)}")
        sys.exit(1)
    try:
        mark_task(task_id, status, plan_path)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_verify(task_id: str, plan_path: str | None, prd_path: str | None):
    try:
        result = verify_task(task_id, plan_path, prd_path)
        if result["verified"]:
            print(f"\n  Task {task_id} verified successfully!")
        else:
            print(f"\n  Task {task_id} did NOT pass verification.")
    except (FileNotFoundError, ValueError) as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_verify_story(plan_path: str | None, prd_path: str | None):
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
    except (FileNotFoundError, ValueError) as e:
        print(f"  {e}")
        sys.exit(1)


def cmd_self_improve(
    dry_run: bool = False,
    max_improvements: int = 1,
    stash_dirty: bool = False,
    resume_cycle_id: str | None = None,
    list_resumable: bool = False,
):
    from main.self_improve import _list_resumable_cycles, run_self_improve

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


def cmd_help():
    print(HELP_TEXT.strip())


def main():
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    args = sys.argv[1:]
    if not args:
        print(BANNER)
        print("Usage: python main.py <command> [arguments...]")
        print("       python main.py help   to see all commands.\n")
        sys.exit(1)

    sub = args[0].lower()
    if sub in ("help", "-h", "--help"):
        print(BANNER)
        cmd_help()
        sys.exit(0)

    print(BANNER)
    if _command_requires_api(sub, args) and not _check_api_key():
        sys.exit(1)
    _, vision_ctx = _extract_self_flag(args)
    if _command_requires_vision(sub, args):
        _check_vision_exists(vision_ctx)

    if sub == "prd":
        rest = args[1:]
        rest, vision_context = _extract_self_flag(rest)
        resume_id = None
        if "--resume" in rest:
            idx = rest.index("--resume")
            if idx + 1 >= len(rest):
                print("Provide a flow ID after --resume")
                sys.exit(1)
            resume_id = rest[idx + 1]
            rest = rest[:idx] + rest[idx + 2:]
        if len(rest) < 1 and not resume_id:
            print("Provide the feature: python main.py prd 'your feature here'")
            sys.exit(1)
        file_paths: list[str] = []
        if "--files" in rest:
            idx = rest.index("--files")
            feature_parts = rest[:idx]
            file_paths = [f for f in rest[idx + 1:] if not f.startswith("-")]
            invalid = [f for f in file_paths if not os.path.exists(f)]
            if invalid:
                print(f"  File(s) not found: {', '.join(invalid)}")
                sys.exit(1)
        else:
            feature_parts = rest
        feature_request = " ".join(feature_parts).strip() or None
        cmd_prd(
            feature_request,
            file_paths=file_paths or None,
            vision_context=vision_context,
            resume_id=resume_id,
        )
        return
    if sub == "plan":
        remaining = args[1:]
        remaining, vision_context = _extract_self_flag(remaining)
        prd_path = remaining[0] if len(remaining) > 0 else None
        us_ref = remaining[1] if len(remaining) > 1 else None
        cmd_plan(prd_path, us_ref, vision_context=vision_context)
        return
    if sub == "execute":
        remaining_all = args[1:]
        remaining_all, vision_context = _extract_self_flag(remaining_all)
        resume_run_id = None
        if "--resume-run" in remaining_all:
            idx = remaining_all.index("--resume-run")
            if idx + 1 >= len(remaining_all):
                print("Provide a run ID after --resume-run")
                sys.exit(1)
            resume_run_id = remaining_all[idx + 1]
            remaining_all = remaining_all[:idx] + remaining_all[idx + 2:]
        remaining = [a for a in remaining_all if not a.startswith("-")]
        spec_only = "--spec-only" in remaining_all
        plan_path = remaining[0] if remaining else "--latest"
        cmd_execute(
            plan_path,
            spec_only=spec_only,
            vision_context=vision_context,
            resume_run_id=resume_run_id,
        )
        return
    if sub == "status":
        plan_path = args[1] if len(args) > 1 else None
        cmd_status(plan_path)
        return
    if sub == "verify-story":
        remaining = [a for a in args[1:] if not a.startswith("-")]
        plan_path = remaining[0] if remaining else None
        prd_path = None
        if "--prd" in args:
            prd_idx = args.index("--prd")
            if prd_idx + 1 < len(args):
                prd_path = args[prd_idx + 1]
        cmd_verify_story(plan_path, prd_path)
        return
    if sub == "mark":
        if len(args) < 3:
            print("Usage: python main.py mark <task_id> <status> [plan.json]")
            print("  Valid statuses: pending, in_progress, completed, failed")
            sys.exit(1)
        task_id = args[1]
        status = args[2]
        plan_path = args[3] if len(args) > 3 else None
        cmd_mark(task_id, status, plan_path)
        return
    if sub == "verify":
        if len(args) < 2:
            print("Usage: python main.py verify <task_id> [plan.json] [--prd prd.json]")
            sys.exit(1)
        task_id = args[1]
        remaining = [a for a in args[2:] if not a.startswith("-")]
        plan_path = remaining[0] if remaining else None
        prd_path = None
        if "--prd" in args:
            prd_idx = args.index("--prd")
            if prd_idx + 1 < len(args):
                prd_path = args[prd_idx + 1]
        cmd_verify(task_id, plan_path, prd_path)
        return
    if sub == "self-improve":
        remaining = args[1:]
        dry_run = "--dry-run" in remaining
        stash_dirty = "--stash-dirty" in remaining
        list_resumable = "--list-resumable" in remaining
        resume_cycle_id = None
        max_n = 1
        if "--resume" in remaining:
            idx = remaining.index("--resume")
            if idx + 1 >= len(remaining):
                print("Provide a cycle ID after --resume")
                sys.exit(1)
            resume_cycle_id = remaining[idx + 1]
        if "--max" in remaining:
            idx = remaining.index("--max")
            if idx + 1 < len(remaining):
                try:
                    max_n = int(remaining[idx + 1])
                except ValueError:
                    print("--max requires an integer argument")
                    sys.exit(1)
        cmd_self_improve(
            dry_run=dry_run,
            max_improvements=max_n,
            stash_dirty=stash_dirty,
            resume_cycle_id=resume_cycle_id,
            list_resumable=list_resumable,
        )
        return

    print(f"Unknown command: '{args[0]}'. Use: prd | plan | execute | status | verify-story | self-improve | help")
    sys.exit(1)


if __name__ == "__main__":
    main()
