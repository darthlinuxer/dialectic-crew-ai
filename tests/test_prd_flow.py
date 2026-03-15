"""Focused tests for PRD flow retry feedback handling."""

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=protected-access,too-few-public-methods,import-outside-toplevel
# pylint: disable=consider-using-with,unnecessary-lambda,line-too-long
# pylint: disable=use-implicit-booleaness-not-comparison,consider-using-from-import

import inspect
import json
import logging
from types import SimpleNamespace
from typing import Any, cast

import dialectic.prd_guardrails as prd_guardrails
import dialectic.prd_flow as prd_flow
from schemas import AntiDriftQuestion, MacroImpact, PRDSchema, UserStory


def test_build_retry_feedback_context_inlines_full_feedback_below_threshold():
    feedback = "Issue A\nIssue B\nIssue C"

    prompt_block, knowledge_sources = prd_guardrails._build_retry_feedback_context(
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

    monkeypatch.setattr(prd_guardrails, "StringKnowledgeSource", FakeStringKnowledgeSource)
    feedback = "A" * (prd_guardrails.RETRY_FEEDBACK_INLINE_CHAR_THRESHOLD + 1)

    prompt_block, knowledge_sources = prd_guardrails._build_retry_feedback_context(
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
    prompt_block, knowledge_sources = prd_guardrails._build_retry_feedback_context(
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

    extracted = prd_guardrails._extract_prd_from_result(Result())

    assert extracted is not None
    assert extracted.feature_name == prd.feature_name
    assert extracted.quality_score == prd.quality_score


def test_extract_prd_from_result_accepts_json_dict():
    prd = _make_prd()

    class Result:
        json_dict = prd.model_dump()

    extracted = prd_guardrails._extract_prd_from_result(Result())

    assert extracted is not None
    assert extracted.feature_name == prd.feature_name
    assert extracted.consensus_reached is True


def test_extract_prd_from_result_accepts_pydantic_instance():
    prd = _make_prd()

    class Result:
        pydantic = prd

    extracted = prd_guardrails._extract_prd_from_result(Result())

    assert extracted is prd


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

    plain = prd_guardrails._materialize_plain_data(proxied)

    assert isinstance(plain, dict)
    assert isinstance(plain["macro_impact"], dict)
    assert isinstance(plain["user_stories"][0], dict)


def test_prd_guardrail_accepts_raw_json():
    prd = _make_prd()

    class Result:
        raw = json.dumps(prd.model_dump())

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is True
    assert isinstance(payload, str)
    assert 'feature_name' in payload


def test_prd_guardrail_accepts_pydantic_result():
    prd = _make_prd()

    class Result:
        pydantic = prd
        raw = json.dumps(prd.model_dump())

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is True
    assert isinstance(payload, str)
    assert 'feature_name' in payload


def test_prd_guardrail_serializes_pydantic_without_raw():
    prd = _make_prd()

    class Result:
        pydantic = prd

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is True
    assert isinstance(payload, str)
    assert 'feature_name' in payload


def test_prd_guardrail_ignores_unrelated_raw_json_fragments():
    prd = _make_prd()

    class Result:
        pydantic = prd
        raw = '{"file_path": "internal/SELF_VISION.md", "line_count": 200}'

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is True
    assert isinstance(payload, str)
    assert 'internal/SELF_VISION.md' not in payload
    assert 'feature_name' in payload


def test_prd_guardrail_rejects_placeholder_acceptance_criterion():
    prd = _make_prd().model_copy(deep=True)
    prd_data = prd.model_dump()
    prd_data["user_stories"][0]["acceptance_criteria"][2] = "effort "

    class Result:
        raw = json.dumps(prd_data)

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is False
    assert "valid PRDSchema JSON" in payload


def test_prd_guardrail_rejects_circular_story_dependencies():
    prd = _make_prd().model_copy(deep=True)
    prd_data = prd.model_dump()
    prd_data["user_stories"] = [
        {
            "id": "US-001",
            "title": "Read memory",
            "description": "Retrieve persisted memory safely.",
            "acceptance_criteria": ["A", "B", "C"],
            "effort": "M",
            "dependencies": ["US-002"],
        },
        {
            "id": "US-002",
            "title": "Write memory",
            "description": "Persist memory safely.",
            "acceptance_criteria": ["D", "E", "F"],
            "effort": "M",
            "dependencies": ["US-001"],
        },
    ]

    class Result:
        raw = json.dumps(prd_data)

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is False
    assert "circular dependenc" in payload.lower()


def test_prd_guardrail_logs_dependency_rejection(caplog):
    prd = _make_prd().model_copy(deep=True)
    prd_data = prd.model_dump()
    prd_data["user_stories"][0]["dependencies"] = ["US-999"]

    class Result:
        raw = json.dumps(prd_data)

    with caplog.at_level(logging.WARNING):
        ok, _ = prd_guardrails._prd_guardrail(Result())

    assert ok is False
    assert "dependency-graph-rejected by prd guardrail" in caplog.text


def test_prd_guardrail_rejects_unknown_story_dependencies():
    prd = _make_prd().model_copy(deep=True)
    prd_data = prd.model_dump()
    prd_data["user_stories"][0]["dependencies"] = ["US-999"]

    class Result:
        raw = json.dumps(prd_data)

    ok, payload = prd_guardrails._prd_guardrail(Result())

    assert ok is False
    assert "unknown dependenc" in payload.lower()


def test_dialectic_flow_uses_explicit_retry_label_listener_wiring():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert '@router(iniciar_dialetica)' in source
    assert '@listen("rodar_rodada")' in source
    assert '@listen("retry")' not in source


def test_dialectic_flow_validator_uses_full_dialectic_context():
    import dialectic.prd_runtime as prd_runtime

    source = inspect.getsource(prd_runtime._build_prd_tasks)

    assert 'context=[task_vision, task_critica, task_sintese]' in source


def test_dialectic_flow_synthesizer_requests_candidate_prd_json():
    runtime_source = inspect.getsource(prd_flow.build_prd_crew)
    template_source = inspect.getsource(__import__("dialectic.prd_runtime", fromlist=["build_prd_crew"]).build_prd_crew)

    source = runtime_source + template_source + open("/home/darthlinuxer/dialectic-crew-ai/src/dialectic/config/tasks_prd.yaml", "r", encoding="utf-8").read()

    assert 'Output a CANDIDATE PRD as raw JSON with these fields only:' in source
    assert 'Candidate PRD as raw JSON for validator review' in source
    assert 'output_schema: PRDSchema' in source


def test_dialectic_flow_uses_shared_prd_extractor_after_kickoff():
    source = inspect.getsource(prd_flow.DialecticFlow)

    assert 'prd: PRDSchema | None = _extract_prd_from_result(resultado)' in source
    assert 'for task_output in reversed(tasks_out):' in source


def test_rodar_rodada_dialetica_persists_pydantic_prd_result(monkeypatch):
    prd = _make_prd()
    captured_kwargs = {}

    class FakeHookScope:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return SimpleNamespace(total_tokens=0, budget=0)

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeCrew:
        def kickoff(self, **kwargs):
            del kwargs
            return SimpleNamespace(pydantic=prd)

    def fake_build_prd_crew(**kwargs):
        captured_kwargs.update(kwargs)
        return FakeCrew()

    monkeypatch.setattr(prd_flow, "build_prd_crew", fake_build_prd_crew)
    monkeypatch.setattr(prd_flow, "HookScope", FakeHookScope)

    flow = prd_flow.DialecticFlow()
    flow.state.feature_objective = "Ship resilient PRD validation"
    flow.state.vision_context = prd_flow.VisionContext.SELF.value
    flow.state.retry_count = 0
    flow.state.final_validation_notes = ""
    flow.state.file_paths = []

    next_step = cast(Any, getattr(prd_flow.DialecticFlow, "rodar_rodada_dialetica"))(flow)

    assert next_step == "avaliar"
    assert flow.state.prd_data["feature_name"] == prd.feature_name
    assert flow.state.quality_score == prd.quality_score
    assert flow.state.consensus_reached is True
    assert flow.state.final_validation_notes == prd.final_validation_notes
    assert captured_kwargs["memory_namespace"] == f"prd/{flow.flow_id}"


def test_avaliar_approves_when_consensus_floor_is_met():
    flow = prd_flow.DialecticFlow()
    flow.state.quality_score = 8.6
    flow.state.consensus_reached = True
    flow.state.consensus_min_score = 8.5
    flow.state.retry_count = 1
    flow.state.max_retries = 5

    next_step = cast(Any, getattr(prd_flow.DialecticFlow, "avaliar"))(flow)

    assert next_step == "aprovar"
    assert flow.state.current_phase == "save"


def test_avaliar_retries_when_consensus_floor_is_not_met(capsys):
    flow = prd_flow.DialecticFlow()
    flow.state.quality_score = 8.4
    flow.state.consensus_reached = True
    flow.state.consensus_min_score = 8.5
    flow.state.retry_count = 1
    flow.state.max_retries = 5
    flow.state.final_validation_notes = "needs stronger acceptance criteria"

    next_step = cast(Any, getattr(prd_flow.DialecticFlow, "avaliar"))(flow)

    captured = capsys.readouterr()
    assert next_step == "rodar_rodada"
    assert flow.state.current_phase == "dialectic"
    assert flow.state.retry_count == 2
    assert "Consensus reached, but score 8.4 is below consensus floor 8.5" in captured.out


def test_run_dialectic_flow_returns_flow_id(monkeypatch):
    mock_flow = SimpleNamespace(
        flow_id="flow-123",
        state=SimpleNamespace(
            consensus_reached=True,
            quality_score=9.2,
            retry_count=1,
            prd_data={"feature_name": "Feature"},
            prd_path_json="prd_output/test.json",
            prd_path_md="prd_output/test.md",
            final_validation_notes="ok",
        ),
    )

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


def test_run_dialectic_flow_passes_max_retries_override(monkeypatch):
    mock_flow = SimpleNamespace(
        flow_id="flow-456",
        state=SimpleNamespace(
            consensus_reached=False,
            quality_score=8.8,
            retry_count=2,
            prd_data={"feature_name": "Feature"},
            prd_path_json="",
            prd_path_md="",
            final_validation_notes="needs one more round",
        ),
    )

    captured = {}

    def fake_kickoff(*, inputs):
        captured.update(inputs)

    mock_flow.kickoff = fake_kickoff
    monkeypatch.setattr(prd_flow, "DialecticFlow", lambda persistence: mock_flow)
    monkeypatch.setattr(prd_flow, "_get_persistence", lambda: object())

    prd_flow.run_dialectic_flow(
        "Ship resilient PRD validation",
        max_retries=7,
    )

    assert captured["max_retries"] == 7


def test_run_dialectic_flow_passes_consensus_min_score_override(monkeypatch):
    mock_flow = SimpleNamespace(
        flow_id="flow-789",
        state=SimpleNamespace(
            consensus_reached=True,
            quality_score=8.7,
            retry_count=1,
            prd_data={"feature_name": "Feature"},
            prd_path_json="",
            prd_path_md="",
            final_validation_notes="good consensus",
        ),
    )

    captured = {}

    def fake_kickoff(*, inputs):
        captured.update(inputs)

    mock_flow.kickoff = fake_kickoff
    monkeypatch.setattr(prd_flow, "DialecticFlow", lambda persistence: mock_flow)
    monkeypatch.setattr(prd_flow, "_get_persistence", lambda: object())

    prd_flow.run_dialectic_flow(
        "Ship resilient PRD validation",
        consensus_min_score=8.5,
    )

    assert captured["consensus_min_score"] == 8.5
