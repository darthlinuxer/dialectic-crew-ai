"""Tests for task-flow verification runtime construction and wiring."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,import-outside-toplevel,line-too-long
# pylint: disable=duplicate-code

# pyright: reportPrivateUsage=none

from typing import Any, cast

from dialectic.vision import VisionContext


def test_build_task_flow_verification_crew_uses_yaml_templates(monkeypatch):
    from execution import task_verify_runtime as runtime

    captured_tasks = []
    captured_crew = {}
    captured_helper = {}

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(runtime, "_build_agent", lambda: "verifier")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")
    monkeypatch.setattr(
        runtime,
        "build_sequential_crew_kwargs",
        lambda **kwargs: captured_helper.setdefault("kwargs", kwargs) or kwargs,
    )

    runtime.build_task_flow_verification_crew(
        task_id="T-001",
        task_title="Verify stuff",
        task_description="Ensure files exist",
        acceptance_checks=["file exists", "function exists"],
        vision_context=VisionContext.SELF,
    )

    assert len(captured_tasks) == 1
    assert "T-001" in captured_tasks[0]["description"]
    assert "ACCEPTANCE CHECKS" in captured_tasks[0]["description"]
    assert "- file exists" in captured_tasks[0]["description"]
    assert "imports and references still resolve" in captured_tasks[0]["description"]
    assert "related tests or package exports" in captured_tasks[0]["description"]
    assert (
        "Return ONLY valid JSON matching VerificationResult"
        in captured_tasks[0]["description"]
    )
    assert captured_tasks[0]["output_pydantic"].__name__ == "VerificationResult"
    assert captured_tasks[0]["guardrail"].__name__ == "_verification_guardrail"
    assert captured_crew["agents"] == ["verifier"]
    assert captured_crew.get("memory") is None
    assert captured_crew["knowledge_sources"] == ["vision:self"]
    assert captured_helper["kwargs"]["tasks"] == captured_crew["tasks"]
    assert captured_helper["kwargs"].get("memory") is None
    assert captured_helper["kwargs"]["knowledge_sources"] == ["vision:self"]


def test_build_task_flow_verification_crew_omits_acceptance_block_when_empty(
    monkeypatch,
):
    from execution import task_verify_runtime as runtime

    captured_tasks = []

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(runtime, "_build_agent", lambda: "verifier")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision")

    runtime.build_task_flow_verification_crew(
        task_id="T-001",
        task_title="Verify stuff",
        task_description="Ensure files exist",
        acceptance_checks=[],
        vision_context=VisionContext.PROJECT,
    )

    assert "ACCEPTANCE CHECKS" not in captured_tasks[0]["description"]
    assert "obvious static-analysis breakage" in captured_tasks[0]["description"]


def test_build_task_flow_verification_agent_uses_structured_mode():
    from execution import task_verify_runtime as runtime

    build_agent = cast(Any, getattr(runtime, "_build_agent"))
    agent = build_agent()

    tool_names = {getattr(tool, "name", "") for tool in agent.tools}

    assert "stack_aware_validation" in tool_names
    assert "list_directory" not in tool_names
    assert agent.reasoning is False
    assert "structured verification mode" in agent.backstory


def test_run_independent_verifier_uses_runtime_builder(monkeypatch):
    from execution.task_flow import TaskExecutionFlow

    class FakeCrew:
        def kickoff(self):
            class Result:
                pydantic = None
                tasks_output = []

            return Result()

    captured = {}

    def fake_build_task_flow_verification_crew(**kwargs):
        captured.update(kwargs)
        return FakeCrew()

    monkeypatch.setattr(
        "execution.task_flow.build_task_flow_verification_crew",
        fake_build_task_flow_verification_crew,
    )

    flow = TaskExecutionFlow()
    flow.state.task_id = "T-002"
    flow.state.task_title = "Inspect"
    flow.state.task_description = "Check implementation"
    flow.state.acceptance_checks = ["one", "two"]
    flow.state.vision_context = VisionContext.SELF.value

    result = cast(Any, getattr(flow, "_run_independent_verifier"))()

    assert captured == {
        "task_id": "T-002",
        "task_title": "Inspect",
        "task_description": "Check implementation",
        "acceptance_checks": ["one", "two"],
        "vision_context": VisionContext.SELF,
    }
    assert result.verified is False
    assert result.notes == "Failed to obtain structured VerificationResult"
