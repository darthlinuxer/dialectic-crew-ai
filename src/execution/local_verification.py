"""Deterministic fallback verification helpers for execution flows.

This module intentionally supports only the currently implemented, local,
deterministic acceptance checks that can be evaluated without calling an LLM.

The currently supported acceptance-check phrases are:
- ``<relative path> exists``
- phrases containing ``Schemas validate example manifests``
- phrases containing ``version_semver pattern enforcement``
- phrases containing ``contract_schema_url uses HTTPS``
- phrases containing ``ISO-8601 deprecation_date validation``
- phrases containing ``owner.sub-object includes required fields``
- phrases containing ``single authoritative lifecycle contract exists``
- phrases containing ``explicitly names and defines the three lifecycle contexts``
- phrases containing ``approved publication requires persistence of both``

Future roadmap-specific phrases belong in prompt/test data until the repo ships
those artifacts for real. Keep this module scoped to present-tense repository
behavior so fallback verification does not drift ahead of implementation.

Supported publication-policy phrases currently include:
- ``single authoritative lifecycle contract exists``
- ``explicitly names and defines the three lifecycle contexts``
- ``approved publication requires persistence of both``
- ``centralized policy function, rule table, or equivalent
    implementation exists``
- ``approved publication branch of the policy always resolves
    persistence requirements``
- ``preview and ad hoc export branches resolve emitted view
    choices``

Supported publication-guardrail phrases currently include:
- ``publish-path enforcement rejects or overrides any code
    path where `markdown_only` or `json_only```
- ``approved publication code persists both `*.md` and
    `*.json` artifacts under `prd_output/```
- ``no publish-path code path treats preview/export semantics
    as sufficient for approved publication persistence``

Supported publication-test phrases currently include:
- ``tests exist for `pre_approval_preview` showing
    markdown-only, json-only, and dual emitted views``
- ``tests exist for `approved_publication` showing that
    requested markdown-only, json-only, and dual emitted views``
- ``negative tests verify that any implementation path attempting single-artifact persistence``
- ``tests distinguish ad hoc export from publish``

Supported publication-documentation phrases currently include:
- ``documentation includes one normative example for `pre_approval_preview```
- ``documentation includes one normative example for `approved_publication```
- ``documentation includes one normative example for `ad_hoc_export```
- ``documentation explicitly states that `markdown_only` and
    `json_only` are client-visible view/export choices only``
"""

from __future__ import annotations

import logging
from pathlib import Path

from schemas import VerificationResult

from .local_verification_publication import (
    _APPROVED_POLICY_BRANCH_PHRASE,
    _APPROVED_PUBLICATION_PERSISTENCE_PHRASE,
    _APPROVED_PUBLICATION_PERSISTS_BOTH_ARTIFACTS_PHRASE,
    _AUTHORITATIVE_LIFECYCLE_CONTRACT_PHRASE,
    _CENTRALIZED_PUBLICATION_POLICY_PHRASE,
    _DOC_APPROVED_EXAMPLE_PHRASE,
    _DOC_EXPORT_EXAMPLE_PHRASE,
    _DOC_PREVIEW_EXAMPLE_PHRASE,
    _DOC_SINGLE_VIEW_ONLY_PHRASE,
    _LIFECYCLE_CONTEXTS_PHRASE,
    _NO_PREVIEW_EXPORT_PUBLISH_SEMANTICS_PHRASE,
    _PREVIEW_EXPORT_POLICY_BRANCH_PHRASE,
    _PUBLISH_PATH_REJECTS_SINGLE_ARTIFACT_PHRASE,
    _TESTS_APPROVED_VIEWS_PHRASE,
    _TESTS_EXPORT_DISTINGUISH_PUBLISH_PHRASE,
    _TESTS_NEGATIVE_SINGLE_ARTIFACT_PHRASE,
    _TESTS_PREVIEW_VIEWS_PHRASE,
    _check_approved_publication_dual_persistence,
    _check_approved_publication_persists_both_artifacts,
    _check_approved_publication_policy_branch,
    _check_authoritative_publication_contract,
    _check_centralized_publication_policy,
    _check_preview_export_policy_branches,
    _check_publication_documentation_has_approved_example,
    _check_publication_documentation_has_export_example,
    _check_publication_documentation_has_preview_example,
    _check_publication_documentation_states_single_view_rule,
    _check_publication_lifecycle_contexts,
    _check_publication_tests_cover_approved_views,
    _check_publication_tests_cover_negative_guardrails,
    _check_publication_tests_cover_preview_views,
    _check_publication_tests_distinguish_export_publish,
    _check_publish_path_distinguishes_preview_export,
    _check_publish_path_rejects_single_artifact_persistence,
)
from .local_verification_schema import (
    _check_deprecation_date_validation,
    _check_https_contract_schema,
    _check_owner_required_fields,
    _check_version_semver_pattern,
    _validate_schema_examples,
)
from .local_verification_shared import (
    _dedupe_preserve_order,
    _join_verification_notes,
)

