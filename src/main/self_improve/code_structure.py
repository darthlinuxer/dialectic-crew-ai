"""Code structure validation for self-improve enforcement.

Validates architectural rules:
- Files <= 400 lines (excluding comments/blanks)
- One main class per file
- New code in src/ folder
- No GOD classes (> 15 public methods or > 10 dependencies)
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FILE_LINES = 400
MAX_PUBLIC_METHODS = 15
MAX_DEPENDENCIES = 10
ALLOWED_CODE_DIRS = frozenset({"src"})


@dataclass
class FileViolation:
    """A single file-level violation."""

    file_path: str
    rule: str
    message: str
    severity: str = "error"


@dataclass
class StructureValidationResult:
    """Result of code structure validation."""

    passed: bool = True
    violations: list[FileViolation] = field(default_factory=list)
    summary: str = ""

    def add_violation(
        self,
        file_path: str,
        rule: str,
        message: str,
        severity: str = "error",
    ) -> None:
        self.violations.append(
            FileViolation(
                file_path=file_path,
                rule=rule,
                message=message,
                severity=severity,
            )
        )
        if severity == "error":
            self.passed = False

    def build_summary(self) -> str:
        error_count = sum(1 for v in self.violations if v.severity == "error")
        warn_count = sum(1 for v in self.violations if v.severity == "warning")
        self.summary = f"{error_count} errors, {warn_count} warnings"
        return self.summary


def _count_code_lines(file_path: Path) -> int:
    """Count non-blank, non-comment lines in a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0

    lines = content.split("\n")
    code_lines = 0
    in_multiline_string = False
    multiline_quote = None

    for line in lines:
        stripped = line.strip()

        if in_multiline_string:
            if multiline_quote and multiline_quote in stripped:
                in_multiline_string = False
                multiline_quote = None
            continue

        if not stripped or stripped.startswith("#"):
            continue

        for quote in ('"""', "'''"):
            if quote in stripped:
                count = stripped.count(quote)
                if count == 1:
                    in_multiline_string = True
                    multiline_quote = quote
                    break

        code_lines += 1

    return code_lines


