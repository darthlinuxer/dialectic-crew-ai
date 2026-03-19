"""Target project persistence and resolution helpers."""

# pylint: disable=trailing-newlines

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from dialectic.vision import resolve_app_root


_ACTIVE_TARGET_PATH = Path(".dialectic") / "target.json"
_TARGET_REGISTRY_PATH = Path(".dialectic") / "targets.json"
_DEFAULT_PROJECT_VISION = Path("knowledge") / "VISION.md"
_TARGET_VISION_DIR = Path("knowledge") / "target"
_SLUG_SEPARATOR = "--"


@dataclass(frozen=True)
class GitTargetInfo:
    """Normalized Git metadata for a target repository."""

    repo_root: Path
    remote_url: str | None


@dataclass(frozen=True)
class TargetConfig:
    """Persisted configuration for a known target repository."""

    target_path: Path
    set_at: datetime
    repo_name: str
    repo_remote: str | None
    vision_path: Path | None
    target_slug: str


def _resolve_app_root() -> Path:
    return resolve_app_root()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _active_target_file(app_root: Path) -> Path:
    return app_root / _ACTIVE_TARGET_PATH


def _target_registry_file(app_root: Path) -> Path:
    return app_root / _TARGET_REGISTRY_PATH


def _normalize_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )


def _probe_git_repository(path: Path) -> GitTargetInfo:
    candidate = _normalize_path(path)
    if not candidate.exists():
        raise ValueError(f"Target path does not exist: {candidate}")

    top_level = _run_git(["rev-parse", "--show-toplevel"], candidate)
    if top_level.returncode != 0:
        raise ValueError(f"Not a git repository: {candidate}")

    repo_root = Path(top_level.stdout.strip()).resolve()
    remote = _run_git(["config", "--get", "remote.origin.url"], repo_root)
    remote_url = remote.stdout.strip() or None if remote.returncode == 0 else None
    return GitTargetInfo(repo_root=repo_root, remote_url=remote_url)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "target"


def _parse_remote(remote_url: str | None) -> tuple[str, str, str] | None:
    """Extract host/owner/repo information from a Git remote URL when possible."""
    if not remote_url:
        return None

    ssh_match = re.match(
        r"^(?:.+@)?(?P<host>[^:]+):(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        remote_url,
    )
    if ssh_match:
        return (
            ssh_match.group("host"),
            ssh_match.group("owner"),
            ssh_match.group("repo"),
        )

    https_match = re.match(
        r"^(?:https?://)?(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
        remote_url,
    )
    if https_match:
        return (
            https_match.group("host"),
            https_match.group("owner"),
            https_match.group("repo"),
        )
    return None


def _build_target_slug(repo_root: Path, repo_name: str, repo_remote: str | None) -> str:
    remote_parts = _parse_remote(repo_remote)
    if remote_parts is not None:
        host, owner, repo = remote_parts
        base = "-".join(_slugify(part) for part in (host, owner, repo))
        identity = f"{host}/{owner}/{repo}"
    else:
        base = _slugify(repo_name)
        identity = str(repo_root)

    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8]
    return f"{base}{_SLUG_SEPARATOR}{digest}"


def _target_to_dict(config: TargetConfig) -> dict[str, str | None]:
    payload = asdict(config)
    payload["target_path"] = str(config.target_path)
    payload["set_at"] = config.set_at.isoformat()
    payload["vision_path"] = str(config.vision_path) if config.vision_path else None
    return payload


def _target_from_dict(payload: dict[str, str | None]) -> TargetConfig:
    vision_raw = payload.get("vision_path")
    return TargetConfig(
        target_path=Path(payload["target_path"] or "").resolve(),
        set_at=datetime.fromisoformat(payload["set_at"] or _utcnow().isoformat()),
        repo_name=payload["repo_name"] or "",
        repo_remote=payload.get("repo_remote"),
        vision_path=Path(vision_raw) if vision_raw else None,
        target_slug=payload["target_slug"] or "",
    )


def _read_registry(path: Path) -> list[TargetConfig]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [_target_from_dict(item) for item in payload]


def _write_registry(path: Path, targets: list[TargetConfig]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [_target_to_dict(item) for item in targets]
    path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")


def get_target_vision_path(target: TargetConfig) -> Path:
    """Return the canonical app-managed VISION path for a target repository."""
    app_root = _resolve_app_root()
    return app_root / _TARGET_VISION_DIR / target.target_slug / "VISION.md"


def get_active_target() -> TargetConfig | None:
    """Load the currently active target configuration, if one is set."""
    path = _active_target_file(_resolve_app_root())
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return _target_from_dict(payload)


def set_target(path: Path) -> TargetConfig:
    """Validate and persist the active target repository selection."""
    app_root = _resolve_app_root()
    git_info = _probe_git_repository(path)
    repo_name = git_info.repo_root.name
    slug = _build_target_slug(git_info.repo_root, repo_name, git_info.remote_url)
    config = TargetConfig(
        target_path=git_info.repo_root,
        set_at=_utcnow(),
        repo_name=repo_name,
        repo_remote=git_info.remote_url,
        vision_path=app_root / _TARGET_VISION_DIR / slug / "VISION.md",
        target_slug=slug,
    )

    active_path = _active_target_file(app_root)
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(
        json.dumps(_target_to_dict(config), indent=2), encoding="utf-8"
    )

    registry_path = _target_registry_file(app_root)
    existing = {item.target_slug: item for item in _read_registry(registry_path)}
    existing[config.target_slug] = config
    known_targets = sorted(
        existing.values(), key=lambda item: item.set_at, reverse=True
    )
    _write_registry(registry_path, known_targets)
    return config


def clear_target() -> None:
    """Remove the active target selection without deleting the known-target registry."""
    path = _active_target_file(_resolve_app_root())
    if path.exists():
        path.unlink()


def resolve_active_project_root() -> Path:
    """Resolve the currently active project root for project-scoped file operations."""
    active = get_active_target()
    if active is not None:
        return active.target_path
    return _resolve_app_root()


def list_known_targets() -> list[TargetConfig]:
    """Return all known targets, keeping the active selection included if present."""
    app_root = _resolve_app_root()
    registry = _read_registry(_target_registry_file(app_root))
    active = get_active_target()
    if active is None:
        return registry

    known = {item.target_slug: item for item in registry}
    known[active.target_slug] = active
    return sorted(known.values(), key=lambda item: item.set_at, reverse=True)


def resolve_project_vision_path() -> Path:
    """Resolve the project vision path for the active target or default project."""
    active = get_active_target()
    if active is not None and active.vision_path is not None:
        return active.vision_path
    return _resolve_app_root() / _DEFAULT_PROJECT_VISION


def resolve_execution_root() -> Path:
    """Resolve where project-mode execution should write code artifacts."""
    return resolve_active_project_root()


def target_memory_namespace(namespace: str) -> str:
    """Namespace project memory by active target slug when a target is selected."""
    active = get_active_target()
    if active is None:
        return f"default/{namespace}"
    return f"{active.target_slug}/{namespace}"


@contextmanager
def temporary_working_directory(path: Path):
    """Temporarily switch cwd for tool-relative project operations and restore it after."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


TARGET_FILE_FORMAT = 1
