"""Tests for make-vision command handling and CLI wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import src.main.cli as cli
from dialectic.repo_analyzer import RepoAnalysis
from dialectic.target import TargetConfig
from src.main.vision import cli as vision_commands
from typer.testing import CliRunner


RUNNER = CliRunner()


def _analysis(repo_root: Path) -> RepoAnalysis:
    return RepoAnalysis(
        repo_root=repo_root,
        repo_name=repo_root.name,
        about_summary="A generated vision summary.",
        business_objectives=["Keep the project aligned"],
        design_principles=["Simplicity first"],
        main_modules=["src/app"],
        integrations=["External: none detected"],
        runtime="Python 3.x",
        framework="FastAPI",
        database="TBD",
        performance_notes="Define performance targets.",
        security_notes="Define security requirements.",
        scalability_notes="Define scaling expectations.",
        source_documents=["README.md"],
    )


def _target_config(tmp_path: Path) -> TargetConfig:
    target_root = tmp_path / "target-repo"
    target_root.mkdir(parents=True, exist_ok=True)
    return TargetConfig(
        target_path=target_root,
        set_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
        repo_name="target-repo",
        repo_remote="git@github.com:octo/target-repo.git",
        vision_path=tmp_path
        / "knowledge"
        / "target"
        / "github-com-octo-target-repo--abc12345"
        / "VISION.md",
        target_slug="github-com-octo-target-repo--abc12345",
    )


class TestMakeVisionCommands:
    def test_cmd_make_vision_requires_target_when_not_self(self, monkeypatch):
        monkeypatch.setattr(vision_commands, "get_active_target", lambda: None)

        with pytest.raises(SystemExit):
            vision_commands.cmd_make_vision(output_path=None, self_mode=False)

    def test_cmd_make_vision_writes_target_vision_by_default(
        self, tmp_path, monkeypatch, capsys
    ):
        target_config = _target_config(tmp_path)

        def fake_analysis(repo_root: Path) -> RepoAnalysis:
            return _analysis(repo_root)

        monkeypatch.setattr(vision_commands, "get_active_target", lambda: target_config)
        monkeypatch.setattr(vision_commands, "analyze_repository", fake_analysis)
        monkeypatch.setattr(
            vision_commands,
            "generate_vision_markdown",
            lambda analysis: "# Generated Vision\n",
        )
        monkeypatch.setattr(vision_commands, "resolve_app_root", lambda: tmp_path)

        vision_commands.cmd_make_vision(output_path=None, self_mode=False)

        output = capsys.readouterr().out
        assert "Vision saved:" in output
        assert target_config.vision_path is not None
        assert (
            target_config.vision_path.read_text(encoding="utf-8")
            == "# Generated Vision\n"
        )


class TestMakeVisionCli:
    def test_cli_help_lists_make_vision(self):
        result = RUNNER.invoke(cli.app, ["--help"])

        assert result.exit_code == 0
        assert "make-vision" in result.stdout

    def test_cli_make_vision_routes_to_handler(self, monkeypatch):
        captured = {}

        def fake_cmd_make_vision(*, output_path=None, self_mode=False):
            captured["output_path"] = output_path
            captured["self_mode"] = self_mode

        monkeypatch.setattr(cli, "cmd_make_vision", fake_cmd_make_vision)

        result = RUNNER.invoke(
            cli.app, ["make-vision", "--self", "--output", "/tmp/out.md"]
        )

        assert result.exit_code == 0
        assert captured == {"output_path": "/tmp/out.md", "self_mode": True}
