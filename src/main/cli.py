"""Main entry point for Dialectic Crew AI."""

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
from dialectic.vision import VisionContext
from .cli_commands import (
    _build_prd_flow_kwargs,
    _check_vision_exists,
    cmd_execute,
    cmd_mark,
    cmd_plan,
    cmd_prd as _cmd_prd,
    cmd_self_improve,
    cmd_status,
    cmd_verify,
    cmd_verify_story,
)
from .target_commands import (
    cmd_clear_target,
    cmd_get_target,
    cmd_list_targets,
    cmd_set_target,
)
from .cleanup_commands import cmd_clear_runtime, cmd_clear_self_improve
from .vision_commands import cmd_make_vision

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

app = typer.Typer(
    add_completion=False,
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
    get_prd_resume_state_fn=get_prd_resume_state,
) -> None:
    """Forward PRD dispatch while preserving the CLI module's test seam."""
    flow_kwargs = _build_prd_flow_kwargs(
        file_paths,
        vision_context,
        resume_id,
        max_retries,
        consensus_min_score,
    )
    _cmd_prd(
        feature_request,
        **flow_kwargs,
        get_prd_resume_state_fn=get_prd_resume_state_fn,
    )


def cmd_help():
    """Print the unified modern help guide for the CLI."""
    command = get_command(app)
    context = click.Context(command, info_name="dialectic-crew")
    print(command.get_help(context))


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


