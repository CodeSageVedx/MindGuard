from typing import List, Dict
from pydantic import BaseModel, Field

from src.report_agent.report_graph import report_graph
from src.report_agent.report_state import GraphBState
from src.api.schemas import MessageTurn
import uuid


async def generate_clinical_report(transcript: List[Dict[str, str]], user_id: str = None, session_id: str = None) -> dict:
    """
    Generates a comprehensive clinical report using Graph B (LangGraph-based report generation).
    
    Args:
        transcript: List of conversation turns with 'sender' and 'content' fields
        user_id: Optional user identifier
        session_id: Optional session identifier
        
    Returns:
        dict with keys: risk_score, symptoms, summary, next_steps
    """
    try:
        # Convert transcript to Graph B format
        formatted_transcript = []
        for turn in transcript:
            formatted_transcript.append({
                "role": "user" if turn["sender"].lower() == "user" else "assistant",
                "content": turn["content"],
            })
        
        # Build initial state for Graph B
        initial_state: GraphBState = {
            "userId": user_id or str(uuid.uuid4()),
            "sessionId": session_id or str(uuid.uuid4()),
            "input": {
                "locale": "en-IN",
                "transcript": formatted_transcript,
                "now": ""  # Will be set by report_init_node
            },
            #"guardrails": {},
            "extracted": {
                "symptoms": [],
                "stressors": [],
                "emotions": [],
                "protectiveFactors": [],
                "timeHints": []
            },
            "safety": {
                "riskScore": 0,
                "crisisRecommendation": False,
                "flags": []
            },
            "reportContext": {
                "ragDocs": [],
                "kgFacts": [],
                "memoryItems": []
            },
            "report": {},
            "validation": {},
            "trace": {
                "traceId": str(uuid.uuid4())
            },
            "checkpoint": {}
        }
        
        # Configure with session ID for checkpointing
        config = {
            "configurable": {
                "thread_id": initial_state["sessionId"]
            }
        }
        
        # Invoke Graph B
        print(f"\n{'='*80}")
        print("🧠 Graph B: Clinical Report Generation Started")
        print(f"{'='*80}\n")
        
        result = await report_graph.ainvoke(initial_state, config)
        
        print(f"\n{'='*80}")
        print("✅ Graph B: Clinical Report Generation Complete")
        print(f"{'='*80}\n")
        
        # Extract report from final state
        report = result.get("report", {})
        
        return {
            "risk_score": report.get("riskScore", 0),
            "symptoms": report.get("symptoms", []),
            "summary": report.get("summary", "Report generation completed."),
            "next_steps": report.get("nextSteps", [])
        }
        
    except Exception as e:
        print(f"Clinical report error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "risk_score": 0,
            "symptoms": [],
            "summary": "Unable to generate report at this time.",
            "next_steps": ["Try again later"]
        }
