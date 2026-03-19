"""Tests for shared stack validation planning and execution."""

# pylint: disable=missing-function-docstring,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, cast

from dialectic import stack_validation


StackValidationTool = stack_validation.StackValidationTool
build_validation_plan = stack_validation.build_validation_plan
detect_project_stacks = stack_validation.detect_project_stacks
run_validation_plan = stack_validation.run_validation_plan
step_labels_for_profile = stack_validation.step_labels_for_profile


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detect_project_stacks_uses_repo_markers(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(
        tmp_path / "package.json",
        json.dumps(
            {
                "name": "demo-web",
                "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
                "devDependencies": {"typescript": "^5.0.0"},
            }
        ),
    )
    _write(tmp_path / "tsconfig.json", "{}")
    _write(tmp_path / "demo.csproj", "<Project Sdk='Microsoft.NET.Sdk'></Project>")

    assert detect_project_stacks(tmp_path) == [
        "python",
        "dotnet",
        "typescript",
        "react",
    ]


def test_build_validation_plan_for_python_repo_prefers_uv(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")
    _write(tmp_path / "tests" / "test_app.py", "def test_ok():\n    assert True\n")

    plan = build_validation_plan(
        tmp_path,
        command_available_fn=lambda command: command in {"uv", "env"},
        python_executable="/tmp/venv/bin/python",
    )

    assert plan.detected_stacks == ["python"]
    assert [step.label for step in plan.steps] == [
        "ruff",
        "ruff-format",
        "mypy",
        "pytest",
    ]
    assert plan.steps[0].command == ["uv", "run", "ruff", "check", "src", "tests"]
    assert plan.steps[1].command == [
        "uv",
        "run",
        "ruff",
        "format",
        "--check",
        "src",
        "tests",
    ]
    assert plan.steps[2].command == [
        "env",
        "MYPYPATH=src",
        "uv",
        "run",
        "python",
        "-m",
        "mypy",
        "-m",
        "app",
    ]
    assert plan.steps[3].command == [
        "uv",
        "run",
        "pytest",
        "--tb=short",
        "-q",
        "--reruns",
        "1",
    ]


def test_build_validation_plan_for_python_repo_adds_pyright_step_for_release(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "pyrightconfig.json", "{}")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")

    plan = build_validation_plan(
        tmp_path,
        command_available_fn=lambda command: command in {"uv", "env", "npx"},
        python_executable="/tmp/venv/bin/python",
    )

    assert [step.label for step in plan.steps] == [
        "ruff",
        "ruff-format",
        "mypy",
        "pytest",
        "pyright",
    ]
    assert plan.steps[4].command == [
        "npx",
        "--yes",
        "pyright",
        "--project",
        "pyrightconfig.json",
        "--outputjson",
    ]


def test_step_labels_for_release_profile_include_full_python_suite(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "pyrightconfig.json", "{}")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")

    plan = build_validation_plan(
        tmp_path,
        command_available_fn=lambda command: command in {"uv", "env", "npx"},
        python_executable="python",
    )

    assert step_labels_for_profile(plan, "release") == [
        "ruff",
        "ruff-format",
        "mypy",
        "pytest",
        "pyright",
    ]


def test_build_validation_plan_for_react_repo_prefers_package_scripts(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "package.json",
        json.dumps(
            {
                "name": "demo-react",
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"typescript": "^5.0.0"},
                "scripts": {
                    "lint": "eslint .",
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                    "build": "vite build",
                },
            }
        ),
    )
    _write(tmp_path / "tsconfig.json", "{}")
    _write(tmp_path / "src" / "App.tsx", "export function App() { return null; }\n")

    plan = build_validation_plan(
        tmp_path,
        command_available_fn=lambda command: command == "npm",
        python_executable="python",
    )

    assert plan.detected_stacks == ["typescript", "react"]
    assert [step.label for step in plan.steps] == [
        "lint",
        "typecheck",
        "test",
        "build",
    ]
    assert plan.steps[0].command == ["npm", "run", "lint"]
    assert plan.steps[1].command == ["npm", "run", "typecheck"]
    assert plan.steps[2].command == ["npm", "run", "test"]
    assert plan.steps[3].command == ["npm", "run", "build"]


def test_run_validation_plan_executes_allowlisted_steps(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")

    observed_commands: list[list[str]] = []

    def fake_run_cmd(command: list[str], **_: object) -> CompletedProcess[str]:
        observed_commands.append(command)
        return CompletedProcess(command, 0, stdout="ok", stderr="")

    report = run_validation_plan(
        tmp_path,
        include_steps=["ruff", "ruff-format", "mypy"],
        command_available_fn=lambda command: command in {"uv", "python", "env"},
        python_executable="python",
        run_cmd_fn=fake_run_cmd,
    )

    assert report.detected_stacks == ["python"]
    assert report.passed is True
    assert [result.label for result in report.results] == [
        "ruff",
        "ruff-format",
        "mypy",
    ]
    assert observed_commands == [
        ["uv", "run", "ruff", "check", "src"],
        ["uv", "run", "ruff", "format", "--check", "src"],
        ["env", "MYPYPATH=src", "uv", "run", "python", "-m", "mypy", "-m", "app"],
    ]


def test_stack_validation_tool_guide_mode_returns_json(
    monkeypatch, tmp_path: Path
) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")

    monkeypatch.setenv("DIALECTIC_PROJECT_ROOT", str(tmp_path))
    tool = StackValidationTool()
    tool_run = cast(Any, getattr(tool, "_run"))

    payload = json.loads(tool_run(mode="guide", target="auto"))

    assert payload["detected_stacks"] == ["python"]
    assert payload["steps"][0]["label"] == "ruff"
