"""Git and subprocess helpers used by the self-improve orchestrator."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    safe_timeout = max(int(timeout), 1)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=safe_timeout,
        cwd=str(cwd) if cwd else None,
    )


def git_branch_create(
    branch: str,
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> bool:
    result = run_cmd_fn(["git", "checkout", "-b", branch], cwd=cwd)
    return result.returncode == 0


def git_branch_create_from_head(
    branch: str,
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    result = run_cmd_fn(["git", "checkout", "-b", branch], cwd=cwd)
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return True, output or f"created branch {branch} from current HEAD"
    return False, output or f"failed to create branch {branch} from current HEAD"


def git_discard_branch(
    branch: str,
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> None:
    run_cmd_fn(["git", "checkout", "-"], cwd=cwd)
    run_cmd_fn(["git", "branch", "-D", branch], cwd=cwd)


def git_current_branch(
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> str:
    result = run_cmd_fn(["git", "branch", "--show-current"], cwd=cwd)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def git_checkout_branch(
    branch: str,
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    result = run_cmd_fn(["git", "checkout", branch], cwd=cwd)
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return True, output or f"checked out {branch}"
    return False, output or f"failed to checkout {branch}"


def recover_stale_self_improve_worktree(
    cwd: Path,
    *,
    git_current_branch_fn=git_current_branch,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    """Recover from an interrupted run only when already on a self-improve branch."""
    branch = git_current_branch_fn(cwd)
    if not branch.startswith("self-improve/"):
        return False, "not on a self-improve branch"

    reset_result = run_cmd_fn(["git", "reset", "--hard", "HEAD"], cwd=cwd)
    if reset_result.returncode != 0:
        return False, f"failed to reset stale self-improve branch {branch}"

    clean_result = run_cmd_fn(["git", "clean", "-fd"], cwd=cwd)
    if clean_result.returncode != 0:
        return False, f"failed to clean stale self-improve branch {branch}"

    return True, f"discarded stale self-improve worktree on {branch}"


def git_stash_worktree(
    cwd: Path,
    message: str,
    *,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    result = run_cmd_fn(
        ["git", "stash", "push", "--include-untracked", "-m", message],
        cwd=cwd,
    )
    if result.returncode != 0:
        return False, "failed to stash current branch changes"
    return True, (result.stdout or result.stderr or "stashed current branch changes").strip()


def dirty_worktree_guidance(
    cwd: Path,
    worktree_reason: str,
    *,
    git_current_branch_fn=git_current_branch,
) -> str:
    branch = git_current_branch_fn(cwd) or "<detached HEAD>"
    return (
        f"{worktree_reason} on branch '{branch}'. "
        "Commit the changes, discard them manually, or rerun with --stash-dirty "
        "to stash current branch changes before self-improve continues."
    )


def git_worktree_clean(
    cwd: Path,
    *,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    result = run_cmd_fn(["git", "status", "--porcelain"], cwd=cwd)
    if result.returncode != 0:
        return False, "Unable to determine git worktree status"

    dirty_entries = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not dirty_entries:
        return True, "clean"

    preview = ", ".join(dirty_entries[:5])
    suffix = "" if len(dirty_entries) <= 5 else f", +{len(dirty_entries) - 5} more"
    return False, f"Worktree has uncommitted changes: {preview}{suffix}"


def git_commit_all(
    cwd: Path,
    message: str,
    *,
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    add_result = run_cmd_fn(["git", "add", "-A"], cwd=cwd)
    if add_result.returncode != 0:
        reason = (add_result.stderr or add_result.stdout or "failed to stage changes").strip()
        return False, reason

    commit_result = run_cmd_fn(["git", "commit", "-m", message], cwd=cwd)
    output = (commit_result.stdout or commit_result.stderr or "").strip()
    normalized_output = output.lower()
    if commit_result.returncode == 0:
        return True, output or "created commit"
    if "nothing to commit" in normalized_output or "no changes added to commit" in normalized_output:
        return False, "nothing to commit"
    return False, output or "failed to create commit"


def git_has_commits_ahead(
    cwd: Path,
    *,
    base_branch: str = "main",
    run_cmd_fn=run_cmd,
) -> tuple[bool, str]:
    result = run_cmd_fn(["git", "rev-list", "--count", f"{base_branch}..HEAD"], cwd=cwd)
    if result.returncode != 0:
        reason = (result.stderr or result.stdout or f"failed to compare against {base_branch}").strip()
        return False, reason

    ahead_count_text = result.stdout.strip() or "0"
    try:
        ahead_count = int(ahead_count_text)
    except ValueError:
        return False, f"invalid ahead count: {ahead_count_text}"

    if ahead_count > 0:
        return True, f"{ahead_count} commit(s) ahead of {base_branch}"
    return False, f"no commits ahead of {base_branch}"