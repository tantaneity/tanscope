import asyncio
import logging

from tanscope.core.constants import WATCH_ACCOUNT_GAP_SECONDS
from tanscope.db.models import TrackedAccount
from tanscope.services.delivery import MediaDelivery, build_caption
from tanscope.services.watch.service import WatchBatch, WatchService

logger = logging.getLogger(__name__)


class WatchScheduler:
    def __init__(
        self, service: WatchService, delivery: MediaDelivery, interval_seconds: int
    ) -> None:
        self._service = service
        self._delivery = delivery
        self._interval = interval_seconds

    async def run(self) -> None:
        while True:
            await self._tick()
            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        for account in await self._service.enabled():
            await self._poll_one(account)
            await asyncio.sleep(WATCH_ACCOUNT_GAP_SECONDS)

    async def _poll_one(self, account: TrackedAccount) -> None:
        batch: WatchBatch | None = None
        try:
            batch = await self._service.poll(account)
            if batch.items:
                caption = build_caption(f"{account.platform} @{account.username}")
                await self._delivery.send_paths(account.chat_id, batch.items, caption)
        except Exception:
            logger.exception("watch poll failed for %s @%s", account.platform, account.username)
        finally:
            if batch is not None:
                self._service.cleanup(batch)
