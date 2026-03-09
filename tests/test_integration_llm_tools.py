"""Integration tests: LLM tool calling via CrewAI (requires API keys).

Each test verifies that a configured LLM tier can invoke FileReadTool
and FileWriterTool correctly through a single-agent Crew.
"""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Task, Crew, LLM
from crewai_tools import FileReadTool, FileWriterTool

LLM_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "900"))


def _run_tool_test(model_name: str) -> dict:
    """Create a temp file, ask a single agent to read it and write the secret."""
    write_dir = tempfile.mkdtemp(prefix="llm_tool_test_")
    test_file = os.path.join(write_dir, "input.txt")
    output_file = os.path.join(write_dir, "output.txt")
    Path(test_file).write_text(
        "Hello from test file. The secret word is BANANA.", encoding="utf-8"
    )

    llm = LLM(model=model_name, timeout=LLM_TIMEOUT)
    read_tool = FileReadTool(name="read_file", description="Read content from a file")
    write_tool = FileWriterTool(name="write_file", description="Write content to a file")

    agent = Agent(
        role="File Worker",
        goal="Read files and write output files when instructed",
        backstory="You use tools to read and write files. Always use the tools.",
        llm=llm,
        tools=[read_tool, write_tool],
        verbose=False,
        allow_delegation=False,
        max_retry_limit=2,
    )
    task = Task(
        description=(
            f"1. Use read_file to read: {test_file}\n"
            f"2. Find the secret word in the content.\n"
            f"3. Use write_file to write ONLY the secret word to: {output_file}\n"
            "You MUST use the tools."
        ),
        expected_output="Confirmation that the secret word was written.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    crew.kickoff()

    output_exists = Path(output_file).exists()
    output_content = ""
    if output_exists:
        output_content = Path(output_file).read_text(encoding="utf-8").strip()

    return {
        "output_exists": output_exists,
        "output_content": output_content,
        "tool_invoked": output_exists and len(output_content) > 0,
        "correct": "BANANA" in output_content.upper() if output_content else False,
    }


@pytest.mark.llm
@pytest.mark.timeout(300)
def test_llm_simple_tool_calling():
    model = os.getenv("LLM_MODEL_SIMPLE", "gpt-4o-mini")
    result = _run_tool_test(model)
    assert result["tool_invoked"], f"Model {model} did not invoke tools"
    assert result["correct"], f"Model {model} wrote wrong content: {result['output_content']}"


@pytest.mark.llm
@pytest.mark.timeout(300)
def test_llm_complex_tool_calling():
    model = os.getenv("LLM_MODEL_COMPLEX", "gpt-4o")
    result = _run_tool_test(model)
    assert result["tool_invoked"], f"Model {model} did not invoke tools"
    assert result["correct"], f"Model {model} wrote wrong content: {result['output_content']}"


@pytest.mark.llm
@pytest.mark.timeout(300)
def test_llm_reasoning_tool_calling():
    model = os.getenv("LLM_MODEL_REASONING", "o3-mini")
    result = _run_tool_test(model)
    assert result["tool_invoked"], f"Model {model} did not invoke tools"
    assert result["correct"], f"Model {model} wrote wrong content: {result['output_content']}"
