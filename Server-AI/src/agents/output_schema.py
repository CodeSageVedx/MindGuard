from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any


class SafetyModel(BaseModel):
    """Pydantic model for LLM structured output"""
    riskLevel: Literal["low", "medium", "high", "critical"]
    needsCrisis: bool
    flags: List[str] = Field(default_factory=list, description="e.g., ['self_harm', 'panic', 'abuse']")

class FastAcknowledgeModel (BaseModel):
    """Pydantic model for LLM structured fast acknowledgement output"""
    fastAckText: str

class route_decider_node_Model(BaseModel):
    """Pydantic model for LLM structured route decider node output"""
    route: List[str]
    retrievalNeeded: bool

class query_fanout_translate_node_Model(BaseModel):
    """Pydantic model for LLM structured query fanout translate node output"""
    fanoutQueries: List[str]

# Single retrieval document model
class RetrievalDocModel(BaseModel):
    """Pydantic model for a single retrieval document"""
    content: str = Field(description="Text chunk from the retrieved document")
    score: Optional[float] = Field(default=None, description="Similarity score")
    source: Optional[str] = Field(default=None, description="File/book id, url, etc.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

# RAG response containing multiple documents
class RAG_retrieval_docs_Model(BaseModel):
    """Pydantic model for LLM structured RAG retrieval docs output"""
    docs: List[RetrievalDocModel] = Field(
        default_factory=list,
        description="List of retrieved documents from vector store"
    )

class WHETHER_USER_SHARED_CONCERN_Model(BaseModel):
    """Pydantic model for LLM structured opening to working check output"""
    user_shared_concern : bool

class whether_GOAL_ACHEIVED_Model(BaseModel) :
    goal_achieved : bool

class WHETHER_USER_CONFIRMED_END_Model(BaseModel) :
    user_confirmed_end : bool

class counselling_composer_node_Model(BaseModel):
    """Pydantic model for LLM structured counselling_composer node output"""
    finalText : str