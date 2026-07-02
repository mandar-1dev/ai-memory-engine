import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import Base, engine
from app.models import models  # noqa: F401 ensures models are registered
from app.api import auth, memory, notes, search, chat, dashboard

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Personal AI Memory Engine & Knowledge OS - core MVP (auth, memory, notes, semantic search, RAG chat)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


app.include_router(auth.router)
app.include_router(memory.router)
app.include_router(notes.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
