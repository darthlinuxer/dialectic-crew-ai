"""Shared CrewAI tool bundle registry for dialectic agents."""

from __future__ import annotations

from typing import Any

from dialectic.tools import (
    code_docs_tool,
    file_read_tool,
    file_write_tool,
    directory_read_tool,
    stack_validation_tool,
)

TOOL_BUNDLES: dict[str, list[Any]] = {
    "none": [],
    "read_only": [file_read_tool, code_docs_tool],
    "planning_read_only": [file_read_tool],
    "validator_read": [file_read_tool],
    "implementer_io": [file_read_tool, file_write_tool, directory_read_tool, stack_validation_tool],
}