"""Semantic comparison helpers for structure validation."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


def read_file_at_ref(
    project_root: Path,
    file_path: Path,
    git_ref: str,
) -> str | None:
    """Read a file as stored at a given git ref."""
    try:
        rel_path = file_path.relative_to(project_root)
    except ValueError:
        return None

    result = subprocess.run(
        ["git", "show", f"{git_ref}:{rel_path.as_posix()}"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    return result.stdout


def normalized_ast_dump(content: str) -> str | None:
    """Build a normalized AST dump for semantic Python comparisons."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    return ast.dump(tree, annotate_fields=False, include_attributes=False)


def has_semantic_changes_since_ref(
    project_root: Path,
    file_path: Path,
    git_ref: str,
) -> bool:
    """Return True when a Python file differs semantically from a git ref."""
    baseline_content = read_file_at_ref(project_root, file_path, git_ref)
    if baseline_content is None:
        return True

    try:
        current_content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True

    baseline_ast = normalized_ast_dump(baseline_content)
    current_ast = normalized_ast_dump(current_content)
    if baseline_ast is None or current_ast is None:
        return True

    return baseline_ast != current_ast


__all__ = ["has_semantic_changes_since_ref", "read_file_at_ref"]
