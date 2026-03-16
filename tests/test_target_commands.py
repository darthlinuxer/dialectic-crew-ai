"""Tests for target CLI command handlers and routing."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import src.main.cli as cli
import pytest
from src.main.targets import cli as target_commands
from dialectic.target import TargetConfig
from typer.testing import CliRunner


RUNNER = CliRunner()


def _make_target(tmp_path: Path, name: str = "demo") -> TargetConfig:
    repo_root = tmp_path / name
    repo_root.mkdir(parents=True, exist_ok=True)
    return TargetConfig(
        target_path=repo_root,
        set_at=datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
        repo_name=name,
        repo_remote="git@github.com:octo/demo.git",
        vision_path=Path("/tmp/fake-vision.md"),
        target_slug="github-com-octo-demo--abc12345",
    )


class TestTargetCommands:
    def test_cmd_get_target_prints_helpful_message_when_unset(self, monkeypatch, capsys):
        monkeypatch.setattr(target_commands, "get_active_target", lambda: None)

        target_commands.cmd_get_target()

        assert "No target project set." in capsys.readouterr().out

    def test_cmd_get_target_prints_target_details(self, tmp_path, monkeypatch, capsys):
        target_config = _make_target(tmp_path)
        monkeypatch.setattr(target_commands, "get_active_target", lambda: target_config)

        target_commands.cmd_get_target()

        output = capsys.readouterr().out
        assert str(target_config.target_path) in output
        assert target_config.repo_name in output
        assert target_config.repo_remote in output

    def test_cmd_set_target_prints_confirmation(self, tmp_path, monkeypatch, capsys):
        target_config = _make_target(tmp_path)
        monkeypatch.setattr(target_commands, "set_target", lambda path: target_config)

        target_commands.cmd_set_target(str(target_config.target_path))

        output = capsys.readouterr().out
        assert "Active target:" in output
        assert str(target_config.target_path) in output

    def test_cmd_set_target_exits_for_invalid_repo(self, tmp_path, monkeypatch):
        repo_path = tmp_path / "missing"
        monkeypatch.setattr(
            target_commands,
            "set_target",
            lambda path: (_ for _ in ()).throw(ValueError("invalid repo")),
        )

        with pytest.raises(SystemExit):
            target_commands.cmd_set_target(str(repo_path))

    def test_cmd_clear_target_prints_confirmation(self, monkeypatch, capsys):
        called = {"value": False}

        def fake_clear_target():
            called["value"] = True

        monkeypatch.setattr(target_commands, "clear_target", fake_clear_target)

        target_commands.cmd_clear_target()

        assert called["value"] is True
        assert "Target project cleared." in capsys.readouterr().out

    def test_cmd_list_targets_prints_known_targets(self, tmp_path, monkeypatch, capsys):
        target_config = _make_target(tmp_path)
        monkeypatch.setattr(target_commands, "get_active_target", lambda: target_config)
        monkeypatch.setattr(target_commands, "list_known_targets", lambda: [target_config])

        target_commands.cmd_list_targets()

        output = capsys.readouterr().out
        assert "Known targets:" in output
        assert target_config.repo_name in output
        assert "ACTIVE" in output


class TestTargetCliRouting:
    def test_cli_help_lists_target_commands(self):
        result = RUNNER.invoke(cli.app, ["--help"])

        assert result.exit_code == 0
        assert "set-target" in result.stdout
        assert "get-target" in result.stdout
        assert "clear-target" in result.stdout
        assert "list-targets" in result.stdout

    def test_set_target_cli_routes_to_handler(self, tmp_path, monkeypatch):
        captured = {}
        repo_path = tmp_path / "demo"

        monkeypatch.setattr(cli, "cmd_set_target", lambda path: captured.setdefault("path", path))

        result = RUNNER.invoke(cli.app, ["set-target", str(repo_path)])

        assert result.exit_code == 0
        assert captured["path"] == str(repo_path)

    def test_get_target_cli_routes_to_handler(self, monkeypatch):
        captured = {"called": False}

        def fake_get_target():
            captured["called"] = True

        monkeypatch.setattr(cli, "cmd_get_target", fake_get_target)

        result = RUNNER.invoke(cli.app, ["get-target"])

        assert result.exit_code == 0
        assert captured["called"] is True
