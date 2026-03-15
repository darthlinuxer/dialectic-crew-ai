"""Regression tests for PRD runtime task prompt construction."""

from dialectic import prd_runtime
from dialectic.vision import VisionContext


def test_build_prd_crew_uses_yaml_templates(monkeypatch):
    """Build the PRD crew from YAML task templates and preserve task wiring."""

    captured_tasks = []
    captured_crew = {}

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Lightweight task stub capturing CrewAI task construction inputs."""

        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)
            self.kwargs = kwargs

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Lightweight crew stub capturing final CrewAI crew construction."""

        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(
        prd_runtime,
        "crew_memory",
        lambda ctx, namespace: f"memory:{ctx.value}:{namespace}",
    )
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
    assert captured_tasks[0]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[2]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[2]["context"] == [captured_crew["tasks"][0], captured_crew["tasks"][1]]
    assert captured_tasks[3]["context"] == [
        captured_crew["tasks"][0],
        captured_crew["tasks"][1],
        captured_crew["tasks"][2],
    ]
    assert captured_tasks[3]["output_pydantic"].__name__ == "PRDSchema"
    assert captured_tasks[3]["guardrail"].__name__ == "_prd_guardrail"
    assert captured_crew["knowledge_sources"] == ["vision:self", "feedback-source"]
    assert captured_crew["memory"].startswith("memory:self:prd/")
    assert captured_crew["planning"] is False


def test_build_prd_crew_strips_interactive_tools_from_agents(monkeypatch):
    """Prevent PRD agents from returning raw tool-call outputs as final answers."""

    captured_crew = {}

    class FakeTask:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeCrew:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    class FakeAgent:  # pylint: disable=too-few-public-methods
        def __init__(self, label):
            self.label = label
            self.tools = [f"tool:{label}"]
            self.mcps = [f"mcp:{label}"]
            self.mcp_servers = [f"server:{label}"]

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: FakeAgent("visionario"))
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: FakeAgent("critico"))
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: FakeAgent("sint"))
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: FakeAgent("val"))
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Prevent PRD tool-call leakage",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    for agent in captured_crew["agents"]:
        assert agent.tools == []
        assert agent.mcps == []
        assert agent.mcp_servers == []


def test_prd_memory_namespace_is_feature_scoped():
    first = prd_runtime._prd_memory_namespace("Ship resilient PRD validation")
    second = prd_runtime._prd_memory_namespace("Ship resilient PRD validation")
    third = prd_runtime._prd_memory_namespace("A different feature entirely")

    assert first == second
    assert first.startswith("prd/")
    assert third.startswith("prd/")
    assert first != third


def test_build_prd_crew_uses_explicit_memory_namespace_override(monkeypatch):
    captured_crew = {}

    class FakeTask:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeCrew:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(
        prd_runtime,
        "crew_memory",
        lambda ctx, namespace: f"memory:{ctx.value}:{namespace}",
    )
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Explicit namespace",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
        memory_namespace="prd/test-flow-id",
    )

    assert captured_crew["memory"] == "memory:self:prd/test-flow-id"


def test_build_prd_crew_includes_exact_vision_path_in_prompts(monkeypatch):
    """Render self-context task prompts with the exact self vision path."""

    captured_tasks = []

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Capture rendered task configuration for assertions."""

        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Minimal crew stub for prompt rendering tests."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Harden self-improve vision alignment",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    for task in captured_tasks:
        assert "internal/SELF_VISION.md" in task["description"]
        assert "lack of file-tool access is NOT a blocker" in task["description"]


def test_build_prd_crew_prompts_require_using_upstream_task_context(monkeypatch):
    """Require downstream PRD tasks to use prior task context instead of re-asking."""

    captured_tasks = []

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Capture rendered task configuration for assertions."""

        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Minimal crew stub for context prompt tests."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Harden self-improve PRD context propagation",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    assert "Do NOT ask the user for the PRD" in captured_tasks[1]["description"]
    assert "Do NOT ask the user to resend them" in captured_tasks[2]["description"]
    assert "Do NOT ask the user to resend Task 3 output" in captured_tasks[3]["description"]


def test_build_prd_crew_validation_prompt_avoids_impossible_schema_requirements(monkeypatch):
    """Avoid instructing the validator to require fields absent from PRDSchema."""

    captured_tasks = []

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Capture rendered task configuration for assertions."""

        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Minimal crew stub for validator prompt tests."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(prd_runtime, "Task", FakeTask)
    monkeypatch.setattr(prd_runtime, "Crew", FakeCrew)
    monkeypatch.setattr(prd_runtime, "create_visionario", lambda ctx: "visionario")
    monkeypatch.setattr(prd_runtime, "create_critico_socratico", lambda ctx: "critico")
    monkeypatch.setattr(prd_runtime, "create_sintetizador", lambda ctx: "sint")
    monkeypatch.setattr(prd_runtime, "create_validador_macro", lambda ctx: "val")
    monkeypatch.setattr(prd_runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(prd_runtime, "vision_knowledge", lambda ctx: "vision")

    prd_runtime.build_prd_crew(
        feature_objective="Prevent impossible PRD validation criteria",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    validation_prompt = captured_tasks[3]["description"]
    assert "Do NOT require separate top-level fields" in validation_prompt
    assert "standalone VisionContext field" in validation_prompt
    assert "standalone mapping-table field" in validation_prompt
    assert "Never return a tool call" in validation_prompt


def test_build_prd_crew_preserves_agent_order(monkeypatch):
    """Keep the PRD crew agent order stable across template rendering."""

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Minimal task stub used only to satisfy Crew construction."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_crew = {}

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Capture the final ordered crew configuration."""

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


def test_build_prd_crew_disables_internal_planner_to_avoid_toolless_stalls(monkeypatch):
    """Disable CrewAI's internal planner for PRD crews to avoid runtime stalls."""

    class FakeTask:  # pylint: disable=too-few-public-methods
        """Minimal task stub used only to satisfy Crew construction."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    captured_crew = {}

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Capture final crew construction flags for runtime regression coverage."""

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
        feature_objective="Avoid planner loops before PRD generation",
        vision_context=VisionContext.SELF,
        retry_feedback_block="",
        retry_feedback_sources=[],
    )

    assert captured_crew["planning"] is False
    assert "planning_llm" not in captured_crew
