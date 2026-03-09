from __future__ import annotations

import hashlib
import os
from pathlib import Path


_ENV_PROJECT_ROOT = "DIALECTIC_PROJECT_ROOT"
_VISION_RELATIVE_PATH = Path("knowledge") / "VISION.md"


def _search_lineage(start: Path) -> list[Path]:
    return [start, *start.parents]


def _find_first_matching(candidates: list[Path], predicate) -> Path | None:
    for candidate in candidates:
        if predicate(candidate):
            return candidate
    return None


def resolve_project_root() -> Path:
    env_root = os.getenv(_ENV_PROJECT_ROOT)
    if env_root:
        env_path = Path(env_root).expanduser().resolve()
        if env_path.exists():
            return env_path

    cwd_candidates = _search_lineage(Path.cwd().resolve())
    module_candidates = _search_lineage(Path(__file__).resolve().parent)

    for candidates in (cwd_candidates, module_candidates):
        exact = _find_first_matching(
            candidates,
            lambda candidate: (candidate / "pyproject.toml").exists()
            and (candidate / _VISION_RELATIVE_PATH).exists(),
        )
        if exact is not None:
            return exact

        project_root = _find_first_matching(
            candidates,
            lambda candidate: (candidate / "pyproject.toml").exists(),
        )
        if project_root is not None:
            return project_root

        vision_root = _find_first_matching(
            candidates,
            lambda candidate: (candidate / _VISION_RELATIVE_PATH).exists(),
        )
        if vision_root is not None:
            return vision_root

    return Path.cwd().resolve()


def get_vision_path() -> Path:
    return resolve_project_root() / _VISION_RELATIVE_PATH


def ensure_vision_path() -> Path:
    vision_path = get_vision_path()
    if not vision_path.exists():
        raise FileNotFoundError(
            f"knowledge/VISION.md not found. Expected at: {vision_path}"
        )
    return vision_path


def prepare_vision_runtime() -> Path:
    project_root = resolve_project_root()
    if Path.cwd().resolve() != project_root:
        os.chdir(project_root)
    return ensure_vision_path()


def get_vision_hash() -> str | None:
    try:
        content = ensure_vision_path().read_text(encoding="utf-8")
    except OSError:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
