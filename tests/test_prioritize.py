"""Tests for dialectic.prioritize -- dialectic prioritization of improvement opportunities."""

from unittest.mock import MagicMock, patch

import pytest

from dialectic.prioritize import (
    _apply_ranking,
    _build_opportunities_text,
    _fallback_sort,
    _prioritization_guardrail,
    dialectic_prioritize,
)
from dialectic.vision import VisionContext
from schemas import (
    ImprovementOpportunity,
    PrioritizationResult,
    PrioritizedOpportunity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _opp(
    id: str = "opp-1",
    title: str = "Test opportunity",
    impact: str = "medium",
    category: str = "vision_gap",
) -> ImprovementOpportunity:
    return ImprovementOpportunity(
        id=id,
        category=category,
        title=title,
        description=f"Description for {title}",
        evidence=["evidence-1", "evidence-2"],
        estimated_impact=impact,
    )


def _ranked(
    opportunity_id: str = "opp-1",
    rank: int = 1,
    score: float = 8.0,
) -> PrioritizedOpportunity:
    return PrioritizedOpportunity(
        opportunity_id=opportunity_id,
        rank=rank,
        justification=f"Justified for {opportunity_id}",
        feasibility_score=score,
        alignment_score=score,
        final_priority_score=score,
    )


# ---------------------------------------------------------------------------
# PrioritizedOpportunity schema tests
# ---------------------------------------------------------------------------


class TestPrioritizedOpportunitySchema:
    def test_valid(self):
        p = _ranked()
        assert p.opportunity_id == "opp-1"
        assert p.rank == 1
        assert p.feasibility_score == 8.0

    def test_score_bounds_upper(self):
        with pytest.raises(Exception):
            PrioritizedOpportunity(
                opportunity_id="x",
                rank=1,
                justification="j",
                feasibility_score=11.0,
                alignment_score=5.0,
                final_priority_score=5.0,
            )

    def test_score_bounds_lower(self):
        with pytest.raises(Exception):
            PrioritizedOpportunity(
                opportunity_id="x",
                rank=1,
                justification="j",
                feasibility_score=-1.0,
                alignment_score=5.0,
                final_priority_score=5.0,
            )

    def test_required_fields(self):
        with pytest.raises(Exception):
            PrioritizedOpportunity(rank=1)


# ---------------------------------------------------------------------------
# PrioritizationResult schema tests
# ---------------------------------------------------------------------------


class TestPrioritizationResultSchema:
    def test_valid(self):
        r = PrioritizationResult(
            ranked=[_ranked()],
            debate_summary="Summary text",
        )
        assert len(r.ranked) == 1
        assert r.debate_summary == "Summary text"

    def test_empty_ranked(self):
        r = PrioritizationResult(ranked=[], debate_summary="None found")
        assert len(r.ranked) == 0

    def test_defaults(self):
        r = PrioritizationResult()
        assert r.ranked == []
        assert r.debate_summary == ""


# ---------------------------------------------------------------------------
# _build_opportunities_text
# ---------------------------------------------------------------------------


class TestBuildOpportunitiesText:
    def test_single_opportunity(self):
        text = _build_opportunities_text([_opp()])
        assert "opp-1" in text
        assert "Test opportunity" in text
        assert "evidence-1" in text

    def test_multiple_opportunities(self):
        text = _build_opportunities_text([
            _opp(id="a", title="First"),
            _opp(id="b", title="Second"),
        ])
        assert "1. [a]" in text
        assert "2. [b]" in text

    def test_empty_list(self):
        text = _build_opportunities_text([])
        assert text == ""


# ---------------------------------------------------------------------------
# _fallback_sort
# ---------------------------------------------------------------------------


class TestFallbackSort:
    def test_sorts_by_impact(self):
        opps = [
            _opp(id="low", impact="low"),
            _opp(id="high", impact="high"),
            _opp(id="med", impact="medium"),
        ]
        result = _fallback_sort(opps)
        assert [o.id for o in result] == ["high", "med", "low"]

    def test_stable_for_same_impact(self):
        opps = [
            _opp(id="a", impact="medium"),
            _opp(id="b", impact="medium"),
        ]
        result = _fallback_sort(opps)
        assert [o.id for o in result] == ["a", "b"]


# ---------------------------------------------------------------------------
# _prioritization_guardrail
# ---------------------------------------------------------------------------


class TestPrioritizationGuardrail:
    def test_accepts_valid_result(self):
        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(
            ranked=[_ranked()],
            debate_summary="ok",
        )
        ok, payload = _prioritization_guardrail(mock_result)
        assert ok is True
        assert isinstance(payload, str)
        assert '"opportunity_id":"opp-1"' in payload
        assert '"debate_summary":"ok"' in payload

    def test_rejects_empty_ranked(self):
        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(ranked=[], debate_summary="empty")
        ok, msg = _prioritization_guardrail(mock_result)
        assert ok is False
        assert "at least one" in msg

    def test_rejects_non_pydantic(self):
        mock_result = MagicMock()
        mock_result.pydantic = None
        ok, msg = _prioritization_guardrail(mock_result)
        assert ok is False
        assert "PrioritizationResult" in msg

    def test_rejects_wrong_type(self):
        mock_result = MagicMock()
        mock_result.pydantic = "not a PrioritizationResult"
        ok, msg = _prioritization_guardrail(mock_result)
        assert ok is False


# ---------------------------------------------------------------------------
# _apply_ranking
# ---------------------------------------------------------------------------


class TestApplyRanking:
    def test_reorders_by_score(self):
        candidates = [
            _opp(id="a", title="A"),
            _opp(id="b", title="B"),
            _opp(id="c", title="C"),
        ]
        prioritization = PrioritizationResult(
            ranked=[
                _ranked(opportunity_id="c", rank=1, score=9.5),
                _ranked(opportunity_id="a", rank=2, score=8.0),
                _ranked(opportunity_id="b", rank=3, score=6.0),
            ],
            debate_summary="C is best",
        )
        result = _apply_ranking(candidates, prioritization)
        assert [o.id for o in result] == ["c", "a", "b"]

    def test_appends_unranked(self):
        candidates = [
            _opp(id="a"),
            _opp(id="b"),
            _opp(id="c"),
        ]
        prioritization = PrioritizationResult(
            ranked=[_ranked(opportunity_id="b", rank=1, score=9.0)],
            debate_summary="only b",
        )
        result = _apply_ranking(candidates, prioritization)
        assert result[0].id == "b"
        assert set(o.id for o in result) == {"a", "b", "c"}

    def test_handles_unknown_ids(self):
        candidates = [_opp(id="a")]
        prioritization = PrioritizationResult(
            ranked=[_ranked(opportunity_id="unknown", rank=1, score=9.0)],
            debate_summary="miss",
        )
        result = _apply_ranking(candidates, prioritization)
        assert len(result) == 1
        assert result[0].id == "a"

    def test_no_duplicates(self):
        candidates = [_opp(id="a"), _opp(id="b")]
        prioritization = PrioritizationResult(
            ranked=[
                _ranked(opportunity_id="a", rank=1, score=9.0),
                _ranked(opportunity_id="a", rank=2, score=8.0),
            ],
            debate_summary="dup",
        )
        result = _apply_ranking(candidates, prioritization)
        ids = [o.id for o in result]
        assert ids == ["a", "b"]


# ---------------------------------------------------------------------------
# dialectic_prioritize (with mocked Crew)
# ---------------------------------------------------------------------------


class TestDialecticPrioritize:
    def _mock_crew_result(self, opps):
        """Build a mock crew result with a valid PrioritizationResult."""
        ranked = [
            _ranked(
                opportunity_id=opp.id,
                rank=i + 1,
                score=10.0 - i,
            )
            for i, opp in enumerate(reversed(opps))
        ]
        prioritization = PrioritizationResult(
            ranked=ranked,
            debate_summary="Mock debate completed",
        )
        mock_result = MagicMock()
        mock_result.pydantic = prioritization
        mock_result.tasks_output = []
        return mock_result

    def test_empty_list(self):
        result = dialectic_prioritize([])
        assert result == []

    def test_single_opportunity_passthrough(self):
        single = [_opp(id="only")]
        result = dialectic_prioritize(single)
        assert len(result) == 1
        assert result[0].id == "only"

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_returns_reordered_list(self, mock_build_crew):
        opps = [
            _opp(id="low", impact="low"),
            _opp(id="high", impact="high"),
            _opp(id="med", impact="medium"),
        ]
        ranked_items = [
            _ranked(opportunity_id="med", rank=1, score=9.5),
            _ranked(opportunity_id="high", rank=2, score=8.0),
            _ranked(opportunity_id="low", rank=3, score=6.0),
        ]
        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(
            ranked=ranked_items,
            debate_summary="Med is best",
        )
        mock_result.tasks_output = []
        mock_build_crew.return_value.kickoff.return_value = mock_result

        result = dialectic_prioritize(opps, max_to_debate=5)
        assert result[0].id == "med"
        assert len(result) == 3

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_fallback_on_crew_failure(self, mock_build_crew):
        mock_build_crew.return_value.kickoff.side_effect = RuntimeError("LLM down")
        opps = [
            _opp(id="low", impact="low"),
            _opp(id="high", impact="high"),
        ]
        result = dialectic_prioritize(opps)
        assert result[0].id == "high"
        assert result[1].id == "low"

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_fallback_on_invalid_output(self, mock_build_crew):
        mock_result = MagicMock()
        mock_result.pydantic = None
        mock_result.tasks_output = []
        mock_result.raw = "garbage"
        mock_build_crew.return_value.kickoff.return_value = mock_result

        opps = [_opp(id="a", impact="high"), _opp(id="b", impact="low")]
        result = dialectic_prioritize(opps)
        assert result[0].id == "a"

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_max_to_debate_limits_crew_input(self, mock_build_crew):
        opps = [_opp(id=f"opp-{i}", impact="medium") for i in range(10)]

        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(
            ranked=[_ranked(opportunity_id=f"opp-{i}", rank=i + 1, score=float(10 - i)) for i in range(3)],
            debate_summary="top 3",
        )
        mock_result.tasks_output = []
        mock_build_crew.return_value.kickoff.return_value = mock_result

        result = dialectic_prioritize(opps, max_to_debate=3)
        assert len(result) == 10
        debated_ids = {result[i].id for i in range(3)}
        assert "opp-0" in debated_ids or "opp-1" in debated_ids or "opp-2" in debated_ids
        build_kwargs = mock_build_crew.call_args.kwargs
        assert "opp-0" in build_kwargs["opp_text"]
        assert "opp-1" in build_kwargs["opp_text"]
        assert "opp-2" in build_kwargs["opp_text"]
        assert "opp-3" not in build_kwargs["opp_text"]

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_non_debated_appended_in_order(self, mock_build_crew):
        opps = [
            _opp(id="a", impact="high"),
            _opp(id="b", impact="high"),
            _opp(id="c", impact="medium"),
            _opp(id="d", impact="low"),
        ]

        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(
            ranked=[
                _ranked(opportunity_id="b", rank=1, score=9.0),
                _ranked(opportunity_id="a", rank=2, score=8.0),
            ],
            debate_summary="debated a and b",
        )
        mock_result.tasks_output = []
        mock_build_crew.return_value.kickoff.return_value = mock_result

        result = dialectic_prioritize(opps, max_to_debate=2)
        assert result[0].id == "b"
        assert result[1].id == "a"
        remaining_ids = [o.id for o in result[2:]]
        assert "c" in remaining_ids
        assert "d" in remaining_ids

    @patch("dialectic.prioritize.build_prioritization_crew")
    def test_self_context_passes_self_vision_to_builder(self, mock_build_crew):
        mock_result = MagicMock()
        mock_result.pydantic = PrioritizationResult(
            ranked=[_ranked(opportunity_id="opp-1", rank=1, score=9.0)],
            debate_summary="ok",
        )
        mock_result.tasks_output = []
        mock_build_crew.return_value.kickoff.return_value = mock_result

        result = dialectic_prioritize(
            [_opp(id="opp-1"), _opp(id="opp-2")],
            vision_context=VisionContext.SELF,
            max_to_debate=5,
        )

        assert len(result) == 2
        assert mock_build_crew.call_args.kwargs["vision_context"] is VisionContext.SELF
