"""Tests for TaskFlowState defaults and mutation."""

from execution.task_flow import TaskFlowState
from schemas import VerificationResult


def test_defaults():
    state = TaskFlowState()
    assert state.task_id == ""
    assert state.task_title == ""
    assert state.task_description == ""
    assert state.context_str == ""
    assert state.output_dir == ""
    assert state.acceptance_checks == []
    assert state.dialectic_score == 0.0
    assert state.dialectic_success is False
    assert state.dialectic_retries == 0
    assert state.impl_output == ""
    assert state.verified is False
    assert state.reimplement_score == 0.0
    assert state.reimplement_success is False
    assert state.phases_executed == []


def test_mutation():
    state = TaskFlowState()
    state.task_id = "T-001"
    state.dialectic_score = 9.0
    state.dialectic_success = True
    state.phases_executed.append("dialectic")
    state.phases_executed.append("verify")

    assert state.task_id == "T-001"
    assert state.dialectic_score == 9.0
    assert state.dialectic_success is True
    assert state.phases_executed == ["dialectic", "verify"]


def test_verification_default():
    state = TaskFlowState()
    assert isinstance(state.verification, VerificationResult)
    assert state.verification.verified is False
