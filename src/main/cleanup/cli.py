"""CLI command handlers for runtime cleanup helpers."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from schemas import SelfImprovementRecord

from dialectic.vision import resolve_app_root

from ..self_improve.persistence import SELF_IMPROVE_STATE_DIR


def _remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _describe_action(path: Path, *, dry_run: bool) -> str:
    return f"Would remove: {path}" if dry_run else f"- {path}"


def _selected_runtime_paths(app_root: Path, selections: dict[str, bool]) -> list[Path]:
    paths: list[Path] = []
    if selections["logs"]:
        paths.extend(
            [
                app_root / ".dialectic" / "app.log",
                app_root / ".dialectic" / "app.jsonl",
                app_root / ".dialectic" / "error.log",
            ]
        )
    if selections["metrics"]:
        paths.append(app_root / ".dialectic" / "metrics.db")
    if selections["flows"]:
        paths.append(app_root / ".dialectic" / "flows.db")
    if selections["prd"]:
        paths.append(app_root / "prd_output")
    if selections["exec_output"]:
        paths.append(app_root / "exec_output")
    return paths


def cmd_clear_runtime(
    *,
    logs: bool = False,
    metrics: bool = False,
    flows: bool = False,
    prd: bool = False,
    exec_output: bool = False,
    dry_run: bool = False,
) -> None:
    """Clear selected runtime artifacts from the app-owned workspace state."""
    app_root = resolve_app_root()
    selections = {
        "logs": logs,
        "metrics": metrics,
        "flows": flows,
        "prd": prd,
        "exec_output": exec_output,
    }
    if not any(selections.values()):
        print("Select at least one runtime scope or use --all.")
        sys.exit(1)

    selected_paths = _selected_runtime_paths(app_root, selections)
    removed = [
        path
        for path in selected_paths
        if (path.exists() if dry_run else _remove_path(path))
    ]

    if removed:
        print("Runtime artifacts to remove:" if dry_run else "Removed runtime artifacts:")
        for path in removed:
            print(_describe_action(path, dry_run=dry_run))
    else:
        if dry_run:
            print("No matching runtime artifacts would be removed.")
        else:
            print("No matching runtime artifacts found.")


def _linked_paths(app_root: Path, record: SelfImprovementRecord) -> list[Path]:
    linked: list[Path] = []
    for raw in (record.execution_output_path, record.execution_report_path):
        if not raw:
            continue
        path = Path(raw)
        linked.append(path if path.is_absolute() else (app_root / path))
    return linked


def cmd_clear_self_improve(
    *,
    cycle_id: str | None,
    clear_all: bool = False,
    dry_run: bool = False,
    with_linked_exec: bool = False,
) -> None:
    """Clear one or all persisted self-improve snapshots and linked artifacts."""
    app_root = resolve_app_root()
    state_dir = app_root / SELF_IMPROVE_STATE_DIR
    if clear_all:
        if dry_run:
            if state_dir.exists():
                print(f"Would remove self-improve state: {state_dir}")
            else:
                print("No self-improve snapshots found.")
        elif _remove_path(state_dir):
            print(f"Removed self-improve state: {state_dir}")
        else:
            print("No self-improve snapshots found.")
        return

    if not cycle_id:
        print("Provide a cycle ID or use --all.")
        sys.exit(1)

    snapshot = state_dir / f"{cycle_id}.json"
    if not snapshot.exists():
        print(f"Self-improve snapshot not found: {snapshot}")
        sys.exit(1)

    record = SelfImprovementRecord.model_validate_json(
        snapshot.read_text(encoding="utf-8")
    )
    linked_paths = _linked_paths(app_root, record) if with_linked_exec else []
    if dry_run:
        print(f"Would remove self-improve snapshot: {snapshot}")
        for path in linked_paths:
            print(f"Would remove linked execution artifact: {path}")
        return

    for path in linked_paths:
        _remove_path(path)
    _remove_path(snapshot)
    print(f"Removed self-improve snapshot: {snapshot}")

