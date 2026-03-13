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

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import click
import typer
from dotenv import load_dotenv
from typer.main import get_command

from dialectic.app_logging import (
    configure_application_logging,
    log_context,
    new_correlation_id,
)
from dialectic.crewai_event_logger import register_crewai_event_logger
from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic.prd_flow import get_prd_resume_state
from dialectic.vision import ensure_vision_path, VisionContext
from .cli_commands import (
    cmd_execute,
    cmd_mark,
    cmd_plan,
    cmd_prd as _cmd_prd,
    cmd_self_improve,
    cmd_status,
    cmd_verify,
    cmd_verify_story,
)

load_dotenv()

logger = logging.getLogger(__name__)


BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     DIALECTIC CREW AI - PRD & Planning v1.3                       ║
║                                                                   ║
║     Dialectic: Thesis → Antithesis → Synthesis → Validation       ║
║     Commands: prd | plan | execute | status | verify-story | help ║
║              | self-improve                                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Usage:
  python main.py <command> [arguments...]
  dialectic-crew <command> [arguments...]

Commands:

    prd "your feature request" [--files file1.pdf file2.png ...] [--resume FLOW_ID] [--max-retries N] [--consensus-min-score SCORE]
      Generates a PRD (Product Requirement Document) using the dialectic method
      (thesis → antithesis → synthesis → validation). By default requires
      knowledge/VISION.md; use --self to run against internal/SELF_VISION.md.
      Saves to prd_output/ (JSON + Markdown).
            Use --resume FLOW_ID to continue a persisted PRD flow.
            Use --max-retries N to allow more dialectic rounds before stopping.
                Use --consensus-min-score SCORE to stop early when consensus is reached
                and the quality score is at least SCORE.
      Use --files to attach reference documents (PDF, images, text) for agents to analyze.
    Ex.: python main.py prd "Login with 2FA"
               python main.py prd --resume <flow-id>
               python main.py prd "Login with 2FA" --max-retries 8
                    python main.py prd "Login with 2FA" --consensus-min-score 8.5
           python main.py prd "Dashboard redesign" --files wireframe.png spec.pdf

    plan [prd.json|--latest] [US-001|index]
      Plans the execution of a user story with dialectic. Generates a plan
      (UserStoryExecutionPlan) with tasks and score. By default uses the latest
            PRD in prd_output/ and the first user story. By default it uses
            knowledge/VISION.md; use --self to plan against internal/SELF_VISION.md.
      Saves to prd_output/ (exec_<US>_<timestamp>.json and .md).
      Ex.: python main.py plan
                     python main.py plan --self --latest US-01
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


app = typer.Typer(
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Modern typed CLI for Dialectic Crew AI workflows, including PRD generation, "
        "planning, execution, and self-improvement."
    ),
    no_args_is_help=False,
    pretty_exceptions_enable=False,
    rich_markup_mode="rich",
)


def _print_banner() -> None:
    print(BANNER)


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
        print("  Vision document not found!")
        print(f"  {exc}")
        sys.exit(1)


def _command_requires_api(sub: str, args: list[str]) -> bool:
    """Return whether the requested subcommand requires an API key."""
    if sub in {"status", "mark"}:
        return False
    if sub == "execute" and "--spec-only" in args:
        return False
    return True


def _command_requires_vision(sub: str, args: list[str]) -> bool:
    """Return whether the requested subcommand requires a vision document."""
    if sub in {"prd", "plan", "verify", "verify-story"}:
        return True
    if sub == "execute" and "--spec-only" not in args:
        return True
    if sub == "self-improve":
        return False  # self-improve checks SELF vision internally
    return False


def cmd_prd(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    feature_request: str | None,
    file_paths: list[str] | None = None,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_id: str | None = None,
    max_retries: int | None = None,
    consensus_min_score: float | None = None,
):
    """Dispatch the PRD workflow while preserving the historical helper API."""
    _cmd_prd(
        feature_request,
        file_paths=file_paths,
        vision_context=vision_context,
        resume_id=resume_id,
        max_retries=max_retries,
        consensus_min_score=consensus_min_score,
        get_prd_resume_state_fn=get_prd_resume_state,
    )


def cmd_help():
    """Print the detailed project-specific help guide."""
    print(HELP_TEXT.strip())


