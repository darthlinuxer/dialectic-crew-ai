"""Console rendering helpers for self-improve quality-gate results."""

from __future__ import annotations

from .quality_gate_models import QualityGateResult


def print_quality_gate_result(
    result: QualityGateResult,
    prefix: str = "  ",
) -> None:
    """Print quality gate results to console."""
    for check in result.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{prefix}{check.tool}: {status}")
        if check.errors:
            for error in check.errors[:5]:
                print(f"{prefix}  {error}")
            if len(check.errors) > 5:
                print(f"{prefix}  ... and {len(check.errors) - 5} more")
