"""Tests to verify SELF_VISION.md is injected as knowledge for self-improve flows."""

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

from dialectic.knowledge import (
    _STYLE_GUIDE_PATHS,
    style_guide_knowledge,
    vision_knowledge,
)
from dialectic.vision import VisionContext
from execution import runtime as execution_runtime


def _legacy_src_vision_context(name: str):
    """Load VisionContext from the legacy src.* import surface for regression tests."""
    module = __import__("src.dialectic.vision", fromlist=["VisionContext"])
    return getattr(module.VisionContext, name)


class TestVisionKnowledgeInjection:
    """Verify that SELF_VISION.md is loaded via vision_knowledge for VisionContext.SELF."""

    @patch("dialectic.knowledge.prepare_vision_runtime")
    @patch("dialectic.knowledge.get_vision_path")
    def test_vision_knowledge_loads_self_vision(
        self, mock_get_path, mock_prepare
    ):
        """vision_knowledge should load internal/SELF_VISION.md for SELF context."""
        expected_path = Path("/app/internal/SELF_VISION.md")
        mock_get_path.return_value = expected_path

        mock_source_cls = MagicMock()
        result = vision_knowledge(
            VisionContext.SELF,
            prepare_vision_runtime_fn=mock_prepare,
            get_vision_path_fn=mock_get_path,
            knowledge_source_cls=mock_source_cls,
        )

        mock_prepare.assert_called_once_with(VisionContext.SELF)
        mock_get_path.assert_called_once_with(VisionContext.SELF)
        mock_source_cls.assert_called_once_with(file_paths=[expected_path])
        assert result is mock_source_cls.return_value

    @patch("dialectic.knowledge.prepare_vision_runtime")
    @patch("dialectic.knowledge.get_vision_path")
    def test_vision_knowledge_loads_project_vision(
        self, mock_get_path, mock_prepare
    ):
        """vision_knowledge should load knowledge/VISION.md for PROJECT context."""
        expected_path = Path("/app/knowledge/VISION.md")
        mock_get_path.return_value = expected_path

        mock_source_cls = MagicMock()
        result = vision_knowledge(
            VisionContext.PROJECT,
            prepare_vision_runtime_fn=mock_prepare,
            get_vision_path_fn=mock_get_path,
            knowledge_source_cls=mock_source_cls,
        )

        mock_prepare.assert_called_once_with(VisionContext.PROJECT)
        mock_get_path.assert_called_once_with(VisionContext.PROJECT)
        mock_source_cls.assert_called_once_with(file_paths=[expected_path])
        assert result is mock_source_cls.return_value


class TestStyleGuideKnowledge:
    """Verify style guide knowledge sources are created for self-improve."""

    def test_style_guide_paths_defined(self):
        """Style guide paths should be defined."""
        assert len(_STYLE_GUIDE_PATHS) == 3
        assert all(str(p).endswith(".md") for p in _STYLE_GUIDE_PATHS)
        assert any("python-style" in str(p) for p in _STYLE_GUIDE_PATHS)
        assert any("python-patterns" in str(p) for p in _STYLE_GUIDE_PATHS)
        assert any("python-testing" in str(p) for p in _STYLE_GUIDE_PATHS)

    def test_style_guide_knowledge_creates_sources(self, tmp_path):
        """style_guide_knowledge should create sources for existing files."""
        # Create mock style guide files
        skill_dir = tmp_path / "src/mcp/skills/senior-software-developer/reference"
        skill_dir.mkdir(parents=True)
        (skill_dir / "python-style.md").write_text("# Style")
        (skill_dir / "python-patterns.md").write_text("# Patterns")
        (skill_dir / "python-testing.md").write_text("# Testing")

        mock_source_cls = MagicMock()
        sources = style_guide_knowledge(
            resolve_project_root_fn=lambda: tmp_path,
            knowledge_source_cls=mock_source_cls,
        )

        assert len(sources) == 3
        assert mock_source_cls.call_count == 3

    def test_style_guide_knowledge_skips_missing_files(self, tmp_path):
        """style_guide_knowledge should skip files that don't exist."""
        # Create only one style guide file
        skill_dir = tmp_path / "src/mcp/skills/senior-software-developer/reference"
        skill_dir.mkdir(parents=True)
        (skill_dir / "python-style.md").write_text("# Style")

        mock_source_cls = MagicMock()
        sources = style_guide_knowledge(
            resolve_project_root_fn=lambda: tmp_path,
            knowledge_source_cls=mock_source_cls,
        )

        assert len(sources) == 1
        assert mock_source_cls.call_count == 1


