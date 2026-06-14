from dataclasses import asdict

from tanscope.cache.redis_cache import Cache
from tanscope.core.constants import IMAGE_SEARCH_CACHE_TTL_SECONDS
from tanscope.services.image_search.base import ImageResult, ImageSearchProvider


class ImageSearchService:
    def __init__(self, provider: ImageSearchProvider, cache: Cache) -> None:
        self._provider = provider
        self._cache = cache

    async def search(self, query: str, limit: int) -> list[ImageResult]:
        key = self._cache_key(query, limit)
        cached = await self._cache.get_json(key)
        if cached is not None:
            return [ImageResult(**row) for row in cached]

        results = await self._provider.search(query, limit)
        await self._cache.set_json(
            key, [asdict(result) for result in results], IMAGE_SEARCH_CACHE_TTL_SECONDS
        )
        return results

    @staticmethod
    def _cache_key(query: str, limit: int) -> str:
        return f"imgsearch:{query.strip().lower()}:{limit}"
