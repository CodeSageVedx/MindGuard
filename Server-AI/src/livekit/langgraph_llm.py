"""
Custom LLM wrapper for LangGraph agent to work with LiveKit
"""
from typing import Optional, Any, List
import asyncio
import logging
from livekit.agents import llm
from livekit.agents.llm.llm import APIConnectOptions
from src.agents.graph import app_graph
from src.agents.state import GraphAState
import uuid
from datetime import datetime, UTC


logger = logging.getLogger(__name__)


class LangGraphLLM(llm.LLM):
    """
    Custom LLM implementation that wraps the LangGraph agent
    """
    
    def __init__(self, session_id: Optional[str] = None):
        super().__init__()
        self.session_id = session_id or str(uuid.uuid4())
        
    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: Optional[list] = None,
        conn_options: APIConnectOptions = APIConnectOptions(),
        tool_choice: Optional[str] = None,
        **_: Any,
    ) -> "llm.LLMStream":
        """
        Execute the LangGraph agent and return streaming response
        """
        return LangGraphLLMStream(
            llm=self,
            chat_ctx=chat_ctx,
            session_id=self.session_id,
            tools=tools or [],
            conn_options=conn_options,
        )


class LangGraphLLMStream(llm.LLMStream):
    """
    Streaming implementation for LangGraph agent responses
    """
    
    def __init__(
        self,
        llm: "LangGraphLLM",
        chat_ctx: llm.ChatContext,
        session_id: str,
        tools: list,
        conn_options: APIConnectOptions,
    ):
        super().__init__(
            llm=llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options
        )
        self._session_id = session_id
        self._collected_text = ""
        
    async def _run(self) -> None:
        """
        Run the LangGraph agent and stream the response
        """
        # Get the last user message
        user_messages = [msg for msg in self._chat_ctx.items if msg.role == "user"]
        if not user_messages:
            return
        
        # Extract text content from the message (content is a list of ChatContent items)
        last_message = user_messages[-1]
        user_text = ""
        for content_item in last_message.content:
            if isinstance(content_item, str):
                user_text += content_item
        
        if not user_text:
            return
        
        # Initialize state for the LangGraph agent
        initial_state: GraphAState = {
            "userId": "user_" + self._session_id[:10],  # Generate user_id from session
            "sessionId": self._session_id,
            "input": {
                "userText": user_text,
                "locale": "en-US",
                "channel": "livekit",
                "topK": 4,
                "now": datetime.now(UTC).isoformat()
            },
            "transcript": {
                "recentTurns": self._build_recent_turns()
            },
            "safety": {
                "riskLevel": "low",
                "needsCrisis": False,
                "flags": []
            },
            "routing": {
                "route": [],
                "retrievalNeeded": False,
                "fanoutQueries": []
            },
            "rag": {
                "docs": []
            },
            "memory": {
                "items": []
            },
            "contextPack": {
                "mergedContext": "",
                "sourcesMeta": []
            },
            "output": {
                "fastAckText": "",
                "finalText": "",
                "safetyOverride": False,
                "events": []
            },
            "streaming": {
                "started": False,
                "tokensSent": 0
            },
            "trace": {
                "traceId": str(uuid.uuid4()),
                "sessionSpanId": self._session_id
            },
            "sessionPhase": {
                "current": "opening",
                "startTime": datetime.now(UTC).isoformat(),
                "phaseStartTime": datetime.now(UTC).isoformat(),
                "openingTurns": 0,
                "workingTurns": 0,
                "closingTurns": 0,
                "totalDuration": 0,
                "interventionType": "general",
                "rapportEstablished": False,
                "goalAchieved": False
            },
            "checkpoint": {
                "route": "",
                "riskLevel": "low",
                "usedRag": False,
                "usedKg": False,
                "usedMem": False,
                "sourceIds": []
            }
        }
        
        # Configure the graph with thread_id for checkpointing
        config = {
            "configurable": {
                "thread_id": self._session_id
            }
        }
        
        sent_anything = False
        processed_events: set[tuple] = set()
        last_final_text = ""

        try:
            # Stream LangGraph state updates and flush new events to TTS ASAP
            async for chunk in app_graph.astream(initial_state, config, stream_mode="values"):
                output = chunk.get("output", {}) or {}
                events: List[dict] = output.get("events") or []
                last_final_text = output.get("finalText", last_final_text)

                # Dequeue unseen events and push them to LiveKit
                for ev in events:
                    key = (ev.get("type"), ev.get("text"))
                    if key in processed_events:
                        continue
                    processed_events.add(key)

                    text = ev.get("text") or ev.get("payload")
                    if not text:
                        continue

                    delay_ms = ev.get("delay_ms") or 0
                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000)

                    logger.debug(
                        "[LiveKitBridge] send type=%s len=%s text=%r",
                        ev.get("type"),
                        len(text),
                        text,
                    )
                    await self._send_text(text)
                    sent_anything = True

            # Fallback: if graph finished without emitting events, send finalText or a default
            if not sent_anything:
                fallback = last_final_text or "I'm here to support you. How can I help you today?"
                await self._send_text(fallback)

        except Exception as e:
            print(f"Error in LangGraph execution: {e}")
            error_response = "I'm experiencing some technical difficulties. Please try again."
            await self._send_text(error_response)
    
    def _build_recent_turns(self) -> list:
        """
        Build recent turns from chat context for the LangGraph agent
        """
        turns = []
        for msg in self._chat_ctx.items:
            # Extract text content from the message
            text_content = ""
            for content_item in msg.content:
                if isinstance(content_item, str):
                    text_content += content_item
            
            if text_content:  # Only add if there's text content
                turns.append({
                    "role": msg.role,
                    "content": text_content,
                    "ts": datetime.now(UTC).isoformat()
                })
        return turns[-12:]  # Keep last 12 turns

    async def _send_text(self, text: str) -> None:
        """Send a single chunk (no token streaming)."""
        if not text:
            return
        safe_text = text if text.endswith((" ", "\n")) else text + " "
        self._event_ch.send_nowait(
            llm.ChatChunk(
                id=str(uuid.uuid4()),
                delta=llm.ChoiceDelta(
                    role="assistant",
                    content=safe_text,
                )
            )
        )
