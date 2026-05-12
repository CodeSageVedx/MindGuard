from langchain_core.tools import tool
from typing import List, Dict, Any
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from src.mem0_config import get_memory_client
from src.config import settings
from langchain_openai import OpenAIEmbeddings

@tool
def retrieve_from_qdrant(query: str, top_k: int = 10) -> List[dict]:
    """Search Qdrant vector DB for relevant mental health guidance."""
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        timeout=300  # Increase timeout to 5 minutes
    )

    embeddings = OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY,
        model="text-embedding-3-small"
    )

    qdrant = QdrantVectorStore(
        client=client,
        collection_name="mental_health_guidance",
        embedding=embeddings,
        retrieval_mode=RetrievalMode.DENSE,
    )

    results = qdrant.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content, 
            "score": float(score), 
            "source": doc.metadata.get("source_file", "unknown"), 
            "metadata": doc.metadata 
        }
        for doc, score in results
    ]
@tool
def recall_user_memory(user_id: str, query: str, limit: int = 5) -> List[str]:
    """
    Fetch user's personalized memory from mem0 (backed by Neo4j).
    Returns past preferences, helpful strategies, and patterns.
    """
    memory_client = get_memory_client()  # Get singleton instance
    
    # Search user's memory graph
    memories = memory_client.search(
        query=query, 
        user_id=user_id, 
        limit=limit
    )
    
    # Extract memory text
    return [
        m.get("memory", "")
        for m in memories.get("results", [])
    ]

@tool
def add_user_memory(user_id: str, messages: List[Dict[str, str]]) -> bool:
    """
    Store conversation in user's memory (mem0 + Neo4j).
    Call this after each conversation turn.
    """
    memory_client = get_memory_client()
    
    try:
        memory_client.add(messages=messages, user_id=user_id)
        return True
    except Exception as e:
        print(f"[mem0] Error adding memory: {e}")
        return False

