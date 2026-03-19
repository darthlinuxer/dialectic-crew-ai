"""Publication policy and publisher guardrail verification helpers."""

# pylint: disable=line-too-long

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

from .local_verification_shared import _display_path, _read_text_if_exists

_CENTRALIZED_PUBLICATION_POLICY_PHRASE = (
    "centralized policy function, rule table, or equivalent implementation exists"
)
_APPROVED_POLICY_BRANCH_PHRASE = (
    "approved publication branch of the policy always resolves persistence requirements"
)
_PREVIEW_EXPORT_POLICY_BRANCH_PHRASE = (
    "preview and ad hoc export branches resolve emitted view choices"
)
_PUBLISH_PATH_REJECTS_SINGLE_ARTIFACT_PHRASE = "publish-path enforcement rejects or overrides any code path where `markdown_only` or `json_only`"
_APPROVED_PUBLICATION_PERSISTS_BOTH_ARTIFACTS_PHRASE = "approved publication code persists both `*.md` and `*.json` artifacts under `prd_output/`"
_NO_PREVIEW_EXPORT_PUBLISH_SEMANTICS_PHRASE = "no publish-path code path treats preview/export semantics as sufficient for approved publication persistence"
_PUBLICATION_POLICY_PATH = Path("src/publication/policy.py")
_PUBLICATION_PACKAGE_INIT_PATH = Path("src/publication/__init__.py")
_PUBLICATION_PUBLISHER_PATH = Path("src/publication/publisher.py")


def _check_publication_source_markers(
    repo_root: Path,
    relative_path: Path,
    required_markers: tuple[str, ...],
    success_message: str,
    failure_message: str,
) -> tuple[bool, str]:
    source = _read_text_if_exists(repo_root / relative_path)
    if source is None:
        return (
            False,
            f"{_display_path(repo_root / relative_path, repo_root)} missing or unreadable",
        )

    missing = [marker for marker in required_markers if marker not in source]
    if missing:
        return False, f"{failure_message} Missing markers: {', '.join(missing)}"
    return True, success_message