logger = logging.getLogger(__name__)

_EXISTS_CHECK_SUFFIX = " exists"
_SCHEMA_EXAMPLE_VALIDATION_PHRASE = "Schemas validate example manifests"
_VERSION_SEMVER_PATTERN_PHRASE = "version_semver pattern enforcement"
_HTTPS_CONTRACT_SCHEMA_PHRASE = "contract_schema_url uses HTTPS"
_DEPRECATION_DATE_VALIDATION_PHRASE = "ISO-8601 deprecation_date validation"
_OWNER_REQUIRED_FIELDS_PHRASE = "owner.sub-object includes required fields"

# Keep this list aligned with the module docstring. These are the only
# acceptance-check phrase families that local fallback verification supports.
_SUPPORTED_FALLBACK_PHRASES = (
    f"<relative path>{_EXISTS_CHECK_SUFFIX}",
    _SCHEMA_EXAMPLE_VALIDATION_PHRASE,
    _VERSION_SEMVER_PATTERN_PHRASE,
    _HTTPS_CONTRACT_SCHEMA_PHRASE,
    _DEPRECATION_DATE_VALIDATION_PHRASE,
    _OWNER_REQUIRED_FIELDS_PHRASE,
    _AUTHORITATIVE_LIFECYCLE_CONTRACT_PHRASE,
    _LIFECYCLE_CONTEXTS_PHRASE,
    _APPROVED_PUBLICATION_PERSISTENCE_PHRASE,
    _CENTRALIZED_PUBLICATION_POLICY_PHRASE,
    _APPROVED_POLICY_BRANCH_PHRASE,
    _PREVIEW_EXPORT_POLICY_BRANCH_PHRASE,
    _PUBLISH_PATH_REJECTS_SINGLE_ARTIFACT_PHRASE,
    _APPROVED_PUBLICATION_PERSISTS_BOTH_ARTIFACTS_PHRASE,
    _NO_PREVIEW_EXPORT_PUBLISH_SEMANTICS_PHRASE,
    _TESTS_PREVIEW_VIEWS_PHRASE,
    _TESTS_APPROVED_VIEWS_PHRASE,
    _TESTS_NEGATIVE_SINGLE_ARTIFACT_PHRASE,
    _TESTS_EXPORT_DISTINGUISH_PUBLISH_PHRASE,
    _DOC_PREVIEW_EXAMPLE_PHRASE,
    _DOC_APPROVED_EXAMPLE_PHRASE,
    _DOC_EXPORT_EXAMPLE_PHRASE,
    _DOC_SINGLE_VIEW_ONLY_PHRASE,
)


def _run_local_verification_fallback(
    checks: list[str],
    repo_root: Path | None = None,
) -> VerificationResult | None:
    """Evaluate deterministic file and schema checks without the LLM verifier."""
    base_repo_root = (repo_root or Path.cwd()).resolve()
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    notes: list[str] = []
    handled = 0

    for check in checks:
        outcome = _evaluate_acceptance_check(check, base_repo_root)
        if outcome is None:
            continue
        handled += 1
        passed, note = outcome
        notes.append(note)
        if passed:
            checks_passed.append(check)
        else:
            checks_failed.append(check)

    if handled == 0:
        return None

    return VerificationResult(
        verified=not checks_failed,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        notes=_join_verification_notes("Local fallback verification executed.", *notes),
    )


