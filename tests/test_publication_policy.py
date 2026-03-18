from publication import (
    EmittedView,
    PRD_OUTPUT_DIR,
    PublicationLifecycle,
    RequestedView,
    resolve_publication_policy,
)
import pytest


@pytest.mark.parametrize(
    ("requested_view", "expected_view"),
    [
        (RequestedView.MARKDOWN, EmittedView.MARKDOWN),
        (RequestedView.JSON, EmittedView.JSON),
        (RequestedView.BOTH, EmittedView.BOTH),
    ],
)
def test_preview_policy_preserves_requested_view_without_persistence(
    requested_view, expected_view
):
    decision = resolve_publication_policy(
        PublicationLifecycle.PRE_APPROVAL_PREVIEW,
        requested_view,
    )

    assert decision.emitted_view is expected_view
    assert decision.persistence.persist_markdown is False
    assert decision.persistence.persist_json is False
    assert decision.persistence.output_dir is None


def test_ad_hoc_export_policy_preserves_requested_view_without_persistence():
    decision = resolve_publication_policy(
        PublicationLifecycle.AD_HOC_EXPORT,
        RequestedView.JSON,
    )

    assert decision.emitted_view is EmittedView.JSON
    assert decision.persistence.requires_persistence is False
    assert decision.persistence.output_dir is None


def test_approved_publication_policy_enforces_dual_persistence_for_all_views():
    decisions = [
        resolve_publication_policy(
            PublicationLifecycle.APPROVED_PUBLICATION, RequestedView.MARKDOWN
        ),
        resolve_publication_policy(
            PublicationLifecycle.APPROVED_PUBLICATION, RequestedView.JSON
        ),
        resolve_publication_policy(
            PublicationLifecycle.APPROVED_PUBLICATION, RequestedView.BOTH
        ),
    ]

    assert [decision.emitted_view for decision in decisions] == [
        EmittedView.MARKDOWN,
        EmittedView.JSON,
        EmittedView.BOTH,
    ]
    assert all(decision.persistence.persist_markdown for decision in decisions)
    assert all(decision.persistence.persist_json for decision in decisions)
    assert all(
        decision.persistence.output_dir == PRD_OUTPUT_DIR for decision in decisions
    )
