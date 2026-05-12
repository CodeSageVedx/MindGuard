from typing import TypedDict, List, Literal, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# Type definitions
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

class InputData(TypedDict, total=False):
    userText: str  # current user message (STT result or typed)
    locale: str  # e.g., "en-IN"
    channel: Literal["livekit", "web", "whatsapp"]
    topK: int  # retrieval topK (default 4)
    now: str  # ISO timestamp

class Transcript(TypedDict):
    recentTurns: List[TranscriptTurn]  # last N turns (6–12)

# class Guardrails(TypedDict, total=False):
#     cleanedText: str  # sanitized user text (optional)
#     blocked: bool  # if request must be refused
#     blockReason: str

class Routing(TypedDict, total=False):
    route: List[str] # ["grounding", "cbt", "coping", "mindfulness", "resources", "info", "support"]
    retrievalNeeded: bool
    fanoutQueries: List[str]  # produced by QueryFanoutTranslate

class RAG(TypedDict):
    docs: List[RetrievalDoc]


class Memory(TypedDict):
    items: List[str]  # mem0 recalled snippets (short)

class SourceMeta(TypedDict, total=False):
    source: str
    score: float
    metadata: Dict[str, Any]

class ContextPack(TypedDict, total=False):
    mergedContext: str  # final compact context string fed to LLM
    sourcesMeta: List[SourceMeta]

class OutputEvent(TypedDict):
    type: str
    payload: Any

class Output(TypedDict, total=False):
    fastAckText: str  # from FastAcknowledge
    finalText: str  # main assistant content
    safetyOverride: bool  # if CrisisOverride took control
    events: List[OutputEvent]  # optional telemetry

class Streaming(TypedDict, total=False):
    started: bool
    tokensSent: int

class Checkpoint(TypedDict, total=False):
    route: str
    riskLevel: str
    usedRag: bool
    usedKg: bool
    usedMem: bool
    sourceIds: List[str]  # optional identifiers
    endedAt: str  # ISO timestamp

class SessionPhase(TypedDict, total=False):
    """Tracks clinical session structure"""
    current: Literal["opening", "working", "closing", "ended"]
    startTime: str  # ISO timestamp when session started
    phaseStartTime: str  # When current phase started
    openingTurns: int  # Turns spent in opening (target: 2-4)
    workingTurns: int  # Turns in working phase (target: 6-10)
    closingTurns: int  # Turns in closing (target: 2-3)
    totalDuration: float  # Minutes elapsed
    interventionType: str  # "cbt", "grounding", "coping" etc.
    rapportEstablished: bool  # Flag from opening phase
    goalAchieved: bool  # Flag from working phase


class GraphAState(TypedDict, total=False):
    # Identity (shared between Express and FastAPI)
    userId: str  # sole user identifier (from Express)
    sessionId: str  # conversation session id (from Express)
    
    # Input for this turn
    input: InputData

    # Session management
    sessionPhase : SessionPhase
    
    # Recent context (provided by Express; AI does not read DB)
    transcript: Transcript
    
    # Guardrails + triage outputs
    # guardrails: Guardrails # removed guardrails for now
    safety: Safety
    
    # Routing decisions
    routing: Routing
    
    # Context sources
    rag: RAG
    memory: Memory
    contextPack: ContextPack
    
    # Output for this turn
    output: Output
    
    # Streaming + tracing
    streaming: Streaming
    trace: TraceInfo
    
    # Checkpoint summary (what you store in Mongo checkpointing)
    checkpoint: Checkpoint