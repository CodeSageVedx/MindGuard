from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from src.agents.state import TranscriptTurn

class ChatRequest(BaseModel):
    userId: str
    sessionId: str
    userText: str
    locale: Optional[str] = "en-US"
    channel: Optional[Literal["livekit", "web", "whatsapp"]] = "web"
    topK: Optional[int] = 4
    recentTurns: Optional[List[TranscriptTurn]] = []

class ChatResponse(BaseModel):
    assistantText: str
    riskLevel: str
    route: str
    traceId: str

class MessageTurn(BaseModel):
    sender: str = Field(..., description="USER or AI")
    content: str = Field(..., description="The message text")


class ReportRequest(BaseModel):
    transcript: List[MessageTurn]
    userId: Optional[str] = None
    sessionId: Optional[str] = None 

class ReportResponse(BaseModel):
    risk_score: int
    symptoms: List[str]
    summary: str
    next_steps: List[str]

class SentimentRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    score: float 
    label: str   
    emotion: str