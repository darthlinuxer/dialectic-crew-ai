"""Tests for CLI runtime gating, logging bootstrap, and VISION helpers."""

# pylint: disable=missing-class-docstring,missing-function-docstring,too-many-public-methods
# pylint: disable=too-many-arguments,too-many-positional-arguments
# pylint: disable=consider-using-from-import,wrong-import-order,line-too-long

from pathlib import Path

import src.main.cli as cli
import pytest
from typer.testing import CliRunner

from src.main.cli import _command_requires_api, _command_requires_vision
from dialectic.vision import (
    VisionContext,
    ensure_vision_path,
    get_vision_hash,
    get_vision_path,
    resolve_project_root,
)


RUNNER = CliRunner()


class TestCliRequirementRouting:
    def test_typer_help_lists_core_commands(self):
        result = RUNNER.invoke(cli.app, ["--help"])

        assert result.exit_code == 0
        assert "prd" in result.stdout
        assert "plan" in result.stdout
        assert "execute" in result.stdout
        assert "self-improve" in result.stdout
        assert "--install-completion" not in result.stdout
        assert "--show-completion" not in result.stdout

    def test_help_command_uses_modern_help_surface(self):
        modern_help = RUNNER.invoke(cli.app, ["--help"])
        help_command = RUNNER.invoke(cli.app, ["help"])

        assert modern_help.exit_code == 0
        assert help_command.exit_code == 0
        assert "Modern typed CLI for Dialectic Crew AI workflows" in help_command.stdout
        assert "Commands:" not in help_command.stdout
        assert "prd" in help_command.stdout
        assert "Generate or resume a PRD workflow" in help_command.stdout

    def test_clear_runtime_requires_scope_or_all(self):
        result = RUNNER.invoke(cli.app, ["clear-runtime"])

        assert result.exit_code == 1
        assert "Select at least one runtime scope or use --all" in result.stdout

    def test_clear_self_improve_help_mentions_linked_exec_flag(self):
        result = RUNNER.invoke(cli.app, ["clear-self-improve", "--help"])

        assert result.exit_code == 0
        assert "--with-linked-exec" in result.stdout
        assert "--dry-run" in result.stdout

    def test_prd_help_includes_examples(self):
        result = RUNNER.invoke(cli.app, ["prd", "--help"])

        assert result.exit_code == 0
        assert 'uv run dialectic-crew prd "Login with 2FA"' in result.stdout
        assert "uv run dialectic-crew prd --resume flow-123" in result.stdout

    def test_execute_help_includes_examples(self):
        result = RUNNER.invoke(cli.app, ["execute", "--help"])

        assert result.exit_code == 0
        assert "uv run dialectic-crew execute --latest" in result.stdout
        assert "uv run dialectic-crew execute --resume-run 20260310_120000" in result.stdout

    def test_status_does_not_require_api(self):
        assert _command_requires_api("status", ["status"]) is False

    def test_mark_does_not_require_api(self):
        assert _command_requires_api("mark", ["mark", "T-001", "completed"]) is False

    def test_execute_spec_only_does_not_require_api(self):
        assert _command_requires_api("execute", ["execute", "--spec-only"]) is False

    def test_execute_full_requires_api(self):
        assert _command_requires_api("execute", ["execute"]) is True

    def test_verify_requires_vision(self):
        assert _command_requires_vision("verify", ["verify", "T-001"]) is True

    def test_status_does_not_require_vision(self):
        assert _command_requires_vision("status", ["status"]) is False

    def test_main_disables_crewai_telemetry_by_default(self, monkeypatch):
        monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "status"])
        monkeypatch.setattr(cli, "cmd_status", lambda plan_path: None)

        cli.main()

        assert cli.os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"

    def test_main_respects_existing_telemetry_override(self, monkeypatch):
        monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "false")
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "status"])
        monkeypatch.setattr(cli, "cmd_status", lambda plan_path: None)

        cli.main()

        assert cli.os.environ["CREWAI_DISABLE_TELEMETRY"] == "false"

    def test_main_bootstraps_application_logging(self, monkeypatch):
        calls: list[str] = []
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "status"])
        monkeypatch.setattr(cli, "configure_application_logging", lambda: calls.append("logging"))
        monkeypatch.setattr(cli, "register_crewai_event_logger", lambda: calls.append("events"))
        monkeypatch.setattr(cli, "new_correlation_id", lambda: "corr-123")
        monkeypatch.setattr(cli, "cmd_status", lambda plan_path: calls.append("status"))

        cli.main()

        assert calls[:2] == ["logging", "events"]
        assert calls[-1] == "status"

    def test_plan_help_mentions_self_mode(self):
        result = RUNNER.invoke(cli.app, ["plan", "--help"])

        assert result.exit_code == 0
        assert "internal/SELF_VISION.md" in result.stdout
        assert "uv run dialectic-crew plan --self --latest US-01" in result.stdout

    def test_prd_resume_requires_existing_persisted_flow(self, monkeypatch):
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)
        monkeypatch.setattr(cli, "get_prd_resume_state", lambda flow_id: None)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "prd", "--resume", "missing-flow"])

        with pytest.raises(SystemExit):
            cli.main()

    def test_cmd_prd_requires_feature_when_not_resuming(self, monkeypatch):
        monkeypatch.setattr("src.main.cli_commands.run_dialectic_flow", lambda *args, **kwargs: None)

        with pytest.raises(SystemExit):
            cli.cmd_prd(None, resume_id=None)

    def test_cmd_prd_passes_max_retries_override(self, monkeypatch):
        captured = {}

        def fake_run_dialectic_flow(
            feature_request,
            *,
            file_paths=None,
            vision_context=VisionContext.PROJECT,
            resume_id=None,
            max_retries=None,
            consensus_min_score=None,
        ):
            captured["feature_request"] = feature_request
            captured["file_paths"] = file_paths
            captured["vision_context"] = vision_context
            captured["resume_id"] = resume_id
            captured["max_retries"] = max_retries
            captured["consensus_min_score"] = consensus_min_score
            return {
                "flow_id": "flow-123",
                "quality_score": 8.5,
                "iterations": 3,
                "consensus_reached": False,
            }

        monkeypatch.setattr("src.main.cli_commands.run_dialectic_flow", fake_run_dialectic_flow)

        cli.cmd_prd("Ship resilient PRD validation", max_retries=6)

        assert captured["max_retries"] == 6

    def test_cmd_prd_passes_consensus_min_score_override(self, monkeypatch):
        captured = {}

        def fake_run_dialectic_flow(
            feature_request,
            *,
            file_paths=None,
            vision_context=VisionContext.PROJECT,
            resume_id=None,
            max_retries=None,
            consensus_min_score=None,
        ):
            captured["feature_request"] = feature_request
            captured["file_paths"] = file_paths
            captured["vision_context"] = vision_context
            captured["resume_id"] = resume_id
            captured["max_retries"] = max_retries
            captured["consensus_min_score"] = consensus_min_score
            return {
                "flow_id": "flow-123",
                "quality_score": 8.7,
                "iterations": 2,
                "consensus_reached": True,
            }

        monkeypatch.setattr("src.main.cli_commands.run_dialectic_flow", fake_run_dialectic_flow)

        cli.cmd_prd("Ship resilient PRD validation", consensus_min_score=8.5)

        assert captured["consensus_min_score"] == 8.5

    def test_execute_resume_run_passes_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_execute(plan_path, spec_only=False, vision_context=VisionContext.PROJECT, resume_run_id=None):
            del spec_only, vision_context
            captured["plan_path"] = plan_path
            captured["resume_run_id"] = resume_run_id

        monkeypatch.setattr(cli, "cmd_execute", fake_cmd_execute)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "execute", "--resume-run", "run-123"])

        cli.main()

        assert captured["plan_path"] == "--latest"
        assert captured["resume_run_id"] == "run-123"

    def test_execute_self_passes_self_vision_context_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_execute(
            plan_path,
            spec_only=False,
            vision_context=VisionContext.PROJECT,
            resume_run_id=None,
        ):
            del spec_only, resume_run_id
            captured["plan_path"] = plan_path
            captured["vision_context"] = vision_context

        monkeypatch.setattr(cli, "cmd_execute", fake_cmd_execute)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "execute", "--latest", "--self"],
        )

        cli.main()

        assert captured == {
            "plan_path": "--latest",
            "vision_context": VisionContext.SELF,
        }

    def test_plan_latest_passes_story_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_plan(prd_path, us_ref, vision_context=VisionContext.PROJECT):
            captured["prd_path"] = prd_path
            captured["us_ref"] = us_ref
            captured["vision_context"] = vision_context

        monkeypatch.setattr(cli, "cmd_plan", fake_cmd_plan)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "plan", "--latest", "US-01"])

        cli.main()

        assert captured == {
            "prd_path": None,
            "us_ref": "US-01",
            "vision_context": VisionContext.PROJECT,
        }

    def test_plan_single_story_argument_uses_latest_prd(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_plan(prd_path, us_ref, vision_context=VisionContext.PROJECT):
            captured["prd_path"] = prd_path
            captured["us_ref"] = us_ref
            captured["vision_context"] = vision_context

        monkeypatch.setattr(cli, "cmd_plan", fake_cmd_plan)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "plan", "US-01"])

        cli.main()

        assert captured == {
            "prd_path": None,
            "us_ref": "US-01",
            "vision_context": VisionContext.PROJECT,
        }

    def test_prd_max_retries_passes_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_prd(
            feature_request,
            file_paths=None,
            vision_context=VisionContext.PROJECT,
            resume_id=None,
            max_retries=None,
            consensus_min_score=None,
        ):
            captured["feature_request"] = feature_request
            captured["file_paths"] = file_paths
            captured["vision_context"] = vision_context
            captured["resume_id"] = resume_id
            captured["max_retries"] = max_retries
            captured["consensus_min_score"] = consensus_min_score

        monkeypatch.setattr(cli, "cmd_prd", fake_cmd_prd)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            [
                "dialectic-crew",
                "prd",
                "Harden memory",
                "--max-retries",
                "6",
                "--self",
            ],
        )

        cli.main()

        assert captured == {
            "feature_request": "Harden memory",
            "file_paths": None,
            "vision_context": VisionContext.SELF,
            "resume_id": None,
            "max_retries": 6,
            "consensus_min_score": None,
        }

    def test_prd_consensus_min_score_passes_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_prd(
            feature_request,
            file_paths=None,
            vision_context=VisionContext.PROJECT,
            resume_id=None,
            max_retries=None,
            consensus_min_score=None,
        ):
            captured["feature_request"] = feature_request
            captured["file_paths"] = file_paths
            captured["vision_context"] = vision_context
            captured["resume_id"] = resume_id
            captured["max_retries"] = max_retries
            captured["consensus_min_score"] = consensus_min_score

        monkeypatch.setattr(cli, "cmd_prd", fake_cmd_prd)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            [
                "dialectic-crew",
                "prd",
                "Harden memory",
                "--consensus-min-score",
                "8.5",
                "--self",
            ],
        )

        cli.main()

        assert captured == {
            "feature_request": "Harden memory",
            "file_paths": None,
            "vision_context": VisionContext.SELF,
            "resume_id": None,
            "max_retries": None,
            "consensus_min_score": 8.5,
        }

    def test_prd_consensus_min_score_requires_float_in_range(self, monkeypatch):
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "prd", "Harden memory", "--consensus-min-score", "11"],
        )

        with pytest.raises(SystemExit):
            cli.main()

    def test_prd_max_retries_requires_positive_integer(self, monkeypatch):
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "prd", "Harden memory", "--max-retries", "0"],
        )

        with pytest.raises(SystemExit):
            cli.main()

    def test_self_improve_resume_passes_cycle_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_self_improve(
            simulate=False,
            max_improvements=1,
            stash_dirty=False,
            resume_cycle_id=None,
            list_resumable=False,
            skip_baseline_tests=False,
        ):
            captured["simulate"] = simulate
            captured["max_improvements"] = max_improvements
            captured["stash_dirty"] = stash_dirty
            captured["resume_cycle_id"] = resume_cycle_id
            captured["list_resumable"] = list_resumable
            captured["skip_baseline_tests"] = skip_baseline_tests

        monkeypatch.setattr(cli, "cmd_self_improve", fake_cmd_self_improve)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "self-improve", "--resume", "cycle-123"],
        )

        cli.main()

        assert captured == {
            "simulate": False,
            "max_improvements": 1,
            "stash_dirty": False,
            "resume_cycle_id": "cycle-123",
            "list_resumable": False,
            "skip_baseline_tests": False,
        }

    def test_self_improve_rejects_max_greater_than_one(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "self-improve", "--max", "2"],
        )

        with pytest.raises(SystemExit):
            cli.main()

        err = capsys.readouterr().err
        assert "only supports --max 1" in err

    def test_self_improve_list_resumable_passes_flag_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_self_improve(
            simulate=False,
            max_improvements=1,
            stash_dirty=False,
            resume_cycle_id=None,
            list_resumable=False,
            skip_baseline_tests=False,
        ):
            del simulate, max_improvements, stash_dirty, skip_baseline_tests
            captured["list_resumable"] = list_resumable
            captured["resume_cycle_id"] = resume_cycle_id

        monkeypatch.setattr(cli, "cmd_self_improve", fake_cmd_self_improve)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "self-improve", "--list-resumable"])

        cli.main()

        assert captured == {
            "list_resumable": True,
            "resume_cycle_id": None,
        }

    def test_self_improve_skip_baseline_tests_passes_flag_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_self_improve(
            simulate=False,
            max_improvements=1,
            stash_dirty=False,
            resume_cycle_id=None,
            list_resumable=False,
            skip_baseline_tests=False,
        ):
            del simulate, max_improvements, stash_dirty, resume_cycle_id, list_resumable
            captured["skip_baseline_tests"] = skip_baseline_tests

        monkeypatch.setattr(cli, "cmd_self_improve", fake_cmd_self_improve)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "self-improve", "--skip-baseline-tests"],
        )

        cli.main()

        assert captured == {"skip_baseline_tests": True}


