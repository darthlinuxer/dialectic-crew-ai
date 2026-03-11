from crewai import Agent, Task

from dialectic.yaml_config import get_guardrail_registry


def test_registered_guardrails_are_accepted_by_crewai_task_validation():
    agent = Agent(
        role="Guardrail Validation Tester",
        goal="Exercise CrewAI task validation without executing LLM work",
        backstory="You exist only so tests can instantiate Task objects safely.",
        verbose=False,
        allow_delegation=False,
    )

    for name, guardrail in get_guardrail_registry().items():
        task = Task(
            description=f"Validate guardrail registration for {name}",
            expected_output="Any structured output",
            agent=agent,
            guardrail=guardrail,
        )

        assert task.guardrail is guardrail