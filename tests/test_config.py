"""Tests for dialectic.config.get_export_config() — format validation."""

from dialectic.config import get_export_config


def test_default_format(monkeypatch):
    monkeypatch.delenv("PRD_OUTPUT_FORMAT", raising=False)
    cfg = get_export_config()
    assert cfg.output_format == "both"


def test_explicit_both(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "both")
    cfg = get_export_config()
    assert cfg.output_format == "both"


def test_invalid_format_falls_back(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "invalid")
    cfg = get_export_config()
    assert cfg.output_format == "both"
