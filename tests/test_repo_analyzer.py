"""Tests for repository analysis and target vision generation."""

from __future__ import annotations

from pathlib import Path

import dialectic.repo_analyzer as repo_analyzer
import dialectic.vision_generator as vision_generator


class TestRepoAnalyzer:
    def test_analyze_repository_detects_stack_and_modules(self, tmp_path):
        repo_root = tmp_path / "demo-repo"
        (repo_root / "src" / "demo_app").mkdir(parents=True)
        (repo_root / "docs").mkdir()
        (repo_root / "README.md").write_text(
            "# Demo App\n\nA project for managing field operations.\n",
            encoding="utf-8",
        )
        (repo_root / "pyproject.toml").write_text(
            "[project]\nname='demo-app'\ndependencies=['fastapi','sqlalchemy']\n",
            encoding="utf-8",
        )

        analysis = repo_analyzer.analyze_repository(repo_root)

        assert analysis.repo_name == "demo-repo"
        assert analysis.about_summary == "A project for managing field operations."
        assert "Python" in analysis.runtime
        assert analysis.framework == "FastAPI"
        assert analysis.main_modules
        assert "src/demo_app" in analysis.main_modules


class TestVisionGenerator:
    def test_generate_vision_markdown_renders_expected_sections(self):
        analysis = repo_analyzer.RepoAnalysis(
            repo_root=Path("/tmp/demo-repo"),
            repo_name="demo-repo",
            about_summary="A project for managing field operations.",
            business_objectives=["Improve operator productivity"],
            design_principles=["Reliability first"],
            main_modules=["src/demo_app"],
            integrations=["External: none detected"],
            runtime="Python 3.x",
            framework="FastAPI",
            database="SQLAlchemy / TBD",
            performance_notes="No explicit targets found; define latency budgets.",
            security_notes="No explicit auth docs found; review security posture.",
            scalability_notes="No explicit scaling guidance found; validate expected load.",
            source_documents=["README.md"],
        )

        rendered = vision_generator.generate_vision_markdown(analysis)

        assert "## About Your Project" in rendered
        assert "Improve operator productivity" in rendered
        assert "| src/demo_app | Core project module |" in rendered
        assert "**Framework:** FastAPI" in rendered
        assert "README.md" in rendered
