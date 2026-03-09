"""Integration tests: agent creation and basic LLM execution (requires API keys)."""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Task, Crew


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
def test_single_agent_simple_task():
    """Run validador_macro with a minimal scoring task to verify LLM connectivity."""
    from dialectic.agents import create_validador_macro

    agent = create_validador_macro()
    task = Task(
        description=(
            "Score the following feature request on a scale of 0-10 for clarity:\n"
            "'Add a login page with email and password fields.'\n"
            "Respond with ONLY a number between 0 and 10."
        ),
        expected_output="A number between 0 and 10",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))
    assert any(c.isdigit() for c in raw), f"Expected a numeric score, got: {raw[:200]}"


@pytest.mark.llm
@pytest.mark.timeout(180)
def test_agent_with_tool_usage():
    """Run create_implementer with a file reading task."""
    from dialectic.agents import create_implementer

    tmp_dir = tempfile.mkdtemp(prefix="agent_tool_test_")
    test_file = os.path.join(tmp_dir, "data.txt")
    Path(test_file).write_text("The answer is 42.", encoding="utf-8")

    agent = create_implementer()
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
