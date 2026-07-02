from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User, Note
from app.schemas.schemas import NoteCreate, NoteUpdate, NoteOut
from app.services import ai, vector_store

router = APIRouter(prefix="/api/notes", tags=["Notes"])


@router.post("", response_model=NoteOut, status_code=201)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrichment = ai.enrich_memory(payload.content)

    note = Note(
        user_id=current_user.id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags or enrichment["keywords"],
        folder=payload.folder,
        ai_summary=enrichment["summary"],
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    vector_id = f"note-{note.id}"
    embedding = ai.embed_text(f"{payload.title}\n{payload.content}")
    vector_store.upsert_vector(
        vector_id=vector_id,
        embedding=embedding,
        document=f"{payload.title}\n{payload.content}",
        metadata={
            "user_id": current_user.id,
            "source_type": "note",
            "record_id": note.id,
            "title": note.title,
        },
    )
    note.vector_id = vector_id
    db.commit()
    db.refresh(note)

    return note


@router.get("", response_model=List[NoteOut])
def list_notes(
    folder: str = None,
    is_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Note).filter(
        Note.user_id == current_user.id, Note.is_archived == is_archived
    )
    if folder:
        query = query.filter(Note.folder == folder)
    return query.order_by(Note.is_pinned.desc(), Note.updated_at.desc()).all()


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = payload.model_dump(exclude_unset=True)
    content_changed = "content" in update_data or "title" in update_data
    for field, value in update_data.items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)

    if content_changed:
        embedding = ai.embed_text(f"{note.title}\n{note.content}")
        vector_id = note.vector_id or f"note-{note.id}"
        vector_store.upsert_vector(
            vector_id=vector_id,
            embedding=embedding,
            document=f"{note.title}\n{note.content}",
            metadata={
                "user_id": current_user.id,
                "source_type": "note",
                "record_id": note.id,
                "title": note.title,
            },
        )
        note.vector_id = vector_id
        db.commit()
        db.refresh(note)

    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.vector_id:
        vector_store.delete_vector(note.vector_id)
    db.delete(note)
    db.commit()
    return None
