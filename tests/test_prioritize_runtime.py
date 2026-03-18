from dialectic.vision import VisionContext


def test_build_prioritization_crew_uses_yaml_templates(monkeypatch):
    from dialectic import prioritize_runtime

    captured_tasks = []
    captured_crew = {}

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prioritize_runtime, "Task", FakeTask)
    monkeypatch.setattr(prioritize_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prioritize_runtime, "Agent", lambda **kwargs: kwargs)
    monkeypatch.setattr(
        prioritize_runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}"
    )

    prioritize_runtime.build_prioritization_crew(
        opp_text="1. [opp-1] Improve thing",
        opp_ids_str="opp-1, opp-2",
        vision_context=VisionContext.SELF,
    )

    assert len(captured_tasks) == 3
    assert "Improve thing" in captured_tasks[0]["description"]
    assert "SELF_VISION.md" in captured_crew["agents"][0]["backstory"]
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[2]["context"] == [
        captured_crew["tasks"][0],
        captured_crew["tasks"][1],
    ]
    assert captured_tasks[2]["output_pydantic"].__name__ == "PrioritizationResult"
    assert captured_tasks[2]["guardrail"].__name__ == "_prioritization_guardrail"
    assert captured_crew["knowledge_sources"] == ["vision:self"]


def test_build_prioritization_crew_uses_sequential_process(monkeypatch):
    from dialectic import prioritize_runtime

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_crew = {}

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prioritize_runtime, "Task", FakeTask)
    monkeypatch.setattr(prioritize_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prioritize_runtime, "Agent", lambda **kwargs: kwargs)
    monkeypatch.setattr(prioritize_runtime, "vision_knowledge", lambda ctx: "vision")

    prioritize_runtime.build_prioritization_crew(
        opp_text="1. [opp-1] Improve thing",
        opp_ids_str="opp-1",
        vision_context=VisionContext.PROJECT,
    )

    assert captured_crew["process"] is prioritize_runtime.Process.sequential
