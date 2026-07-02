import json
from typing import Optional, Any

import redis

from app.core.config import get_settings

settings = get_settings()

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    try:
        redis_client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


def cache_get(key: str) -> Optional[Any]:
    try:
        raw = redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def push_recent_search(user_id: str, query: str, max_items: int = 10):
    try:
        key = f"recent_searches:{user_id}"
        redis_client.lpush(key, query)
        redis_client.ltrim(key, 0, max_items - 1)
    except Exception:
        pass


def get_recent_searches(user_id: str, limit: int = 10):
    try:
        key = f"recent_searches:{user_id}"
        return redis_client.lrange(key, 0, limit - 1)
    except Exception:
        return []
