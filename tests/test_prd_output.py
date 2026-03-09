"""Tests for dialectic.prd_output.get_prd_output_format()."""

from dialectic.prd_output import get_prd_output_format


def test_default_fallback(monkeypatch):
    monkeypatch.delenv("PRD_OUTPUT_FORMAT", raising=False)
    assert get_prd_output_format() == "json"


def test_valid_values(monkeypatch):
    for v, exp in [("md", "md"), ("JSON", "json"), ("Both", "both")]:
        monkeypatch.setenv("PRD_OUTPUT_FORMAT", v)
        assert get_prd_output_format() == exp


def test_invalid_value(monkeypatch):
    monkeypatch.setenv("PRD_OUTPUT_FORMAT", "invalid-value")
    assert get_prd_output_format() == "json"
