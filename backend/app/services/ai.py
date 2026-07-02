import json
import logging
from typing import List, Dict, Any

from google import genai
from google.genai import types

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env to enable AI features."
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """Generate an embedding vector for a piece of text using Gemini."""
    client = _get_client()
    result = client.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return result.embeddings[0].values


def embed_query(text: str) -> List[float]:
    return embed_text(text, task_type="RETRIEVAL_QUERY")


def generate_json(prompt: str) -> Dict[str, Any]:
    """Ask Gemini for a structured JSON response (used for memory enrichment)."""
    client = _get_client()
    response = client.models.generate_content(
        model=settings.GEMINI_CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    try:
        return json.loads(response.text)
    except Exception:
        logger.warning("Failed to parse JSON from Gemini response: %s", response.text)
        return {}


def enrich_memory(content: str) -> Dict[str, Any]:
    """Use Gemini to derive summary, topic, category, keywords, emotion, importance."""
    prompt = f"""Analyze the following piece of personal knowledge/memory text and return a JSON object
with exactly these fields:
- "summary": one sentence summary (string)
- "topic": a short topic phrase (string)
- "category": one of ["technology","personal","work","learning","health","finance","other"]
- "keywords": array of up to 6 lowercase keyword strings
- "emotion": one of ["neutral","positive","negative","excited","concerned"]
- "importance_score": float between 0 and 1 estimating how important this is to remember long-term

Text:
\"\"\"{content}\"\"\"

Return ONLY the JSON object, nothing else."""
    data = generate_json(prompt)
    return {
        "summary": data.get("summary", content[:200]),
        "topic": data.get("topic", "general"),
        "category": data.get("category", "other"),
        "keywords": data.get("keywords", []),
        "emotion": data.get("emotion", "neutral"),
        "importance_score": float(data.get("importance_score", 0.5) or 0.5),
    }


def generate_answer(query: str, context_chunks: List[str]) -> str:
    """RAG final-answer generation grounded in retrieved context."""
    client = _get_client()
    context_block = "\n\n---\n\n".join(
        f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
    )
    prompt = f"""You are a personal AI memory assistant. Answer the user's question using ONLY the
context below, which was retrieved from their personal notes and memories. If the context does not
contain the answer, say you don't have that information stored yet. Cite sources inline like [Source 1]
when you use them. Be concise and direct.

Context:
{context_block if context_block else "(no relevant context found)"}

User question: {query}

Answer:"""
    response = client.models.generate_content(
        model=settings.GEMINI_CHAT_MODEL,
        contents=prompt,
    )
    return response.text
