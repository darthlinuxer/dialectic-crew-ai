"""Tests for CrewAI runtime defaults and kickoff behavior."""

# pylint: disable=missing-function-docstring,too-few-public-methods
# pylint: disable=missing-class-docstring,line-too-long

import os

from dialectic.crewai_runtime import configure_crewai_runtime
from dialectic import crewai_runtime


def test_configure_crewai_runtime_sets_defaults_and_suppresses_prompt(monkeypatch):
    calls: list[tuple[str, object]] = []

    monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)
    monkeypatch.delenv("CREWAI_TRACING_ENABLED", raising=False)

    monkeypatch.setattr(
        crewai_runtime,
        "_load_tracing_utils",
        lambda: (
            lambda suppress: calls.append(("suppress", suppress)),
            lambda **kwargs: calls.append(("mark", kwargs.get("user_consented"))),
            type(
                "Hook",
                (),
                {
                    "set": staticmethod(
                        lambda value: calls.append(
                            ("hook", value() if callable(value) else value)
                        )
                    )
                },
            )(),
            type("Handler", (), {})(),
        ),
    )

    configure_crewai_runtime()

    assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"
    assert os.environ["CREWAI_TRACING_ENABLED"] == "false"
    assert calls == [("suppress", True), ("hook", False), ("mark", False)]


def test_configure_crewai_runtime_respects_explicit_tracing_opt_in(monkeypatch):
    calls: list[tuple[str, object]] = []

    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "true")
    monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)

    monkeypatch.setattr(
        crewai_runtime,
        "_load_tracing_utils",
        lambda: (
            lambda suppress: calls.append(("suppress", suppress)),
            lambda **kwargs: calls.append(("mark", kwargs.get("user_consented"))),
            type(
                "Hook",
                (),
                {
                    "set": staticmethod(
                        lambda value: calls.append(
                            ("hook", value() if callable(value) else value)
                        )
                    )
                },
            )(),
            type("Handler", (), {})(),
        ),
    )

    configure_crewai_runtime()

    assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"
    assert os.environ["CREWAI_TRACING_ENABLED"] == "true"
    assert calls == [("suppress", True), ("hook", False), ("mark", True)]


def test_run_crew_kickoff_prints_summary_when_log_file_is_configured(
    monkeypatch, capsys
):
    calls: list[tuple[str, object]] = []

    class FakeCrew:
        def kickoff(self, **kwargs):
            calls.append(("kickoff", kwargs))
            print("hidden verbose output")
            return "crew-result"

    monkeypatch.setattr(crewai_runtime, "get_output_log_file", lambda: "/tmp/crew.log")
    monkeypatch.setattr(
        crewai_runtime, "is_crewai_event_logger_registered", lambda: False
    )
    monkeypatch.setattr(
        crewai_runtime, "summarize_crew_log", lambda path: f"summary:{path}"
    )

    result = crewai_runtime.run_crew_kickoff(FakeCrew(), sample=True)

    captured = capsys.readouterr()
    assert result == "crew-result"
    assert calls == [("kickoff", {"sample": True})]
    assert captured.out == ""
    assert captured.err.strip() == "summary:/tmp/crew.log"


def test_run_crew_kickoff_skips_summary_when_native_event_logger_is_active(
    monkeypatch,
    capsys,
):
    calls: list[tuple[str, object]] = []

    class FakeCrew:
        def kickoff(self, **kwargs):
            calls.append(("kickoff", kwargs))
            print("hidden verbose output")
            return {"status": "ok"}

    def fail_if_called(path: str) -> str:
        raise AssertionError(f"summarize_crew_log should not run for {path}")

    monkeypatch.setattr(crewai_runtime, "get_output_log_file", lambda: "/tmp/crew.log")
    monkeypatch.setattr(
        crewai_runtime, "is_crewai_event_logger_registered", lambda: True
    )
    monkeypatch.setattr(crewai_runtime, "summarize_crew_log", fail_if_called)

    result = crewai_runtime.run_crew_kickoff(FakeCrew(), sample=False)

    captured = capsys.readouterr()
    assert result == {"status": "ok"}
    assert calls == [("kickoff", {"sample": False})]
    assert captured.out == ""
    assert captured.err == ""
