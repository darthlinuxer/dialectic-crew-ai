"""Schema-focused deterministic verification helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from jsonschema import FormatChecker
from jsonschema.validators import validator_for

from .local_verification_shared import _display_path, _load_json_file


def _load_schema_json(path: Path, repo_root: Path) -> tuple[dict | None, str | None]:
    try:
        loaded = _load_json_file(path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{_display_path(path, repo_root)}: {exc}"
    if not isinstance(loaded, dict):
        return (
            None,
            f"{_display_path(path, repo_root)}: schema root must be a JSON object",
        )
    return loaded, None


# pylint: disable=too-many-locals
def _validate_schema_examples(repo_root: Path) -> tuple[bool, str]:
    adapter_schema_path = repo_root / "schemas/adapter_manifest.schema.json"
    registry_schema_path = repo_root / "schemas/registry_item.schema.json"

    adapter_schema, adapter_error = _load_schema_json(adapter_schema_path, repo_root)
    if adapter_schema is None:
        return False, adapter_error or "adapter schema unreadable"

    registry_schema, registry_error = _load_schema_json(
        registry_schema_path,
        repo_root,
    )
    if registry_schema is None:
        return False, registry_error or "registry schema unreadable"

    adapter_validator = _build_jsonschema_validator(
        _inline_local_json_refs(adapter_schema, adapter_schema_path.parent, repo_root)
    )
    registry_validator = _build_jsonschema_validator(
        _inline_local_json_refs(
            registry_schema,
            registry_schema_path.parent,
            repo_root,
        )
    )

    checks: list[tuple[Path, Any, bool]] = []
    checks.extend(
        (path, adapter_validator, path.name.startswith("valid_"))
        for path in sorted((repo_root / "adapters/examples").glob("*.json"))
    )
    checks.extend(
        (path, registry_validator, path.name.startswith("valid_"))
        for path in sorted((repo_root / "registry/examples").glob("*.json"))
    )
    if not checks:
        return False, "No example manifests found for schema validation fallback."

    failures: list[str] = []
    for path, validator, should_pass in checks:
        try:
            instance = _load_json_file(path)
            valid = validator.is_valid(instance)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{_display_path(path, repo_root)} unreadable: {exc}")
            continue
        if should_pass and not valid:
            failures.append(
                f"{_display_path(path, repo_root)} should validate but did not"
            )
        if not should_pass and valid:
            failures.append(
                f"{_display_path(path, repo_root)} should fail validation but passed"
            )

    return (not failures), (
        "Schema/example validation passed." if not failures else "; ".join(failures)
    )


def _build_jsonschema_validator(schema: dict[str, Any]) -> Any:
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, format_checker=FormatChecker())


def _inline_local_json_refs(
    value: Any,
    base_dir: Path,
    repo_root: Path,
    current_document: Any | None = None,
) -> Any:
    current_document = value if current_document is None else current_document

    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            resolved = _resolve_local_json_ref(
                ref,
                base_dir,
                repo_root,
                current_document,
            )
            if resolved is not None:
                return _inline_local_json_refs(resolved, base_dir, repo_root, resolved)
        return {
            key: _inline_local_json_refs(item, base_dir, repo_root, current_document)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _inline_local_json_refs(item, base_dir, repo_root, current_document)
            for item in value
        ]
    return value


def _resolve_local_json_ref(
    ref: str,
    base_dir: Path,
    repo_root: Path,
    current_document: Any,
) -> Any | None:
    parsed = urlparse(ref)
    if parsed.scheme and parsed.scheme not in {"file"}:
        return None

    path_part = unquote(parsed.path)
    fragment = parsed.fragment

    if not path_part:
        if not fragment:
            return None
        return _resolve_json_pointer(current_document, fragment)

    if not path_part.endswith(".json"):
        return None

    target_path = (base_dir / path_part).resolve()
    target_schema, error = _load_schema_json(target_path, repo_root)
    if target_schema is None:
        raise ValueError(error or f"Unreadable schema ref: {ref}")

    target_value: Any = target_schema
    if fragment:
        target_value = _resolve_json_pointer(target_schema, fragment)
    return _inline_local_json_refs(
        target_value,
        target_path.parent,
        repo_root,
        target_schema,
    )


def _resolve_json_pointer(document: Any, fragment: str) -> Any:
    pointer = fragment[1:] if fragment.startswith("/") else fragment
    current = document
    if not pointer:
        return current
    for raw_part in pointer.split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def _check_version_semver_pattern(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(
        repo_root / "schemas/adapter_manifest.schema.json",
        repo_root,
    )
    if schema is None:
        return False, error or "adapter schema unreadable"
    pattern = schema.get("properties", {}).get("version_semver", {}).get("pattern")
    passed = isinstance(pattern, str) and "\\." in pattern
    return (
        passed,
        "version_semver pattern present."
        if passed
        else "version_semver pattern missing.",
    )


def _check_https_contract_schema(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(
        repo_root / "schemas/adapter_manifest.schema.json",
        repo_root,
    )
    if schema is None:
        return False, error or "adapter schema unreadable"
    contract = schema.get("properties", {}).get("contract_schema_url", {})
    pattern = contract.get("pattern")
    passed = (
        contract.get("format") == "uri"
        and isinstance(pattern, str)
        and pattern.startswith("^https://")
    )
    return (
        passed,
        "contract_schema_url enforces HTTPS URI."
        if passed
        else "contract_schema_url HTTPS enforcement missing.",
    )


def _check_deprecation_date_validation(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(
        repo_root / "schemas/adapter_manifest.schema.json",
        repo_root,
    )
    if schema is None:
        return False, error or "adapter schema unreadable"
    deprecation = schema.get("properties", {}).get("deprecation_date", {})
    passed = deprecation.get("format") == "date-time"
    return (
        passed,
        "deprecation_date uses ISO-8601 date-time validation."
        if passed
        else "deprecation_date format missing.",
    )


def _check_owner_required_fields(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(
        repo_root / "schemas/adapter_manifest.schema.json",
        repo_root,
    )
    if schema is None:
        return False, error or "adapter schema unreadable"
    required = set(schema.get("properties", {}).get("owner", {}).get("required", []))
    expected = {"team_id", "primary_contact", "escalation_policy_url"}
    passed = expected.issubset(required)
    return (
        passed,
        "owner required fields present."
        if passed
        else "owner required fields incomplete.",
    )