def _normalize_legacy_args(args: Sequence[str]) -> list[str]:
    """Normalize legacy argument patterns to the Typer-friendly form."""
    normalized = list(args)
    if not normalized or normalized[0].lower() != "prd" or "--files" not in normalized:
        return normalized

    files_index = normalized.index("--files")
    cursor = files_index + 1
    file_args: list[str] = []
    while cursor < len(normalized) and not normalized[cursor].startswith("-"):
        file_args.extend(["--files", normalized[cursor]])
        cursor += 1
    if not file_args:
        return normalized
    return normalized[:files_index] + file_args + normalized[cursor:]


def _run_guarded_command(
    subcommand: str,
    args: list[str],
    action: Callable[[], None],
    vision_context: VisionContext = VisionContext.PROJECT,
) -> None:
    """Run a command after applying API-key and vision preflight checks."""
    if _command_requires_api(subcommand, args) and not _check_api_key():
        logger.error("CLI command requires API key", extra={"phase": "preflight"})
        raise SystemExit(1)
    if _command_requires_vision(subcommand, args):
        _check_vision_exists(vision_context)
    with log_context(phase="command_dispatch"):
        action()


@app.command("prd")
def prd_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    feature_request_parts: list[str] | None = typer.Argument(
        None,
        metavar="FEATURE",
        help="Feature request to turn into a dialectic PRD.",
    ),
    file_paths: list[Path] | None = typer.Option(
        None,
        "--files",
        metavar="PATH",
        help=(
            "Attach one or more reference files; repeat the option or use the "
            "legacy single --files form."
        ),
    ),
    resume_id: str | None = typer.Option(
        None,
        "--resume",
        metavar="FLOW_ID",
        help="Resume a persisted PRD flow by ID.",
    ),
    max_retries: int | None = typer.Option(
        None,
        "--max-retries",
        min=1,
        help="Maximum dialectic rounds before stopping.",
    ),
    consensus_min_score: float | None = typer.Option(
        None,
        "--consensus-min-score",
        min=0.0,
        max=10.0,
        help="Allow consensus-aware early stopping at or above this score.",
    ),
    self_mode: bool = typer.Option(
        False,
        "--self",
        help="Use internal/SELF_VISION.md instead of knowledge/VISION.md.",
    ),
) -> None:
    """Generate or resume a PRD workflow from the command line.

    Examples:
      uv run dialectic-crew prd "Login with 2FA"
      uv run dialectic-crew prd --resume flow-123
      uv run dialectic-crew prd "Dashboard redesign" --files wireframe.png --files spec.pdf
      uv run dialectic-crew prd "Improve self-improve UX" --self --max-retries 8
    """
    vision_context = VisionContext.SELF if self_mode else VisionContext.PROJECT
    file_list = [str(path) for path in file_paths or []]
    invalid = [path for path in file_list if not Path(path).exists()]
    if invalid:
        print(f"  File(s) not found: {', '.join(invalid)}")
        raise SystemExit(1)

    feature_request = " ".join(feature_request_parts or []).strip() or None
    args = ["prd"]
    if self_mode:
        args.append("--self")
    if resume_id:
        args.extend(["--resume", resume_id])
    if max_retries is not None:
        args.extend(["--max-retries", str(max_retries)])
    if consensus_min_score is not None:
        args.extend(["--consensus-min-score", str(consensus_min_score)])
    if file_list:
        for path in file_list:
            args.extend(["--files", path])
    if feature_request:
        args.extend(feature_request.split())

    _run_guarded_command(
        "prd",
        args,
        lambda: cmd_prd(
            feature_request,
            file_paths=file_list or None,
            vision_context=vision_context,
            resume_id=resume_id,
            max_retries=max_retries,
            consensus_min_score=consensus_min_score,
        ),
        vision_context=vision_context,
    )


