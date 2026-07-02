from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User, SearchLog
from app.schemas.schemas import SearchQuery, SearchResponse, SearchResultItem
from app.services import ai, vector_store, cache

router = APIRouter(prefix="/api/search", tags=["Semantic Search"])


@router.post("", response_model=SearchResponse)
def semantic_search(
    payload: SearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query_embedding = ai.embed_query(payload.query)

    where = {"user_id": current_user.id}
    if payload.source_types and len(payload.source_types) == 1:
        where = {"$and": [{"user_id": current_user.id}, {"source_type": payload.source_types[0]}]}

    raw = vector_store.query_vectors(query_embedding, top_k=payload.top_k, where=where)

    results = []
    ids = raw.get("ids", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    for i in range(len(ids)):
        meta = metas[i] or {}
        if payload.source_types and meta.get("source_type") not in payload.source_types:
            continue
        distance = dists[i] if i < len(dists) else 1.0
        score = max(0.0, 1.0 - distance)
        snippet = docs[i][:300] if docs[i] else ""
        results.append(
            SearchResultItem(
                id=meta.get("record_id", ids[i]),
                source_type=meta.get("source_type", "unknown"),
                title=meta.get("title") or meta.get("topic"),
                snippet=snippet,
                score=round(score, 4),
            )
        )

    # log + cache recent search
    db.add(SearchLog(user_id=current_user.id, query=payload.query, result_count=len(results)))
    db.commit()
    cache.push_recent_search(current_user.id, payload.query)

    return SearchResponse(query=payload.query, results=results)
