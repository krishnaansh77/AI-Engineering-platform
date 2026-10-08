"""Low-cost provider usage accounting backed by Redis."""
from datetime import datetime, timezone
import uuid
from redis import asyncio as redis


def usage_key(user_id: uuid.UUID, day: str | None = None) -> str:
    current_day = day or datetime.now(timezone.utc).date().isoformat()
    return f"aise:usage:llm:{user_id}:{current_day}"


async def consume_llm_request(redis_url: str, user_id: uuid.UUID, limit: int) -> tuple[bool, int]:
    """Consume one daily request slot and return (allowed, remaining)."""
    if limit <= 0:
        return True, -1
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        key = usage_key(user_id)
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 172800)
        if count > limit:
            await client.decr(key)
            return False, 0
        return True, limit - count
    finally:
        await client.aclose()


async def current_llm_usage(redis_url: str, user_id: uuid.UUID, limit: int) -> dict:
    client = redis.from_url(redis_url, decode_responses=True)
    try:
        count = int(await client.get(usage_key(user_id)) or 0)
        return {"used": count, "daily_limit": limit, "remaining": max(limit - count, 0) if limit > 0 else None}
    finally:
        await client.aclose()