def _extract_classes(file_path: Path) -> list[ast.ClassDef]:
    """Extract all class definitions from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _count_public_methods(class_def: ast.ClassDef) -> int:
    """Count public methods (not starting with _) in a class."""
    count = 0
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            count += 1
    return count


def _count_dependencies(class_def: ast.ClassDef) -> int:
    """Count unique type annotations (dependencies) in __init__ parameters."""
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            deps: set[str] = set()
            for arg in node.args.args[1:]:
                if arg.annotation:
                    deps.add(ast.dump(arg.annotation))
            return len(deps)
    return 0


def _is_dataclass_or_model(class_def: ast.ClassDef) -> bool:
    """Check if class is a dataclass, Pydantic model, or similar data container."""
    for decorator in class_def.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id in ("dataclass", "dataclasses"):
            return True
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name) and decorator.func.id in ("dataclass", "dataclasses"):
                return True
            if isinstance(decorator.func, ast.Attribute) and decorator.func.attr in ("dataclass", "validator", "field_validator"):
                return True

    for base in class_def.bases:
        if isinstance(base, ast.Name) and base.id in ("BaseModel", "BaseSettings", "NamedTuple", "TypedDict"):
            return True
        if isinstance(base, ast.Attribute) and base.attr in ("BaseModel", "BaseSettings"):
            return True

    return False


def _check_file_line_count(
    file_path: Path,
    project_root: Path,
    result: StructureValidationResult,
) -> None:
    """Check if file exceeds MAX_FILE_LINES."""
    line_count = _count_code_lines(file_path)
    if line_count > MAX_FILE_LINES:
        rel_path = file_path.relative_to(project_root)
        result.add_violation(
            file_path=str(rel_path),
            rule="max-file-lines",
            message=f"File has {line_count} code lines (max: {MAX_FILE_LINES})",
            severity="error",
        )


def _check_classes_per_file(
    file_path: Path,
    project_root: Path,
    result: StructureValidationResult,
) -> None:
    """Check if file has more than one main class (excluding dataclasses/models)."""
    classes = _extract_classes(file_path)
    main_classes = [c for c in classes if not _is_dataclass_or_model(c)]

    if len(main_classes) > 1:
        rel_path = file_path.relative_to(project_root)
        class_names = [c.name for c in main_classes]
        result.add_violation(
            file_path=str(rel_path),
            rule="one-class-per-file",
            message=f"File has {len(main_classes)} main classes: {', '.join(class_names)}",
            severity="error",
        )


def _check_god_class(
    file_path: Path,
    project_root: Path,
    result: StructureValidationResult,
) -> None:
    """Check for GOD classes (too many public methods or dependencies)."""
    classes = _extract_classes(file_path)

    for class_def in classes:
        if _is_dataclass_or_model(class_def):
            continue

        public_methods = _count_public_methods(class_def)
        dependencies = _count_dependencies(class_def)
        rel_path = file_path.relative_to(project_root)

        if public_methods > MAX_PUBLIC_METHODS:
            result.add_violation(
                file_path=str(rel_path),
                rule="god-class-methods",
                message=(
                    f"Class '{class_def.name}' has {public_methods} public methods "
                    f"(max: {MAX_PUBLIC_METHODS})"
                ),
                severity="warning",
            )

        if dependencies > MAX_DEPENDENCIES:
            result.add_violation(
                file_path=str(rel_path),
                rule="god-class-deps",
                message=(
                    f"Class '{class_def.name}' has {dependencies} dependencies "
                    f"(max: {MAX_DEPENDENCIES})"
                ),
                severity="warning",
            )


def _check_file_location(
    file_path: Path,
    project_root: Path,
    result: StructureValidationResult,
) -> None:
    """Check if new code is placed in allowed directories (src/)."""
    try:
        rel_path = file_path.relative_to(project_root)
    except ValueError:
        return

    parts = rel_path.parts
    if not parts:
        return

    top_dir = parts[0]
    if top_dir not in ALLOWED_CODE_DIRS and top_dir != "tests":
        if file_path.suffix == ".py" and not file_path.name.startswith("test_"):
            result.add_violation(
                file_path=str(rel_path),
                rule="code-location",
                message=f"New code should be in src/, found in '{top_dir}/'",
                severity="error",
            )


def validate_code_structure(
    project_root: Path,
    changed_files: list[Path] | None = None,
    check_all_src: bool = False,
) -> StructureValidationResult:
    """Validate code structure for the given files."""
    result = StructureValidationResult()

    if changed_files is None or check_all_src:
        src_dir = project_root / "src"
        changed_files = list(src_dir.rglob("*.py")) if src_dir.exists() else []

    for file_path in changed_files:
        if not file_path.exists() or file_path.suffix != ".py":
            continue
        if file_path.name.startswith("test_"):
            continue
        if "/__pycache__/" in str(file_path) or file_path.name == "__pycache__":
            continue

        _check_file_line_count(file_path, project_root, result)
        _check_classes_per_file(file_path, project_root, result)
        _check_god_class(file_path, project_root, result)
        _check_file_location(file_path, project_root, result)

    result.build_summary()
    return result


def print_structure_validation_result(
    result: StructureValidationResult,
    prefix: str = "  ",
) -> None:
    """Print structure validation results to console."""
    errors = [v for v in result.violations if v.severity == "error"]
    warnings = [v for v in result.violations if v.severity == "warning"]

    if errors:
        print(f"{prefix}Errors:")
        for violation in errors[:10]:
            print(f"{prefix}  [{violation.rule}] {violation.file_path}: {violation.message}")
        if len(errors) > 10:
            print(f"{prefix}  ... and {len(errors) - 10} more errors")

    if warnings:
        print(f"{prefix}Warnings:")
        for violation in warnings[:5]:
            print(f"{prefix}  [{violation.rule}] {violation.file_path}: {violation.message}")
        if len(warnings) > 5:
            print(f"{prefix}  ... and {len(warnings) - 5} more warnings")

__all__ = [
    "ALLOWED_CODE_DIRS",
    "MAX_DEPENDENCIES",
    "MAX_FILE_LINES",
    "MAX_PUBLIC_METHODS",
    "FileViolation",
    "StructureValidationResult",
    "print_structure_validation_result",
    "validate_code_structure",
]

