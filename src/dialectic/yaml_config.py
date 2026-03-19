"""Helpers for loading and rendering small YAML-backed CrewAI config files."""

from __future__ import annotations

# pylint: disable=import-outside-toplevel

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping from *path*.

    The roadmap only needs small mapping-based config files for now, so this
    helper keeps validation intentionally narrow.
    """
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML config at {config_path} must contain a top-level mapping"
        )
    return data


def render_yaml_config(value: Any, placeholders: dict[str, Any]) -> Any:
    """Recursively substitute ``str.format`` placeholders within YAML values."""
    if isinstance(value, str):
        return value.format(**placeholders)
    if isinstance(value, list):
        return [render_yaml_config(item, placeholders) for item in value]
    if isinstance(value, dict):
        return {
            key: render_yaml_config(item, placeholders) for key, item in value.items()
        }
    return value


def _resolve_named_reference(name: str, registry: dict[str, Any], kind: str) -> Any:
    try:
        return registry[name]
    except KeyError as exc:
        raise KeyError(f"Unknown {kind}: {name}") from exc


def get_output_schema_registry() -> dict[str, Any]:
    """Return the mapping of YAML schema names to concrete Python classes."""
    from schemas import (
        PRDSchema,
        PrioritizationResult,
        UserStoryExecutionPlan,
        ValidationOutput,
        VerificationResult,
    )

    return {
        "PRDSchema": PRDSchema,
        "PrioritizationResult": PrioritizationResult,
        "UserStoryExecutionPlan": UserStoryExecutionPlan,
        "ValidationOutput": ValidationOutput,
        "VerificationResult": VerificationResult,
    }


def get_guardrail_registry() -> dict[str, Any]:
    """Return the mapping of YAML guardrail names to callable implementations."""
    from dialectic.prd_flow import _prd_guardrail
    from dialectic.prioritize import _prioritization_guardrail
    from execution.task_guardrails import (
        _quality_guardrail,
        _text_result_guardrail,
        _verification_guardrail,
    )
    from planning.flow import _plan_guardrail

    return {
        "plan": _plan_guardrail,
        "prd": _prd_guardrail,
        "prioritization": _prioritization_guardrail,
        "quality": _quality_guardrail,
        "text_result": _text_result_guardrail,
        "verification": _verification_guardrail,
    }


def resolve_output_schema(name: str) -> Any:
    """Resolve an output schema name declared in YAML into its Python class."""
    return _resolve_named_reference(name, get_output_schema_registry(), "output schema")


def resolve_guardrail(name: str) -> Any:
    """Resolve a guardrail name declared in YAML into its Python callable."""
    return _resolve_named_reference(name, get_guardrail_registry(), "guardrail")
