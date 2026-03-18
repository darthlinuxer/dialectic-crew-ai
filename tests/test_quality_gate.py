"""Tests for the quality gate module."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=too-few-public-methods,too-many-arguments
# pylint: disable=too-many-positional-arguments

from pathlib import Path
from unittest.mock import MagicMock, patch

from dialectic.stack_validation import ValidationReport, ValidationStepResult
from src.main.self_improve.quality_gate import (
    QualityCheckResult,
    QualityGateResult,
    _run_mypy,
    _run_python_remediation,
    _run_ruff_check,
    _run_ruff_format_check,
    _run_pyright,
    build_mypy_command,
    collect_touched_python_files,
    run_quality_gate,
)


class TestQualityCheckResult:
    def test_default_values(self):
        result = QualityCheckResult(tool="test", passed=True)
        assert result.tool == "test"
        assert result.passed is True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.output == ""
        assert not result.errors


class TestQualityGateResult:
    def test_add_check_passing(self):
        result = QualityGateResult(passed=True)
        check = QualityCheckResult(tool="ruff", passed=True)
        result.add_check(check)
        assert result.passed is True
        assert len(result.checks) == 1

    def test_add_check_failing(self):
        result = QualityGateResult(passed=True)
        check = QualityCheckResult(tool="ruff", passed=False, error_count=1)
        result.add_check(check)
        assert result.passed is False
        assert len(result.checks) == 1

    def test_build_summary(self):
        result = QualityGateResult(passed=True)
        result.add_check(QualityCheckResult(tool="ruff", passed=True, error_count=0))
        result.add_check(QualityCheckResult(tool="mypy", passed=False, error_count=3))
        summary = result.build_summary()
        assert "ruff: PASS" in summary
        assert "mypy: FAIL" in summary

    def test_remediation_defaults(self):
        result = QualityGateResult(passed=True)
        assert result.remediation_attempted is False
        assert result.remediation_attempt_count == 0
        assert result.remediation_succeeded is False
        assert not result.remediation_steps
        assert result.remediation_failure_reason == ""
        assert result.remediation_exhausted is False


class TestRuffCheck:
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_ruff_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_ruff_check(Path("/tmp"))
        assert result.passed is True
        assert "not available" in result.output

    @patch("src.main.self_improve.quality_gate.command_available")
    def test_target_path_missing(self, mock_available):
        mock_available.return_value = True
        result = _run_ruff_check(Path("/nonexistent"), "src/")
        assert result.passed is True
        assert "does not exist" in result.output

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_ruff_passes(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_check(Path("/tmp"), "src/")
        assert result.passed is True
        assert result.error_count == 0
        mock_run.assert_called_once_with(
            ["ruff", "check", "src", "--output-format=json"],
            Path("/tmp"),
        )

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_ruff_fails_with_errors(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=(
                '[{"filename": "test.py", "location": {"row": 1}, '
                '"code": "E501", "message": "line too long"}]'
            ),
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_check(Path("/tmp"), "src/")
        assert result.passed is False
        assert result.error_count == 1
        assert len(result.errors) == 1

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_ruff_scopes_to_touched_files(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")

        result = _run_ruff_check(
            Path("/tmp"),
            touched_files=["src/dialectic/agents.py", "src/main/cli/entrypoint.py"],
        )

        assert result.passed is True
        mock_run.assert_called_once_with(
            [
                "ruff",
                "check",
                "src/dialectic/agents.py",
                "src/main/cli/entrypoint.py",
                "--output-format=json",
            ],
            Path("/tmp"),
        )


class TestRuffFormatCheck:
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_ruff_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_ruff_format_check(Path("/tmp"))
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_format_passes(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_format_check(Path("/tmp"), "src/")
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_format_fails(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="--- test.py\n+++ test.py\n@@ -1 +1 @@\n-x=1\n+x = 1",
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_format_check(Path("/tmp"), "src/")
        assert result.passed is False

    @patch("src.main.self_improve.quality_gate.command_available")
    def test_format_skips_when_no_touched_python_files(self, mock_available):
        mock_available.return_value = True

        result = _run_ruff_format_check(Path("/tmp"), touched_files=[])

        assert result.passed is True
        assert "No touched Python source files" in result.output


class TestMypyCheck:
    def test_build_mypy_command_uses_explicit_package_bases(self):
        command = build_mypy_command(
            ["src/dialectic/agents.py", "src/main/cli/entrypoint.py", "src/schemas.py"]
        )

        assert command is not None
        cmd, env = command
        assert cmd == [
            "mypy",
            "--explicit-package-bases",
            "-p",
            "dialectic",
            "-p",
            "main",
            "-m",
            "schemas",
        ]
        assert env["MYPYPATH"].startswith("src")

    def test_build_mypy_command_can_target_precise_files(self):
        command = build_mypy_command(
            ["src/execution/verify.py", "src/publication/policy.py"],
            prefer_precise_paths=True,
        )

        assert command is not None
        cmd, env = command
        assert cmd == [
            "mypy",
            "--explicit-package-bases",
            "--follow-imports=skip",
            "src/execution/verify.py",
            "src/publication/policy.py",
        ]
        assert env["MYPYPATH"].startswith("src")

    def test_build_mypy_command_excludes_skill_scripts_from_precise_targets(self):
        command = build_mypy_command(
            [
                "src/mcp/skills/senior-software-developer/scripts/check_quality.py",
                "src/main/self_improve/persistence.py",
            ],
            prefer_precise_paths=True,
        )

        assert command is not None
        cmd, env = command
        assert cmd == [
            "mypy",
            "--explicit-package-bases",
            "--follow-imports=skip",
            "src/main/self_improve/persistence.py",
        ]
        assert env["MYPYPATH"].startswith("src")

    @patch("src.main.self_improve.quality_gate.command_available")
    def test_mypy_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_mypy(Path("/tmp"))
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_mypy_passes(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        with patch.object(Path, "exists", return_value=True):
            result = _run_mypy(Path("/tmp"), "src/")
        assert result.passed is True
        assert result.error_count == 0
        called_cmd = mock_run.call_args.args[0]
        called_env = mock_run.call_args.kwargs["env"]
        assert called_cmd[:3] == ["mypy", "--explicit-package-bases", "-p"]
        assert called_env["MYPYPATH"].startswith("src")

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_mypy_fails(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="test.py:1: error: Name 'x' is not defined",
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_mypy(Path("/tmp"), "src/")
        assert result.passed is False
        assert result.error_count == 1

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_mypy_falls_back_to_package_command_when_precise_paths_fail(
        self,
        mock_available,
        mock_run,
    ):
        mock_available.return_value = True
        mock_run.side_effect = [
            MagicMock(
                returncode=1,
                stdout="src/dialectic/config.py:1: error: boom",
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout="Success: no issues found in 10 source files",
                stderr="",
            ),
        ]

        result = _run_mypy(
            Path("/tmp"),
            touched_files=["src/dialectic/config.py", "src/main/cli/entrypoint.py"],
        )

        assert result.passed is True
        assert "package-level fallback passed" in result.output
        first_cmd = mock_run.call_args_list[0].args[0]
        second_cmd = mock_run.call_args_list[1].args[0]
        assert "--follow-imports=skip" in first_cmd
        assert "--follow-imports=skip" not in second_cmd

    @patch("src.main.self_improve.quality_gate.command_available")
    @patch("src.main.self_improve.quality_gate.run_cmd")
    def test_mypy_falls_back_to_canonical_repo_command_when_needed(
        self,
        mock_run,
        mock_available,
    ):
        mock_available.return_value = True
        mock_run.side_effect = [
            MagicMock(
                returncode=1,
                stdout="src/dialectic/config.py:1: error: boom",
                stderr="",
            ),
            MagicMock(
                returncode=1,
                stdout="src/main/cli/entrypoint.py:1: error: boom again",
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout="Success: no issues found in 262 source files",
                stderr="",
            ),
        ]

        result = _run_mypy(
            Path("/tmp"),
            touched_files=["src/dialectic/config.py", "src/main/cli/entrypoint.py"],
        )

        assert result.passed is True
        assert "canonical repo-wide fallback passed" in result.output
        first_cmd = mock_run.call_args_list[0].args[0]
        second_cmd = mock_run.call_args_list[1].args[0]
        third_cmd = mock_run.call_args_list[2].args[0]
        assert "--follow-imports=skip" in first_cmd
        assert "--follow-imports=skip" not in second_cmd
        assert third_cmd == [
            "mypy",
            "--explicit-package-bases",
            "-p",
            "dialectic",
            "-p",
            "execution",
            "-p",
            "main",
            "-p",
            "mcp",
            "-p",
            "planning",
            "-m",
            "schemas",
            "--no-error-summary",
        ]


class TestPyrightCheck:
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_pyright_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_pyright(Path("/tmp"))
        assert result.passed is True  # pyright is warn-only

    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_pyright_always_passes(self, mock_available, mock_run):
        """Pyright is warn-only, so it should always pass."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=(
                '{"generalDiagnostics": [{"severity": 1, "message": "error", '
                '"file": "test.py", "range": {"start": {"line": 1}}}]}'
            ),
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_pyright(Path("/tmp"), "src/")
        assert result.passed is True  # warn-only
        assert result.error_count == 1


