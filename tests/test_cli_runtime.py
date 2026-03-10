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
