from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Memory ----------
class MemoryCreate(BaseModel):
    content: str
    topic: Optional[str] = None
    category: Optional[str] = None
    memory_type: Optional[str] = "episodic"
    importance_score: Optional[float] = 0.5
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class MemoryOut(BaseModel):
    id: str
    content: str
    summary: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = []
    emotion: Optional[str] = None
    importance_score: float
    memory_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Notes ----------
class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []
    folder: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    folder: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class NoteOut(BaseModel):
    id: str
    title: str
    content: str
    tags: Optional[List[str]] = []
    folder: Optional[str] = None
    is_favorite: bool
    is_pinned: bool
    is_archived: bool
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Search / RAG ----------
class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    source_types: Optional[List[str]] = None  # ["memory", "note"]


class SearchResultItem(BaseModel):
    id: str
    source_type: str
    title: Optional[str] = None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    top_k: int = 5


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[SearchResultItem]


# ---------- Dashboard ----------
class DashboardStats(BaseModel):
    total_memories: int
    total_notes: int
    total_conversations: int
    recent_searches: List[str]
    memory_health_score: float
    top_topics: List[Dict[str, Any]]
