import logging

from aiogram import F, Router
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from tanscope.db.models import EventKind
from tanscope.db.stats_repository import StatsRepository
from tanscope.services.delivery import MediaDelivery, build_caption
from tanscope.services.download.errors import DownloadError
from tanscope.services.download.service import DownloadService

logger = logging.getLogger(__name__)
router = Router()

DOWNLOADING_TEXT = "📥 Downloading…"
FAILED_TEXT = "❌ Couldn't download. Check the link or try later."


@router.message(F.text.regexp(r"https?://"))
async def handle_link(
    message: Message,
    service: FromDishka[DownloadService],
    stats: FromDishka[StatsRepository],
    delivery: FromDishka[MediaDelivery],
) -> None:
    match = service.find(message.text or "")
    if match is None:
        return
    platform, url = match
    user_id = message.from_user.id if message.from_user else 0

    cached = await service.get_cached(url)
    if cached is not None:
        await delivery.send_cached(message.chat.id, cached, build_caption(platform.value, url))
        await stats.record(user_id, EventKind.DOWNLOAD, url, platform.value, cached=True)
        return

    status = await message.reply(DOWNLOADING_TEXT)
    try:
        result = await service.download(url, platform)
    except DownloadError as error:
        logger.warning("download failed for %s: %s", url, error)
        await status.edit_text(FAILED_TEXT)
        return
    except Exception:
        logger.exception("unexpected download error for %s", url)
        await status.edit_text(FAILED_TEXT)
        return

    try:
        stored = await delivery.send_paths(message.chat.id, result.items, build_caption(result.title, url))
        await service.store(url, stored)
        await stats.record(user_id, EventKind.DOWNLOAD, url, platform.value, cached=False)
    finally:
        service.cleanup(result)
        await status.delete()
