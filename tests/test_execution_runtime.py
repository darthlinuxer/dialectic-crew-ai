from dialectic.vision import VisionContext


def test_build_task_dialectic_crew_uses_yaml_templates(monkeypatch):
    from execution import runtime

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
    monkeypatch.setattr(runtime, "create_implementer", lambda ctx: "impl")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "crit")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")

    runtime.build_task_dialectic_crew(
        task_id="T-001",
        task_title="Title",
        task_description="Do the thing",
        context_str="Context block",
        min_score=7.5,
        vision_context=VisionContext.SELF,
        synthesis_for_retry="Refine this implementation",
        retry=1,
        max_retries=3,
    )

    assert len(captured_tasks) == 4
    assert "RETRY 1/3" in captured_tasks[0]["description"]
    assert "Refine this implementation" in captured_tasks[0]["description"]
    assert captured_tasks[0]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[2]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[2]["context"] == [captured_crew["tasks"][0], captured_crew["tasks"][1]]
    assert captured_tasks[3]["output_pydantic"].__name__ == "ValidationOutput"
    assert captured_tasks[3]["guardrail"].__name__ == "_quality_guardrail"
    assert captured_crew["planning"] is True
    assert captured_crew["knowledge_sources"] == ["vision:self"]


def test_build_task_dialectic_crew_uses_initial_template_without_retry(monkeypatch):
    from execution import runtime

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
    monkeypatch.setattr(runtime, "create_implementer", lambda ctx: "impl")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "crit")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision")

    runtime.build_task_dialectic_crew(
        task_id="T-001",
        task_title="Title",
        task_description="Do the thing",
        context_str="Context block",
        min_score=7.5,
        vision_context=VisionContext.PROJECT,
        synthesis_for_retry=None,
        retry=0,
        max_retries=3,
    )

    assert "TASK TO IMPLEMENT: T-001 — Title" in captured_tasks[0]["description"]
    assert "Context block" in captured_tasks[0]["description"]
    assert "RETRY 1/3" not in captured_tasks[0]["description"]