class TestVisionResolution:
    def test_resolve_project_root_from_nested_directory(self, tmp_path, monkeypatch):
        project = tmp_path / "demo"
        nested = project / "src" / "pkg"
        nested.mkdir(parents=True)
        (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        (project / "knowledge").mkdir()
        (project / "knowledge" / "VISION.md").write_text("Vision", encoding="utf-8")

        monkeypatch.chdir(nested)

        assert resolve_project_root() == project
        assert ensure_vision_path() == project / "knowledge" / "VISION.md"

    def test_vision_hash_reads_from_knowledge_directory(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        (tmp_path / "knowledge").mkdir()
        vision_path = tmp_path / "knowledge" / "VISION.md"
        vision_path.write_text("Vision hash content", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        assert get_vision_hash() is not None

    def test_missing_vision_raises_with_expected_path(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        try:
            ensure_vision_path()
        except FileNotFoundError as exc:
            assert str(Path("knowledge") / "VISION.md") in str(exc)
        else:
            raise AssertionError("Expected ensure_vision_path to raise FileNotFoundError")


class TestVisionContextSelf:
    """Tests for VisionContext.SELF (internal/SELF_VISION.md)."""

    @staticmethod
    def _setup_dual_vision(root: Path) -> None:
        (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
        (root / "knowledge").mkdir()
        (root / "knowledge" / "VISION.md").write_text("User Vision", encoding="utf-8")
        (root / "internal").mkdir()
        (root / "internal" / "SELF_VISION.md").write_text("Self Vision", encoding="utf-8")

    def test_vision_context_self_path(self, tmp_path, monkeypatch):
        """VisionContext.SELF resolves to internal/SELF_VISION.md."""
        self._setup_dual_vision(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert get_vision_path(VisionContext.PROJECT) == tmp_path / "knowledge" / "VISION.md"
        assert get_vision_path(VisionContext.SELF) == tmp_path / "internal" / "SELF_VISION.md"

    def test_ensure_vision_path_self(self, tmp_path, monkeypatch):
        """ensure_vision_path returns correct content for each context."""
        self._setup_dual_vision(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert ensure_vision_path(VisionContext.PROJECT).read_text(encoding="utf-8") == "User Vision"
        assert ensure_vision_path(VisionContext.SELF).read_text(encoding="utf-8") == "Self Vision"

    def test_vision_hash_differs_by_context(self, tmp_path, monkeypatch):
        """Different vision documents produce different hashes."""
        self._setup_dual_vision(tmp_path)
        monkeypatch.chdir(tmp_path)

        project_hash = get_vision_hash(VisionContext.PROJECT)
        self_hash = get_vision_hash(VisionContext.SELF)

        assert project_hash is not None
        assert self_hash is not None
        assert project_hash != self_hash

    def test_ensure_vision_self_missing(self, tmp_path, monkeypatch):
        """ensure_vision_path raises when internal/SELF_VISION.md is missing."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
        (tmp_path / "knowledge").mkdir()
        (tmp_path / "knowledge" / "VISION.md").write_text("User Vision", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(FileNotFoundError, match="SELF_VISION.md"):
            ensure_vision_path(VisionContext.SELF)

    def test_get_vision_hash_self_missing_returns_none(self, tmp_path, monkeypatch):
        """get_vision_hash returns None when the SELF vision file is absent."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
        (tmp_path / "knowledge").mkdir()
        (tmp_path / "knowledge" / "VISION.md").write_text("User Vision", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        assert get_vision_hash(VisionContext.PROJECT) is not None
        assert get_vision_hash(VisionContext.SELF) is None
