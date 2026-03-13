from __future__ import annotations

from pathlib import Path

import execution.validation_gate as validation_gate
from dialectic.stack_validation import (
    ValidationPlan,
    ValidationReport,
    ValidationStep,
    ValidationStepResult,
)


def test_run_stack_validation_gate_uses_task_profile_steps(monkeypatch, tmp_path: Path) -> None:
    plan = ValidationPlan(
        project_root=tmp_path,
        detected_stacks=["python"],
        steps=[
            ValidationStep("python", "ruff", ["uv", "run", "ruff", "check", "src"], "lint"),
            ValidationStep("python", "mypy", ["uv", "run", "mypy", "src"], "types"),
            ValidationStep("python", "pytest", ["uv", "run", "pytest"], "tests"),
        ],
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(validation_gate, "resolve_project_root", lambda: tmp_path)
    monkeypatch.setattr(validation_gate, "build_validation_plan", lambda *args, **kwargs: plan)

    def fake_run_validation_plan(project_root, *, include_steps=None, **kwargs):
        del kwargs
        captured["project_root"] = project_root
        captured["include_steps"] = include_steps
        return ValidationReport(
            project_root=tmp_path,
            detected_stacks=["python"],
            results=[
                ValidationStepResult("python", "ruff", ["uv", "run", "ruff", "check", "src"], True, 0, "", ""),
                ValidationStepResult("python", "mypy", ["uv", "run", "mypy", "src"], True, 0, "", ""),
            ],
            passed=True,
        )

    monkeypatch.setattr(validation_gate, "run_validation_plan", fake_run_validation_plan)

    result = validation_gate.run_stack_validation_gate(profile="task")

    assert captured["project_root"] == tmp_path
    assert captured["include_steps"] == ["ruff", "mypy"]
    assert result.verified is True
    assert result.checks_passed == ["stack validation: ruff", "stack validation: mypy"]


def test_run_stack_validation_gate_reports_failed_steps(monkeypatch, tmp_path: Path) -> None:
    plan = ValidationPlan(
        project_root=tmp_path,
        detected_stacks=["python"],
        steps=[
            ValidationStep("python", "ruff", ["uv", "run", "ruff", "check", "src"], "lint"),
            ValidationStep("python", "mypy", ["uv", "run", "mypy", "src"], "types"),
        ],
    )

    monkeypatch.setattr(validation_gate, "resolve_project_root", lambda: tmp_path)
    monkeypatch.setattr(validation_gate, "build_validation_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(
        validation_gate,
        "run_validation_plan",
        lambda *args, **kwargs: ValidationReport(
            project_root=tmp_path,
            detected_stacks=["python"],
            results=[
                ValidationStepResult("python", "ruff", ["uv", "run", "ruff", "check", "src"], True, 0, "", ""),
                ValidationStepResult("python", "mypy", ["uv", "run", "mypy", "src"], False, 1, "", "type error"),
            ],
            passed=False,
        ),
    )

    result = validation_gate.run_stack_validation_gate(profile="task")

    assert result.verified is False
    assert result.checks_failed == ["stack validation: mypy"]
    assert "mypy" in result.notes
