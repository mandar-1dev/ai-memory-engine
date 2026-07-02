from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User, Conversation, Message, Memory
from app.schemas.schemas import ChatRequest, ChatResponse, SearchResultItem
from app.services import ai, vector_store

router = APIRouter(prefix="/api/chat", tags=["RAG Assistant"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Resolve or create conversation
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title=payload.message[:60],
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # save user message
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.message))
    db.commit()

    # 2. Embedding generation + vector search (retrieval)
    query_embedding = ai.embed_query(payload.message)
    raw = vector_store.query_vectors(
        query_embedding,
        top_k=payload.top_k,
        where={"user_id": current_user.id},
    )

    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    sources = []
    context_chunks = []
    for i in range(len(docs)):
        meta = metas[i] or {}
        score = max(0.0, 1.0 - (dists[i] if i < len(dists) else 1.0))
        context_chunks.append(docs[i])
        sources.append(
            SearchResultItem(
                id=meta.get("record_id", ""),
                source_type=meta.get("source_type", "unknown"),
                title=meta.get("title") or meta.get("topic"),
                snippet=docs[i][:300],
                score=round(score, 4),
            )
        )

    # 3. Generation grounded in retrieved context
    answer = ai.generate_answer(payload.message, context_chunks)

    # save assistant message
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()

    # 4. Memory update: store this exchange as a new episodic memory
    enrichment = ai.enrich_memory(f"Q: {payload.message}\nA: {answer}")
    memory = Memory(
        user_id=current_user.id,
        conversation_id=conversation.id,
        source_type="conversation",
        content=f"Q: {payload.message}\nA: {answer}",
        summary=enrichment["summary"],
        topic=enrichment["topic"],
        category=enrichment["category"],
        keywords=enrichment["keywords"],
        emotion=enrichment["emotion"],
        importance_score=enrichment["importance_score"],
        memory_type="episodic",
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    vector_id = f"memory-{memory.id}"
    mem_embedding = ai.embed_text(memory.content)
    vector_store.upsert_vector(
        vector_id=vector_id,
        embedding=mem_embedding,
        document=memory.content,
        metadata={
            "user_id": current_user.id,
            "source_type": "memory",
            "record_id": memory.id,
            "topic": memory.topic or "",
        },
    )
    memory.vector_id = vector_id
    db.commit()

    return ChatResponse(conversation_id=conversation.id, answer=answer, sources=sources)
