"""Tests for CrewAI log summarizer (fallback and excerpt)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dialectic.crew_log_summarizer import summarize_crew_log


def test_summarize_crew_log_file_missing():
    out = summarize_crew_log(Path("/nonexistent/crew.log"))
    assert "unavailable" in out.lower() or "not found" in out.lower()


def test_summarize_crew_log_empty_file(tmp_path):
    log_file = tmp_path / "empty.log"
    log_file.write_text("")
    out = summarize_crew_log(log_file)
    assert "empty" in out.lower() or "completed" in out.lower()


def test_summarize_crew_log_whitespace_only(tmp_path):
    log_file = tmp_path / "blank.log"
    log_file.write_text("   \n\n  ")
    out = summarize_crew_log(log_file)
    assert "empty" in out.lower() or "completed" in out.lower() or "content" in out.lower()


def test_summarize_crew_log_llm_failure_returns_fallback(tmp_path):
    log_file = tmp_path / "crew.log"
    log_file.write_text("Task 1 started. Agent thinking...")
    with patch("dialectic.crew_log_summarizer.llm_simple") as mock_llm:
        mock_llm.call.side_effect = RuntimeError("API error")
        out = summarize_crew_log(log_file)
    assert "unavailable" in out.lower() or "error" in out.lower()


def test_summarize_crew_log_llm_empty_response_returns_fallback(tmp_path):
    log_file = tmp_path / "crew.log"
    log_file.write_text("Task 1 started.")
    with patch("dialectic.crew_log_summarizer.llm_simple") as mock_llm:
        mock_llm.call.return_value = ""
        out = summarize_crew_log(log_file)
    assert "unavailable" in out.lower() or "empty" in out.lower()


def test_summarize_crew_log_returns_llm_summary_when_success(tmp_path):
    log_file = tmp_path / "crew.log"
    log_file.write_text("Agent executed task. Validation passed.")
    with patch("dialectic.crew_log_summarizer.llm_simple") as mock_llm:
        mock_llm.call.return_value = "Line 1\nLine 2\nLine 3\nLine 4"
        out = summarize_crew_log(log_file)
    assert "Line 1" in out
    assert "Line 4" in out
