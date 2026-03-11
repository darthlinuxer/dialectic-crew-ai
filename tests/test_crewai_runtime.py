import os

from dialectic.crewai_runtime import configure_crewai_runtime
import dialectic.crewai_runtime as crewai_runtime


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
            type("Hook", (), {"set": staticmethod(lambda value: calls.append(("hook", value() if callable(value) else value)))})(),
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
            type("Hook", (), {"set": staticmethod(lambda value: calls.append(("hook", value() if callable(value) else value)))})(),
            type("Handler", (), {})(),
        ),
    )

    configure_crewai_runtime()

    assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"
    assert os.environ["CREWAI_TRACING_ENABLED"] == "true"
    assert calls == [("suppress", True), ("hook", False), ("mark", True)]