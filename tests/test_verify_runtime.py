"""Tests for standalone verification runtime construction."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,import-outside-toplevel,line-too-long

from __future__ import annotations

from execution import verify_runtime
from dialectic.vision import VisionContext


def test_build_verification_crew_uses_yaml_template_and_tool_override(monkeypatch):
    from tests.conftest import make_task

    captured_tasks: list[dict] = []
    captured_crew: dict = {}
    captured_helper: dict = {}

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    agent = {"role": "validator", "tools": ["orig"]}
    monkeypatch.setattr(verify_runtime, "Task", FakeTask)
    monkeypatch.setattr(verify_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(verify_runtime, "create_validador_macro", lambda ctx: agent)
    monkeypatch.setattr(verify_runtime, "file_read_tool", "reader")
    monkeypatch.setattr(verify_runtime, "stack_validation_tool", "validator")
    monkeypatch.setattr(verify_runtime, "crew_memory", lambda ctx, scope: f"memory:{ctx.value}:{scope}")
    monkeypatch.setattr(verify_runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")
    monkeypatch.setattr(
        verify_runtime,
        "build_sequential_crew_kwargs",
        lambda **kwargs: captured_helper.setdefault("kwargs", kwargs) or kwargs,
    )

    verify_runtime.build_verification_crew(
        task=make_task(id="T-123", title="Verify API", description="Confirm API endpoint exists"),
        acceptance_criteria=["Endpoint returns 200", "Schema matches contract"],
        vision_context=VisionContext.SELF,
    )

    assert agent["tools"] == ["reader", "validator"]
    assert len(captured_tasks) == 1
    assert "T-123" in captured_tasks[0]["description"]
    assert "Endpoint returns 200" in captured_tasks[0]["description"]
    assert "package/module boundaries remain coherent" in captured_tasks[0]["description"]
    assert "Related tests, exports, or supporting files" in captured_tasks[0]["description"]
    assert captured_tasks[0]["output_pydantic"].__name__ == "ValidationOutput"
    assert captured_crew["agents"] == [agent]
    assert captured_crew["tasks"][0] is not None
    assert captured_crew["memory"] == "memory:self:verify"
    assert captured_crew["knowledge_sources"] == ["vision:self"]
    assert captured_helper["kwargs"]["tasks"] == captured_crew["tasks"]
    assert captured_helper["kwargs"]["memory"] == "memory:self:verify"
    assert captured_helper["kwargs"]["knowledge_sources"] == ["vision:self"]


def test_build_verification_crew_omits_acceptance_criteria_block_when_empty(monkeypatch):
    from tests.conftest import make_task

    captured_tasks: list[dict] = []

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(verify_runtime, "Task", FakeTask)
    monkeypatch.setattr(verify_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(verify_runtime, "create_validador_macro", lambda ctx: {"tools": []})
    monkeypatch.setattr(verify_runtime, "file_read_tool", "reader")
    monkeypatch.setattr(verify_runtime, "stack_validation_tool", "validator")
    monkeypatch.setattr(verify_runtime, "crew_memory", lambda ctx, scope: "memory")
    monkeypatch.setattr(verify_runtime, "vision_knowledge", lambda ctx: "vision")

    verify_runtime.build_verification_crew(
        task=make_task(id="T-9", title="Check docs", description="Docs exist"),
        acceptance_criteria=[],
        vision_context=VisionContext.PROJECT,
    )

    assert "ACCEPTANCE CRITERIA" not in captured_tasks[0]["description"]
    assert "static-analysis/editor inconsistencies" in captured_tasks[0]["description"]
