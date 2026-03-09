import pytest
from pathlib import Path

from dialectic.config import get_export_config


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
    assert cfg.output_format == "json"


def test_empty_or_absent_fallbacks_to_json(monkeypatch):
    # set explicitly to empty string to simulate absent/empty
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "")
    cfg = get_export_config()
    assert cfg.output_format == "json"


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
