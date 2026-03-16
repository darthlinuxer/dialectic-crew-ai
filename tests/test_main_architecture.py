"""Architecture tests for the refactored `src.main` deep-module surfaces."""

# pylint: disable=trailing-newlines

from __future__ import annotations

import ast
from pathlib import Path

from src.main.self_improve.code_structure import validate_code_structure

REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_IMPROVE_PACKAGE = REPO_ROOT / "src" / "main" / "self_improve"
ENFORCED_PACKAGE_FILES = sorted(
    path
    for path in SELF_IMPROVE_PACKAGE.glob("*.py")
    if path.name not in {"__init__.py"}
)
BANNED_IMPORT_PREFIXES = (
    "src.main.cleanup_commands",
    "src.main.target_commands",
    "src.main.vision_commands",
)
WRAPPER_FILES = (
    "cli_commands.py",
    "code_structure_validation.py",
    "git_helpers.py",
    "metrics_comparison.py",
    "pr_builder.py",
    "quality_gate.py",
    "self_improve_persistence.py",
    "test_runner.py",
)


def _imported_modules(file_path: Path) -> set[str]:
    """Return imported module names from a Python source file."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_self_improve_package_files_pass_structure_validation():
    """Self-improve package files should satisfy the structure guardrails."""
    result = validate_code_structure(REPO_ROOT, ENFORCED_PACKAGE_FILES)
    assert result.passed, [f"{v.file_path}: {v.rule}" for v in result.violations]


def test_self_improve_package_avoids_flat_command_shims():
    """Self-improve package files should not import removed flat command shims."""
    for file_path in ENFORCED_PACKAGE_FILES:
        imports = _imported_modules(file_path)
        assert not any(
            imported.startswith(BANNED_IMPORT_PREFIXES) for imported in imports
        ), f"{file_path} imports flat command shim modules: {sorted(imports)}"


def test_main_package_has_no_flat_wrapper_files():
    """The flat compatibility wrapper files should be removed from src.main."""
    main_package = REPO_ROOT / "src" / "main"
    wrapper_paths = [main_package / wrapper_name for wrapper_name in WRAPPER_FILES]

    assert not any(path.exists() for path in wrapper_paths), (
        "Thin wrapper modules still exist: "
        f"{[str(path.relative_to(REPO_ROOT)) for path in wrapper_paths if path.exists()]}"
    )


def test_main_bootstrap_imports_canonical_modules_directly():
    """The bootstrap module should wire legacy aliases from canonical modules."""
    main_module = REPO_ROOT / "main.py"
    imports = _imported_modules(main_module)

    assert "src.main.self_improve.git_helpers" in imports
    assert "src.main.self_improve.pr_builder" in imports
    assert "src.main.git_helpers" not in imports
    assert "src.main.pr_builder" not in imports

# End of architecture regression tests.

