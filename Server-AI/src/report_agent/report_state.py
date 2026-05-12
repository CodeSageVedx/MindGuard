from typing import TypedDict, List, Literal, Optional, Dict, Any
from datetime import datetime

# Shared type definitions
Role = Literal["user", "assistant", "system"]

class TranscriptTurn(TypedDict, total=False):
    role: Role
    content: str
    ts: str  # ISO timestamp

class RetrievalDoc(TypedDict, total=False):
    content: str  # text chunk
    score: float  # similarity score
    source: str  # file/book id, url, etc.
    metadata: Dict[str, Any]

class TraceInfo(TypedDict, total=False):
    traceId: str  # one trace per turn/report
    sessionSpanId: str  # optional

class Safety(TypedDict):
    riskLevel: Literal["low", "medium", "high", "critical"]
    needsCrisis: bool
    flags: List[str]  # e.g., ["self_harm", "panic", "abuse"]

# Graph B specific types
class InputData(TypedDict, total=False):
    locale: str  # "en-IN"
    transcript: List[TranscriptTurn]  # full transcript or larger slice
    now: str

class Guardrails(TypedDict, total=False):
    scrubbedTranscript: List[TranscriptTurn]

class Extracted(TypedDict, total=False):
    symptoms: List[str]
    stressors: List[str]
    emotions: List[str]
    protectiveFactors: List[str]
    timeHints: List[str]  # duration/frequency hints

class SafetyReport(TypedDict, total=False):
    riskScore: int  # 0..5 (or 1..5)
    crisisRecommendation: bool
    flags: List[str]

class ReportContext(TypedDict, total=False):
    ragDocs: List[RetrievalDoc]
    kgFacts: List[str]
    memoryItems: List[str]

class Report(TypedDict, total=False):
    riskScore: int
    symptoms: List[str]
    summary: str
    nextSteps: List[str]

class Validation(TypedDict, total=False):
    valid: bool
    errors: List[str]
    repaired: bool

class Checkpoint(TypedDict, total=False):
    riskScore: int
    endedAt: str

# Main Graph B State
class GraphBState(TypedDict, total=False):
    # Identity (shared between Express and FastAPI)
    userId: str  # same ID as Graph A
    sessionId: str
    
    # Input for report generation
    input: InputData
    
    # Guardrails outputs
    guardrails: Guardrails
    
    # Extracted signals
    extracted: Extracted
    
    # Safety assessment
    safety: SafetyReport
    
    # Context sources for report
    reportContext: ReportContext
    
    # Final report output
    report: Report
    
    # Validation state
    validation: Validation
    
    # Tracing
    trace: TraceInfo
    
    # Checkpoint summary
    checkpoint: Checkpoint
