"""Tests for the quality gate module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.main.self_improve.quality_gate import (
    QualityCheckResult,
    QualityGateResult,
    _build_mypy_command,
    _collect_touched_python_files,
    _run_mypy,
    _run_ruff_check,
    _run_ruff_format_check,
    _run_pyright,
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
        assert result.errors == []


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


class TestRuffCheck:
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_ruff_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_ruff_check(Path("/tmp"))
        assert result.passed is True
        assert "not available" in result.output

    @patch("src.main.self_improve.quality_gate._command_available")
    def test_target_path_missing(self, mock_available):
        mock_available.return_value = True
        result = _run_ruff_check(Path("/nonexistent"), "src/")
        assert result.passed is True
        assert "does not exist" in result.output

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
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

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_ruff_fails_with_errors(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='[{"filename": "test.py", "location": {"row": 1}, "code": "E501", "message": "line too long"}]',
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_check(Path("/tmp"), "src/")
        assert result.passed is False
        assert result.error_count == 1
        assert len(result.errors) == 1

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
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
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_ruff_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_ruff_format_check(Path("/tmp"))
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_format_passes(self, mock_available, mock_run):
        mock_available.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(Path, "exists", return_value=True):
            result = _run_ruff_format_check(Path("/tmp"), "src/")
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
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

    @patch("src.main.self_improve.quality_gate._command_available")
    def test_format_skips_when_no_touched_python_files(self, mock_available):
        mock_available.return_value = True

        result = _run_ruff_format_check(Path("/tmp"), touched_files=[])

        assert result.passed is True
        assert "No touched Python source files" in result.output


class TestMypyCheck:
    def test_build_mypy_command_uses_explicit_package_bases(self):
        command = _build_mypy_command(
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

    @patch("src.main.self_improve.quality_gate._command_available")
    def test_mypy_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_mypy(Path("/tmp"))
        assert result.passed is True

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
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

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
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


class TestPyrightCheck:
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_pyright_not_available(self, mock_available):
        mock_available.return_value = False
        result = _run_pyright(Path("/tmp"))
        assert result.passed is True  # pyright is warn-only

    @patch("src.main.self_improve.quality_gate._run_cmd")
    @patch("src.main.self_improve.quality_gate._command_available")
    def test_pyright_always_passes(self, mock_available, mock_run):
        """Pyright is warn-only, so it should always pass."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='{"generalDiagnostics": [{"severity": 1, "message": "error", "file": "test.py", "range": {"start": {"line": 1}}}]}',
            stderr="",
        )
        with patch.object(Path, "exists", return_value=True):
            result = _run_pyright(Path("/tmp"), "src/")
        assert result.passed is True  # warn-only
        assert result.error_count == 1


class TestRunQualityGate:
    @patch("src.main.self_improve.quality_gate._collect_touched_python_files")
    @patch("src.main.self_improve.quality_gate._run_pyright")
    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_all_checks_pass(
        self, mock_ruff, mock_format, mock_mypy, mock_pyright, mock_collect
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=True)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)
        mock_pyright.return_value = QualityCheckResult(tool="pyright", passed=True)

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is True
        assert len(result.checks) == 4
        mock_ruff.assert_called_once_with(
            Path("/tmp"),
            "src/",
            touched_files=["src/dialectic/agents.py"],
        )

    @patch("src.main.self_improve.quality_gate._collect_touched_python_files")
    @patch("src.main.self_improve.quality_gate._run_pyright")
    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_one_check_fails(
        self, mock_ruff, mock_format, mock_mypy, mock_pyright, mock_collect
    ):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=False, error_count=1)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)
        mock_pyright.return_value = QualityCheckResult(tool="pyright", passed=True)

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is False

    @patch("src.main.self_improve.quality_gate._collect_touched_python_files")
    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_exclude_pyright(self, mock_ruff, mock_format, mock_mypy, mock_collect):
        mock_collect.return_value = ["src/dialectic/agents.py"]
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=True)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)

        result = run_quality_gate(Path("/tmp"), include_pyright=False)
        assert result.passed is True
        assert len(result.checks) == 3


class TestTouchedFileCollection:
    @patch("src.main.self_improve.quality_gate._run_cmd")
    def test_collect_touched_python_files_uses_branch_diff_and_status(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="src/dialectic/agents.py\nsrc/README.md\n", stderr=""),
            MagicMock(returncode=0, stdout=" M src/main/cli/entrypoint.py\n?? tests/test_cli_runtime.py\n", stderr=""),
        ]

        with patch.object(Path, "exists", return_value=True):
            files = _collect_touched_python_files(Path("/tmp"))

        assert files == ["src/dialectic/agents.py", "src/main/cli/entrypoint.py"]
