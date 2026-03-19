from pathlib import Path


def test_publication_lifecycle_contract_exists():
    contract_path = Path("docs/publication_lifecycle_contract.md")
    assert contract_path.exists(), (
        "Expected authoritative publication lifecycle contract to exist"
    )


def test_publication_lifecycle_contract_contains_required_terms_and_contexts():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    required_terms = [
        "`canonical_model`",
        "`render`",
        "`emit`",
        "`persist`",
        "`preview`",
        "`export`",
        "`publish`",
        "`approved_publication`",
        "`pre_approval_preview`",
        "`ad_hoc_export`",
    ]

    for term in required_terms:
        assert term in content, f"Missing required term or context: {term}"


def test_publication_lifecycle_contract_defines_core_invariants():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    required_phrases = [
        "sole source of truth",
        "rendering produces Markdown and/or JSON views from the `canonical_model`",
        "`emit` controls what is returned or displayed to the client",
        "`persist` controls what is written as durable artifacts",
        "separate client-visible emitted view from compliance-grade persistence requirements",
        "MUST persist both Markdown and JSON artifacts in `prd_output/`",
        "can only occur after full dialectic validation",
    ]

    for phrase in required_phrases:
        assert phrase in content, f"Missing core invariant phrase: {phrase}"


def test_publication_lifecycle_contract_distinguishes_lifecycle_contexts():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    assert "### `pre_approval_preview`" in content
    assert "### `approved_publication`" in content
    assert "### `ad_hoc_export`" in content

    assert (
        "The system MUST NOT treat this context as `approved_publication`." in content
    )
    assert (
        "The system MUST NOT classify ad hoc exports as `approved_publication`."
        in content
    )


def test_publication_lifecycle_contract_includes_publish_governance_and_evidence():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    required_phrases = [
        "Publish MUST be blocked unless validation reaches the required threshold.",
        "Publish MUST be blocked on unresolved contradiction or failed validation checks.",
        "For self-evolution flows, logs or equivalent evidence MUST show `VisionContext.SELF` ingestion",
        "The publish path SHOULD produce validation artifacts or logs that demonstrate the dialectic process completed.",
    ]

    for phrase in required_phrases:
        assert phrase in content, (
            f"Missing publish governance/evidence phrase: {phrase}"
        )


def test_publication_lifecycle_contract_includes_normative_examples_for_each_context():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    required_phrases = [
        "### Example — `pre_approval_preview`",
        "### Example — `approved_publication`",
        "### Example — `ad_hoc_export`",
        "Requested view:",
        "Effective emitted view:",
        "Persisted artifacts:",
    ]

    for phrase in required_phrases:
        assert phrase in content, f"Missing normative example phrase: {phrase}"


def test_publication_lifecycle_contract_states_single_view_is_response_only():
    content = Path("docs/publication_lifecycle_contract.md").read_text(encoding="utf-8")

    required_phrases = [
        "`markdown_only` and `json_only` are client-visible view/export choices only",
        "cannot weaken approved-publication persistence",
    ]

    for phrase in required_phrases:
        assert phrase in content, (
            f"Missing single-view persistence rule phrase: {phrase}"
        )
