from fastapi import APIRouter, HTTPException, Header, Depends
from src.api.schemas import ChatRequest, ChatResponse, ReportResponse, ReportRequest, SentimentResponse, SentimentRequest
from src.agents.graph import app_graph
from src.agents.state import GraphAState
from src.config import settings
from datetime import datetime
import uuid
from src.agents.sentiment import analyze_sentiment
from src.agents.reporting import generate_clinical_report
from fastapi.responses import StreamingResponse
import asyncio
import json


router = APIRouter()

async def verify_secret(x_internal_secret: str = Header(...)):
    if x_internal_secret != settings.AI_SERVICE_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

from fastapi.responses import StreamingResponse
import asyncio

@router.post("/agent/stream", dependencies=[Depends(verify_secret)])
async def stream_agent_endpoint(request: ChatRequest):
    """
    Streams fast_ack immediately, then final after a 2s client-side delay.
    """
    initial_state: GraphAState = {
        "userId": request.userId,
        "sessionId": request.sessionId,
        "input": {
            "userText": request.userText,
            "locale": request.locale or "en-US",
            "channel": request.channel or "web",
            "topK": request.topK or 4,
            "now": datetime.now().isoformat() + "Z",
        },
        "transcript": {"recentTurns": request.recentTurns or []},
        "trace": {"traceId": str(uuid.uuid4()), "sessionSpanId": str(uuid.uuid4())},
        "safety": {"riskLevel": "low", "needsCrisis": False, "flags": []},
        "routing": {"route": "support", "retrievalNeeded": False},
        "rag": {"docs": []},
        "kg": {"facts": []},
        "memory": {"items": []},
        "contextPack": {"mergedContext": "", "sourcesMeta": []},
        "output": {},
        "streaming": {"started": False, "tokensSent": 0},
        "checkpoint": {"endedAt": ""},
    }

    config = {"configurable": {"thread_id": request.sessionId}}

    async def event_generator():
        async for chunk in app_graph.astream(initial_state, config, stream_mode="values"):
            events = chunk.get("output", {}).get("events") or []
            for ev in events:
                # send full messages as JSON lines
                yield f"data: {json.dumps(ev)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/agent/invoke", response_model=ChatResponse, dependencies=[Depends(verify_secret)])
async def invoke_agent_endpoint(request: ChatRequest):
    """
    Invokes the AI agent with the provided chat messages and returns the response.
    Initializes the complete GraphAState from the request.
    """
    # Build initial state from request
    initial_state: GraphAState = {
        # Identity
        "userId": request.userId,
        "sessionId": request.sessionId,
        
        # Input for this turn
        "input": {
            "userText": request.userText,
            "locale": request.locale or "en-US",
            "channel": request.channel or "web",
            "topK": request.topK or 4,
            "now": datetime.now().isoformat() + "Z"
        },
        
        # Recent context (from Express server)
        "transcript": {
            "recentTurns": request.recentTurns or []
        },
        
        # Initialize trace
        "trace": {
            "traceId": str(uuid.uuid4()),
            "sessionSpanId": str(uuid.uuid4())
        },
        
        # Initialize empty structures
        # "guardrails": {},
        "safety": {
            "riskLevel": "low",
            "needsCrisis": False,
            "flags": []
        },
        "routing": {
            "route": "support",
            "retrievalNeeded": False
        },
        "rag": {"docs": []},
        "kg": {"facts": []},
        "memory": {"items": []},
        "contextPack": {
            "mergedContext": "",
            "sourcesMeta": []
        },
        "output": {},
        "streaming": {
            "started": False,
            "tokensSent": 0
        },
        "checkpoint": {
            "endedAt": ""
        }
    }
    
    # Invoke the graph with initial state
    config = {
        "configurable": {
            "thread_id": request.sessionId
        }
    }
    
    try:
        result = await app_graph.ainvoke(initial_state, config)
        
        return ChatResponse(
            assistantText=result.get("output", {}).get("finalText", ""),
            riskLevel=result.get("safety", {}).get("riskLevel", "low"),
            route=result.get("routing", {}).get("route", "support"),
            traceId=result.get("trace", {}).get("traceId", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/report", response_model=ReportResponse, dependencies=[Depends(verify_secret)])
async def generate_report_endpoint(request: ReportRequest):
    # Convert MessageTurn to dict format expected by generate_clinical_report
    transcript_dicts = [
        {"sender": turn.sender, "content": turn.content}
        for turn in request.transcript
    ]
    result = await generate_clinical_report(
        transcript=transcript_dicts,
        user_id=getattr(request, 'userId', None),
        session_id=getattr(request, 'sessionId', None)
    )
    return result


@router.post("/analyze/sentiment", response_model=SentimentResponse, dependencies=[Depends(verify_secret)])
async def analyze_sentiment_endpoint(request: SentimentRequest):
    """
    Quick sentiment check for dashboards.
    """
    result = await analyze_sentiment(request.text)
    return result