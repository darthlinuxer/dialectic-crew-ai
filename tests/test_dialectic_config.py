import pytest
from pathlib import Path

from dialectic.config import _HAS_PYDANTIC_SETTINGS, get_export_config


def test_uppercase_md(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "MD")
    cfg = get_export_config()
    assert cfg.output_format == "md"


def test_json_lower(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "json")
    cfg = get_export_config()
    assert cfg.output_format == "json"


def test_both(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "both")
    cfg = get_export_config()
    assert cfg.output_format == "both"


def test_invalid_fallbacks_to_json(monkeypatch):
    # override any .env value with an invalid value
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "invalid")
    cfg = get_export_config()
    assert cfg.output_format == "both"


def test_empty_or_absent_fallbacks_to_json(monkeypatch):
    # set explicitly to empty string to simulate absent/empty
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "")
    cfg = get_export_config()
    assert cfg.output_format == "both"


def test_output_dir_conversion_and_fallback(monkeypatch, tmp_path):
    # explicit dir provided
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "json")
    monkeypatch.setenv("PRD_OUTPUT_DIR", str(tmp_path / "out"))
    cfg = get_export_config()
    assert isinstance(cfg.output_dir, Path)
    assert cfg.output_dir == Path(str(tmp_path / "out"))

    # remove the env var to test fallback
    monkeypatch.delenv("PRD_OUTPUT_DIR", raising=False)
    cfg2 = get_export_config()
    assert cfg2.output_dir == Path("prd_output")


@pytest.mark.skipif(not _HAS_PYDANTIC_SETTINGS, reason="requires pydantic-settings")
def test_dotenv_with_unrelated_keys_does_not_trigger_fallback(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.delenv("PRD_OUTPUT_FORMAT", raising=False)
    monkeypatch.delenv("PRD_OUTPUT_DIR", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=test-key",
                "LLM_REQUEST_TIMEOUT=180",
                "CREWAI_TRACING_ENABLED=false",
                "PRD_OUTPUT_FORMAT=both",
                f"PRD_OUTPUT_DIR={tmp_path / 'exports'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    caplog.clear()
    cfg = get_export_config(_env_file=env_file)

    assert cfg.output_format == "both"
    assert cfg.output_dir == tmp_path / "exports"
    assert "pydantic-settings unavailable or failed to load" not in caplog.text
