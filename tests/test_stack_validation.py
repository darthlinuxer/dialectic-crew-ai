from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, cast

import dialectic.stack_validation as stack_validation


StackValidationTool = stack_validation.StackValidationTool
build_validation_plan = stack_validation.build_validation_plan
detect_project_stacks = stack_validation.detect_project_stacks
run_validation_plan = stack_validation.run_validation_plan


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

    assert detect_project_stacks(tmp_path) == ["python", "dotnet", "typescript", "react"]


def test_build_validation_plan_for_python_repo_prefers_uv(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")
    _write(tmp_path / "tests" / "test_app.py", "def test_ok():\n    assert True\n")

    plan = build_validation_plan(
        tmp_path,
        command_available_fn=lambda command: command == "uv",
        python_executable="/tmp/venv/bin/python",
    )

    assert plan.detected_stacks == ["python"]
    assert [step.label for step in plan.steps] == ["ruff", "mypy", "pytest"]
    assert plan.steps[0].command == ["uv", "run", "ruff", "check", "src", "tests"]
    assert plan.steps[1].command == ["uv", "run", "mypy", "src"]
    assert plan.steps[2].command == ["uv", "run", "pytest", "--tb=short", "-q", "--reruns", "1"]


def test_build_validation_plan_for_react_repo_prefers_package_scripts(tmp_path: Path) -> None:
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
    assert [step.label for step in plan.steps] == ["lint", "typecheck", "test", "build"]
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
        include_steps=["ruff", "mypy"],
        command_available_fn=lambda command: command in {"uv", "python"},
        python_executable="python",
        run_cmd_fn=fake_run_cmd,
    )

    assert report.detected_stacks == ["python"]
    assert report.passed is True
    assert [result.label for result in report.results] == ["ruff", "mypy"]
    assert observed_commands == [
        ["uv", "run", "ruff", "check", "src"],
        ["uv", "run", "mypy", "src"],
    ]


def test_stack_validation_tool_guide_mode_returns_json(monkeypatch, tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='demo'\n")
    _write(tmp_path / "src" / "app.py", "print('hi')\n")

    monkeypatch.setenv("DIALECTIC_PROJECT_ROOT", str(tmp_path))
    tool = StackValidationTool()
    tool_run = cast(Any, getattr(tool, "_run"))

    payload = json.loads(tool_run(mode="guide", target="auto"))

    assert payload["detected_stacks"] == ["python"]
    assert payload["steps"][0]["label"] == "ruff"
