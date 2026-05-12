"""
LiveKit Voice Agent with Deepgram STT/TTS and LangGraph Brain
"""
import logging
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import deepgram, silero
from src.livekit.langgraph_llm import LangGraphLLM
from src.config import settings

load_dotenv()

# Configure logging - suppress verbose database/checkpoint logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s - %(message)s'
)

# Suppress verbose logs from these modules
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)
logging.getLogger('pymongo.command').setLevel(logging.WARNING)
logging.getLogger('pymongo.serverSelection').setLevel(logging.WARNING)
logging.getLogger('pymongo.topology').setLevel(logging.WARNING)
logging.getLogger('neo4j').setLevel(logging.WARNING)
logging.getLogger('neo4j.io').setLevel(logging.WARNING)
logging.getLogger('neo4j.pool').setLevel(logging.WARNING)
logging.getLogger('livekit.plugins.deepgram').setLevel(logging.WARNING)
logging.getLogger('livekit.agents').setLevel(logging.WARNING)
logging.getLogger('livekit').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('mem0.vector_stores.qdrant').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class MindGuardAgent(Agent):
    """
    MindGuard AI Mental Health Voice Agent
    Uses LangGraph for counseling logic and decision-making
    """
    
    def __init__(self, session_id: str = None) -> None:
        super().__init__(
            instructions="""You are MindGuard AI, a compassionate mental health support assistant.
            Your purpose is to provide empathetic, evidence-based support to individuals seeking mental health guidance.
            
            Key guidelines:
            - Always be empathetic, non-judgmental, and supportive
            - Prioritize user safety - detect and respond to crisis situations immediately
            - Use active listening and validation techniques
            - Provide grounding exercises when users are in distress
            - Suggest coping strategies based on CBT, mindfulness, and other evidence-based approaches
            - Know your limits - always recommend professional help when appropriate
            - Maintain confidentiality and respect user privacy
            - Speak naturally and conversationally, avoiding overly clinical language
            - Keep responses concise and clear for voice interaction
            - Avoid using complex formatting, emojis, or special characters in speech
            
            Remember: You are a supportive companion, not a replacement for professional mental health care.
            """
        )
        self.session_id = session_id


# Create the agent server
server = AgentServer()


@server.rtc_session()
async def mindguard_voice_agent(ctx: agents.JobContext):
    """
    Main entry point for the LiveKit agent
    Sets up the voice pipeline with Deepgram STT/TTS and LangGraph brain
    """
    logger.info(f"Starting MindGuard agent for room: {ctx.room.name}")
    
    # Generate session ID for this conversation
    session_id = f"{ctx.room.name}_{ctx.job.id}"
    
    # Create the Pipeline Session
    session = AgentSession(
        vad=silero.VAD.load(),              # Voice Activity Detection
        stt=deepgram.STT(),                 # Speech-to-Text: Deepgram
        llm=LangGraphLLM(session_id=session_id),  # Brain: Your LangGraph agent
        tts=deepgram.TTS(
            model="aura-asteria-en",        # Empathetic voice
        ),
    )

    # # Start Tavus avatar bridge so the agent appears on video
    # avatar = tavus.AvatarSession(
    #     replica_id=settings.TAVUS_REPLICA_ID,
    #     persona_id=settings.TAVUS_PERSONA_ID,
    #     avatar_participant_name=settings.TAVUS_AVATAR_NAME,
    # )
    # await avatar.start(session, room=ctx.room)
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=MindGuardAgent(session_id=session_id),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Keep it simple - Deepgram handles its own noise cancellation
                noise_cancellation=lambda params: None
            ),
        ),
    )
    
    # Generate initial greeting
    await session.generate_reply(
        instructions="""Greet the user warmly and introduce yourself as MindGuard AI.
        Let them know you're here to provide mental health support and that this is a safe,
        confidential space. Ask how they're feeling today or what brought them here.
        Keep it conversational and welcoming."""
    )
    
    logger.info(f"MindGuard agent started successfully for session: {session_id}")


# CLI entry point
if __name__ == "__main__":
    logger.info("Starting MindGuard AI Voice Agent Server...")
    agents.cli.run_app(server)
