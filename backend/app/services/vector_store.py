import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

settings = get_settings()

_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIR,
    settings=ChromaSettings(anonymized_telemetry=False),
)

_collection = _client.get_or_create_collection(
    name="knowledge",
    metadata={"hnsw:space": "cosine"},
)


def upsert_vector(vector_id: str, embedding, document: str, metadata: dict):
    _collection.upsert(
        ids=[vector_id],
        embeddings=[embedding],
        documents=[document],
        metadatas=[metadata],
    )


def delete_vector(vector_id: str):
    try:
        _collection.delete(ids=[vector_id])
    except Exception:
        pass


def query_vectors(embedding, top_k: int, where: dict = None):
    return _collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=where or None,
    )
