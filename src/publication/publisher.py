from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .policy import EmittedView, PublicationLifecycle, enforce_publication_guardrails


@dataclass(frozen=True)
class PublishResult:
    lifecycle: str
    emitted_view: str
    persisted_artifacts: tuple[str, ...]
    response_artifacts: tuple[str, ...]
    publish_proof: dict[str, Any] | None


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_markdown(document: Mapping[str, Any]) -> str:
    title = str(document.get("title", "Untitled PRD"))
    body = str(document.get("markdown", document.get("body", "")))
    return f"# {title}\n\n{body}\n"


def _render_json(document: Mapping[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def publish_prd(
    request: Mapping[str, Any],
    *,
    document: Mapping[str, Any],
    validated: bool,
    compliant: bool,
    vision_self_loaded: bool,
    signature_verified: bool,
    output_dir: str | Path = "prd_output",
) -> PublishResult:
    policy = enforce_publication_guardrails(
        request,
        validated=validated,
        compliant=compliant,
        vision_self_loaded=vision_self_loaded,
        signature_verified=signature_verified,
    )

    slug = str(request.get("slug") or document.get("slug") or "prd")
    markdown_content = _render_markdown(document)
    json_content = _render_json(document)

    persisted_artifacts: list[str] = []
    response_artifacts: list[str] = []

    if policy.lifecycle is PublicationLifecycle.APPROVED_PUBLICATION:
        base = Path(output_dir) / slug
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")

        # Hard guardrail: storage/compliance behavior is independent of emitted view.
        _write_text(md_path, markdown_content)
        _write_text(json_path, json_content)

        persisted_artifacts.extend([str(md_path), str(json_path)])

        if policy.emitted_view is EmittedView.BOTH:
            response_artifacts.extend([str(md_path), str(json_path)])
        elif policy.emitted_view is EmittedView.MARKDOWN_ONLY:
            response_artifacts.append(str(md_path))
        elif policy.emitted_view is EmittedView.JSON_ONLY:
            response_artifacts.append(str(json_path))
        else:
            raise ValueError("Unsupported emitted view for approved publication response shaping.")

        return PublishResult(
            lifecycle=policy.lifecycle.value,
            emitted_view=policy.emitted_view.value,
            persisted_artifacts=tuple(persisted_artifacts),
            response_artifacts=tuple(response_artifacts),
            publish_proof={
                "approved_publication": True,
                "vision_self_loaded": vision_self_loaded,
                "signature_verified": signature_verified,
                "validated": validated,
                "compliant": compliant,
                "persisted_artifacts": tuple(persisted_artifacts),
            },
        )

    # Non-approved lifecycles do not write approval-grade persistence artifacts.
    if policy.emitted_view is EmittedView.BOTH:
        response_artifacts.extend(["inline.md", "inline.json"])
    elif policy.emitted_view is EmittedView.MARKDOWN_ONLY:
        response_artifacts.append("inline.md")
    elif policy.emitted_view is EmittedView.JSON_ONLY:
        response_artifacts.append("inline.json")

    return PublishResult(
        lifecycle=policy.lifecycle.value,
        emitted_view=policy.emitted_view.value,
        persisted_artifacts=tuple(),
        response_artifacts=tuple(response_artifacts),
        publish_proof=None,
    )
