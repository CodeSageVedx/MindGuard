from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    #app
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"

    # gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MODEL_MINI : str = "gemini-2.5-flash-lite"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # openai
    OPENAI_API_KEY: str
    OPENAI_MODEL_MINI : str = "gpt-4o-mini"
    
    # neo4j
    NEO4J_USERNAME : str
    NEO4J_PASSWORD : str
    NEO4J_URL : str

    # qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str
    COLLECTION_NAME: str = "mindguard-knowledge-base"

    # mongodb
    MONGO_URI: str
    CHECKPOINT_DB_NAME: str = "mindguard_checkpoints"

    # neo4j (optional)
    neo4j_url: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""

    # internal auth
    AI_SERVICE_SECRET: str
    
    # LiveKit
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # Tavus (avatar plugin)
    TAVUS_API_KEY: str
    TAVUS_REPLICA_ID: str
    TAVUS_PERSONA_ID: str
    TAVUS_AVATAR_NAME: str = "MindGuard Avatar"
    
    # Deepgram (for STT/TTS)
    DEEPGRAM_API_KEY: str
    
    # ElevenLabs (optional backup)
    ELEVENLABS_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
