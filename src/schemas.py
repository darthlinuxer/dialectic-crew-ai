from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class UserStory(BaseModel):
    id: str = Field(..., description="US-001")
    title: str
    description: str
    acceptance_criteria: List[str] = Field(..., min_length=3)
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
    user_stories: List[UserStory] = Field(..., min_length=1)
    anti_drift_questions: List[AntiDriftQuestion] = Field(..., min_length=5)
    quality_score: float = Field(..., ge=0.0, le=10.0)
    consensus_reached: bool = False
    final_validation_notes: str
    vision_hash: Optional[str] = None


# --- Execution plans (dialectic per user story) ---


class ImplementationTask(BaseModel):
    id: str = Field(..., description="e.g.: T-001")
    title: str
    description: str
    order: int = 0
    dependencies: List[str] = []
    acceptance_checks: List[str] = Field(
        default_factory=list,
        description="Verifiable criteria: e.g. 'file X exists', 'function Y defined in Z'",
    )
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    completed_at: Optional[str] = None
    verification_notes: str = ""


class UserStoryExecutionPlan(BaseModel):
    """Approved implementation plan for a user story (output of the dialectic execution flow)."""
    user_story_id: str
    user_story_title: str
    approach_summary: str = Field(..., description="Summary of the technical approach")
    tasks: List[ImplementationTask] = Field(..., min_length=1)
    risks_mitigated: List[str] = []
    tech_notes: str = ""
    quality_score: float = Field(..., ge=0.0, le=10.0)
    consensus_reached: bool = False
    final_validation_notes: str = ""
    source_prd_path: Optional[str] = None
    vision_hash: Optional[str] = None
    status: Literal[
        "pending", "in_progress", "completed", "partially_completed", "failed"
    ] = "pending"
    completed_at: Optional[str] = None


# --- Dialectic execution results ---


class ValidationOutput(BaseModel):
    """Structured output from the Validator agent (used with output_pydantic)."""
    quality_score: float = Field(..., ge=0.0, le=10.0)
    consensus_reached: bool = False
    final_validation_notes: str = ""


class VerificationResult(BaseModel):
    """Result of post-execution verification (Phase A)."""
    verified: bool = False
    checks_passed: List[str] = Field(default_factory=list)
    checks_failed: List[str] = Field(default_factory=list)
    notes: str = ""


class TaskExecutionResult(BaseModel):
    task_id: str
    title: str
    success: bool
    score: float
    retry_count: int
    output_paths: List[str] = Field(default_factory=list)
    validation_notes: str = ""
    output_summary: str = ""
    verification: Optional[VerificationResult] = None
    execution_phases: List[str] = Field(
        default_factory=list,
        description="Phases executed: dialectic, verify, reimplement",
    )


class ExecutionReport(BaseModel):
    plan_id: str
    plan_title: str
    run_id: str
    plan_path: Optional[str] = None
    vision_hash: Optional[str] = None
    task_results: List[TaskExecutionResult] = Field(default_factory=list)
    overall_success: bool = False
    verified_tasks: List[str] = Field(default_factory=list)
    failed_verification_tasks: List[str] = Field(default_factory=list)


# --- Self-improvement schemas ---


# --- Dialectic prioritization schemas ---


class PrioritizedOpportunity(BaseModel):
    """Result of dialectic debate ranking for a single improvement opportunity."""
    opportunity_id: str
    rank: int
    justification: str
    feasibility_score: float = Field(..., ge=0.0, le=10.0)
    alignment_score: float = Field(..., ge=0.0, le=10.0)
    final_priority_score: float = Field(..., ge=0.0, le=10.0)


class PrioritizationResult(BaseModel):
    """Output of the dialectic prioritization crew."""
    ranked: List[PrioritizedOpportunity] = Field(default_factory=list)
    debate_summary: str = ""


# --- Self-improvement schemas ---


class ImprovementOpportunity(BaseModel):
    id: str
    category: Literal[
        "vision_gap", "metric_regression", "code_health", "failure_pattern"
    ]
    title: str
    description: str
    evidence: List[str] = Field(default_factory=list)
    estimated_impact: Literal["low", "medium", "high"] = "medium"


class IntrospectionReport(BaseModel):
    timestamp: str
    opportunities: List[ImprovementOpportunity] = Field(default_factory=list)
    baseline_metrics: dict = Field(default_factory=dict)


class SelfImprovementRecord(BaseModel):
    cycle_id: str
    timestamp: str
    opportunities_found: int = 0
    opportunities_attempted: int = 0
    prd_generated: bool = False
    plan_generated: bool = False
    execution_attempted: bool = False
    tests_passed: bool = False
    metrics_stable: bool = False
    pr_created: bool = False
    branch_name: str = ""
    prd_path_json: str = ""
    prd_path_md: str = ""
    plan_path_json: str = ""
    plan_path_md: str = ""
    execution_run_id: str = ""
    execution_output_path: str = ""
    execution_report_path: str = ""
    failure_reason: str = ""
    total_tokens: int = 0
    estimated_cost: float = 0.0
