"""Tests for CrewAI verbose and log file configuration."""

from __future__ import annotations

from dialectic.crew_verbose_config import get_output_log_file, is_verbose


def test_is_verbose_default_false(monkeypatch):
    monkeypatch.delenv("CREWAI_VERBOSE", raising=False)
    assert is_verbose() is False


def test_is_verbose_true_when_set(monkeypatch):
    monkeypatch.setenv("CREWAI_VERBOSE", "true")
    assert is_verbose() is True
    monkeypatch.setenv("CREWAI_VERBOSE", "1")
    assert is_verbose() is True
    monkeypatch.setenv("CREWAI_VERBOSE", "yes")
    assert is_verbose() is True


def test_is_verbose_false_when_off(monkeypatch):
    monkeypatch.setenv("CREWAI_VERBOSE", "false")
    assert is_verbose() is False
    monkeypatch.setenv("CREWAI_VERBOSE", "0")
    assert is_verbose() is False


def test_get_output_log_file_none_when_not_verbose(monkeypatch):
    monkeypatch.setenv("CREWAI_VERBOSE", "false")
    monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", "/some/path.log")
    assert get_output_log_file() is None


def test_get_output_log_file_explicit_path_when_verbose(monkeypatch):
    monkeypatch.setenv("CREWAI_VERBOSE", "true")
    monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", "/tmp/crew.log")
    assert get_output_log_file() == "/tmp/crew.log"


def test_get_output_log_file_default_under_dialectic_when_verbose_no_path(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("CREWAI_VERBOSE", "true")
    monkeypatch.delenv("CREWAI_OUTPUT_LOG_FILE", raising=False)
    monkeypatch.setenv("DIALECTIC_LOG_DIR", str(tmp_path))
    out = get_output_log_file()
    assert out is not None
    assert "crewai_verbose.log" in out
    assert out == (tmp_path / "crewai_verbose.log").as_posix()


def test_get_output_log_file_strips_and_expands_user(monkeypatch):
    monkeypatch.setenv("CREWAI_VERBOSE", "true")
    monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", "  .dialectic/crew.log  ")
    out = get_output_log_file()
    assert out is not None
    assert "crew.log" in out
