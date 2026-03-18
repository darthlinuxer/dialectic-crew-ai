from __future__ import annotations

from enum import Enum


class EmittedView(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    BOTH = "both"
    MARKDOWN_ONLY = "markdown"
    JSON_ONLY = "json"
