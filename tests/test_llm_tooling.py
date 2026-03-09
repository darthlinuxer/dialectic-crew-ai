"""
Teste isolado: LLM + Tool Calling via CrewAI.

Verifica se os modelos configurados nos tiers invocam ferramentas corretamente.

Uso:
    uv run python tests/test_llm_tooling.py
"""

import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if not (os.getenv("OPENAI_API_KEY") or os.getenv("MINIMAX_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
    print("No API key set in .env — skipping test.")
    sys.exit(0)

from crewai import Agent, Task, Crew, LLM
from crewai_tools import FileReadTool, FileWriterTool

MODELS_TO_TEST = [
    os.getenv("LLM_MODEL_SIMPLE", "gpt-4o-mini"),
    os.getenv("LLM_MODEL_COMPLEX", "gpt-4o"),
    os.getenv("LLM_MODEL_REASONING", "o3-mini"),
]

WRITE_DIR = tempfile.mkdtemp(prefix="llm_tool_test_")
TEST_FILE = os.path.join(WRITE_DIR, "input.txt")
OUTPUT_FILE = os.path.join(WRITE_DIR, "output.txt")

Path(TEST_FILE).write_text("Hello from test file. The secret word is BANANA.", encoding="utf-8")

print(f"Test dir: {WRITE_DIR}")
print(f"Input file: {TEST_FILE}")
print(f"Expected output: {OUTPUT_FILE}")
print("=" * 60)


def run_tool_test(model_name: str) -> dict:
    """Run a simple tool-calling test with one agent."""
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"{'='*60}")

    llm = LLM(model=model_name, timeout=300)

    read_tool = FileReadTool(
        name="read_file",
        description="Read content from a file given its path",
    )
    write_tool = FileWriterTool(
        name="write_file",
        description="Write content to a file",
    )

    agent = Agent(
        role="File Worker",
        goal="Read files and write output files when instructed",
        backstory="You are a simple file worker. You use tools to read and write files. Always use the tools, never just describe what you would do.",
        llm=llm,
        tools=[read_tool, write_tool],
        verbose=True,
        allow_delegation=False,
        max_retry_limit=2,
    )

    task = Task(
        description=f"""
1. Use the read_file tool to read the file at: {TEST_FILE}
2. Find the secret word in the file content.
3. Use the write_file tool to write ONLY the secret word to: {OUTPUT_FILE}

You MUST use the tools. Do NOT just describe what you would do.
""",
        expected_output="Confirmation that the secret word was written to the output file.",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )

    result = crew.kickoff()
    raw = getattr(result, "raw", str(result))

    output_exists = Path(OUTPUT_FILE).exists()
    output_content = ""
    if output_exists:
        output_content = Path(OUTPUT_FILE).read_text(encoding="utf-8").strip()

    tool_invoked = output_exists and len(output_content) > 0
    correct_answer = "BANANA" in output_content.upper() if output_content else False

    return {
        "model": model_name,
        "raw_output": raw[:2000],
        "output_file_exists": output_exists,
        "output_content": output_content,
        "tool_was_invoked": tool_invoked,
        "correct_answer": correct_answer,
    }


if __name__ == "__main__":
    results = []
    for model in MODELS_TO_TEST:
        try:
            r = run_tool_test(model)
            results.append(r)
        except Exception as e:
            results.append({
                "model": model,
                "error": str(e),
                "tool_was_invoked": False,
                "correct_answer": False,
            })
        if Path(OUTPUT_FILE).exists():
            Path(OUTPUT_FILE).unlink()

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"\nModel: {r['model']}")
        if "error" in r:
            print(f"  ERROR: {r['error'][:200]}")
        else:
            print(f"  Output file created: {r['output_file_exists']}")
            print(f"  Output content: '{r['output_content']}'")
            print(f"  Tool was invoked: {r['tool_was_invoked']}")
            print(f"  Correct answer: {r['correct_answer']}")
            print(f"  Raw output (first 500 chars): {r['raw_output'][:500]}")

    all_ok = all(r.get("tool_was_invoked", False) for r in results)
    print(f"\n{'='*60}")
    if all_ok:
        print("VERDICT: All configured LLM tiers support tool calling correctly")
    else:
        failed = [r["model"] for r in results if not r.get("tool_was_invoked", False)]
        print(f"VERDICT: Tool calling FAILED for: {', '.join(failed)}")
    print(f"{'='*60}")
