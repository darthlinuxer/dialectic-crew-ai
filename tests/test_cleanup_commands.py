"""Tests for runtime and self-improve cleanup commands."""

from __future__ import annotations

import json

from src.main.cleanup import cli as cleanup_commands
from schemas import SelfImprovementRecord


def test_cmd_clear_runtime_removes_selected_artifacts(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    files = [
        app_root / ".dialectic" / "app.log",
        app_root / ".dialectic" / "app.jsonl",
        app_root / ".dialectic" / "error.log",
        app_root / ".dialectic" / "metrics.db",
        app_root / ".dialectic" / "flows.db",
        app_root / "prd_output" / "default" / "plan.json",
        app_root / "exec_output" / "default" / "report.json",
    ]
    for file_path in files:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("x", encoding="utf-8")

    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_runtime(
        logs=True,
        metrics=False,
        flows=False,
        prd=True,
        exec_output=False,
    )

    assert not (app_root / ".dialectic" / "app.log").exists()
    assert not (app_root / "prd_output").exists()
    assert (app_root / ".dialectic" / "metrics.db").exists()
    assert (app_root / "exec_output").exists()


def test_cmd_clear_runtime_requires_explicit_scope(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    app_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    try:
        cleanup_commands.cmd_clear_runtime()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("expected SystemExit when no runtime scope is selected")


def test_cmd_clear_runtime_dry_run_preserves_files(tmp_path, monkeypatch, capsys):
    app_root = tmp_path / "app"
    artifact = app_root / "prd_output" / "default" / "plan.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_runtime(prd=True, dry_run=True)

    assert artifact.exists()
    assert "Would remove" in capsys.readouterr().out


def test_cmd_clear_self_improve_removes_snapshot_and_linked_execution(
    tmp_path, monkeypatch
):
    app_root = tmp_path / "app"
    snapshot = app_root / ".dialectic" / "self_improve" / "cycle-1.json"
    exec_dir = app_root / "exec_output" / "self" / "run-123"
    exec_report = exec_dir / "report.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    exec_dir.mkdir(parents=True, exist_ok=True)
    exec_report.write_text("{}", encoding="utf-8")
    snapshot.write_text(
        SelfImprovementRecord(
            cycle_id="cycle-1",
            timestamp="2026-03-14T00:00:00Z",
            execution_output_path=str(exec_dir.relative_to(app_root)),
            execution_report_path=str(exec_report.relative_to(app_root)),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_self_improve(
        cycle_id="cycle-1",
        clear_all=False,
        with_linked_exec=True,
    )

    assert not snapshot.exists()
    assert not exec_dir.exists()


def test_cmd_clear_self_improve_without_linked_exec_keeps_execution_artifacts(
    tmp_path, monkeypatch
):
    app_root = tmp_path / "app"
    snapshot = app_root / ".dialectic" / "self_improve" / "cycle-1.json"
    exec_dir = app_root / "exec_output" / "self" / "run-123"
    exec_report = exec_dir / "report.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    exec_dir.mkdir(parents=True, exist_ok=True)
    exec_report.write_text("{}", encoding="utf-8")
    snapshot.write_text(
        SelfImprovementRecord(
            cycle_id="cycle-1",
            timestamp="2026-03-14T00:00:00Z",
            execution_output_path=str(exec_dir.relative_to(app_root)),
            execution_report_path=str(exec_report.relative_to(app_root)),
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_self_improve(cycle_id="cycle-1", clear_all=False)

    assert not snapshot.exists()
    assert exec_dir.exists()


def test_cmd_clear_self_improve_all_removes_all_snapshots_only(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    state_dir = app_root / ".dialectic" / "self_improve"
    first = state_dir / "cycle-1.json"
    second = state_dir / "cycle-2.json"
    state_dir.mkdir(parents=True, exist_ok=True)
    first.write_text(
        json.dumps({"cycle_id": "cycle-1", "timestamp": "2026-03-14T00:00:00Z"}),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps({"cycle_id": "cycle-2", "timestamp": "2026-03-14T01:00:00Z"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_self_improve(cycle_id=None, clear_all=True)

    assert not state_dir.exists()


def test_cmd_clear_self_improve_dry_run_preserves_snapshot(
    tmp_path, monkeypatch, capsys
):
    app_root = tmp_path / "app"
    snapshot = app_root / ".dialectic" / "self_improve" / "cycle-1.json"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        json.dumps({"cycle_id": "cycle-1", "timestamp": "2026-03-14T00:00:00Z"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cleanup_commands, "resolve_app_root", lambda: app_root)

    cleanup_commands.cmd_clear_self_improve(cycle_id="cycle-1", dry_run=True)

    assert snapshot.exists()
    assert "Would remove self-improve snapshot" in capsys.readouterr().out
