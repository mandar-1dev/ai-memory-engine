import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User, Memory
from app.schemas.schemas import MemoryCreate, MemoryOut
from app.services import ai, vector_store

router = APIRouter(prefix="/api/memories", tags=["Memory Engine"])


@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(
    payload: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrichment = ai.enrich_memory(payload.content)

    memory = Memory(
        user_id=current_user.id,
        content=payload.content,
        summary=enrichment["summary"],
        topic=payload.topic or enrichment["topic"],
        category=payload.category or enrichment["category"],
        keywords=enrichment["keywords"],
        emotion=enrichment["emotion"],
        importance_score=payload.importance_score or enrichment["importance_score"],
        memory_type=payload.memory_type,
        session_id=payload.session_id,
        extra_metadata=payload.metadata or {},
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    vector_id = f"memory-{memory.id}"
    embedding = ai.embed_text(payload.content)
    vector_store.upsert_vector(
        vector_id=vector_id,
        embedding=embedding,
        document=payload.content,
        metadata={
            "user_id": current_user.id,
            "source_type": "memory",
            "record_id": memory.id,
            "topic": memory.topic or "",
        },
    )
    memory.vector_id = vector_id
    db.commit()
    db.refresh(memory)

    return memory


@router.get("", response_model=List[MemoryOut])
def list_memories(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Memory)
        .filter(Memory.user_id == current_user.id)
        .order_by(Memory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = (
        db.query(Memory)
        .filter(Memory.id == memory_id, Memory.user_id == current_user.id)
        .first()
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=204)
def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = (
        db.query(Memory)
        .filter(Memory.id == memory_id, Memory.user_id == current_user.id)
        .first()
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if memory.vector_id:
        vector_store.delete_vector(memory.vector_id)
    db.delete(memory)
    db.commit()
    return None