def _dispatch_prd_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    feature_request: str | None,
    *,
    file_paths: list[str] | None,
    vision_context: VisionContext,
    resume_id: str | None,
    max_retries: int | None,
    consensus_min_score: float | None,
) -> None:
    """Dispatch PRD generation while preserving the historical non-resume call shape."""
    flow_kwargs = _build_prd_flow_kwargs(
        file_paths,
        vision_context,
        resume_id,
        max_retries,
        consensus_min_score,
    )
    cmd_prd(
        feature_request,
        **flow_kwargs,
        get_prd_resume_state_fn=get_prd_resume_state,
    )


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
        lambda: _dispatch_prd_command(
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
def self_improve_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    artifact_path: str | None = typer.Argument(
        None,
        metavar="[PRD_OR_PLAN_PATH]",
        help="Optional PRD or execution plan JSON artifact to continue self-improve from.",
    ),
    simulate: bool = typer.Option(
        False,
        "--simulate",
        help=(
            "Run the full self-improve pipeline on a disposable branch "
            "without preserving changes."
        ),
    ),
    max_improvements: int = typer.Option(
        1,
        "--max",
        min=1,
        help="Maximum number of improvements per cycle (currently only 1 is supported).",
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
    skip_baseline_tests: bool = typer.Option(
        False,
        "--skip-baseline-tests",
        help="Skip the initial baseline pytest run before self-improve proceeds.",
    ),
    next_roadmap_item: bool = typer.Option(
        False,
        "--next-roadmap-item",
        help="Skip dialectic prioritization and use the first introspection opportunity.",
    ),
) -> None:
    """Run the guarded self-improvement orchestration workflow.

    Examples:
            uv run dialectic-crew self-improve --simulate
        uv run dialectic-crew self-improve --skip-baseline-tests
            uv run dialectic-crew self-improve --next-roadmap-item
      uv run dialectic-crew self-improve --max 1
            uv run dialectic-crew self-improve prd_output/PRD_20260308_1640.json
            uv run dialectic-crew self-improve prd_output/exec_US-01_20260313_125038.json
      uv run dialectic-crew self-improve --resume 20260310T120000
      uv run dialectic-crew self-improve --list-resumable
    """
    if max_improvements != 1:
        raise typer.BadParameter(
            "self-improve currently only supports --max 1 while "
            "end-to-end reliability is being validated.",
            param_hint="--max",
        )

    args = ["self-improve"]
    if simulate:
        args.append("--simulate")
    if stash_dirty:
        args.append("--stash-dirty")
    if list_resumable:
        args.append("--list-resumable")
    if skip_baseline_tests:
        args.append("--skip-baseline-tests")
    if next_roadmap_item:
        args.append("--next-roadmap-item")
    if resume_cycle_id:
        args.extend(["--resume", resume_cycle_id])
    if artifact_path:
        args.append(artifact_path)

    _run_guarded_command(
        "self-improve",
        args,
        lambda: cmd_self_improve(
            simulate=simulate,
            max_improvements=max_improvements,
            stash_dirty=stash_dirty,
            resume_cycle_id=resume_cycle_id,
            list_resumable=list_resumable,
            skip_baseline_tests=skip_baseline_tests,
            artifact_path=artifact_path,
            next_roadmap_item=next_roadmap_item,
        ),
    )


@app.command("set-target")
def set_target_command(
    path: str = typer.Argument(..., metavar="PATH", help="Path to a local git repository."),
) -> None:
    """Set the active target repository for project-mode workflows."""
    cmd_set_target(path)


@app.command("get-target")
def get_target_command() -> None:
    """Show the currently configured target repository."""
    cmd_get_target()


@app.command("clear-target")
def clear_target_command() -> None:
    """Clear the currently configured target repository."""
    cmd_clear_target()


@app.command("list-targets")
def list_targets_command() -> None:
    """List known target repositories and their vision status."""
    cmd_list_targets()


@app.command("make-vision")
def make_vision_command(
    output_path: str | None = typer.Option(
        None,
        "--output",
        metavar="PATH",
        help="Optional path where the generated vision document should be written.",
    ),
    self_mode: bool = typer.Option(
        False,
        "--self",
        help=(
            "Analyze the dialectic-crew-ai repository and write to "
            "internal/SELF_VISION.md by default."
        ),
    ),
) -> None:
    """Generate a VISION.md draft for the active target or, with --self, this repository."""
    cmd_make_vision(output_path=output_path, self_mode=self_mode)


@app.command("clear-runtime")
# pylint: disable=too-many-arguments,too-many-positional-arguments
def clear_runtime_command(
    logs: bool = typer.Option(False, "--logs", help="Clear application log files."),
    metrics: bool = typer.Option(False, "--metrics", help="Clear the metrics database."),
    flows: bool = typer.Option(False, "--flows", help="Clear the CrewAI flow database."),
    prd: bool = typer.Option(
        False,
        "--prd",
        help="Clear centralized PRD and plan artifacts.",
    ),
    exec_output: bool = typer.Option(
        False,
        "--exec",
        help="Clear centralized execution artifacts.",
    ),
    all_scopes: bool = typer.Option(
        False,
        "--all",
        help="Clear all runtime artifact categories.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview matching runtime artifacts without deleting them.",
    ),
) -> None:
    """Clear selected centralized runtime artifacts."""
    if all_scopes:
        logs = metrics = flows = prd = exec_output = True
    cmd_clear_runtime(
        logs=logs,
        metrics=metrics,
        flows=flows,
        prd=prd,
        exec_output=exec_output,
        dry_run=dry_run,
    )


@app.command("clear-self-improve")
def clear_self_improve_command(
    cycle_id: str | None = typer.Argument(
        None,
        metavar="[CYCLE_ID]",
        help="Optional self-improve cycle ID to clear.",
    ),
    clear_all: bool = typer.Option(
        False,
        "--all",
        help="Clear all persisted self-improve snapshots.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview self-improve cleanup without deleting files.",
    ),
    with_linked_exec: bool = typer.Option(
        False,
        "--with-linked-exec",
        help="Also remove linked execution artifacts for a specific cycle.",
    ),
) -> None:
    """Clear persisted self-improve snapshots and linked execution artifacts."""
    cmd_clear_self_improve(
        cycle_id=cycle_id,
        clear_all=clear_all,
        dry_run=dry_run,
        with_linked_exec=with_linked_exec,
    )


@app.command("help")
def help_command() -> None:
    """Show the same top-level help as --help."""
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
