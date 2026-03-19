"""Shared helpers for deterministic local verification modules."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _load_json_file(path: Path) -> Any:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _extract_json_payload(raw_text)
        if payload is None:
            raise
        return json.loads(re.sub(r"(?ms)\s*/\*.*?\*/", "", payload))


def _read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _join_verification_notes(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _extract_json_payload(content: str) -> str | None:
    payload_start = next(
        (index for index, char in enumerate(content) if char in "[{"), -1
    )
    if payload_start < 0:
        return None

    opener = content[payload_start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escape = False

    for index in range(payload_start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == opener:
            depth += 1
            continue
        if char == closer:
            depth -= 1
            if depth == 0:
                return content[payload_start : index + 1]

    return None
