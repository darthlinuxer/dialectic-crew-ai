from __future__ import annotations

from pathlib import Path

import pytest

from src.publication.policy import (
    derive_publication_policy,
    enforce_publication_guardrails,
)
from src.publication.publisher import publish_prd


def test_approved_publication_persists_both_artifacts_even_when_markdown_only_requested(
    tmp_path: Path,
) -> None:
    result = publish_prd(
        {
            "lifecycle": "approved_publication",
            "emitted_view": "markdown_only",
            "slug": "sample-prd",
        },
        document={"title": "Sample", "body": "Body", "slug": "sample-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=tmp_path,
    )

    assert result.persisted_artifacts == (
        str(tmp_path / "sample-prd.md"),
        str(tmp_path / "sample-prd.json"),
    )
    assert result.response_artifacts == (str(tmp_path / "sample-prd.md"),)
    assert (tmp_path / "sample-prd.md").exists()
    assert (tmp_path / "sample-prd.json").exists()


def test_approved_publication_persists_both_artifacts_even_when_json_only_requested(
    tmp_path: Path,
) -> None:
    result = publish_prd(
        {
            "lifecycle": "approved_publication",
            "emitted_view": "json_only",
            "slug": "sample-prd",
        },
        document={"title": "Sample", "body": "Body", "slug": "sample-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=tmp_path,
    )

    assert result.persisted_artifacts == (
        str(tmp_path / "sample-prd.md"),
        str(tmp_path / "sample-prd.json"),
    )
    assert result.response_artifacts == (str(tmp_path / "sample-prd.json"),)
    assert (tmp_path / "sample-prd.md").exists()
    assert (tmp_path / "sample-prd.json").exists()


def test_preview_and_export_never_persist_to_prd_output() -> None:
    preview = derive_publication_policy(
        {"lifecycle": "preview", "emitted_view": "markdown_only"}
    )
    export = derive_publication_policy(
        {"lifecycle": "export", "emitted_view": "json_only"}
    )
    publish = derive_publication_policy(
        {"lifecycle": "publish", "emitted_view": "both"}
    )

    assert preview.persist_to_prd_output is False
    assert export.persist_to_prd_output is False
    assert publish.persist_to_prd_output is False
    assert preview.required_artifacts == ()
    assert export.required_artifacts == ()
    assert publish.required_artifacts == ()


def test_approved_publication_requires_full_gate_proofs() -> None:
    with pytest.raises(ValueError, match="VisionContext.SELF"):
        enforce_publication_guardrails(
            {"lifecycle": "approved_publication", "emitted_view": "both"},
            validated=True,
            compliant=True,
            vision_self_loaded=False,
            signature_verified=True,
        )

    with pytest.raises(ValueError, match="signature verification"):
        enforce_publication_guardrails(
            {"lifecycle": "approved_publication", "emitted_view": "both"},
            validated=True,
            compliant=True,
            vision_self_loaded=True,
            signature_verified=False,
        )


def test_publish_is_not_treated_as_approved_publication() -> None:
    result = publish_prd(
        {"lifecycle": "publish", "emitted_view": "markdown_only", "slug": "draft-prd"},
        document={"title": "Draft", "body": "Draft body", "slug": "draft-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
    )

    assert result.persisted_artifacts == ()
    assert result.publish_proof is None
