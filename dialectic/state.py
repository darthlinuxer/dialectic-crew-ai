from pydantic import BaseModel

MAX_RETRIES = 5


class DialecticState(BaseModel):
    """Estado persistente do fluxo dialético"""
    feature_objective: str = ""
    vision_content: str = ""
    prd_data: dict = {}
    quality_score: float = 0.0
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    consensus_reached: bool = False
    final_validation_notes: str = ""
