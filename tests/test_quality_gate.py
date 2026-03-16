"""Tests for the quality gate module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.main.self_improve.quality_gate import (
    QualityCheckResult,
    QualityGateResult,
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


class TestMypyCheck:
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
    @patch("src.main.self_improve.quality_gate._run_pyright")
    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_all_checks_pass(
        self, mock_ruff, mock_format, mock_mypy, mock_pyright
    ):
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=True)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)
        mock_pyright.return_value = QualityCheckResult(tool="pyright", passed=True)

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is True
        assert len(result.checks) == 4

    @patch("src.main.self_improve.quality_gate._run_pyright")
    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_one_check_fails(
        self, mock_ruff, mock_format, mock_mypy, mock_pyright
    ):
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=False, error_count=1)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)
        mock_pyright.return_value = QualityCheckResult(tool="pyright", passed=True)

        result = run_quality_gate(Path("/tmp"))
        assert result.passed is False

    @patch("src.main.self_improve.quality_gate._run_mypy")
    @patch("src.main.self_improve.quality_gate._run_ruff_format_check")
    @patch("src.main.self_improve.quality_gate._run_ruff_check")
    def test_exclude_pyright(self, mock_ruff, mock_format, mock_mypy):
        mock_ruff.return_value = QualityCheckResult(tool="ruff-lint", passed=True)
        mock_format.return_value = QualityCheckResult(tool="ruff-format", passed=True)
        mock_mypy.return_value = QualityCheckResult(tool="mypy", passed=True)

        result = run_quality_gate(Path("/tmp"), include_pyright=False)
        assert result.passed is True
        assert len(result.checks) == 3
