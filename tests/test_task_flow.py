"""Execution-flow regressions for TaskExecutionFlow routing."""

from execution.task_flow import TaskExecutionFlow
from schemas import ValidationOutput, VerificationResult, TaskExecutionResult


def test_task_execution_flow_kickoff_runs_dialectic_and_verify(monkeypatch):
    """Kickoff should route from dispatch into dialectic work instead of stopping early."""

    class DummyScope:  # pylint: disable=too-few-public-methods
        """No-op hook scope used to keep the flow test deterministic."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        """Minimal CrewAI task output stub for dialectic validation."""

        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Return a successful dialectic validation payload."""

        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="implementation complete"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw="synthesis"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.7,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(
        TaskExecutionFlow,
        "_run_independent_verifier",
        lambda self, checks=None: VerificationResult(
            verified=True,
            checks_passed=checks or self.state.acceptance_checks,
            notes="All checks passed.",
        ),
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-001",
            "task_title": "Define schema",
            "task_description": "Create the schema for vision metadata.",
            "acceptance_checks": ["schema file exists"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert result.success is True
    assert result.score == 8.7
    assert flow.state.phases_executed == ["dialectic", "verify"]
    assert flow.state.current_phase == "completed"


def test_task_execution_flow_high_confidence_reimplementation_still_runs_stack_gate(monkeypatch):
    class DummyScope:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    class FakeDialecticCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="implementation complete"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw="synthesis"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.1,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    class FakeReimplementationCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="fixed implementation"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=9.6,
                                consensus_reached=True,
                                final_validation_notes="Repair accepted.",
                            )
                        ),
                    ]
                },
            )()

    verification_calls = {"count": 0}

    def fake_verifier(self, checks=None):
        del self, checks
        verification_calls["count"] += 1
        return VerificationResult(
            verified=False,
            checks_failed=["imports broken"],
            notes="Initial verification failed.",
        )

    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeDialecticCrew())
    monkeypatch.setattr("execution.task_flow.build_task_flow_reimplementation_crew", lambda **kwargs: FakeReimplementationCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(TaskExecutionFlow, "_run_independent_verifier", fake_verifier)
    monkeypatch.setattr(
        "execution.task_flow.run_stack_validation_gate",
        lambda profile: VerificationResult(
            verified=False,
            checks_failed=["stack validation: mypy"],
            notes="stack validation failed: mypy",
        ),
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-009",
            "task_title": "Repair import graph",
            "task_description": "Fix module wiring.",
            "acceptance_checks": ["imports resolve"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert verification_calls["count"] == 1
    assert result.success is False
    assert flow.state.reimplement_score == 9.6
    assert flow.state.verification.checks_failed == ["stack validation: mypy"]
    assert "stack validation failed" in flow.state.verification.notes