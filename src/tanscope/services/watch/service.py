import shutil
from dataclasses import dataclass
from pathlib import Path
from secrets import token_hex

from tanscope.db.models import TrackedAccount
from tanscope.db.tracked_repository import TrackedRepository
from tanscope.services.download.base import MediaItem, Platform
from tanscope.services.watch.poller import ProfileWatcher


@dataclass(frozen=True, slots=True)
class WatchBatch:
    work_dir: Path | None
    items: list[MediaItem]


class WatchService:
    def __init__(
        self, repo: TrackedRepository, watcher: ProfileWatcher, downloads_dir: Path
    ) -> None:
        self._repo = repo
        self._watcher = watcher
        self._downloads_dir = downloads_dir

    async def track(self, chat_id: int, platform: Platform, username: str) -> bool:
        return await self._repo.add(chat_id, platform.value, username.lstrip("@"))

    async def untrack(self, chat_id: int, platform: Platform, username: str) -> bool:
        return await self._repo.remove(chat_id, platform.value, username.lstrip("@"))

    async def list_for(self, chat_id: int) -> list[TrackedAccount]:
        return await self._repo.list_for(chat_id)

    async def enabled(self) -> list[TrackedAccount]:
        return await self._repo.list_enabled()

    async def poll(self, account: TrackedAccount) -> WatchBatch:
        platform = Platform(account.platform)
        if not account.primed:
            await self._watcher.prime(platform, account.username)
            await self._repo.mark_primed(account.id)
            return WatchBatch(work_dir=None, items=[])
        dest = self._downloads_dir / "watch" / token_hex(8)
        dest.mkdir(parents=True, exist_ok=True)
        items = await self._watcher.fetch_new(platform, account.username, dest)
        return WatchBatch(work_dir=dest, items=items)

    @staticmethod
    def cleanup(batch: WatchBatch) -> None:
        if batch.work_dir is not None:
            shutil.rmtree(batch.work_dir, ignore_errors=True)
