# AI Memory Engine

> A personal knowledge OS that remembers what you tell it. Store memories and notes, search them semantically, and chat with an AI that grounds its answers in your own stored knowledge — a full retrieval-augmented generation (RAG) pipeline, built from scratch.

Every memory and note you save is automatically summarized, tagged, and embedded into a vector store. Ask a question, and the assistant retrieves the relevant pieces of your own knowledge before answering — with citations back to the source.

---

## Features

- 🔐 **Auth** — JWT-based register/login, bcrypt password hashing
- 🧠 **Memory Engine** — every memory is auto-enriched (summary, topic, category, keywords, emotion, importance score) via Gemini, then embedded
- 📝 **Notes** — create, edit, archive, favorite, pin — auto-summarized and embedded on save
- 🔍 **Semantic Search** — real vector similarity search across memories + notes (ChromaDB, cosine similarity)
- 💬 **RAG Chat** — the full pipeline: embed query → vector search → retrieve top-k → generate grounded answer → persist conversation → auto-create a new memory from the exchange
- 📊 **Dashboard** — live counts, memory health score, top topics, recent searches (Redis-backed)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, Pydantic v2 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Vector Store | ChromaDB (embedded, persistent) |
| AI | Google Gemini (`google-genai` SDK) — `gemini-embedding-001` for embeddings, `gemini-2.5-flash` for enrichment + generation |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| Deployment | Docker + Docker Compose |

## Architecture

```
User → Frontend (HTML/JS)
         │
         ▼
   FastAPI Backend
    │      │      │
    ▼      ▼      ▼
Postgres Redis ChromaDB
 (data)  (cache) (vectors)
    │
    ▼
 Gemini API
(embeddings + generation)
```

**RAG pipeline** (`/api/chat`):
```
User query → embed_query() → ChromaDB similarity search → top-k chunks
  → Gemini generation (grounded in retrieved context) → response
  → persist conversation + messages → auto-create memory from exchange
```

## Getting Started

### Option A — Docker (recommended)

```bash
git clone https://github.com/<your-username>/ai-memory-engine.git
cd ai-memory-engine
cp backend/.env.example backend/.env
# edit backend/.env and add your GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

docker compose up --build
```

Once you see `Uvicorn running on http://0.0.0.0:8000` in the logs:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Frontend: open `frontend/index.html` directly in your browser

### Option B — Local (no Docker)

Requires Python 3.11+, PostgreSQL, Redis.

```bash
# Database + cache
sudo apt-get install postgresql redis-server
sudo service postgresql start
redis-server --daemonize yes

sudo -u postgres psql -c "CREATE USER memoryengine WITH PASSWORD 'memoryengine_dev_pw';"
sudo -u postgres psql -c "CREATE DATABASE memory_engine OWNER memoryengine;"

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/index.html` in your browser.

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Create account, returns JWT |
| `POST` | `/api/auth/login` | — | Login, returns JWT |
| `GET` | `/api/auth/me` | ✅ | Current user |
| `POST` | `/api/memories` | ✅ | Create memory (auto-enriched + embedded) |
| `GET` | `/api/memories` | ✅ | List memories |
| `DELETE` | `/api/memories/{id}` | ✅ | Delete memory |
| `POST` | `/api/notes` | ✅ | Create note (auto-summarized + embedded) |
| `GET` | `/api/notes` | ✅ | List notes |
| `PATCH` | `/api/notes/{id}` | ✅ | Update note (re-embeds on content change) |
| `DELETE` | `/api/notes/{id}` | ✅ | Delete note |
| `POST` | `/api/search` | ✅ | Semantic search across memories + notes |
| `POST` | `/api/chat` | ✅ | RAG chat |
| `GET` | `/api/dashboard` | ✅ | Stats: counts, health score, top topics |
| `GET` | `/api/health` | — | Health check |

Full interactive docs (Swagger) available at `/docs` once running.

## Project Structure

```
ai-memory-engine/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # FastAPI entrypoint
│       ├── core/                  # config, security (JWT/bcrypt), auth deps
│       ├── db/                    # SQLAlchemy engine/session
│       ├── models/                # User, Memory, Note, Conversation, Message
│       ├── schemas/                # Pydantic request/response models
│       ├── services/
│       │   ├── ai.py              # Gemini: embeddings, enrichment, RAG generation
│       │   ├── vector_store.py    # ChromaDB wrapper
│       │   └── cache.py           # Redis helpers
│       └── api/                   # auth, memory, notes, search, chat, dashboard
└── frontend/
    └── index.html                 # single-page test UI
```

## Roadmap

This is the core, working slice of a larger vision. Not yet built:

- [ ] Google/GitHub OAuth
- [ ] Document ingestion (PDF/DOCX/OCR pipeline)
- [ ] Website/URL knowledge capture
- [ ] Knowledge graph visualization
- [ ] Recommendation engine
- [ ] Analytics dashboard with charts
- [ ] Admin panel
- [ ] Celery background jobs for heavier processing
- [ ] Next.js/TypeScript frontend

## License

MIT — free to use, modify, and build on.

## Author

Built by [Mandar](https://github.com/mandar-1dev) — [LinkedIn](https://linkedin.com/in/mandar-acse)