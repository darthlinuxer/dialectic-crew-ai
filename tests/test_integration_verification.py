# ruff: noqa: E402

"""Integration test: _run_verification with real LLM (requires API keys)."""

import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from schemas import ImplementationTask


@pytest.mark.llm
@pytest.mark.timeout(300)
def test_run_verification_with_real_llm(monkeypatch):
    """Create a temp file, build an ImplementationTask referencing it,
    then run _run_verification to verify the LLM agent can check it."""
    tmp_dir = tempfile.mkdtemp(prefix="verify_test_")
    monkeypatch.chdir(tmp_dir)

    (Path(tmp_dir) / "knowledge").mkdir(exist_ok=True)
    (Path(tmp_dir) / "knowledge" / "VISION.md").write_text(
        "# Vision\nBuild a robust system.", encoding="utf-8"
    )

    artifact = Path(tmp_dir) / "endpoint.py"
    artifact.write_text(
        "def get_users():\n    return [{'id': 1, 'name': 'Alice'}]\n",
        encoding="utf-8",
    )

    task = ImplementationTask(
        id="T-001",
        title="Create users endpoint",
        description=(
            f"Create a Python file at {artifact} with a get_users() function "
            "that returns a list of user dicts."
        ),
    )

    from execution.verify import _run_verification

    result = _run_verification(task, acceptance_criteria=["get_users function exists"])

    assert "task_id" in result
    assert result["task_id"] == "T-001"
    assert "verified" in result
    assert "score" in result
    assert "notes" in result
    assert isinstance(result["score"], (int, float))
