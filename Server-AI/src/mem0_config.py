from mem0 import Memory
from src.config import settings


def get_mem0_config():
    """
    Returns mem0 configuration for user memory with Neo4j graph backend.
    Uses OpenAI for embeddings (same as RAG), Gemini for LLM processing.
    """
    config = {
    "version": "v1.1",
    "embedder": {
        "provider": "openai",
        "config": {"api_key": settings.OPENAI_API_KEY, "model": "text-embedding-3-small"},
    },
    "llm": {"provider": "openai", "config": {"api_key": settings.OPENAI_API_KEY, "model": settings.OPENAI_MODEL_MINI}},
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": settings.QDRANT_URL,
            "api_key": settings.QDRANT_API_KEY,
            "collection_name": "mem0_user_memory",
            "embedding_model_dims": 1536,
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": settings.NEO4J_URL, "username": settings.NEO4J_USERNAME, "password": settings.NEO4J_PASSWORD},
    },
}
    return config


# Singleton instance - initialize once, reuse everywhere
_memory_client = None

def get_memory_client() -> Memory:
    """
    Returns singleton mem0 Memory client.
    Call this function wherever you need mem0 access.
    """
    global _memory_client
    if _memory_client is None:
        config = get_mem0_config()
        _memory_client = Memory.from_config(config)
    return _memory_client