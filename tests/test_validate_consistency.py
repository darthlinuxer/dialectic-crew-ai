import json
from pathlib import Path
import hashlib

import pytest

from dialectic.export import render_markdown, validate_consistency
from dialectic.config import ExportConfig
from schemas import PRDSchema, MacroImpact, UserStory, AntiDriftQuestion


def _make_prd():
    mi = MacroImpact(
        modules_affected=["mod1", "mod2"],
        risk_level="LOW",
        performance_impact="minor",
        security_impact="low",
    )
    us = UserStory(
        id="US-001",
        title="Sample",
        description="Do something",
        acceptance_criteria=["AC1", "AC2", "AC3"],
        effort="M",
        dependencies=[],
    )
    adq = [AntiDriftQuestion(question=f"q{i}", answer=f"a{i}") for i in range(5)]
    prd = PRDSchema(
        feature_name="Feat",
        version="1.0",
        objective="Objective",
        macro_impact=mi,
        user_stories=[us],
        anti_drift_questions=adq,
        quality_score=9.0,
        consensus_reached=True,
        final_validation_notes="ok",
    )
    return prd


def test_success_consistency(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    vision = tmp_path / "knowledge" / "VISION.md"
    vision.write_text("Vision Content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig()

    md_text = render_markdown(prd, config)
    md_path = tmp_path / "prd.md"
    md_path.write_text(md_text, encoding="utf-8")

    json_path = tmp_path / "prd.json"
    json_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

    res = validate_consistency(md_path, json_path, prd)
    assert res.is_valid, f"Expected valid but got errors: {res.errors} warnings: {res.warnings}"


def test_missing_headers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    vision = tmp_path / "knowledge" / "VISION.md"
    vision.write_text("Vision Content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig()

    # create MD without required headers
    md_path = tmp_path / "bad.md"
    md_path.write_text("# Some Title\n\nNo required headers here", encoding="utf-8")

    json_path = tmp_path / "prd.json"
    json_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

    res = validate_consistency(md_path, json_path, prd)
    assert not res.is_valid
    assert any("Missing required header" in e for e in res.errors)


def test_quality_score_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    vision = tmp_path / "knowledge" / "VISION.md"
    vision.write_text("Vision Content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig()

    md_text = render_markdown(prd, config)
    # manipulate frontmatter to change quality_score
    lines = md_text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("quality_score:"):
            lines[i] = "quality_score: 5.0"
            break
    md_path = tmp_path / "prd_q_mismatch.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    json_path = tmp_path / "prd.json"
    json_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

    res = validate_consistency(md_path, json_path, prd)
    assert not res.is_valid
    assert any("quality_score mismatch" in e for e in res.errors)


def test_vision_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    vision = tmp_path / "knowledge" / "VISION.md"
    vision.write_text("Original Vision", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig()
    md_text = render_markdown(prd, config)

    # now alter VISION.md to change its hash
    vision.write_text("Modified Vision", encoding="utf-8")

    md_path = tmp_path / "prd_vmismatch.md"
    md_path.write_text(md_text, encoding="utf-8")

    json_path = tmp_path / "prd.json"
    json_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

    res = validate_consistency(md_path, json_path, prd)
    assert not res.is_valid
    assert any("vision_hash in MD does not match" in e or "could not be read to verify" in e for e in res.errors)


def test_json_mismatch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    vision = tmp_path / "knowledge" / "VISION.md"
    vision.write_text("Vision Content", encoding="utf-8")

    prd = _make_prd()
    config = ExportConfig()
    md_text = render_markdown(prd, config)
    md_path = tmp_path / "prd.md"
    md_path.write_text(md_text, encoding="utf-8")

    # create JSON with mismatched feature_name
    bad = json.loads(prd.model_dump_json(indent=2))
    bad["feature_name"] = "Different"
    json_path = tmp_path / "bad.json"
    json_path.write_text(json.dumps(bad, indent=2, ensure_ascii=False), encoding="utf-8")

    res = validate_consistency(md_path, json_path, prd)
    assert not res.is_valid
    assert any("feature_name mismatch" in e for e in res.errors)
