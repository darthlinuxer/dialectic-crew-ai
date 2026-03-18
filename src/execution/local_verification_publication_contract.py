"""Publication contract, tests, and documentation verification helpers."""

# pylint: disable=line-too-long

from __future__ import annotations

from pathlib import Path

from .local_verification_shared import _display_path, _read_text_if_exists

_AUTHORITATIVE_LIFECYCLE_CONTRACT_PHRASE = (
    "single authoritative lifecycle contract exists"
)
_LIFECYCLE_CONTEXTS_PHRASE = "explicitly names and defines the three lifecycle contexts"
_APPROVED_PUBLICATION_PERSISTENCE_PHRASE = (
    "approved publication requires persistence of both"
)
_TESTS_PREVIEW_VIEWS_PHRASE = "tests exist for `pre_approval_preview` showing markdown-only, json-only, and dual emitted views"
_TESTS_APPROVED_VIEWS_PHRASE = "tests exist for `approved_publication` showing that requested markdown-only, json-only, and dual emitted views"
_TESTS_NEGATIVE_SINGLE_ARTIFACT_PHRASE = "negative tests verify that any implementation path attempting single-artifact persistence"
_TESTS_EXPORT_DISTINGUISH_PUBLISH_PHRASE = (
    "tests distinguish ad hoc export from publish"
)
_DOC_PREVIEW_EXAMPLE_PHRASE = (
    "documentation includes one normative example for `pre_approval_preview`"
)
_DOC_APPROVED_EXAMPLE_PHRASE = (
    "documentation includes one normative example for `approved_publication`"
)
_DOC_EXPORT_EXAMPLE_PHRASE = (
    "documentation includes one normative example for `ad_hoc_export`"
)
_DOC_SINGLE_VIEW_ONLY_PHRASE = "documentation explicitly states that `markdown_only` and `json_only` are client-visible view/export choices only"
_PUBLICATION_LIFECYCLE_CONTRACT_CANDIDATES = (
    Path("docs/publication_lifecycle_contract.md"),
    Path("docs/prd_publication_lifecycle_contract.md"),
    Path("docs/prd-publication-lifecycle-contract.md"),
)
_PUBLICATION_LIFECYCLE_REQUIRED_TERMS = (
    "`canonical_model`",
    "`render`",
    "`emit`",
    "`persist`",
    "`preview`",
    "`export`",
    "`publish`",
    "`approved_publication`",
)
_PUBLICATION_LIFECYCLE_CONTEXT_HEADINGS = (
    "`pre_approval_preview`",
    "`approved_publication`",
    "`ad_hoc_export`",
)


def _load_publication_lifecycle_contract(
    repo_root: Path,
) -> tuple[Path | None, str | None, str | None]:
    for relative_path in _PUBLICATION_LIFECYCLE_CONTRACT_CANDIDATES:
        path = repo_root / relative_path
        if not path.exists():
            continue
        try:
            return path, path.read_text(encoding="utf-8"), None
        except OSError as exc:
            return None, None, f"{_display_path(path, repo_root)} unreadable: {exc}"
    return None, None, "publication lifecycle contract file missing"


def _check_authoritative_publication_contract(repo_root: Path) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    missing_terms = [
        term for term in _PUBLICATION_LIFECYCLE_REQUIRED_TERMS if term not in content
    ]
    if missing_terms:
        return (
            False,
            f"{_display_path(path, repo_root)} missing required lifecycle terms: {', '.join(missing_terms)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} defines the authoritative lifecycle vocabulary.",
    )


def _check_publication_lifecycle_contexts(repo_root: Path) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    missing_contexts = [
        context
        for context in _PUBLICATION_LIFECYCLE_CONTEXT_HEADINGS
        if context not in content
    ]
    if missing_contexts:
        return (
            False,
            f"{_display_path(path, repo_root)} missing lifecycle contexts: {', '.join(missing_contexts)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} defines all three lifecycle contexts.",
    )


def _check_approved_publication_dual_persistence(repo_root: Path) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    normalized = " ".join(content.split())
    has_both_formats = all(
        token in normalized for token in ("`.md`", "`.json`", "`prd_output/`")
    )
    has_publication_rule = (
        "approved_publication" in normalized
        and "persist both Markdown and JSON" in normalized
    )
    passed = has_both_formats and has_publication_rule
    if not passed:
        return (
            False,
            f"{_display_path(path, repo_root)} does not clearly require dual-format approved-publication persistence.",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} requires approved publication to persist both .md and .json artifacts in prd_output/.",
    )


def _check_publication_tests_cover_preview_views(repo_root: Path) -> tuple[bool, str]:
    policy_tests = _read_text_if_exists(repo_root / "tests/test_publication_policy.py")
    if policy_tests is None:
        return False, "tests/test_publication_policy.py missing or unreadable"

    required_markers = (
        "PRE_APPROVAL_PREVIEW",
        "RequestedView.MARKDOWN",
        "RequestedView.JSON",
        "RequestedView.BOTH",
    )
    missing = [marker for marker in required_markers if marker not in policy_tests]
    if missing:
        return (
            False,
            f"tests/test_publication_policy.py missing preview-view coverage markers: {', '.join(missing)}",
        )

    return (
        True,
        "publication policy tests cover markdown-only, json-only, and dual preview emitted views.",
    )


