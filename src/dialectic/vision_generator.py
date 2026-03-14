"""Markdown rendering helpers for generated vision documents."""

from __future__ import annotations

from dialectic.repo_analyzer import RepoAnalysis


def _render_list(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _render_modules(modules: list[str]) -> str:
    rows = ["| Component | Description |", "|-----------|-------------|"]
    rows.extend(f"| {module} | Core project module |" for module in modules)
    return "\n".join(rows)


def _render_integrations(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _render_sources(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def generate_vision_markdown(analysis: RepoAnalysis) -> str:
    """Render a VISION.md draft from a deterministic repository analysis."""
    return f"""# VISION.md — {analysis.repo_name}

> Generated from the current repository structure and documentation.

---

## About Your Project

{analysis.about_summary}

---

## Business Objectives

{_render_list(analysis.business_objectives)}

---

## Design Principles

{_render_list(analysis.design_principles)}

---

## System Scope

### Main Modules / Components

{_render_modules(analysis.main_modules)}

### Integrations

{_render_integrations(analysis.integrations)}

---

## Tech Stack

- **Runtime:** {analysis.runtime}
- **Framework:** {analysis.framework}
- **Database:** {analysis.database}

---

## Non-Functional Requirements

- **Performance:** {analysis.performance_notes}
- **Security:** {analysis.security_notes}
- **Scalability:** {analysis.scalability_notes}

---

## Source Documents Consulted

{_render_sources(analysis.source_documents)}
"""
