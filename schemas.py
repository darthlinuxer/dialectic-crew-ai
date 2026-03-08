from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class UserStory(BaseModel):
    id: str = Field(..., description="US-001")
    title: str
    description: str
    acceptance_criteria: List[str] = Field(..., min_items=3)
    effort: Literal["XS", "S", "M", "L", "XL"]
    dependencies: List[str] = []


class MacroImpact(BaseModel):
    modules_affected: List[str]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    performance_impact: str
    security_impact: str


class AntiDriftQuestion(BaseModel):
    question: str
    answer: str


class PRDSchema(BaseModel):
    feature_name: str
    version: str = "1.0"
    objective: str
    macro_impact: MacroImpact
    user_stories: List[UserStory] = Field(..., min_items=1)
    anti_drift_questions: List[AntiDriftQuestion] = Field(..., min_items=5)
    quality_score: float = Field(..., ge=0.0, le=10.0)
    consensus_reached: bool = False
    final_validation_notes: str
