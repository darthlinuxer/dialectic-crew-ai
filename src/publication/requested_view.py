from __future__ import annotations

from enum import Enum


class RequestedView(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    BOTH = "both"