@app.command("plan")
def plan_command(
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Use the latest PRD instead of passing an explicit PRD path.",
    ),
    first: str | None = typer.Argument(
        None,
        metavar="[PRD_PATH|--latest|US-001]",
        help="Optional PRD path, --latest, or a direct user story reference.",
    ),
    second: str | None = typer.Argument(
        None,
        metavar="[US-001|index]",
        help=(
            "Optional user story reference when the first argument is a PRD path "
            "or --latest."
        ),
    ),
    self_mode: bool = typer.Option(
        False,
        "--self",
        help="Use internal/SELF_VISION.md instead of knowledge/VISION.md.",
    ),
) -> None:
    """Plan a user story execution from the latest or a specific PRD.

    Examples:
      uv run dialectic-crew plan --latest US-01
      uv run dialectic-crew plan prd_output/PRD_20260308_1640.json US-01
      uv run dialectic-crew plan --self --latest US-01
    """
    vision_context = VisionContext.SELF if self_mode else VisionContext.PROJECT

    if latest or first == "--latest":
        prd_path = None
        us_ref = first if latest and second is None else second
    elif first and second is None and not os.path.exists(first):
        prd_path = None
        us_ref = first
    else:
        prd_path = first
        us_ref = second

    args = ["plan"]
    if latest:
        args.append("--latest")
    if self_mode:
        args.append("--self")
    if first:
        args.append(first)
    if second:
        args.append(second)

    _run_guarded_command(
        "plan",
        args,
        lambda: cmd_plan(prd_path, us_ref, vision_context=vision_context),
        vision_context=vision_context,
    )


@app.command("execute")
def execute_command(
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Use the latest execution plan instead of passing an explicit plan path.",
    ),
    plan_path: str | None = typer.Argument(
        None,
        metavar="[PLAN_PATH|--latest]",
        help="Execution plan JSON path or --latest.",
    ),
    spec_only: bool = typer.Option(
        False,
        "--spec-only",
        help="Only generate the legacy Markdown spec without executing tasks.",
    ),
    resume_run_id: str | None = typer.Option(
        None,
        "--resume-run",
        metavar="RUN_ID",
        help=(
            "Resume an interrupted execution run from "
            "exec_output/<run_id>/checkpoint.json."
        ),
    ),
    self_mode: bool = typer.Option(
        False,
        "--self",
        help="Use internal/SELF_VISION.md instead of knowledge/VISION.md.",
    ),
) -> None:
    """Execute or resume a plan using the dialectic task runner.

    Examples:
      uv run dialectic-crew execute --latest
      uv run dialectic-crew execute prd_output/exec_US-01_20260313_125038.json
      uv run dialectic-crew execute --resume-run 20260310_120000
      uv run dialectic-crew execute --spec-only --latest
    """
    vision_context = VisionContext.SELF if self_mode else VisionContext.PROJECT
    args = ["execute"]
    if latest:
        args.append("--latest")
    if spec_only:
        args.append("--spec-only")
    if self_mode:
        args.append("--self")
    if resume_run_id:
        args.extend(["--resume-run", resume_run_id])
    if plan_path:
        args.append(plan_path)

    _run_guarded_command(
        "execute",
        args,
        lambda: cmd_execute(
            plan_path or "--latest",
            spec_only=spec_only,
            vision_context=vision_context,
            resume_run_id=resume_run_id,
        ),
        vision_context=vision_context,
    )


@app.command("status")
def status_command(
    plan_path: str | None = typer.Argument(
        None,
        metavar="[PLAN_PATH|--latest]",
        help="Execution plan path; defaults to the latest plan.",
    ),
) -> None:
    """Show the current status for a plan and its tasks.

    Examples:
      uv run dialectic-crew status
      uv run dialectic-crew status prd_output/exec_US-01_20260313_125038.json
    """
    _run_guarded_command("status", ["status"], lambda: cmd_status(plan_path))


@app.command("verify-story")
def verify_story_command(
    plan_path: str | None = typer.Argument(
        None,
        metavar="[PLAN_PATH]",
        help="Optional execution plan to verify.",
    ),
    prd_path: str | None = typer.Option(
        None,
        "--prd",
        metavar="PRD_PATH",
        help="Optional PRD path to verify against.",
    ),
) -> None:
    """Re-verify a story's completed tasks against PRD acceptance criteria.

    Examples:
      uv run dialectic-crew verify-story
      uv run dialectic-crew verify-story --prd prd_output/PRD_20260308_1640.json
    """
    args = ["verify-story"]
    if prd_path:
        args.extend(["--prd", prd_path])
    _run_guarded_command(
        "verify-story",
        args,
        lambda: cmd_verify_story(plan_path, prd_path),
    )