def _load_publication_policy_module(repo_root: Path) -> tuple[Any | None, str | None]:
    policy_path = repo_root / _PUBLICATION_POLICY_PATH
    if not policy_path.exists():
        return None, f"{_display_path(policy_path, repo_root)} missing"

    module_name = (
        f"_publication_policy_fallback_{abs(hash(str(policy_path.resolve())))}"
    )
    spec = importlib.util.spec_from_file_location(module_name, policy_path)
    if spec is None or spec.loader is None:
        return (
            None,
            f"Could not load publication policy module from {_display_path(policy_path, repo_root)}",
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, None


def _load_publication_publisher_module(
    repo_root: Path,
) -> tuple[Any | None, str | None]:
    publisher_path = repo_root / _PUBLICATION_PUBLISHER_PATH
    if not publisher_path.exists():
        return None, f"{_display_path(publisher_path, repo_root)} missing"

    src_root = repo_root / "src"
    src_root_str = str(src_root)
    added_path = False
    if src_root.exists() and src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)
        added_path = True

    saved_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "publication" or name.startswith("publication.")
    }
    for name in list(saved_modules):
        sys.modules.pop(name, None)

    try:
        importlib.invalidate_caches()
        return importlib.import_module("publication.publisher"), None
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        return None, f"Could not import publication.publisher: {exc}"
    finally:
        for name in list(sys.modules):
            if name == "publication" or name.startswith("publication."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        if added_path:
            try:
                sys.path.remove(src_root_str)
            except ValueError:
                pass


def _check_centralized_publication_policy(repo_root: Path) -> tuple[bool, str]:
    module, error = _load_publication_policy_module(repo_root)
    if module is None:
        return False, error or "publication policy module missing"

    init_path = repo_root / _PUBLICATION_PACKAGE_INIT_PATH
    if not init_path.exists():
        return False, f"{_display_path(init_path, repo_root)} missing"

    init_text = init_path.read_text(encoding="utf-8")
    required_exports = (
        "resolve_publication_policy",
        "PublicationLifecycle",
        "RequestedView",
        "EmittedView",
    )
    missing_exports = [name for name in required_exports if name not in init_text]
    if missing_exports:
        return (
            False,
            f"{_display_path(init_path, repo_root)} missing publication-policy exports: {', '.join(missing_exports)}",
        )

    has_function = hasattr(module, "resolve_publication_policy")
    has_lifecycle = hasattr(module, "PublicationLifecycle")
    has_requested = hasattr(module, "RequestedView")
    if not (has_function and has_lifecycle and has_requested):
        return False, "publication policy module is missing required policy symbols"

    return (
        True,
        f"{_display_path(_PUBLICATION_POLICY_PATH, repo_root)} defines a centralized publication policy API.",
    )


def _check_approved_publication_policy_branch(repo_root: Path) -> tuple[bool, str]:
    module, error = _load_publication_policy_module(repo_root)
    if module is None:
        return False, error or "publication policy module missing"

    lifecycle = module.PublicationLifecycle
    requested_view = module.RequestedView
    emitted_view = module.EmittedView
    resolve_policy = module.resolve_publication_policy

    decisions = [
        resolve_policy(lifecycle.APPROVED_PUBLICATION, requested_view.MARKDOWN),
        resolve_policy(lifecycle.APPROVED_PUBLICATION, requested_view.JSON),
        resolve_policy(lifecycle.APPROVED_PUBLICATION, requested_view.BOTH),
    ]

    emitted_views = [decision.emitted_view for decision in decisions]
    preserves_requested_view = emitted_views == [
        emitted_view.MARKDOWN,
        emitted_view.JSON,
        emitted_view.BOTH,
    ]
    forces_dual_emission = all(view is emitted_view.BOTH for view in emitted_views)

    passed = all(
        decision.persistence.persist_markdown
        and decision.persistence.persist_json
        and decision.persistence.output_dir == "prd_output/"
        for decision in decisions
    ) and (preserves_requested_view or forces_dual_emission)
    if not passed:
        return (
            False,
            "approved publication policy branch does not enforce dual persistence to prd_output/",
        )

    return (
        True,
        "approved publication policy branch enforces dual persistence for every requested view.",
    )


def _check_preview_export_policy_branches(repo_root: Path) -> tuple[bool, str]:
    module, error = _load_publication_policy_module(repo_root)
    if module is None:
        return False, error or "publication policy module missing"

    lifecycle = module.PublicationLifecycle
    requested_view = module.RequestedView
    emitted_view = module.EmittedView
    resolve_policy = module.resolve_publication_policy

    preview_decision = resolve_policy(
        lifecycle.PRE_APPROVAL_PREVIEW,
        requested_view.MARKDOWN,
    )
    export_decision = resolve_policy(lifecycle.AD_HOC_EXPORT, requested_view.JSON)

    preview_ok = (
        preview_decision.emitted_view is emitted_view.MARKDOWN
        and not preview_decision.persistence.requires_persistence
        and preview_decision.persistence.output_dir is None
    )
    export_ok = (
        export_decision.emitted_view is emitted_view.JSON
        and not export_decision.persistence.requires_persistence
        and export_decision.persistence.output_dir is None
    )
    if not (preview_ok and export_ok):
        return (
            False,
            "preview/export policy branches do not preserve emitted-view choice without publish-grade persistence",
        )

    return (
        True,
        "preview and ad hoc export policy branches preserve emitted-view choice without approval-grade persistence.",
    )


def _check_publish_path_rejects_single_artifact_persistence(
    repo_root: Path,
) -> tuple[bool, str]:
    publisher, error = _load_publication_publisher_module(repo_root)
    if publisher is None:
        return _check_publication_source_markers(
            repo_root,
            _PUBLICATION_PUBLISHER_PATH,
            (
                "PublicationLifecycle.APPROVED_PUBLICATION",
                'base.with_suffix(".md")',
                'base.with_suffix(".json")',
                "persisted_artifacts.extend([str(md_path), str(json_path)])",
                "EmittedView.MARKDOWN_ONLY",
                "EmittedView.JSON_ONLY",
            ),
            "publisher source shows approved publication always writes both persisted artifacts while preserving single-view responses.",
            error or "publication publisher module missing",
        )

    proof_dir = repo_root / ".tmp_local_verification_publish_guard"
    markdown_result = publisher.publish_prd(
        {
            "lifecycle": "approved_publication",
            "emitted_view": "markdown_only",
            "slug": "guard-md",
        },
        document={"title": "Guard", "body": "Body", "slug": "guard-md"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )
    json_result = publisher.publish_prd(
        {
            "lifecycle": "approved_publication",
            "emitted_view": "json_only",
            "slug": "guard-json",
        },
        document={"title": "Guard", "body": "Body", "slug": "guard-json"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )

    markdown_ok = len(
        markdown_result.persisted_artifacts
    ) == 2 and markdown_result.response_artifacts == (str(proof_dir / "guard-md.md"),)
    json_ok = len(
        json_result.persisted_artifacts
    ) == 2 and json_result.response_artifacts == (str(proof_dir / "guard-json.json"),)
    if not (markdown_ok and json_ok):
        return (
            False,
            "approved-publication publish path does not override single-view requests with dual persistence",
        )

    return (
        True,
        "publish-path guardrails override single-view requests so approved publication still persists both artifacts.",
    )


def _check_approved_publication_persists_both_artifacts(
    repo_root: Path,
) -> tuple[bool, str]:
    publisher, error = _load_publication_publisher_module(repo_root)
    if publisher is None:
        return _check_publication_source_markers(
            repo_root,
            _PUBLICATION_PUBLISHER_PATH,
            (
                "PublicationLifecycle.APPROVED_PUBLICATION",
                "persisted_artifacts.extend([str(md_path), str(json_path)])",
                'publish_proof={"validated": True}',
            ),
            "publisher source requires approved publication to persist both markdown and JSON artifacts.",
            error or "publication publisher module missing",
        )

    proof_dir = repo_root / ".tmp_local_verification_publish_persist"
    result = publisher.publish_prd(
        {
            "lifecycle": "approved_publication",
            "emitted_view": "markdown_only",
            "slug": "approved-prd",
        },
        document={"title": "Approved", "body": "Body", "slug": "approved-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )

    persisted = tuple(sorted(Path(path).suffix for path in result.persisted_artifacts))
    passed = persisted == (".json", ".md") and all(
        Path(path).exists() for path in result.persisted_artifacts
    )
    if not passed:
        return (
            False,
            "approved-publication publisher did not persist both .md and .json artifacts",
        )

    return (
        True,
        "approved publication publisher persists both .md and .json artifacts even for single-format emitted views.",
    )


def _check_publish_path_distinguishes_preview_export(
    repo_root: Path,
) -> tuple[bool, str]:
    publisher, error = _load_publication_publisher_module(repo_root)
    if publisher is None:
        return _check_publication_source_markers(
            repo_root,
            _PUBLICATION_PUBLISHER_PATH,
            (
                "PublicationLifecycle.APPROVED_PUBLICATION",
                "persisted_artifacts=tuple()",
                "publish_proof=None",
            ),
            "publisher source keeps preview, export, and publish distinct from approved-publication persistence.",
            error or "publication publisher module missing",
        )

    proof_dir = repo_root / ".tmp_local_verification_publish_modes"
    preview_result = publisher.publish_prd(
        {
            "lifecycle": "preview",
            "emitted_view": "markdown_only",
            "slug": "preview-prd",
        },
        document={"title": "Preview", "body": "Body", "slug": "preview-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )
    export_result = publisher.publish_prd(
        {
            "lifecycle": "export",
            "emitted_view": "json_only",
            "slug": "export-prd",
        },
        document={"title": "Export", "body": "Body", "slug": "export-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )
    publish_result = publisher.publish_prd(
        {
            "lifecycle": "publish",
            "emitted_view": "both",
            "slug": "publish-prd",
        },
        document={"title": "Publish", "body": "Body", "slug": "publish-prd"},
        validated=True,
        compliant=True,
        vision_self_loaded=True,
        signature_verified=True,
        output_dir=proof_dir,
    )

    passed = (
        not preview_result.persisted_artifacts
        and not export_result.persisted_artifacts
        and not publish_result.persisted_artifacts
    )
    if not passed:
        return (
            False,
            "preview/export/publish paths still create approval-grade persistence artifacts",
        )

    return (
        True,
        "preview, export, and plain publish remain distinct from approved-publication persistence semantics.",
    )
