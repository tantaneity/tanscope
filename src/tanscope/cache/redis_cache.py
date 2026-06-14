import json
from typing import Any

from redis.asyncio import Redis


class Cache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_json(self, key: str) -> Any | None:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)

    async def get_str(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set_str(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)
