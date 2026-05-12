from typing import List, Literal
from pydantic import BaseModel, Field

# Output schema for ReportGuardrails node
class GuardrailsOutputModel(BaseModel):
    scrubbedTranscript: List[dict] = Field(
        ..., 
        description="Transcript with PII scrubbed and safety constraints applied"
    )
    blocked: bool = Field(
        default=False, 
        description="Whether content should be blocked"
    )

# Output schema for SignalExtract node
class SignalExtractModel(BaseModel):
    symptoms: List[str] = Field(
        ..., 
        description="List of identified psychological symptoms (e.g., 'anxiety', 'depressed mood', 'insomnia')"
    )
    stressors: List[str] = Field(
        ..., 
        description="List of identified stressors (e.g., 'work pressure', 'relationship conflict', 'financial stress')"
    )
    emotions: List[str] = Field(
        ..., 
        description="List of emotions expressed (e.g., 'fear', 'sadness', 'anger', 'hopelessness')"
    )
    protectiveFactors: List[str] = Field(
        ..., 
        description="List of protective factors (e.g., 'family support', 'coping skills', 'therapy engagement')"
    )
    timeHints: List[str] = Field(
        ..., 
        description="Duration/frequency hints (e.g., 'for 2 weeks', 'every night', 'since last month')"
    )

# Output schema for RiskScore node
class RiskScoreModel(BaseModel):
    riskScore: int = Field(
        ..., 
        ge=0, 
        le=5, 
        description="Risk score from 0 (minimal) to 5 (critical)"
    )
    crisisRecommendation: bool = Field(
        ..., 
        description="Whether immediate crisis intervention is recommended"
    )
    flags: List[str] = Field(
        ..., 
        description="List of risk flags (e.g., 'self_harm', 'suicidal_ideation', 'severe_distress')"
    )

# Output schema for ReportPlan node
class ReportPlanModel(BaseModel):
    sections: List[str] = Field(
        ..., 
        description="Report sections to include (e.g., 'immediate_actions', 'weekly_plan', 'long_term_goals')"
    )
    emphasis: Literal["immediate", "week", "long-term"] = Field(
        ..., 
        description="What timeframe to emphasize based on risk level"
    )
    retrievalNeeded: bool = Field(
        ..., 
        description="Whether RAG retrieval is needed for evidence-based recommendations"
    )
    kgNeeded: bool = Field(
        ..., 
        description="Whether knowledge graph enrichment is needed"
    )
    memoryNeeded: bool = Field(
        ..., 
        description="Whether memory recall is needed"
    )

# Output schema for AssembleReportJSON node
class AssembleReportModel(BaseModel):
    riskScore: int = Field(
        ..., 
        ge=0, 
        le=5, 
        description="Final risk score"
    )
    symptoms: List[str] = Field(
        ..., 
        description="List of identified symptoms"
    )
    summary: str = Field(
        ..., 
        description="Clinical summary of the session"
    )
    nextSteps: List[str] = Field(
        ..., 
        description="Actionable next steps for the user"
    )

# Output schema for ValidateSchema node
class ValidateSchemaModel(BaseModel):
    valid: bool = Field(
        ..., 
        description="Whether the report schema is valid"
    )
    errors: List[str] = Field(
        default_factory=list, 
        description="List of validation errors if any"
    )
