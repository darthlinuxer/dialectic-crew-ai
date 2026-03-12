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