"""Smoke tests for package-level public exports."""

from dialectic import (
    DialecticFlow,
    PRDExporter,
    execution_plan_to_markdown,
    prd_runtime,
    prioritize_runtime,
    validate_consistency,
)
from execution import (
    dialectic_execution,
    runner,
    runtime,
    status,
    task_reimplement_runtime,
    task_verify_runtime,
    verify_runtime,
)
from main import cli_main, run_self_improve
from planning import run_user_story_planning, runtime as planning_runtime
from src.mcp import skills_mcp
from src.mcp.skills_index import SkillIndex, SkillMetadata, SkillSource


def test_dialectic_exports_are_importable():
    assert DialecticFlow is not None
    assert PRDExporter is not None
    assert execution_plan_to_markdown is not None
    assert validate_consistency is not None
    assert prd_runtime is not None
    assert prioritize_runtime is not None


def test_execution_exports_are_importable():
    assert dialectic_execution is not None
    assert runner is not None
    assert runtime is not None
    assert status is not None
    assert task_reimplement_runtime is not None
    assert task_verify_runtime is not None
    assert verify_runtime is not None


def test_main_planning_and_mcp_exports_are_importable():
    assert cli_main is not None
    assert run_self_improve is not None
    assert run_user_story_planning is not None
    assert planning_runtime is not None
    assert SkillIndex is not None
    assert SkillMetadata is not None
    assert SkillSource is not None
    assert skills_mcp is not None