@app.command("mark")
def mark_command(
    task_id: str = typer.Argument(..., help="Task ID to update."),
    status: str = typer.Argument(..., help="New task status."),
    plan_path: str | None = typer.Argument(
        None,
        metavar="[PLAN_PATH]",
        help="Optional execution plan path.",
    ),
) -> None:
    """Manually override a task status for an execution plan.

    Examples:
      uv run dialectic-crew mark T0 completed
      uv run dialectic-crew mark T3 failed prd_output/exec_US-01_20260313_125038.json
    """
    _run_guarded_command(
        "mark",
        ["mark", task_id, status],
        lambda: cmd_mark(task_id, status, plan_path),
    )


@app.command("verify")
def verify_command(
    task_id: str = typer.Argument(..., help="Task ID to verify."),
    plan_path: str | None = typer.Argument(
        None,
        metavar="[PLAN_PATH]",
        help="Optional execution plan path.",
    ),
    prd_path: str | None = typer.Option(
        None,
        "--prd",
        metavar="PRD_PATH",
        help="Optional PRD path to verify against.",
    ),
) -> None:
    """Re-run verification for a single implementation task.

    Examples:
      uv run dialectic-crew verify T0
      uv run dialectic-crew verify T2 --prd prd_output/PRD_20260308_1640.json
    """
    args = ["verify", task_id]
    if prd_path:
        args.extend(["--prd", prd_path])
    _run_guarded_command(
        "verify",
        args,
        lambda: cmd_verify(task_id, plan_path, prd_path),
    )


@app.command("self-improve")
def self_improve_command(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the introspection report without making changes.",
    ),
    max_improvements: int = typer.Option(
        1,
        "--max",
        min=1,
        help="Maximum number of improvements per cycle.",
    ),
    stash_dirty: bool = typer.Option(
        False,
        "--stash-dirty",
        help="Stash dirty worktree changes before creating the self-improve branch.",
    ),
    resume_cycle_id: str | None = typer.Option(
        None,
        "--resume",
        metavar="CYCLE_ID",
        help="Resume an interrupted self-improve cycle.",
    ),
    list_resumable: bool = typer.Option(
        False,
        "--list-resumable",
        help="List resumable self-improve cycles and exit.",
    ),
) -> None:
    """Run the guarded self-improvement orchestration workflow.

    Examples:
      uv run dialectic-crew self-improve --dry-run
      uv run dialectic-crew self-improve --max 2
      uv run dialectic-crew self-improve --resume 20260310T120000
      uv run dialectic-crew self-improve --list-resumable
    """
    args = ["self-improve"]
    if dry_run:
        args.append("--dry-run")
    if stash_dirty:
        args.append("--stash-dirty")
    if list_resumable:
        args.append("--list-resumable")
    if resume_cycle_id:
        args.extend(["--resume", resume_cycle_id])
    if max_improvements != 1:
        args.extend(["--max", str(max_improvements)])

    _run_guarded_command(
        "self-improve",
        args,
        lambda: cmd_self_improve(
            dry_run=dry_run,
            max_improvements=max_improvements,
            stash_dirty=stash_dirty,
            resume_cycle_id=resume_cycle_id,
            list_resumable=list_resumable,
        ),
    )


@app.command("help")
def help_command() -> None:
    """Show the detailed legacy help text and examples."""
    cmd_help()


def main(argv: Sequence[str] | None = None) -> None:
    """Bootstrap logging/runtime configuration and dispatch the Typer app."""
    configure_application_logging()
    register_crewai_event_logger()
    args = list(argv) if argv is not None else sys.argv[1:]
    sub = args[0].lower() if args else "startup"
    with log_context(command=sub, phase="bootstrap", correlation_id=new_correlation_id()):
        configure_crewai_runtime()
        logger.debug("CLI bootstrap initialized")
        if not args:
            _print_banner()
            print("Usage: python main.py <command> [arguments...]")
            print("       python main.py help   to see all commands.\n")
            logger.warning("CLI invoked without arguments")
            sys.exit(1)

        _print_banner()
        normalized_args = _normalize_legacy_args(args)
        if normalized_args[0].lower() == "help":
            logger.info("CLI help rendered")

        command = get_command(app)
        try:
            command.main(
                args=normalized_args,
                prog_name="dialectic-crew",
                standalone_mode=False,
            )
        except click.exceptions.Exit as exc:
            raise SystemExit(exc.exit_code) from exc
        except click.ClickException as exc:
            exc.show()
            raise SystemExit(exc.exit_code) from exc


if __name__ == "__main__":
    main()
