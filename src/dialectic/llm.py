"""Shared LLM configuration and singleton connectors for dialectic runtimes."""

from __future__ import annotations

import os
from typing import Any

from crewai import LLM

LLM_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "900"))

LLM_MODEL_SIMPLE = os.getenv("LLM_MODEL_SIMPLE", "gpt-4o-mini")
LLM_MODEL_COMPLEX = os.getenv("LLM_MODEL_COMPLEX", "gpt-4o")
LLM_MODEL_REASONING = os.getenv("LLM_MODEL_REASONING", "o3-mini")
LLM_MODEL_PLANNING = os.getenv("LLM_MODEL_PLANNING", LLM_MODEL_REASONING)

_COMMON: dict[str, Any] = {"timeout": LLM_TIMEOUT}

llm_simple = LLM(model=LLM_MODEL_SIMPLE, **_COMMON)
llm_complex = LLM(model=LLM_MODEL_COMPLEX, **_COMMON)
llm_reasoning = LLM(model=LLM_MODEL_REASONING, **_COMMON)
llm_planning = LLM(model=LLM_MODEL_PLANNING, **_COMMON)

LLM_BY_TIER = {
    "simple": llm_simple,
    "complex": llm_complex,
    "reasoning": llm_reasoning,
    "planning": llm_planning,
}
