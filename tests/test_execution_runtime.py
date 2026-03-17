"""Tests for execution runtime task construction."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=too-few-public-methods,import-outside-toplevel,line-too-long
# pylint: disable=protected-access,duplicate-code

from dialectic.vision import VisionContext


def test_build_runtime_placeholders_include_shared_plain_text_contract():
    from execution import runtime

    placeholders = runtime._build_runtime_placeholders(
        task_metadata={
            "task_id": "T-001",
            "task_title": "Title",
            "task_description": "Do the thing",
            "context_str": "Context block",
        },
        min_score=7.5,
        vision_context=VisionContext.PROJECT,
        retry_context={
            "synthesis_for_retry": None,
            "retry": 0,
            "max_retries": 3,
        },
    )

    assert "Return only the completed plain-text answer" in placeholders["final_text_response_rules"]
    assert placeholders["plain_text_implementation_expected_output"].lower().startswith(
        "plain-text answer only"
    )
    assert "detailed critique" in placeholders["plain_text_critique_expected_output"].lower()
    assert "refined synthesis" in placeholders["plain_text_synthesis_expected_output"].lower()
    assert placeholders["file_section_response_rules"].startswith(
        "When the task changes files"
    )


def test_build_task_execution_implementer_disables_research_mcps(monkeypatch):
    from execution import runtime

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        runtime,
        "_get_agent_config",
        lambda name: {
            "role": "Technical Implementer",
            "goal": "Execute task",
            "backstory": "Base backstory.",
            "verbose": True,
            "allow_delegation": False,
            "llm_tier": "complex",
            "tool_bundle": "implementer_io",
            "mcp_bundle": "research",
        },
    )
    monkeypatch.setattr(
        runtime,
        "render_yaml_config",
        lambda config, replacements: {**config, **replacements},
    )
    monkeypatch.setattr(
        runtime,
        "build_agent_from_config",
        lambda config: captured.setdefault("config", config) or "agent",
    )

    runtime.build_task_execution_implementer(VisionContext.SELF)

    config = captured["config"]
    assert config["tool_bundle"] == "none"
    assert config["mcp_bundle"] == "none"
    assert "Never finish with a tool call" in config["backstory"]
    assert "Do not use file tools to reread the vision file" in config["backstory"]
    assert "emit complete file contents using `--- relative/path ---` sections" in config["backstory"]
    assert "internal/SELF_VISION.md" in config["vision_path"]


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
    monkeypatch.setattr(runtime, "build_task_execution_implementer", lambda ctx: "impl")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "crit")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}")
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: f"vision:{ctx.value}")
    monkeypatch.setattr(runtime, "style_guide_knowledge", lambda: [])

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
    monkeypatch.setattr(runtime, "build_task_execution_implementer", lambda ctx: "impl")
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
    assert "Definition of done" in captured_tasks[0]["description"]
    assert "Return only the completed plain-text answer" in captured_tasks[0]["description"]
    assert "Do not use file tools to reread the vision file" in captured_tasks[0]["description"]
    assert "--- relative/path/to/file.ext ---" in captured_tasks[0]["description"]
    assert "plain-text answer only" in captured_tasks[0]["expected_output"].lower()
    assert "complete file sections" in captured_tasks[0]["expected_output"].lower()
    assert "static-analysis" in captured_tasks[0]["description"]
    assert "adjacent files" in captured_tasks[0]["description"]
    assert "Return only the completed plain-text answer" in captured_tasks[1]["description"]
    assert "Return only the completed plain-text answer" in captured_tasks[2]["description"]
    assert "plain-text answer only" in captured_tasks[1]["expected_output"].lower()
    assert "plain-text answer only" in captured_tasks[2]["expected_output"].lower()


def test_build_task_dialectic_crew_validation_mentions_integration_quality(monkeypatch):
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
    monkeypatch.setattr(runtime, "build_task_execution_implementer", lambda ctx: "impl")
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

    assert "imports, references, and package/module boundaries" in captured_tasks[3]["description"]
    assert "related tests or supporting files" in captured_tasks[3]["description"]


def test_build_task_dialectic_crew_mentions_self_antidrift_file(monkeypatch):
    from execution import runtime

    captured_tasks = []

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(runtime, "build_task_execution_implementer", lambda ctx: "impl")
    monkeypatch.setattr(runtime, "create_critico_socratico", lambda ctx: "crit")
    monkeypatch.setattr(runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision")

    runtime.build_task_dialectic_crew(
        task_id="T-SELF",
        task_title="Self task",
        task_description="Stay aligned",
        context_str="Self context",
        min_score=7.5,
        vision_context=VisionContext.SELF,
        synthesis_for_retry=None,
        retry=0,
        max_retries=2,
    )

    assert "#file:SELF_VISION.md" in captured_tasks[0]["description"]
    assert "internal/SELF_VISION.md" in captured_tasks[0]["description"]
    assert "#file:SELF_VISION.md" in captured_tasks[1]["description"]