# pylint: disable=too-many-return-statements,too-many-branches
def _evaluate_acceptance_check(check: str, repo_root: Path) -> tuple[bool, str] | None:
    normalized = check.strip()
    normalized_lower = normalized.lower()

    if normalized.endswith(_EXISTS_CHECK_SUFFIX):
        relative_path = normalized[: -len(_EXISTS_CHECK_SUFFIX)].strip()
        target = repo_root / relative_path
        exists = target.exists()
        return exists, f"{relative_path}: {'present' if exists else 'missing'}"

    if _SCHEMA_EXAMPLE_VALIDATION_PHRASE.lower() in normalized_lower:
        return _validate_schema_examples(repo_root)

    if _VERSION_SEMVER_PATTERN_PHRASE.lower() in normalized_lower:
        return _check_version_semver_pattern(repo_root)

    if _HTTPS_CONTRACT_SCHEMA_PHRASE.lower() in normalized_lower:
        return _check_https_contract_schema(repo_root)

    if _DEPRECATION_DATE_VALIDATION_PHRASE.lower() in normalized_lower:
        return _check_deprecation_date_validation(repo_root)

    if _OWNER_REQUIRED_FIELDS_PHRASE.lower() in normalized_lower:
        return _check_owner_required_fields(repo_root)

    if _AUTHORITATIVE_LIFECYCLE_CONTRACT_PHRASE.lower() in normalized_lower:
        return _check_authoritative_publication_contract(repo_root)

    if _LIFECYCLE_CONTEXTS_PHRASE.lower() in normalized_lower:
        return _check_publication_lifecycle_contexts(repo_root)

    if _APPROVED_PUBLICATION_PERSISTENCE_PHRASE.lower() in normalized_lower:
        return _check_approved_publication_dual_persistence(repo_root)

    if _CENTRALIZED_PUBLICATION_POLICY_PHRASE.lower() in normalized_lower:
        return _check_centralized_publication_policy(repo_root)

    if _APPROVED_POLICY_BRANCH_PHRASE.lower() in normalized_lower:
        return _check_approved_publication_policy_branch(repo_root)

    if _PREVIEW_EXPORT_POLICY_BRANCH_PHRASE.lower() in normalized_lower:
        return _check_preview_export_policy_branches(repo_root)

    if _PUBLISH_PATH_REJECTS_SINGLE_ARTIFACT_PHRASE.lower() in normalized_lower:
        return _check_publish_path_rejects_single_artifact_persistence(repo_root)

    if _APPROVED_PUBLICATION_PERSISTS_BOTH_ARTIFACTS_PHRASE.lower() in normalized_lower:
        return _check_approved_publication_persists_both_artifacts(repo_root)

    if _NO_PREVIEW_EXPORT_PUBLISH_SEMANTICS_PHRASE.lower() in normalized_lower:
        return _check_publish_path_distinguishes_preview_export(repo_root)

    if _TESTS_PREVIEW_VIEWS_PHRASE.lower() in normalized_lower:
        return _check_publication_tests_cover_preview_views(repo_root)

    if _TESTS_APPROVED_VIEWS_PHRASE.lower() in normalized_lower:
        return _check_publication_tests_cover_approved_views(repo_root)

    if _TESTS_NEGATIVE_SINGLE_ARTIFACT_PHRASE.lower() in normalized_lower:
        return _check_publication_tests_cover_negative_guardrails(repo_root)

    if _TESTS_EXPORT_DISTINGUISH_PUBLISH_PHRASE.lower() in normalized_lower:
        return _check_publication_tests_distinguish_export_publish(repo_root)

    if _DOC_PREVIEW_EXAMPLE_PHRASE.lower() in normalized_lower:
        return _check_publication_documentation_has_preview_example(repo_root)

    if _DOC_APPROVED_EXAMPLE_PHRASE.lower() in normalized_lower:
        return _check_publication_documentation_has_approved_example(repo_root)

    if _DOC_EXPORT_EXAMPLE_PHRASE.lower() in normalized_lower:
        return _check_publication_documentation_has_export_example(repo_root)

    if _DOC_SINGLE_VIEW_ONLY_PHRASE.lower() in normalized_lower:
        return _check_publication_documentation_states_single_view_rule(repo_root)

    return None


def _merge_verification_results(
    primary: VerificationResult,
    gate: VerificationResult,
) -> VerificationResult:
    return VerificationResult(
        verified=primary.verified and gate.verified,
        checks_passed=_dedupe_preserve_order(
            primary.checks_passed + gate.checks_passed
        ),
        checks_failed=_dedupe_preserve_order(
            primary.checks_failed + gate.checks_failed
        ),
        notes=_join_verification_notes(primary.notes, gate.notes),
    )
