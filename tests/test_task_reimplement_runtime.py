from dialectic.vision import VisionContext


def test_build_task_flow_reimplementation_crew_uses_yaml_templates(monkeypatch):
    from execution import task_reimplement_runtime as runtime

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
    monkeypatch.setattr(runtime, "_build_agent", lambda: "reimpl")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "validator")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")

    runtime.build_task_flow_reimplementation_crew(
        task_id="T-003",
        task_title="Repair",
        task_description="Fix the task",
        failed_checks=["missing file", "bad config"],
        verification_notes="Verifier found gaps",
        min_score=8.0,
        vision_context=VisionContext.SELF,
    )

    assert len(captured_tasks) == 2
    assert "FAILED CHECKS" in captured_tasks[0]["description"]
    assert "- missing file" in captured_tasks[0]["description"]
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[1]["output_pydantic"].__name__ == "ValidationOutput"
    assert captured_tasks[1]["guardrail"].__name__ == "_quality_guardrail"
    assert captured_crew["agents"] == ["reimpl", "validator"]
    assert captured_crew["memory"] == "memory:self:task_reimplement"


def test_build_task_flow_reimplementation_crew_uses_na_for_empty_failed_checks(monkeypatch):
    from execution import task_reimplement_runtime as runtime

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
    monkeypatch.setattr(runtime, "_build_agent", lambda: "reimpl")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "validator")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision")

    runtime.build_task_flow_reimplementation_crew(
        task_id="T-003",
        task_title="Repair",
        task_description="Fix the task",
        failed_checks=[],
        verification_notes="Verifier found gaps",
        min_score=8.0,
        vision_context=VisionContext.PROJECT,
    )

    assert "N/A" in captured_tasks[0]["description"]