import os
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from dialectic.vision import VisionContext


def _read_optional_float_env(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if 0.0 <= value <= 10.0 else None


MAX_RETRIES = int(os.getenv("PRD_MAX_RETRIES", "5"))
CONSENSUS_MIN_SCORE = _read_optional_float_env("PRD_CONSENSUS_MIN_SCORE")


class DialecticState(BaseModel):
    """Persistent state of the dialectic flow"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    feature_objective: str = ""
    prd_data: dict = {}
    prd_path_json: str = ""
    prd_path_md: str = ""
    quality_score: float = 0.0
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    consensus_min_score: float | None = CONSENSUS_MIN_SCORE
    consensus_reached: bool = False
    final_validation_notes: str = ""
    file_paths: list[str] = Field(default_factory=list)
    vision_context: str = VisionContext.PROJECT.value
    current_phase: Literal["start", "dialectic", "evaluate", "save", "completed"] = "start"
