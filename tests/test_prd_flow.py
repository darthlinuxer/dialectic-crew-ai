"""Focused tests for PRD flow retry feedback handling."""

import inspect
import json

import dialectic.prd_flow as prd_flow
from schemas import AntiDriftQuestion, MacroImpact, PRDSchema, UserStory


def test_build_retry_feedback_context_inlines_full_feedback_below_threshold():
    feedback = "Issue A\nIssue B\nIssue C"

    prompt_block, knowledge_sources = prd_flow._build_retry_feedback_context(
        feedback,
        retry_count=1,
    )

    assert "PREVIOUS ROUND VALIDATION FEEDBACK:" in prompt_block
    assert feedback in prompt_block
    assert "consult it" not in prompt_block.lower()
    assert knowledge_sources == []


def test_build_retry_feedback_context_uses_knowledge_for_large_feedback(monkeypatch):
    captured: list[dict] = []

    class FakeStringKnowledgeSource:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(prd_flow, "StringKnowledgeSource", FakeStringKnowledgeSource)
    feedback = "A" * (prd_flow.RETRY_FEEDBACK_INLINE_CHAR_THRESHOLD + 1)

    prompt_block, knowledge_sources = prd_flow._build_retry_feedback_context(
        feedback,
        retry_count=2,
    )

    assert "available in your knowledge sources" in prompt_block
    assert feedback not in prompt_block
    assert len(knowledge_sources) == 1
    assert captured[0]["chunk_size"] == 1200
    assert captured[0]["chunk_overlap"] == 150
    assert feedback in captured[0]["content"]


def test_build_retry_feedback_context_skips_first_round():
    prompt_block, knowledge_sources = prd_flow._build_retry_feedback_context(
        "Issue A",
        retry_count=0,
    )

    assert prompt_block == ""
    assert knowledge_sources == []


def _make_prd() -> PRDSchema:
    return PRDSchema(
        feature_name="Feature",
        version="1.0",
        objective="Improve validation",
        macro_impact=MacroImpact(
            modules_affected=["src/dialectic/prd_flow.py"],
            risk_level="LOW",
            performance_impact="Low",
            security_impact="Low",
        ),
        user_stories=[
            UserStory(
                id="US1",
                title="Story",
                description="Desc",
                acceptance_criteria=[
                    "It works",
                    "It is validated",
                    "It is documented",
                ],
                effort="S",
                dependencies=[],
            )
        ],
        anti_drift_questions=[
            AntiDriftQuestion(question=f"Q{i}", answer=f"A{i}") for i in range(1, 6)
        ],
        quality_score=9.1,
        consensus_reached=True,
        final_validation_notes="Approved",
    )


def test_extract_prd_from_result_accepts_raw_json():
    prd = _make_prd()

    class Result:
        raw = json.dumps(prd.model_dump())

    extracted = prd_flow._extract_prd_from_result(Result())

    assert extracted is not None
    assert extracted.feature_name == prd.feature_name
    assert extracted.quality_score == prd.quality_score


def test_prd_guardrail_accepts_raw_json():
    prd = _make_prd()

    class Result:
        raw = json.dumps(prd.model_dump())

    ok, payload = prd_flow._prd_guardrail(Result())

    assert ok is True
    assert payload.raw


def test_dialectic_flow_uses_method_refs_for_retry_listener_wiring():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert '@listen(or_(iniciar_dialetica, fazer_retry))' in source
    assert '@listen(or_("iniciar_dialetica", "fazer_retry"))' not in source