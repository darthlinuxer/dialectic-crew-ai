from __future__ import annotations

from typing import Any, Final, Mapping

from .emitted_view import EmittedView
from .lifecycle import PublicationLifecycle
from .persistence_plan import PersistencePlan
from .policy_decision import PublicationPolicyDecision
from .publication_policy import PublicationPolicy
from .requested_view import RequestedView


PRD_OUTPUT_DIR: Final[str] = "prd_output/"


def _normalize_lifecycle(value: Any) -> PublicationLifecycle:
    if isinstance(value, PublicationLifecycle):
        return value
    normalized = str(value or "").strip().lower()
    aliases = {
        "approved": PublicationLifecycle.APPROVED_PUBLICATION,
        "approved-publication": PublicationLifecycle.APPROVED_PUBLICATION,
        "approved_publication": PublicationLifecycle.APPROVED_PUBLICATION,
        "publication": PublicationLifecycle.PUBLISH,
        "publish": PublicationLifecycle.PUBLISH,
        "preview": PublicationLifecycle.PRE_APPROVAL_PREVIEW,
        "pre_approval_preview": PublicationLifecycle.PRE_APPROVAL_PREVIEW,
        "export": PublicationLifecycle.AD_HOC_EXPORT,
        "ad_hoc_export": PublicationLifecycle.AD_HOC_EXPORT,
    }
    if normalized in aliases:
        return aliases[normalized]
    raise ValueError(f"Unsupported publication lifecycle: {value!r}")


def _normalize_requested_view(value: Any) -> RequestedView:
    if isinstance(value, RequestedView):
        return value
    if isinstance(value, EmittedView):
        return RequestedView(value.value)
    normalized = str(value or "both").strip().lower()
    aliases = {
        "both": RequestedView.BOTH,
        "all": RequestedView.BOTH,
        "markdown_only": RequestedView.MARKDOWN,
        "md_only": RequestedView.MARKDOWN,
        "markdown": RequestedView.MARKDOWN,
        "json_only": RequestedView.JSON,
        "json": RequestedView.JSON,
    }
    if normalized in aliases:
        return aliases[normalized]
    raise ValueError(f"Unsupported requested view: {value!r}")


def _requested_to_emitted(requested_view: RequestedView) -> EmittedView:
    if requested_view is RequestedView.MARKDOWN:
        return EmittedView.MARKDOWN
    if requested_view is RequestedView.JSON:
        return EmittedView.JSON
    return EmittedView.BOTH


def resolve_publication_policy(
    lifecycle: PublicationLifecycle | str,
    requested_view: RequestedView | EmittedView | str,
) -> PublicationPolicyDecision:
    normalized_lifecycle = _normalize_lifecycle(lifecycle)
    normalized_view = _normalize_requested_view(requested_view)

    if normalized_lifecycle in (
        PublicationLifecycle.PRE_APPROVAL_PREVIEW,
        PublicationLifecycle.AD_HOC_EXPORT,
        PublicationLifecycle.PUBLISH,
    ):
        return PublicationPolicyDecision(
            lifecycle=normalized_lifecycle,
            requested_view=normalized_view,
            emitted_view=_requested_to_emitted(normalized_view),
            persistence=PersistencePlan(
                persist_markdown=False,
                persist_json=False,
                output_dir=None,
            ),
        )

    if normalized_lifecycle is PublicationLifecycle.APPROVED_PUBLICATION:
        return PublicationPolicyDecision(
            lifecycle=normalized_lifecycle,
            requested_view=normalized_view,
            emitted_view=_requested_to_emitted(normalized_view),
            persistence=PersistencePlan(
                persist_markdown=True,
                persist_json=True,
                output_dir=PRD_OUTPUT_DIR,
            ),
        )

    raise ValueError(f"Unhandled publication lifecycle: {normalized_lifecycle!r}")


def _normalize_emitted_view(value: Any) -> EmittedView:
    if isinstance(value, EmittedView):
        return value
    return _requested_to_emitted(_normalize_requested_view(value))


def derive_publication_policy(request: Mapping[str, Any]) -> PublicationPolicy:
    lifecycle = _normalize_lifecycle(request.get("lifecycle"))
    requested_view = _normalize_requested_view(
        request.get(
            "emitted_view", request.get("output_view", request.get("format", "both"))
        )
    )
    decision = resolve_publication_policy(lifecycle, requested_view)

    # Guardrail semantics:
    # - PREVIEW / EXPORT are never approval-grade and never persist to prd_output.
    # - PUBLISH is not a synonym for preview/export, but it is also not sufficient
    #   to satisfy approved-publication persistence obligations.
    # - APPROVED_PUBLICATION is the only lifecycle that persists approval-grade
    #   artifacts into prd_output and it must always persist both md and json.
    return PublicationPolicy(
        lifecycle=decision.lifecycle,
        emitted_view=decision.emitted_view,
        approval_grade=decision.lifecycle is PublicationLifecycle.APPROVED_PUBLICATION,
        persist_to_prd_output=decision.persistence.requires_persistence,
        required_artifacts=(
            (".md", ".json") if decision.persistence.requires_persistence else ()
        ),
    )


def enforce_publication_guardrails(
    request: Mapping[str, Any],
    *,
    validated: bool,
    compliant: bool,
    vision_self_loaded: bool,
    signature_verified: bool,
) -> PublicationPolicy:
    policy = derive_publication_policy(request)

    if policy.lifecycle in (
        PublicationLifecycle.PRE_APPROVAL_PREVIEW,
        PublicationLifecycle.AD_HOC_EXPORT,
    ):
        if policy.persist_to_prd_output or policy.required_artifacts:
            raise ValueError(
                "Preview/export lifecycles must never be treated as approved publication persistence paths."
            )
        return policy

    if policy.lifecycle is PublicationLifecycle.PUBLISH:
        if policy.persist_to_prd_output or policy.required_artifacts:
            raise ValueError(
                "Publish lifecycle cannot be upgraded implicitly into approval-grade persistence."
            )
        return policy

    if policy.lifecycle is PublicationLifecycle.APPROVED_PUBLICATION:
        if not validated:
            raise ValueError(
                "Approved publication requires successful dialectic validation."
            )
        if not compliant:
            raise ValueError("Approved publication requires compliance approval.")
        if not vision_self_loaded:
            raise ValueError(
                "Approved publication requires proof that VisionContext.SELF was loaded."
            )
        if not signature_verified:
            raise ValueError("Approved publication requires signature verification.")
        if not policy.persist_to_prd_output:
            raise ValueError(
                "Approved publication must persist artifacts to prd_output."
            )
        if tuple(policy.required_artifacts) != (".md", ".json"):
            raise ValueError(
                "Approved publication must persist both .md and .json artifacts."
            )
        if policy.emitted_view not in (
            EmittedView.BOTH,
            EmittedView.MARKDOWN,
            EmittedView.JSON,
        ):
            raise ValueError("Unsupported emitted view for approved publication.")
        return policy

    raise ValueError(
        f"Unhandled publication lifecycle during enforcement: {policy.lifecycle!r}"
    )


__all__ = [
    "EmittedView",
    "PRD_OUTPUT_DIR",
    "PersistencePlan",
    "PublicationLifecycle",
    "PublicationPolicy",
    "PublicationPolicyDecision",
    "RequestedView",
    "derive_publication_policy",
    "enforce_publication_guardrails",
    "resolve_publication_policy",
]
