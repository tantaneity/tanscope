import asyncio
from typing import Any

from ddgs import DDGS

from tanscope.services.image_search.base import ImageResult, ImageSearchProvider


class DuckDuckGoImageSearch(ImageSearchProvider):
    async def search(self, query: str, limit: int) -> list[ImageResult]:
        rows = await asyncio.to_thread(self._search_sync, query, limit)
        results = [self._to_result(row) for row in rows]
        return [result for result in results if self._is_valid(result)]

    @staticmethod
    def _search_sync(query: str, limit: int) -> list[dict[str, Any]]:
        with DDGS() as ddgs:
            return list(ddgs.images(query=query, safesearch="moderate", max_results=limit))

    @staticmethod
    def _to_result(row: dict[str, Any]) -> ImageResult:
        return ImageResult(
            image_url=str(row.get("image", "")),
            thumbnail_url=str(row.get("thumbnail") or row.get("image", "")),
            source_url=str(row.get("url", "")),
            title=str(row.get("title", "")),
            width=int(row.get("width") or 0),
            height=int(row.get("height") or 0),
        )

    @staticmethod
    def _is_valid(result: ImageResult) -> bool:
        return result.image_url.startswith("http") and result.thumbnail_url.startswith("http")
