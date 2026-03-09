"""Shared fixtures and configuration for the test suite."""

import json
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from schemas import (
    PRDSchema,
    MacroImpact,
    UserStory,
    AntiDriftQuestion,
    ImplementationTask,
    UserStoryExecutionPlan,
)


def _has_api_key() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked with @pytest.mark.llm when no API key is set."""
    if _has_api_key():
        return
    skip_llm = pytest.mark.skip(reason="No LLM API key configured in .env")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)


# ---------------------------------------------------------------------------
# Reusable factory helpers (not fixtures — call directly in tests)
# ---------------------------------------------------------------------------


def make_prd(**overrides) -> PRDSchema:
    defaults = dict(
        feature_name="Test Feature",
        version="1.0",
        objective="Test objective",
        macro_impact=MacroImpact(
            modules_affected=["mod1", "mod2"],
            risk_level="LOW",
            performance_impact="minor",
            security_impact="low",
        ),
        user_stories=[
            UserStory(
                id="US-001",
                title="Sample Story",
                description="Do something useful",
                acceptance_criteria=["AC1", "AC2", "AC3"],
                effort="M",
                dependencies=[],
            ),
        ],
        anti_drift_questions=[
            AntiDriftQuestion(question=f"q{i}", answer=f"a{i}") for i in range(5)
        ],
        quality_score=9.0,
        consensus_reached=True,
        final_validation_notes="Approved",
    )
    defaults.update(overrides)
    return PRDSchema(**defaults)


def make_task(**overrides) -> ImplementationTask:
    defaults = dict(
        id="T-001",
        title="Create endpoint",
        description="Implement the REST endpoint for the feature",
        order=1,
        dependencies=[],
    )
    defaults.update(overrides)
    return ImplementationTask(**defaults)


def make_plan(**overrides) -> UserStoryExecutionPlan:
    defaults = dict(
        user_story_id="US-001",
        user_story_title="Sample Story",
        approach_summary="Implement using standard patterns.",
        tasks=[make_task()],
        risks_mitigated=["Data loss"],
        tech_notes="Use PostgreSQL.",
        quality_score=9.0,
        consensus_reached=True,
        final_validation_notes="Plan approved.",
    )
    defaults.update(overrides)
    return UserStoryExecutionPlan(**defaults)


@pytest.fixture
def sample_prd():
    return make_prd()


@pytest.fixture
def sample_plan():
    return make_plan()


@pytest.fixture
def sample_task():
    return make_task()


@pytest.fixture
def plan_file(tmp_path, sample_plan):
    """Write a plan JSON to a temp directory and return its path string."""
    path = tmp_path / "prd_output" / "exec_US-001_20260101_120000.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sample_plan.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(path)
