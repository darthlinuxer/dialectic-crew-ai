"""Tests for CLI runtime gating and VISION resolution helpers."""

from pathlib import Path

import main.cli as cli
import pytest

from main.cli import _command_requires_api, _command_requires_vision
from dialectic.vision import (
    VisionContext,
    ensure_vision_path,
    get_vision_hash,
    get_vision_path,
    resolve_project_root,
)


class TestCliRequirementRouting:
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

    def test_prd_resume_requires_existing_persisted_flow(self, monkeypatch):
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)
        monkeypatch.setattr(cli, "get_prd_resume_state", lambda flow_id: None)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "prd", "--resume", "missing-flow"])

        with pytest.raises(SystemExit):
            cli.main()

    def test_cmd_prd_requires_feature_when_not_resuming(self, monkeypatch):
        monkeypatch.setattr("main.cli_commands.run_dialectic_flow", lambda *args, **kwargs: None)

        with pytest.raises(SystemExit):
            cli.cmd_prd(None, resume_id=None)

    def test_execute_resume_run_passes_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_execute(plan_path, spec_only=False, vision_context=VisionContext.PROJECT, resume_run_id=None):
            captured["plan_path"] = plan_path
            captured["resume_run_id"] = resume_run_id

        monkeypatch.setattr(cli, "cmd_execute", fake_cmd_execute)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "execute", "--resume-run", "run-123"])

        cli.main()

        assert captured["plan_path"] == "--latest"
        assert captured["resume_run_id"] == "run-123"

    def test_self_improve_resume_passes_cycle_id_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_self_improve(
            dry_run=False,
            max_improvements=1,
            stash_dirty=False,
            resume_cycle_id=None,
            list_resumable=False,
        ):
            captured["dry_run"] = dry_run
            captured["max_improvements"] = max_improvements
            captured["stash_dirty"] = stash_dirty
            captured["resume_cycle_id"] = resume_cycle_id
            captured["list_resumable"] = list_resumable

        monkeypatch.setattr(cli, "cmd_self_improve", fake_cmd_self_improve)
        monkeypatch.setattr(
            cli.sys,
            "argv",
            ["dialectic-crew", "self-improve", "--resume", "cycle-123", "--max", "2"],
        )

        cli.main()

        assert captured == {
            "dry_run": False,
            "max_improvements": 2,
            "stash_dirty": False,
            "resume_cycle_id": "cycle-123",
            "list_resumable": False,
        }

    def test_self_improve_list_resumable_passes_flag_through(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "_check_api_key", lambda: True)
        monkeypatch.setattr(cli, "_check_vision_exists", lambda *args, **kwargs: None)

        def fake_cmd_self_improve(
            dry_run=False,
            max_improvements=1,
            stash_dirty=False,
            resume_cycle_id=None,
            list_resumable=False,
        ):
            captured["list_resumable"] = list_resumable
            captured["resume_cycle_id"] = resume_cycle_id

        monkeypatch.setattr(cli, "cmd_self_improve", fake_cmd_self_improve)
        monkeypatch.setattr(cli.sys, "argv", ["dialectic-crew", "self-improve", "--list-resumable"])

        cli.main()

        assert captured == {
            "list_resumable": True,
            "resume_cycle_id": None,
        }


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
