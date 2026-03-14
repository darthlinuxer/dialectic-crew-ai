"""Stack-aware validation planning and execution helpers for repo-safe checks."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Type, cast

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from dialectic.target import resolve_active_project_root

StackName = Literal["python", "dotnet", "typescript", "react"]
ValidationProfile = Literal["task", "story"]
PackageManager = Literal["npm", "pnpm", "yarn", "bun"]
_KNOWN_STACKS: tuple[StackName, ...] = ("python", "dotnet", "typescript", "react")


@dataclass(frozen=True)
class ValidationStep:
    """A single allowlisted validation command for a detected stack."""

    stack: StackName
    label: str
    command: list[str]
    reason: str


@dataclass(frozen=True)
class ValidationPlan:
    """A deterministic validation plan for the current project root."""

    project_root: Path
    detected_stacks: list[StackName]
    steps: list[ValidationStep]


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class ValidationStepResult:
    """The execution result for one validation step."""

    stack: StackName
    label: str
    command: list[str]
    passed: bool
    returncode: int
    stdout_tail: str
    stderr_tail: str
    skipped: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ValidationReport:
    """Structured report for a validation run."""

    project_root: Path
    detected_stacks: list[StackName]
    results: list[ValidationStepResult]
    passed: bool


class StackValidationToolInput(BaseModel):
    """Arguments for the stack-aware validation tool."""

    mode: Literal["guide", "run"] = Field(
        default="guide",
        description="Return an allowlisted validation recipe or execute it safely.",
    )
    target: Literal["auto", "python", "dotnet", "typescript", "react"] = Field(
        default="auto",
        description="Restrict validation to a specific detected stack, or auto-detect.",
    )


class StackValidationTool(BaseTool):
    """CrewAI tool wrapper around the allowlisted validation planner."""

    name: str = "stack_aware_validation"
    description: str = (
        "Detect the repository stack and provide or run allowlisted validation commands "
        "for Python, .NET, TypeScript, and React. Never accepts arbitrary shell input."
    )
    args_schema: Type[BaseModel] = StackValidationToolInput

    def _run(self, *args: Any, **kwargs: Any) -> str:
        del args
        mode = str(kwargs.get("mode", "guide"))
        target = str(kwargs.get("target", "auto"))
        project_root = resolve_active_project_root()
        target_stack = None if target == "auto" else target
        if mode == "run":
            report = run_validation_plan(project_root, target_stack=target_stack)
            return json.dumps(_report_payload(report), indent=2)
        plan = build_validation_plan(project_root, target_stack=target_stack)
        return json.dumps(_plan_payload(plan), indent=2)


def detect_project_stacks(project_root: Path) -> list[StackName]:
    """Infer the active stack from stable repository markers."""
    root = project_root.resolve()
    package_json = _load_package_json(root)
    package_data = package_json or {}

    has_python = any(
        (root / marker).exists()
        for marker in ("pyproject.toml", "setup.py", "requirements.txt")
    )
    has_dotnet = any(root.glob("*.sln")) or any(root.rglob("*.csproj"))
    has_typescript = (
        (root / "tsconfig.json").exists()
        or _package_has_dependency(package_data, "typescript")
        or any(root.rglob("*.ts"))
        or any(root.rglob("*.tsx"))
    )
    has_react = (
        _package_has_dependency(package_data, "react")
        or _package_has_dependency(package_data, "react-dom")
        or any(root.rglob("*.tsx"))
    )

    detected: list[StackName] = []
    if has_python:
        detected.append("python")
    if has_dotnet:
        detected.append("dotnet")
    if has_typescript:
        detected.append("typescript")
    if has_react:
        detected.append("react")
    return detected


def build_validation_plan(
    project_root: Path,
    *,
    target_stack: str | None = None,
    command_available_fn: Callable[[str], bool] | None = None,
    python_executable: str | None = None,
) -> ValidationPlan:
    """Build a deterministic allowlisted validation plan for the detected stack."""
    root = project_root.resolve()
    available = command_available_fn or _command_available
    python_cmd = python_executable or sys.executable or "python"
    detected = detect_project_stacks(root)
    selected_stacks = _select_stacks(detected, target_stack)
    package_json = _load_package_json(root)
    package_manager = _detect_package_manager(root, available)

    steps: list[ValidationStep] = []
    if "python" in selected_stacks:
        steps.extend(_python_steps(root, available, python_cmd))
    if "dotnet" in selected_stacks:
        steps.extend(_dotnet_steps(root))
    if "typescript" in selected_stacks or "react" in selected_stacks:
        steps.extend(
            _javascript_steps(root, package_json, package_manager, selected_stacks)
        )
    return ValidationPlan(
        project_root=root,
        detected_stacks=selected_stacks,
        steps=_dedupe_steps(steps),
    )


# pylint: disable=too-many-arguments,too-many-locals
def run_validation_plan(
    project_root: Path,
    *,
    target_stack: str | None = None,
    include_steps: list[str] | None = None,
    timeout: int = 300,
    command_available_fn: Callable[[str], bool] | None = None,
    python_executable: str | None = None,
    run_cmd_fn: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> ValidationReport:
    """Execute the allowlisted validation plan and return structured results."""
    plan = build_validation_plan(
        project_root,
        target_stack=target_stack,
        command_available_fn=command_available_fn,
        python_executable=python_executable,
    )
    selected_labels = set(include_steps or [])
    steps = [
        step for step in plan.steps
        if not selected_labels or step.label in selected_labels
    ]
    runner = run_cmd_fn or subprocess.run

    results: list[ValidationStepResult] = []
    for step in steps:
        try:
            completed = runner(
                step.command,
                cwd=plan.project_root,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            results.append(
                ValidationStepResult(
                    stack=step.stack,
                    label=step.label,
                    command=step.command,
                    passed=completed.returncode == 0,
                    returncode=completed.returncode,
                    stdout_tail=(completed.stdout or "")[-500:],
                    stderr_tail=(completed.stderr or "")[-500:],
                    reason=step.reason,
                )
            )
        except FileNotFoundError as exc:
            results.append(
                ValidationStepResult(
                    stack=step.stack,
                    label=step.label,
                    command=step.command,
                    passed=False,
                    returncode=127,
                    stdout_tail="",
                    stderr_tail=str(exc),
                    skipped=True,
                    reason=f"Command unavailable: {step.command[0]}",
                )
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                ValidationStepResult(
                    stack=step.stack,
                    label=step.label,
                    command=step.command,
                    passed=False,
                    returncode=-1,
                    stdout_tail=_truncate_process_output(exc.output),
                    stderr_tail=_truncate_process_output(exc.stderr),
                    skipped=False,
                    reason=f"Timed out after {timeout}s",
                )
            )

    passed = all(result.passed for result in results) if results else True
    return ValidationReport(
        project_root=plan.project_root,
        detected_stacks=plan.detected_stacks,
        results=results,
        passed=passed,
    )


def step_labels_for_profile(
    plan: ValidationPlan,
    profile: ValidationProfile,
) -> list[str]:
    """Select the appropriate validation step labels for a task or full-story gate."""
    if profile == "story":
        return [step.label for step in plan.steps]

    preferred_by_stack: dict[StackName, tuple[str, ...]] = {
        "python": ("ruff", "mypy"),
        "dotnet": ("restore", "build"),
        "typescript": ("lint", "typecheck"),
        "react": ("lint", "typecheck", "build"),
    }
    available_labels = {step.label for step in plan.steps}
    selected: list[str] = []
    for stack in plan.detected_stacks:
        for label in preferred_by_stack.get(stack, ()):
            if label in available_labels and label not in selected:
                selected.append(label)
    return selected or [step.label for step in plan.steps]


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _select_stacks(detected: list[StackName], target_stack: str | None) -> list[StackName]:
    if target_stack is None:
        return detected
    if target_stack not in _KNOWN_STACKS:
        raise ValueError(f"Unknown validation target: {target_stack}")
    if target_stack in detected:
        return [cast(StackName, target_stack)]
    return []


def _python_steps(
    project_root: Path,
    command_available_fn: Callable[[str], bool],
    python_executable: str,
) -> list[ValidationStep]:
    prefix = (
        ["uv", "run"]
        if command_available_fn("uv") and (project_root / "pyproject.toml").exists()
        else [python_executable, "-m"]
    )
    lint_targets = _existing_targets(project_root, "src", "tests") or ["."]
    type_targets = ["src"] if (project_root / "src").exists() else ["."]
    return [
        ValidationStep(
            stack="python",
            label="ruff",
            command=[*prefix, "ruff", "check", *lint_targets],
            reason="Catch formatting, lint, and import hygiene regressions.",
        ),
        ValidationStep(
            stack="python",
            label="mypy",
            command=[*prefix, "mypy", *type_targets],
            reason="Catch type and symbol-resolution issues before runtime.",
        ),
        ValidationStep(
            stack="python",
            label="pytest",
            command=[*prefix, "pytest", "--tb=short", "-q", "--reruns", "1"],
            reason="Exercise the repository test suite from the active environment.",
        ),
    ]


def _dotnet_steps(project_root: Path) -> list[ValidationStep]:
    target = _first_dotnet_target(project_root)
    if target is None:
        return []
    target_path = str(target.relative_to(project_root))
    return [
        ValidationStep(
            stack="dotnet",
            label="restore",
            command=["dotnet", "restore", target_path],
            reason="Resolve NuGet dependencies before build and test.",
        ),
        ValidationStep(
            stack="dotnet",
            label="build",
            command=["dotnet", "build", target_path, "--no-restore"],
            reason="Catch compile-time and analyzer errors.",
        ),
        ValidationStep(
            stack="dotnet",
            label="test",
            command=[
                "dotnet",
                "test",
                target_path,
                "--no-build",
                "--verbosity",
                "minimal",
            ],
            reason="Run the .NET test suite after a clean build.",
        ),
    ]


def _javascript_steps(
    project_root: Path,
    package_json: dict[str, Any] | None,
    package_manager: PackageManager,
    stacks: list[StackName],
) -> list[ValidationStep]:
    if package_json is None:
        return []
    scripts = package_json.get("scripts") or {}
    if not isinstance(scripts, dict):
        scripts = {}

    steps: list[ValidationStep] = []
    if "lint" in scripts:
        steps.append(
            ValidationStep(
                stack="typescript" if "typescript" in stacks else "react",
                label="lint",
                command=_package_manager_run(package_manager, "lint"),
                reason="Run repository lint rules through the configured package manager.",
            )
        )

    if "typecheck" in scripts:
        steps.append(
            ValidationStep(
                stack="typescript",
                label="typecheck",
                command=_package_manager_run(package_manager, "typecheck"),
                reason="Run the project's declared static type-checking script.",
            )
        )
    elif (project_root / "tsconfig.json").exists():
        steps.append(
            ValidationStep(
                stack="typescript",
                label="typecheck",
                command=_package_manager_exec(package_manager, "tsc", "--noEmit"),
                reason=(
                    "Fallback TypeScript compile check when no explicit typecheck "
                    "script exists."
                ),
            )
        )

    if "test" in scripts:
        steps.append(
            ValidationStep(
                stack="react" if "react" in stacks else "typescript",
                label="test",
                command=_package_manager_run(package_manager, "test"),
                reason="Run the repository's front-end test suite.",
            )
        )

    if "react" in stacks and "build" in scripts:
        steps.append(
            ValidationStep(
                stack="react",
                label="build",
                command=_package_manager_run(package_manager, "build"),
                reason="Confirm the React application still produces a build artifact.",
            )
        )
    return steps


def _existing_targets(project_root: Path, *candidates: str) -> list[str]:
    return [
        candidate for candidate in candidates if (project_root / candidate).exists()
    ]


def _load_package_json(project_root: Path) -> dict[str, Any] | None:
    package_json = project_root / "package.json"
    if not package_json.exists():
        return None
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _package_has_dependency(package_json: dict[str, Any], name: str) -> bool:
    sections = ("dependencies", "devDependencies", "peerDependencies")
    for section in sections:
        deps = package_json.get(section)
        if isinstance(deps, dict) and name in deps:
            return True
    return False


def _detect_package_manager(
    project_root: Path,
    command_available_fn: Callable[[str], bool],
) -> PackageManager:
    if (project_root / "pnpm-lock.yaml").exists() and command_available_fn("pnpm"):
        return "pnpm"
    if (project_root / "yarn.lock").exists() and command_available_fn("yarn"):
        return "yarn"
    if any(
        (project_root / marker).exists() for marker in ("bun.lock", "bun.lockb")
    ) and command_available_fn("bun"):
        return "bun"
    return "npm"


def _package_manager_run(package_manager: PackageManager, script: str) -> list[str]:
    if package_manager == "npm":
        return ["npm", "run", script]
    return [package_manager, "run", script]


def _package_manager_exec(
    package_manager: PackageManager,
    command: str,
    *args: str,
) -> list[str]:
    if package_manager == "npm":
        return ["npx", command, *args]
    if package_manager == "pnpm":
        return ["pnpm", "exec", command, *args]
    if package_manager == "bun":
        return ["bunx", command, *args]
    return ["yarn", command, *args]


def _first_dotnet_target(project_root: Path) -> Path | None:
    solutions = sorted(project_root.glob("*.sln"))
    if solutions:
        return solutions[0]
    projects = sorted(project_root.rglob("*.csproj"))
    return projects[0] if projects else None


def _dedupe_steps(steps: list[ValidationStep]) -> list[ValidationStep]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    deduped: list[ValidationStep] = []
    for step in steps:
        key = (step.label, tuple(step.command))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(step)
    return deduped


def _truncate_process_output(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")[-500:]
    if isinstance(output, str):
        return output[-500:]
    return ""


def _plan_payload(plan: ValidationPlan) -> dict[str, Any]:
    return {
        "project_root": str(plan.project_root),
        "detected_stacks": plan.detected_stacks,
        "steps": [asdict(step) for step in plan.steps],
    }


def _report_payload(report: ValidationReport) -> dict[str, Any]:
    return {
        "project_root": str(report.project_root),
        "detected_stacks": report.detected_stacks,
        "passed": report.passed,
        "results": [asdict(result) for result in report.results],
    }