class TestExecutionRuntimeStyleGuideInjection:
    """Verify execution runtime includes style guides for SELF context."""

    @patch("execution.runtime.style_guide_knowledge")
    @patch("execution.runtime.vision_knowledge")
    @patch("execution.runtime.crew_memory")
    @patch("execution.runtime.create_validador_macro")
    @patch("execution.runtime.create_sintetizador")
    @patch("execution.runtime.create_critico_socratico")
    @patch("execution.runtime.create_implementer")
    @patch("execution.runtime.load_yaml_config")
    def test_self_context_includes_style_guides(
        self,
        mock_config,
        _mock_impl,
        _mock_crit,
        _mock_sint,
        _mock_val,
        _mock_memory,
        mock_vision_knowledge,
        mock_style_knowledge,
    ):
        """build_task_dialectic_crew should include style guides for SELF context."""
        mock_config.return_value = {
            "execute_task_thesis": {"agent": "implementer", "description": "test"},
            "execute_task_antithesis": {"agent": "critico_socratico", "description": "test"},
            "execute_task_synthesis": {"agent": "sintetizador", "description": "test"},
            "execute_task_validation": {"agent": "validador_macro", "description": "test"},
        }
        mock_vision_knowledge.return_value = MagicMock()
        mock_style_knowledge.return_value = [MagicMock(), MagicMock()]

        with (
            patch("execution.runtime.Task", side_effect=lambda **kwargs: kwargs),
            patch("execution.runtime.Crew") as mock_crew,
        ):
            execution_runtime.build_task_dialectic_crew(
                task_id="T1",
                task_title="Test Task",
                task_description="Test description",
                context_str="Context",
                min_score=7.5,
                vision_context=_legacy_src_vision_context("SELF"),
                synthesis_for_retry=None,
                retry=0,
                max_retries=3,
            )

            mock_style_knowledge.assert_called_once()
            call_kwargs = mock_crew.call_args.kwargs
            knowledge_sources = call_kwargs.get("knowledge_sources", [])
            assert len(knowledge_sources) == 3  # vision + 2 style guides

    @patch("execution.runtime.style_guide_knowledge")
    @patch("execution.runtime.vision_knowledge")
    @patch("execution.runtime.crew_memory")
    @patch("execution.runtime.create_validador_macro")
    @patch("execution.runtime.create_sintetizador")
    @patch("execution.runtime.create_critico_socratico")
    @patch("execution.runtime.create_implementer")
    @patch("execution.runtime.load_yaml_config")
    def test_project_context_excludes_style_guides(
        self,
        mock_config,
        _mock_impl,
        _mock_crit,
        _mock_sint,
        _mock_val,
        _mock_memory,
        mock_vision_knowledge,
        mock_style_knowledge,
    ):
        """build_task_dialectic_crew should NOT include style guides for PROJECT context."""
        mock_config.return_value = {
            "execute_task_thesis": {"agent": "implementer", "description": "test"},
            "execute_task_antithesis": {"agent": "critico_socratico", "description": "test"},
            "execute_task_synthesis": {"agent": "sintetizador", "description": "test"},
            "execute_task_validation": {"agent": "validador_macro", "description": "test"},
        }
        mock_vision_knowledge.return_value = MagicMock()

        with (
            patch("execution.runtime.Task", side_effect=lambda **kwargs: kwargs),
            patch("execution.runtime.Crew") as mock_crew,
        ):
            execution_runtime.build_task_dialectic_crew(
                task_id="T1",
                task_title="Test Task",
                task_description="Test description",
                context_str="Context",
                min_score=7.5,
                vision_context=_legacy_src_vision_context("PROJECT"),
                synthesis_for_retry=None,
                retry=0,
                max_retries=3,
            )

            mock_style_knowledge.assert_not_called()
            call_kwargs = mock_crew.call_args.kwargs
            knowledge_sources = call_kwargs.get("knowledge_sources", [])
            assert len(knowledge_sources) == 1  # vision only

def test_self_improve_uses_self_vision_context():
    """self_improve package should pass VisionContext.SELF to all stages."""
    self_improve = __import__("main", fromlist=["self_improve"]).self_improve
    source = inspect.getsource(self_improve)

    assert "VisionContext.SELF" in source
    assert (
        "vision_context=VisionContext.SELF" in source
        or "vision_context: VisionContext.SELF" in source
    )
