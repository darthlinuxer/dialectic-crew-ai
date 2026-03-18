# ruff: noqa: E402

"""Integration tests: agent creation and basic LLM execution (requires API keys)."""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Task, Crew
from schemas import ValidationOutput


@pytest.mark.llm
def test_create_all_agents():
    """Verify all 5 agent factories return Agent instances with correct roles."""
    from dialectic.agents import (
        create_visionario,
        create_critico_socratico,
        create_sintetizador,
        create_validador_macro,
        create_implementer,
    )

    agents = {
        "visionario": create_visionario(),
        "critico": create_critico_socratico(),
        "sintetizador": create_sintetizador(),
        "validador": create_validador_macro(),
        "implementer": create_implementer(),
    }

    for name, agent in agents.items():
        assert isinstance(agent, Agent), f"{name} is not an Agent"
        assert agent.role, f"{name} has no role"
        assert agent.goal, f"{name} has no goal"


@pytest.mark.llm
@pytest.mark.timeout(180)
def test_single_agent_simple_task(tmp_path, monkeypatch):
    """Run validador_macro with a minimal scoring task to verify LLM connectivity."""
    from dialectic.agents import create_validador_macro

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    (knowledge_dir / "VISION.md").write_text(
        "# Vision\nBuild a robust system that prioritizes clarity and user value.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    agent = create_validador_macro()
    task = Task(
        description=(
            "Evaluate the following feature request for clarity and alignment with the vision:\n"
            "'Add a login page with email and password fields.'\n"
            "Return a validation result with a quality_score between 0 and 10, "
            "set consensus_reached to true or false, and include brief final_validation_notes."
        ),
        expected_output=(
            "A ValidationOutput containing quality_score, consensus_reached, "
            "and final_validation_notes."
        ),
        agent=agent,
        output_pydantic=ValidationOutput,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    structured = getattr(result, "pydantic", None)
    assert isinstance(structured, ValidationOutput), (
        f"Expected ValidationOutput, got: {type(structured)!r}"
    )
    assert 0.0 <= structured.quality_score <= 10.0
    assert isinstance(structured.consensus_reached, bool)
    assert structured.final_validation_notes.strip()


@pytest.mark.llm
@pytest.mark.timeout(180)
def test_agent_with_tool_usage(monkeypatch):
    """Run create_implementer with a file reading task."""
    import dialectic.agents as agents

    tmp_dir = tempfile.mkdtemp(prefix="agent_tool_test_")
    test_file = os.path.join(tmp_dir, "data.txt")
    Path(test_file).write_text("The answer is 42.", encoding="utf-8")

    monkeypatch.setitem(agents.MCP_BUNDLES, "research", [])

    agent = agents.create_implementer()
    task = Task(
        description=(
            f"Read the file at {test_file} using your file reading tool. "
            "What number is mentioned as 'the answer'? Reply with just the number."
        ),
        expected_output="The number mentioned in the file",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))
    assert "42" in raw, f"Expected '42' in output, got: {raw[:200]}"
