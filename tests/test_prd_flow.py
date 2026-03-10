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


def test_extract_prd_from_result_accepts_json_dict():
    prd = _make_prd()

    class Result:
        json_dict = prd.model_dump()

    extracted = prd_flow._extract_prd_from_result(Result())

    assert extracted is not None
    assert extracted.feature_name == prd.feature_name
    assert extracted.consensus_reached is True


def test_materialize_plain_data_recursively_converts_proxy_mappings():
    class ProxyDict(dict):
        pass

    proxied = ProxyDict(
        {
            "feature_name": "Feature",
            "macro_impact": ProxyDict({"risk_level": "LOW"}),
            "user_stories": [ProxyDict({"id": "US1"})],
        }
    )

    plain = prd_flow._materialize_plain_data(proxied)

    assert isinstance(plain, dict)
    assert isinstance(plain["macro_impact"], dict)
    assert isinstance(plain["user_stories"][0], dict)


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


def test_dialectic_flow_validator_uses_synthesis_as_only_context():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert 'context=[task_sintese]' in source
    assert 'context=[task_vision, task_critica, task_sintese]' not in source


def test_dialectic_flow_synthesizer_requests_candidate_prd_json():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert 'Output a CANDIDATE PRD as raw JSON with these fields only:' in source
    assert 'Candidate PRD as raw JSON for validator review' in source
    assert 'output_json=PRDSchema' in source


def test_dialectic_flow_uses_shared_prd_extractor_after_kickoff():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert 'prd: PRDSchema | None = _extract_prd_from_result(resultado)' in source
    assert 'for task_output in reversed(tasks_out):' in source


def test_run_dialectic_flow_returns_flow_id(monkeypatch):
    mock_flow = type("MockFlow", (), {})()
    mock_flow.flow_id = "flow-123"
    mock_flow.state = type(
        "State",
        (),
        {
            "consensus_reached": True,
            "quality_score": 9.2,
            "retry_count": 1,
            "prd_data": {"feature_name": "Feature"},
            "prd_path_json": "prd_output/test.json",
            "prd_path_md": "prd_output/test.md",
            "final_validation_notes": "ok",
        },
    )()

    captured = {}

    def fake_kickoff(*, inputs):
        captured.update(inputs)

    mock_flow.kickoff = fake_kickoff
    monkeypatch.setattr(prd_flow, "DialecticFlow", lambda persistence: mock_flow)
    monkeypatch.setattr(prd_flow, "_get_persistence", lambda: object())

    result = prd_flow.run_dialectic_flow(
        "Ship resumable PRDs",
        resume_id="flow-123",
    )

    assert captured["id"] == "flow-123"
    assert result["flow_id"] == "flow-123"