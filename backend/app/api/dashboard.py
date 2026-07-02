from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User, Memory, Note, Conversation
from app.schemas.schemas import DashboardStats
from app.services import cache

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_memories = db.query(func.count(Memory.id)).filter(Memory.user_id == current_user.id).scalar()
    total_notes = db.query(func.count(Note.id)).filter(Note.user_id == current_user.id).scalar()
    total_conversations = (
        db.query(func.count(Conversation.id)).filter(Conversation.user_id == current_user.id).scalar()
    )

    recent_searches = cache.get_recent_searches(current_user.id)

    topics = (
        db.query(Memory.topic)
        .filter(Memory.user_id == current_user.id, Memory.topic.isnot(None))
        .all()
    )
    topic_counts = Counter(t[0] for t in topics if t[0])
    top_topics = [{"topic": t, "count": c} for t, c in topic_counts.most_common(8)]

    total_items = (total_memories or 0) + (total_notes or 0)
    memory_health_score = min(1.0, round(total_items / 50, 2)) if total_items else 0.0

    return DashboardStats(
        total_memories=total_memories or 0,
        total_notes=total_notes or 0,
        total_conversations=total_conversations or 0,
        recent_searches=recent_searches,
        memory_health_score=memory_health_score,
        top_topics=top_topics,
    )
