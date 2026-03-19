"""Helper utilities for self-improve quality-gate checks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_QUALITY_GATE_TIMEOUT = 120
_TYPED_SOURCE_PACKAGES = {"dialectic", "execution", "main", "planning", "mcp"}


def _is_mypy_supported_source_target(path: Path) -> bool:
    """Return whether a touched source file should be included in mypy checks."""
    parts = path.parts
    if not parts or parts[0] != "src":
        return False
    return not (
        len(parts) >= 5
        and len(parts) >= 3
        and parts[1] == "mcp"
        and parts[2] == "skills"
        and "scripts" in parts[3:]
    )


def parse_pyright_output(output: str, returncode: int) -> tuple[list[str], int, int]:
    """Parse pyright JSON output into user-facing messages and counts."""
    errors: list[str] = []
    error_count = 0
    warning_count = 0

    if not output.strip():
        return errors, error_count, warning_count

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        if returncode != 0:
            return [output[:500]], 1, 0
        return errors, error_count, warning_count

    diagnostics = data.get("generalDiagnostics", [])
    for diag in diagnostics:
        if diag.get("severity") == 1:
            error_count += 1
        else:
            warning_count += 1

    for diag in diagnostics[:10]:
        file_path = diag.get("file", "?")
        rng = diag.get("range", {}).get("start", {})
        message = f"{file_path}:{rng.get('line', '?')}: {diag.get('message', '')}"
        errors.append(message)

    if len(diagnostics) > 10:
        errors.append(f"... and {len(diagnostics) - 10} more")

    return errors, error_count, warning_count


def command_available(command: str) -> bool:
    """Return whether a CLI command is available on PATH."""
    return shutil.which(command) is not None


def run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: int = DEFAULT_QUALITY_GATE_TIMEOUT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a subprocess command for quality-gate checks."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def collect_touched_python_files(
    project_root: Path,
    *,
    base_branch: str = "main",
) -> list[str]:
    """Return changed Python files under src/ relative to the repo root."""
    if not (project_root / ".git").exists():
        return []

    candidates: set[str] = set()

    diff_result = run_cmd(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_branch}...HEAD"],
        project_root,
    )
    if diff_result.returncode == 0:
        candidates.update(
            line.strip() for line in diff_result.stdout.splitlines() if line.strip()
        )

    status_result = run_cmd(["git", "status", "--porcelain"], project_root)
    if status_result.returncode == 0:
        for line in status_result.stdout.splitlines():
            entry = line[3:].strip() if len(line) > 3 else line.strip()
            if entry:
                candidates.add(entry)

    return [
        path
        for path in sorted(candidates)
        if path.startswith("src/") and path.endswith(".py")
    ]


def resolve_python_targets(
    project_root: Path,
    target_path: str,
    touched_files: list[str] | None,
) -> list[str]:
    """Return repo-relative Python targets to validate."""
    if touched_files is not None:
        return list(touched_files)

    target = project_root / target_path
    if not target.exists():
        return []

    return [target_path.rstrip("/")]


def build_mypy_command(
    python_targets: list[str],
    *,
    prefer_precise_paths: bool = False,
) -> tuple[list[str], dict[str, str]] | None:
    """Build a repo-compatible mypy command for the requested source targets."""
    packages: set[str] = set()
    modules: set[str] = set()
    file_targets: set[str] = set()

    for target in python_targets:
        path = Path(target)
        if path.as_posix() == "src":
            packages.update(_TYPED_SOURCE_PACKAGES)
            modules.add("schemas")
            continue

        parts = path.parts
        if not parts or parts[0] != "src":
            continue
        if not _is_mypy_supported_source_target(path):
            continue
        if prefer_precise_paths and path.suffix == ".py":
            file_targets.add(path.as_posix())
            continue
        if len(parts) >= 2 and parts[1] in _TYPED_SOURCE_PACKAGES:
            packages.add(parts[1])
            continue
        if len(parts) == 2 and path.suffix == ".py" and path.stem != "__init__":
            modules.add(path.stem)

    if not packages and not modules and not file_targets:
        return None

    cmd = ["mypy", "--explicit-package-bases"]
    if file_targets:
        cmd.append("--follow-imports=skip")
        cmd.extend(sorted(file_targets))
    for package in sorted(packages):
        cmd.extend(["-p", package])
    for module in sorted(modules):
        cmd.extend(["-m", module])

    env = dict(os.environ)
    current_mypy_path = env.get("MYPYPATH", "").strip()
    env["MYPYPATH"] = (
        "src" if not current_mypy_path else f"src{os.pathsep}{current_mypy_path}"
    )
    return cmd, env


def build_repo_mypy_command() -> tuple[list[str], dict[str, str]]:
    """Build the canonical repository-wide mypy command."""
    cmd = ["mypy", "--explicit-package-bases"]
    for package in sorted(_TYPED_SOURCE_PACKAGES):
        cmd.extend(["-p", package])
    cmd.extend(["-m", "schemas"])

    env = dict(os.environ)
    current_mypy_path = env.get("MYPYPATH", "").strip()
    env["MYPYPATH"] = (
        "src" if not current_mypy_path else f"src{os.pathsep}{current_mypy_path}"
    )
    return cmd, env
