"""Loader utility for PRD_OUTPUT_FORMAT environment variable.

Behavior:
- Reads PRD_OUTPUT_FORMAT from environment (case-insensitive).
- Accepts: 'md', 'json', 'both' (any case).
- Returns the normalized lowercase value.
- Falls back to 'both' if absent or invalid.

This module is intentionally minimal and dependency-free so it can be used
across the project (CLI, exporters, tests).
"""
from __future__ import annotations

import os
from typing import Literal

PRD_OUTPUT_CHOICES = ("md", "json", "both")
FALLBACK: Literal["md", "json", "both"] = "both"


def get_prd_output_format() -> Literal["md", "json", "both"]:
    """Return normalized PRD output format.

    Reads PRD_OUTPUT_FORMAT from the environment, normalizes to lowercase and
    validates against allowed choices. If absent or invalid, returns the default
    fallback 'both'.
    """
    raw = os.getenv("PRD_OUTPUT_FORMAT")
    if raw is None:
        return FALLBACK
    value = raw.strip().lower()
    if value in PRD_OUTPUT_CHOICES:
        # mypy-friendly cast
        return value  # type: ignore[return-value]
    return FALLBACK


if __name__ == "__main__":
    # Quick manual check
    print("PRD_OUTPUT_FORMAT ->", get_prd_output_format())
