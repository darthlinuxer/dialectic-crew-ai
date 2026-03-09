"""Tests for dialectic.state.DialecticState."""

from dialectic.state import DialecticState, MAX_RETRIES


def test_max_retries_constant():
    assert MAX_RETRIES == 5


def test_default_values():
    state = DialecticState()
    assert state.feature_objective == ""
    assert state.prd_data == {}
    assert state.quality_score == 0.0
    assert state.retry_count == 0
    assert state.max_retries == MAX_RETRIES
    assert state.consensus_reached is False
    assert state.final_validation_notes == ""
    assert state.file_paths == []


def test_mutation():
    state = DialecticState()
    state.feature_objective = "Login with 2FA"
    state.quality_score = 9.5
    state.retry_count = 2
    state.consensus_reached = True
    state.file_paths = ["/tmp/spec.pdf"]

    assert state.feature_objective == "Login with 2FA"
    assert state.quality_score == 9.5
    assert state.retry_count == 2
    assert state.consensus_reached is True
    assert state.file_paths == ["/tmp/spec.pdf"]
