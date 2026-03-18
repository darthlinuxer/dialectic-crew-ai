"""Deterministic repository analysis helpers for generated vision documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_IGNORED_DIRS = {
    ".git",
    ".dialectic",
    ".venv",
    "__pycache__",
    "docs",
    "node_modules",
    "tests",
}


@dataclass(frozen=True)
# pylint: disable=too-many-instance-attributes
class RepoAnalysis:
    """Structured summary of a repository used to generate a vision document."""

    repo_root: Path
    repo_name: str
    about_summary: str
    business_objectives: list[str]
    design_principles: list[str]
    main_modules: list[str]
    integrations: list[str]
    runtime: str
    framework: str
    database: str
    performance_notes: str
    security_notes: str
    scalability_notes: str
    source_documents: list[str]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _first_readme_summary(repo_root: Path) -> str:
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return "Repository vision generated from its current file structure."

    lines = [line.strip() for line in _read_text(readme_path).splitlines()]
    for line in lines:
        if line and not line.startswith("#"):
            return line
    return "Repository vision generated from its README heading and file structure."


def _detect_runtime(repo_root: Path) -> str:
    if (repo_root / "pyproject.toml").exists() or (
        repo_root / "requirements.txt"
    ).exists():
        return "Python 3.x"
    if (repo_root / "package.json").exists():
        return "Node.js"
    if (repo_root / "Cargo.toml").exists():
        return "Rust"
    if (repo_root / "go.mod").exists():
        return "Go"
    return "TBD"


def _combined_text(repo_root: Path) -> str:
    text_parts = []
    for path in (
        repo_root / "README.md",
        repo_root / "pyproject.toml",
        repo_root / "package.json",
    ):
        if path.exists():
            text_parts.append(_read_text(path).lower())
    return "\n".join(text_parts)


def _detect_framework(repo_root: Path) -> str:
    combined = _combined_text(repo_root)
    framework_markers = [
        ("fastapi", "FastAPI"),
        ("django", "Django"),
        ("flask", "Flask"),
        ("crewai", "CrewAI"),
        ("next", "Next.js"),
        ("react", "React"),
    ]
    for marker, label in framework_markers:
        if marker in combined:
            return label
    return "TBD"


def _detect_database(repo_root: Path) -> str:
    combined = _combined_text(repo_root)
    database_markers = [
        ("postgres", "PostgreSQL"),
        ("mysql", "MySQL"),
        ("sqlite", "SQLite"),
        ("mongodb", "MongoDB"),
        ("redis", "Redis"),
        ("sqlalchemy", "SQLAlchemy / TBD"),
    ]
    for marker, label in database_markers:
        if marker in combined:
            return label
    return "TBD"


def _discover_main_modules(repo_root: Path) -> list[str]:
    src_root = repo_root / "src"
    if src_root.exists():
        modules = [
            f"src/{child.name}"
            for child in sorted(src_root.iterdir())
            if child.is_dir() and child.name not in _IGNORED_DIRS
        ]
        if modules:
            return modules[:5]

    modules = [
        child.name
        for child in sorted(repo_root.iterdir())
        if child.is_dir() and child.name not in _IGNORED_DIRS
    ]
    return modules[:5] or ["(main module TBD)"]


def _source_documents(repo_root: Path) -> list[str]:
    documents: list[str] = []
    if (repo_root / "README.md").exists():
        documents.append("README.md")
    docs_root = repo_root / "docs"
    if docs_root.exists():
        documents.append("docs/")
    return documents or ["(no source documents detected)"]


def analyze_repository(repo_root: Path) -> RepoAnalysis:
    """Analyze a repository and summarize the material needed for a VISION.md draft."""
    normalized_root = repo_root.expanduser().resolve()
    about_summary = _first_readme_summary(normalized_root)
    runtime = _detect_runtime(normalized_root)
    framework = _detect_framework(normalized_root)
    database = _detect_database(normalized_root)
    main_modules = _discover_main_modules(normalized_root)

    business_objectives = [
        f"Sustain and improve {normalized_root.name}'s core workflow.",
        "Preserve the repository's documented behavior while evolving safely.",
    ]
    design_principles = [
        "Prefer incremental, well-tested changes.",
        f"Stay aligned with the detected stack ({runtime}, {framework}).",
    ]
    integrations = ["External: no explicit third-party integrations detected."]

    return RepoAnalysis(
        repo_root=normalized_root,
        repo_name=normalized_root.name,
        about_summary=about_summary,
        business_objectives=business_objectives,
        design_principles=design_principles,
        main_modules=main_modules,
        integrations=integrations,
        runtime=runtime,
        framework=framework,
        database=database,
        performance_notes="No explicit targets found; define latency budgets.",
        security_notes="No explicit auth docs found; review security posture.",
        scalability_notes="No explicit scaling guidance found; validate expected load.",
        source_documents=_source_documents(normalized_root),
    )
