from conftest import make_prd
from dialectic.vision import VisionContext


def test_build_planning_crew_uses_yaml_templates(monkeypatch):
    from planning import runtime

    captured_tasks = []
    captured_crew = {}

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: f"knowledge:{ctx.value}")

    prd = make_prd()
    us = prd.user_stories[0]
    us_context = "story context"
    feature_context = "feature context"

    runtime.build_planning_crew(
        feature_context=feature_context,
        us=us,
        us_context=us_context,
        vision_context=VisionContext.SELF,
        min_plan_score=7.5,
    )

    assert len(captured_tasks) == 4
    assert "feature context" in captured_tasks[0]["description"]
    assert "story context" in captured_tasks[0]["description"]
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[3]["output_pydantic"].__name__ == "UserStoryExecutionPlan"
    assert captured_tasks[3]["guardrail"].__name__ == "_plan_guardrail"
    assert captured_crew["planning"] is True
    assert captured_crew["planning_llm"] is runtime.llm_planning
    assert captured_crew["knowledge_sources"] == ["knowledge:self"]


def test_build_planning_crew_preserves_agent_order(monkeypatch):
    from planning import runtime

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_crew = {}

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "knowledge")

    prd = make_prd()
    us = prd.user_stories[0]

    runtime.build_planning_crew(
        feature_context="feature",
        us=us,
        us_context="story",
        vision_context=VisionContext.PROJECT,
        min_plan_score=7.5,
    )

    assert captured_crew["agents"] == ["visionario", "critico", "sint", "val"]