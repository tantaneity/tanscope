import hashlib
import shutil
from asyncio import Semaphore
from dataclasses import asdict
from pathlib import Path
from secrets import token_hex

from tanscope.cache.redis_cache import Cache
from tanscope.core.constants import FILE_ID_CACHE_TTL_SECONDS
from tanscope.services.download.base import (
    CachedMedia,
    DownloadResult,
    DownloadSource,
    MediaKind,
    Platform,
)
from tanscope.services.download.resolver import PlatformResolver


class DownloadService:
    def __init__(
        self,
        source: DownloadSource,
        resolver: PlatformResolver,
        cache: Cache,
        semaphore: Semaphore,
        downloads_dir: Path,
    ) -> None:
        self._source = source
        self._resolver = resolver
        self._cache = cache
        self._semaphore = semaphore
        self._downloads_dir = downloads_dir

    def find(self, text: str) -> tuple[Platform, str] | None:
        return self._resolver.find(text)

    async def get_cached(self, url: str) -> list[CachedMedia] | None:
        rows = await self._cache.get_json(self._cache_key(url))
        if rows is None:
            return None
        return [CachedMedia(kind=MediaKind(row["kind"]), file_id=row["file_id"]) for row in rows]

    async def download(self, url: str, platform: Platform) -> DownloadResult:
        async with self._semaphore:
            dest = self._downloads_dir / token_hex(8)
            dest.mkdir(parents=True, exist_ok=True)
            return await self._source.download(url, platform, dest)

    async def store(self, url: str, media: list[CachedMedia]) -> None:
        payload = [asdict(item) for item in media]
        await self._cache.set_json(self._cache_key(url), payload, FILE_ID_CACHE_TTL_SECONDS)

    @staticmethod
    def cleanup(result: DownloadResult) -> None:
        shutil.rmtree(result.work_dir, ignore_errors=True)

    @staticmethod
    def _cache_key(url: str) -> str:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return f"dl:{digest}"
