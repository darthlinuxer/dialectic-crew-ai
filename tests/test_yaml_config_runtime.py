from pathlib import Path

from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


def test_load_yaml_config_reads_agent_templates():
    config_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "dialectic"
        / "config"
        / "agents.yaml"
    )

    config = load_yaml_config(config_path)

    assert "visionario" in config
    assert config["visionario"]["role"] == "Senior Visionary Architect"


def test_render_yaml_config_resolves_nested_placeholders():
    template = {
        "role": "Architect for {vision_label}",
        "nested": ["{vision_label}", {"goal": "Guard {vision_label}"}],
    }

    rendered = render_yaml_config(template, {"vision_label": "SELF_VISION.md"})

    assert rendered == {
        "role": "Architect for SELF_VISION.md",
        "nested": ["SELF_VISION.md", {"goal": "Guard SELF_VISION.md"}],
    }


def test_resolve_output_schema_returns_expected_model():
    schema = resolve_output_schema("PRDSchema")

    assert schema.__name__ == "PRDSchema"


def test_resolve_guardrail_returns_expected_callable():
    guardrail = resolve_guardrail("prd")

    assert callable(guardrail)
    assert guardrail.__name__ == "_prd_guardrail"


def test_resolve_output_schema_rejects_unknown_name():
    try:
        resolve_output_schema("NotRealSchema")
    except KeyError as exc:
        assert "Unknown output schema" in str(exc)
    else:
        raise AssertionError("Expected unknown schema lookup to fail")


def test_resolve_guardrail_rejects_unknown_name():
    try:
        resolve_guardrail("nope")
    except KeyError as exc:
        assert "Unknown guardrail" in str(exc)
    else:
        raise AssertionError("Expected unknown guardrail lookup to fail")