def _check_publication_tests_cover_approved_views(repo_root: Path) -> tuple[bool, str]:
    guardrail_tests = _read_text_if_exists(
        repo_root / "tests/test_publication_guardrails.py"
    )
    policy_tests = _read_text_if_exists(repo_root / "tests/test_publication_policy.py")
    if guardrail_tests is None or policy_tests is None:
        return False, "publication policy/guardrail test files missing"

    required_guardrail_markers = (
        "markdown_only",
        "json_only",
        "persisted_artifacts ==",
        "sample-prd.md",
        "sample-prd.json",
    )
    missing_guardrail = [
        marker for marker in required_guardrail_markers if marker not in guardrail_tests
    ]
    required_policy_markers = (
        "PublicationLifecycle.APPROVED_PUBLICATION",
        "RequestedView.MARKDOWN",
        "RequestedView.JSON",
        "RequestedView.BOTH",
    )
    missing_policy = [
        marker for marker in required_policy_markers if marker not in policy_tests
    ]
    if missing_guardrail or missing_policy:
        missing = missing_guardrail + missing_policy
        return (
            False,
            f"publication tests missing approved-publication coverage markers: {', '.join(missing)}",
        )

    return (
        True,
        "publication tests cover approved-publication single-view and dual-view persistence invariants.",
    )


def _check_publication_tests_cover_negative_guardrails(
    repo_root: Path,
) -> tuple[bool, str]:
    guardrail_tests = _read_text_if_exists(
        repo_root / "tests/test_publication_guardrails.py"
    )
    if guardrail_tests is None:
        return False, "tests/test_publication_guardrails.py missing or unreadable"

    required_markers = (
        "test_approved_publication_requires_full_gate_proofs",
        "with pytest.raises",
        "VisionContext.SELF",
        "signature verification",
    )
    missing = [marker for marker in required_markers if marker not in guardrail_tests]
    if missing:
        return (
            False,
            f"tests/test_publication_guardrails.py missing negative guardrail markers: {', '.join(missing)}",
        )

    return (
        True,
        "negative publication guardrail tests prove enforcement rejects invalid approved-publication paths.",
    )


def _check_publication_tests_distinguish_export_publish(
    repo_root: Path,
) -> tuple[bool, str]:
    guardrail_tests = _read_text_if_exists(
        repo_root / "tests/test_publication_guardrails.py"
    )
    if guardrail_tests is None:
        return False, "tests/test_publication_guardrails.py missing or unreadable"

    required_markers = (
        "test_publish_is_not_treated_as_approved_publication",
        '"lifecycle": "publish"',
        "assert result.persisted_artifacts == ()",
        "assert result.publish_proof is None",
    )
    missing = [marker for marker in required_markers if marker not in guardrail_tests]
    if missing:
        return (
            False,
            f"tests/test_publication_guardrails.py missing publish/export distinction markers: {', '.join(missing)}",
        )

    return (
        True,
        "publication guardrail tests distinguish publish/export behavior from approved-publication persistence.",
    )


def _check_publication_documentation_has_preview_example(
    repo_root: Path,
) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    required_markers = (
        "### Example — `pre_approval_preview`",
        "Requested view:",
        "Effective emitted view:",
        "Persisted artifacts:",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        return (
            False,
            f"{_display_path(path, repo_root)} missing preview example markers: {', '.join(missing)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} includes a normative pre_approval_preview example.",
    )


def _check_publication_documentation_has_approved_example(
    repo_root: Path,
) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    required_markers = (
        "### Example — `approved_publication`",
        "Requested view: `markdown_only`",
        "Effective emitted view: `markdown_only`",
        "Persisted artifacts: `prd_output/",
        "`.md` and `.json`",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        return (
            False,
            f"{_display_path(path, repo_root)} missing approved-publication example markers: {', '.join(missing)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} includes a normative approved_publication example with dual persistence.",
    )


def _check_publication_documentation_has_export_example(
    repo_root: Path,
) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    required_markers = (
        "### Example — `ad_hoc_export`",
        "Requested view:",
        "Effective emitted view:",
        "Persisted artifacts: none required",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        return (
            False,
            f"{_display_path(path, repo_root)} missing ad_hoc_export example markers: {', '.join(missing)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} includes a normative ad_hoc_export example.",
    )


def _check_publication_documentation_states_single_view_rule(
    repo_root: Path,
) -> tuple[bool, str]:
    path, content, error = _load_publication_lifecycle_contract(repo_root)
    if content is None or path is None:
        return False, error or "publication lifecycle contract file missing"

    required_markers = (
        "`markdown_only`",
        "`json_only`",
        "client-visible view/export choices only",
        "cannot weaken approved-publication persistence",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        return (
            False,
            f"{_display_path(path, repo_root)} missing single-view documentation markers: {', '.join(missing)}",
        )

    return (
        True,
        f"{_display_path(path, repo_root)} explicitly states that single-format requests never weaken approved-publication persistence.",
    )
