# pyright: reportPrivateUsage=none

from tests.conftest import make_prd
from dialectic.tool_bundles import TOOL_BUNDLES
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
    created_agents = []

    def fake_build_agent(template, placeholders):
        agent = f"agent:{template['role']}:{placeholders['vision_label']}"
        created_agents.append(agent)
        return agent

    monkeypatch.setattr(runtime, "_build_agent", fake_build_agent)
    monkeypatch.setattr(
        runtime, "crew_memory", lambda ctx, namespace: f"memory:{ctx.value}:{namespace}"
    )
    monkeypatch.setattr(
        runtime, "vision_knowledge", lambda ctx: f"knowledge:{ctx.value}"
    )

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
        retry_feedback_block="",
        retry_feedback_sources=None,
    )

    assert len(captured_tasks) == 4
    assert "feature context" in captured_tasks[0]["description"]
    assert "story context" in captured_tasks[0]["description"]
    assert captured_tasks[0]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[2]["guardrail"].__name__ == "_text_result_guardrail"
    assert captured_tasks[1]["context"] == [captured_crew["tasks"][0]]
    assert captured_tasks[3]["output_pydantic"].__name__ == "UserStoryExecutionPlan"
    assert captured_tasks[3]["guardrail"].__name__ == "_plan_guardrail"
    assert created_agents == [
        "agent:User Story Planning Visionary:SELF_VISION.md",
        "agent:User Story Planning Critic:SELF_VISION.md",
        "agent:User Story Planning Synthesizer:SELF_VISION.md",
        "agent:User Story Planning Validator:SELF_VISION.md",
    ]
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
    monkeypatch.setattr(
        runtime, "_build_agent", lambda template, placeholders: template["role"]
    )
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
        retry_feedback_block="",
        retry_feedback_sources=None,
    )

    assert captured_crew["agents"] == [
        "User Story Planning Visionary",
        "User Story Planning Critic",
        "User Story Planning Synthesizer",
        "User Story Planning Validator",
    ]


def test_build_planning_crew_appends_retry_feedback_sources(monkeypatch):
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
    monkeypatch.setattr(
        runtime, "_build_agent", lambda template, placeholders: template["role"]
    )
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision-source")

    prd = make_prd()
    us = prd.user_stories[0]

    runtime.build_planning_crew(
        feature_context="feature",
        us=us,
        us_context="story",
        vision_context=VisionContext.PROJECT,
        min_plan_score=7.5,
        retry_feedback_block="RETRY BLOCK",
        retry_feedback_sources=["feedback-source"],
    )

    assert captured_crew["knowledge_sources"] == ["vision-source", "feedback-source"]


def test_build_planning_crew_strips_interactive_tools_from_agents(monkeypatch):
    from planning import runtime

    captured_crew = {}

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeCrew:
        def __init__(self, **kwargs):
            captured_crew.update(kwargs)

    class FakeAgent:
        def __init__(self, label):
            self.label = label
            self.tools = [f"tool:{label}"]
            self.mcps = [f"mcp:{label}"]
            self.mcp_servers = [f"server:{label}"]

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(
        runtime,
        "_build_agent",
        lambda template, placeholders: FakeAgent(template["role"]),
    )
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "vision-source")

    prd = make_prd()
    us = prd.user_stories[0]

    runtime.build_planning_crew(
        feature_context="feature",
        us=us,
        us_context="story",
        vision_context=VisionContext.SELF,
        min_plan_score=7.5,
        retry_feedback_block="",
        retry_feedback_sources=None,
    )

    for agent in captured_crew["agents"]:
        assert agent.tools == []
        assert agent.mcps == []
        assert agent.mcp_servers == []


