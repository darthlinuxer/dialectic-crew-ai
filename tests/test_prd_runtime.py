from types import SimpleNamespace

import dialectic.prd_flow as prd_flow
from dialectic.vision import VisionContext


def test_build_prd_crew_uses_yaml_templates(monkeypatch):
    from dialectic import prd_runtime

    captured_tasks = []
    captured_crew = {}

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}")
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")

    crew = prd_runtime.build_prd_crew(
        feature_objective="Ship resilient PRD validation",
        vision_context=VisionContext.SELF,
        retry_feedback_block="\nRETRY FEEDBACK\n",
        retry_feedback_sources=["feedback-source"],
    )

    assert crew is not None
    assert len(captured_tasks) == 4
    assert "Ship resilient PRD validation" in captured_tasks[0]["description"]
    assert "RETRY FEEDBACK" in captured_tasks[0]["description"]
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[2]["context"] == [captured_crew["tasks"][0], captured_crew["tasks"][1]]
    assert captured_tasks[3]["context"] == [captured_crew["tasks"][2]]
    assert captured_tasks[3]["output_pydantic"].__name__ == "PRDSchema"
    assert captured_tasks[3]["guardrail"].__name__ == "_prd_guardrail"
    assert captured_crew["knowledge_sources"] == ["vision:self", "feedback-source"]


def test_build_prd_crew_preserves_agent_order(monkeypatch):
    from dialectic import prd_runtime

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_crew = {}

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Ship resilient PRD validation",
        vision_context=VisionContext.PROJECT,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    assert captured_crew["agents"] == ["visionario", "critico", "sint", "val"]
    assert captured_crew["process"] is prd_runtime.Process.sequential