class TestRunQualityGate:
    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_all_checks_pass(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="ruff")],
        )
        mock_step_labels.return_value = ["ruff", "mypy", "pytest", "pyright"]
        mock_run_plan.return_value = ValidationReport(
            project_root=Path("/tmp"),
            detected_stacks=["python"],
            passed=True,
            results=[
                ValidationStepResult(
                    stack="python",
                    label="ruff",
                    command=["ruff", "check", "src"],
                    passed=True,
                    returncode=0,
                    stdout_tail="",
                    stderr_tail="",
                    reason="lint",
                ),
                ValidationStepResult(
                    stack="python",
                    label="mypy",
                    command=["python", "-m", "mypy"],
                    passed=True,
                    returncode=0,
                    stdout_tail="",
                    stderr_tail="",
                    reason="type",
                ),
                ValidationStepResult(
                    stack="python",
                    label="pytest",
                    command=["python", "-m", "pytest"],
                    passed=True,
                    returncode=0,
                    stdout_tail="",
                    stderr_tail="",
                    reason="tests",
                ),
                ValidationStepResult(
                    stack="python",
                    label="pyright",
                    command=["npx", "--yes", "pyright"],
                    passed=True,
                    returncode=1,
                    stdout_tail='{"generalDiagnostics": []}',
                    stderr_tail="",
                    reason="editor parity",
                ),
            ],
        )

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is True
        assert len(result.checks) == 4
        mock_collect.assert_called_once_with(Path("/tmp"))
        mock_build_plan.assert_called_once_with(Path("/tmp"))
        mock_step_labels.assert_called_once()
        mock_run_plan.assert_called_once_with(
            Path("/tmp"),
            include_steps=["ruff", "mypy", "pytest", "pyright"],
        )

    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_one_check_fails(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="ruff")],
        )
        mock_step_labels.return_value = ["ruff", "mypy"]
        mock_run_plan.return_value = ValidationReport(
            project_root=Path("/tmp"),
            detected_stacks=["python"],
            passed=False,
            results=[
                ValidationStepResult(
                    stack="python",
                    label="ruff",
                    command=["ruff", "check", "src"],
                    passed=False,
                    returncode=1,
                    stdout_tail="bad",
                    stderr_tail="",
                    reason="lint",
                )
            ],
        )

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is False

    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_exclude_pyright(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="ruff"), MagicMock(label="pyright")],
        )
        mock_step_labels.return_value = ["ruff", "mypy", "pytest", "pyright"]
        mock_run_plan.return_value = ValidationReport(
            project_root=Path("/tmp"),
            detected_stacks=["python"],
            passed=True,
            results=[
                ValidationStepResult(
                    stack="python",
                    label="ruff",
                    command=["ruff", "check", "src"],
                    passed=True,
                    returncode=0,
                    stdout_tail="",
                    stderr_tail="",
                    reason="lint",
                ),
                ValidationStepResult(
                    stack="python",
                    label="mypy",
                    command=["python", "-m", "mypy"],
                    passed=True,
                    returncode=0,
                    stdout_tail="",
                    stderr_tail="",
                    reason="type",
                ),
            ],
        )

        result = run_quality_gate(Path("/tmp"), include_pyright=False)
        assert result.passed is True
        assert len(result.checks) == 2
        mock_run_plan.assert_called_once_with(
            Path("/tmp"),
            include_steps=["ruff", "mypy", "pytest"],
        )

    @patch("src.main.self_improve.quality_gate._run_python_remediation")
    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_retries_after_python_validation_failures(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
        mock_remediate,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="ruff")],
        )
        mock_step_labels.return_value = [
            "ruff",
            "ruff-format",
            "mypy",
            "pytest",
            "pyright",
        ]
        mock_run_plan.side_effect = [
            ValidationReport(
                project_root=Path("/tmp"),
                detected_stacks=["python"],
                passed=False,
                results=[
                    ValidationStepResult(
                        stack="python",
                        label="ruff-format",
                        command=["ruff", "format", "--check", "src"],
                        passed=False,
                        returncode=1,
                        stdout_tail="diff",
                        stderr_tail="",
                        reason="format",
                    )
                ],
            ),
            ValidationReport(
                project_root=Path("/tmp"),
                detected_stacks=["python"],
                passed=True,
                results=[
                    ValidationStepResult(
                        stack="python",
                        label="ruff-format",
                        command=["ruff", "format", "--check", "src"],
                        passed=True,
                        returncode=0,
                        stdout_tail="",
                        stderr_tail="",
                        reason="format",
                    )
                ],
            ),
        ]
        mock_remediate.return_value = (True, ["ruff-format-fix", "ruff-lint-fix"])

        result = run_quality_gate(Path("/tmp"))

        assert result.passed is True
        assert result.remediation_attempted is True
        assert result.remediation_succeeded is True
        assert result.remediation_steps == ["ruff-format-fix", "ruff-lint-fix"]
        assert mock_run_plan.call_count == 2
        mock_remediate.assert_called_once_with(
            Path("/tmp"),
            ["src/dialectic/agents.py"],
        )

    @patch("src.main.self_improve.quality_gate._run_python_remediation")
    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_skips_remediation_for_pytest_failures(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
        mock_remediate,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="pytest")],
        )
        mock_step_labels.return_value = ["ruff", "ruff-format", "mypy", "pytest"]
        mock_run_plan.return_value = ValidationReport(
            project_root=Path("/tmp"),
            detected_stacks=["python"],
            passed=False,
            results=[
                ValidationStepResult(
                    stack="python",
                    label="pytest",
                    command=["python", "-m", "pytest"],
                    passed=False,
                    returncode=1,
                    stdout_tail="test failure",
                    stderr_tail="",
                    reason="tests",
                )
            ],
        )

        result = run_quality_gate(Path("/tmp"))

        assert result.passed is False
        assert result.remediation_attempted is False
        mock_remediate.assert_not_called()
        mock_run_plan.assert_called_once()

    @patch("src.main.self_improve.quality_gate._run_python_remediation")
    @patch("src.main.self_improve.quality_gate.step_labels_for_profile")
    @patch("src.main.self_improve.quality_gate.run_validation_plan")
    @patch("src.main.self_improve.quality_gate.build_validation_plan")
    @patch("src.main.self_improve.quality_gate.collect_touched_python_files")
    def test_marks_remediation_budget_exhausted_when_resume_already_used_budget(
        self,
        mock_collect,
        mock_build_plan,
        mock_run_plan,
        mock_step_labels,
        mock_remediate,
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_build_plan.return_value = MagicMock(
            project_root=Path("/tmp"),
            steps=[MagicMock(label="ruff-format")],
        )
        mock_step_labels.return_value = ["ruff", "ruff-format", "mypy", "pytest"]
        mock_run_plan.return_value = ValidationReport(
            project_root=Path("/tmp"),
            detected_stacks=["python"],
            passed=False,
            results=[
                ValidationStepResult(
                    stack="python",
                    label="ruff-format",
                    command=["ruff", "format", "--check", "src"],
                    passed=False,
                    returncode=1,
                    stdout_tail="diff",
                    stderr_tail="",
                    reason="format",
                )
            ],
        )

        result = run_quality_gate(
            Path("/tmp"),
            previous_remediation_attempt_count=1,
            max_python_remediation_attempts=1,
        )

        assert result.passed is False
        assert result.remediation_attempted is False
        assert result.remediation_attempt_count == 1
        assert result.remediation_exhausted is True
        assert "ruff-format: FAIL" in result.remediation_failure_reason
        mock_remediate.assert_not_called()


class TestPythonRemediation:
    @patch("src.main.self_improve.quality_gate.run_cmd")
    @patch("src.main.self_improve.quality_gate.command_available")
    def test_runs_deterministic_ruff_fixes(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        attempted, steps = _run_python_remediation(
            Path("/tmp"),
            ["src/dialectic/agents.py", "src/main/cli/entrypoint.py"],
        )

        assert attempted is True
        assert steps == ["ruff-format-fix", "ruff-lint-fix"]
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0].args[0] == [
            "ruff",
            "format",
            "src/dialectic/agents.py",
            "src/main/cli/entrypoint.py",
        ]
        assert mock_run.call_args_list[1].args[0] == [
            "ruff",
            "check",
            "--fix",
            "src/dialectic/agents.py",
            "src/main/cli/entrypoint.py",
        ]

    @patch("src.main.self_improve.quality_gate.command_available")
    def test_skips_when_ruff_unavailable(self, mock_available):
        mock_available.return_value = False

        attempted, steps = _run_python_remediation(
            Path("/tmp"),
            ["src/dialectic/agents.py"],
        )

        assert attempted is False
        assert not steps


class TestTouchedFileCollection:
    @patch("src.main.self_improve.quality_gate_helpers.run_cmd")
    def test_collect_touched_python_files_uses_branch_diff_and_status(self, mock_run):
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="src/dialectic/agents.py\nsrc/README.md\n",
                stderr="",
            ),
            MagicMock(
                returncode=0,
                stdout=" M src/main/cli/entrypoint.py\n?? tests/test_cli_runtime.py\n",
                stderr="",
            ),
        ]

        with patch.object(Path, "exists", return_value=True):
            files = collect_touched_python_files(Path("/tmp"))

        assert files == ["src/dialectic/agents.py", "src/main/cli/entrypoint.py"]