def test_build_planning_crew_mentions_exact_vision_path(monkeypatch):
    from planning import runtime

    captured_tasks = []

    class FakeAgent:
        def __init__(self, backstory):
            self.backstory = backstory

    class FakeTask:
        def __init__(self, **kwargs):
            captured_tasks.append(kwargs)

    class FakeCrew:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(runtime, "Task", FakeTask)
    monkeypatch.setattr(runtime, "Crew", FakeCrew)
    monkeypatch.setattr(
        runtime,
        "_build_agent",
        lambda template, placeholders: FakeAgent(
            runtime.render_yaml_config(template, placeholders)["backstory"]
        ),
    )
    monkeypatch.setattr(runtime, "crew_memory", lambda ctx, namespace: None)
    monkeypatch.setattr(runtime, "vision_knowledge", lambda ctx: "knowledge")

    prd = make_prd()
    us = prd.user_stories[0]

    runtime.build_planning_crew(
        feature_context="feature",
        us=us,
        us_context="story",
        vision_context=VisionContext.SELF,
        min_plan_score=7.5,
        retry_feedback_block="",
        retry_feedback_sources=None,
    )

    assert "internal/SELF_VISION.md" in captured_tasks[0]["description"]
    assert "Treat the knowledge-source content" in captured_tasks[0]["description"]
    assert (
        "Rely on the provided knowledge sources and task context"
        in captured_tasks[0]["agent"].backstory
    )
    assert (
        "If direct file tools are available" not in captured_tasks[0]["agent"].backstory
    )


def test_build_agent_renders_placeholders_and_binds_runtime(monkeypatch):
    from planning import runtime

    build_agent = getattr(runtime, "_build_agent")

    captured = {}

    def fake_build_agent_from_config(config):
        captured.update(config)
        return "agent"

    monkeypatch.setattr(
        runtime, "build_agent_from_config", fake_build_agent_from_config
    )

    agent = build_agent(
        {
            "role": "Planner for {vision_label}",
            "goal": "Plan {us_title}",
            "backstory": "Context {feature_context} using {vision_path}",
            "llm_tier": "planning",
            "tool_bundle": "planning_read_only",
        },
        {
            "vision_label": "VISION.md",
            "vision_path": "internal/SELF_VISION.md",
            "us_title": "US1",
            "feature_context": "Feature ABC",
        },
    )

    assert agent == "agent"
    assert captured == {
        "role": "Planner for VISION.md",
        "goal": "Plan US1",
        "backstory": "Context Feature ABC using internal/SELF_VISION.md",
        "llm_tier": "planning",
        "tool_bundle": "planning_read_only",
    }


def test_planning_visionary_yaml_uses_local_read_bundle(monkeypatch):
    from planning import runtime

    build_agent = getattr(runtime, "_build_agent")
    agents_config_path = getattr(runtime, "_AGENTS_CONFIG_PATH")

    captured = {}

    def fake_build_agent_from_config(config):
        captured.update(config)
        return "agent"

    monkeypatch.setattr(
        runtime, "build_agent_from_config", fake_build_agent_from_config
    )

    agent_templates = runtime.load_yaml_config(agents_config_path)

    agent = build_agent(
        agent_templates["planning_visionary"],
        {
            "vision_label": "SELF_VISION.md",
            "vision_path": "internal/SELF_VISION.md",
            "us_title": "US1",
            "feature_context": "Feature ABC",
            "us_context": "Story context",
            "us_id": "US-01",
            "min_plan_score": 7.5,
            "retry_feedback_block": "",
        },
    )

    assert agent == "agent"
    assert captured["tool_bundle"] == "planning_read_only"


def test_planning_bundle_avoids_recursive_directory_context():
    tool_names = [
        getattr(tool, "name", "") for tool in TOOL_BUNDLES["planning_read_only"]
    ]

    assert tool_names == ["search_a_files_content"]


def test_planning_validator_bundle_stays_small():
    tool_names = [getattr(tool, "name", "") for tool in TOOL_BUNDLES["validator_read"]]

    assert tool_names == ["search_a_files_content"]
