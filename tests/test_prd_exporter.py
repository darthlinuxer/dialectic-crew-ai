"""Tests for dialectic.export.PRDExporter — JSON+MD export and rollback."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dialectic.export import PRDExporter, ExportException
from dialectic.config import ExportConfig
from schemas import PRDSchema, MacroImpact, UserStory, AntiDriftQuestion


def _make_prd() -> PRDSchema:
    mi = MacroImpact(
        modules_affected=["mod1"],
        risk_level="LOW",
        performance_impact="minor",
        security_impact="low",
    )
    us = UserStory(
        id="US-001",
        title="Test Story",
        description="Test description",
        acceptance_criteria=["AC1", "AC2", "AC3"],
        effort="M",
        dependencies=[],
    )
    adq = [AntiDriftQuestion(question=f"q{i}", answer=f"a{i}") for i in range(5)]
    return PRDSchema(
        feature_name="Test Feature",
        version="1.0",
        objective="Test objective",
        macro_impact=mi,
        user_stories=[us],
        anti_drift_questions=adq,
        quality_score=9.5,
        consensus_reached=True,
        final_validation_notes="Approved",
    )


def test_export_both_creates_json_and_md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig(output_format="both", output_dir=tmp_path)
    exporter = PRDExporter()
    created = exporter.export(prd, config)

    assert len(created) == 2
    extensions = {p.suffix for p in created}
    assert ".json" in extensions
    assert ".md" in extensions
    for p in created:
        assert p.exists()


def test_export_json_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig(output_format="json", output_dir=tmp_path)
    exporter = PRDExporter()
    created = exporter.export(prd, config)

    assert len(created) == 1
    assert created[0].suffix == ".json"
    data = json.loads(created[0].read_text(encoding="utf-8"))
    assert data["feature_name"] == "Test Feature"


def test_export_md_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig(output_format="md", output_dir=tmp_path)
    exporter = PRDExporter()
    created = exporter.export(prd, config)

    assert len(created) == 1
    assert created[0].suffix == ".md"
    md_text = created[0].read_text(encoding="utf-8")
    assert "# Objetivo" in md_text


def test_md_failure_triggers_json_rollback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig(output_format="both", output_dir=tmp_path)
    exporter = PRDExporter()

    original_write = Path.write_text

    def broken_write(self, text, **kwargs):
        if self.suffix == ".md":
            raise OSError("Simulated MD write failure")
        return original_write(self, text, **kwargs)

    with patch.object(Path, "write_text", broken_write):
        with pytest.raises(ExportException):
            exporter.export(prd, config)

    remaining = list(tmp_path.glob("*.json"))
    assert len(remaining) == 0, "JSON should be rolled back when MD fails"


def test_export_encoding_utf8(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    prd.objective = "Teste com acentuação: é, ã, ç"
    config = ExportConfig(output_format="both", output_dir=tmp_path)
    exporter = PRDExporter()
    created = exporter.export(prd, config)

    for p in created:
        content = p.read_text(encoding="utf-8")
        assert "acentuação" in content


def test_export_md_has_frontmatter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VISION.md").write_text("Vision content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig(output_format="md", output_dir=tmp_path)
    exporter = PRDExporter()
    created = exporter.export(prd, config)

    md_text = created[0].read_text(encoding="utf-8")
    assert md_text.startswith("---")
    assert "quality_score:" in md_text
    assert "validation_status:" in md_text
    assert "generated_at:" in md_text
    assert "vision_hash:" in md_text
