from pydantic import BaseModel, Field

MAX_RETRIES = 5


class DialecticState(BaseModel):
    """Persistent state of the dialectic flow"""
    feature_objective: str = ""
    vision_content: str = ""
    prd_data: dict = {}
    quality_score: float = 0.0
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    consensus_reached: bool = False
    final_validation_notes: str = ""
    file_paths: list[str] = Field(default_factory=list)
