"""Tests for CLI runtime gating and VISION resolution helpers."""

from pathlib import Path

from main.cli import _command_requires_api, _command_requires_vision
from dialectic.vision import ensure_vision_path, get_vision_hash, resolve_project_root


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
