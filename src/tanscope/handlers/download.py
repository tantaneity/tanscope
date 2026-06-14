import html
import logging

from aiogram import F, Router
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo, Message
from dishka.integrations.aiogram import FromDishka
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from tanscope.core.constants import MEDIA_GROUP_MAX_ITEMS
from tanscope.db.models import EventKind
from tanscope.db.stats_repository import StatsRepository
from tanscope.services.download.base import CachedMedia, MediaItem, MediaKind
from tanscope.services.download.errors import DownloadError
from tanscope.services.download.service import DownloadService

logger = logging.getLogger(__name__)
router = Router()

DOWNLOADING_TEXT = "📥 Downloading…"
FAILED_TEXT = "❌ Couldn't download. Check the link or try later."

MediaSource = FSInputFile | str
MediaPair = tuple[MediaKind, MediaSource]


@router.message(F.text.regexp(r"https?://"))
async def handle_link(
    message: Message,
    service: FromDishka[DownloadService],
    stats: FromDishka[StatsRepository],
) -> None:
    match = service.find(message.text or "")
    if match is None:
        return
    platform, url = match
    user_id = message.from_user.id if message.from_user else 0

    cached = await service.get_cached(url)
    if cached is not None:
        await _deliver(message, _cached_pairs(cached), _caption(platform.value, url))
        await stats.record(user_id, EventKind.DOWNLOAD, url, platform.value, cached=True)
        return

    status = await message.reply(DOWNLOADING_TEXT)
    try:
        result = await service.download(url, platform)
    except (DownloadError, YtDlpDownloadError) as error:
        logger.warning("download failed for %s: %s", url, error)
        await status.edit_text(FAILED_TEXT)
        return

    try:
        pairs = _fresh_pairs(result.items[:MEDIA_GROUP_MAX_ITEMS])
        sent = await _deliver(message, pairs, _caption(result.title, url))
        stored = [
            CachedMedia(kind=kind, file_id=_file_id(sent_message, kind))
            for (kind, _), sent_message in zip(pairs, sent)
        ]
        await service.store(url, stored)
        await stats.record(user_id, EventKind.DOWNLOAD, url, platform.value, cached=False)
    finally:
        service.cleanup(result)
        await status.delete()


def _fresh_pairs(items: list[MediaItem]) -> list[MediaPair]:
    return [(item.kind, FSInputFile(item.path)) for item in items]


def _cached_pairs(cached: list[CachedMedia]) -> list[MediaPair]:
    return [(item.kind, item.file_id) for item in cached[:MEDIA_GROUP_MAX_ITEMS]]


async def _deliver(message: Message, pairs: list[MediaPair], caption: str) -> list[Message]:
    if len(pairs) == 1:
        kind, source = pairs[0]
        return [await _send_single(message, kind, source, caption)]
    group: list[InputMediaPhoto | InputMediaVideo] = []
    for index, (kind, source) in enumerate(pairs):
        item_caption = caption if index == 0 else None
        media_class = InputMediaVideo if kind == MediaKind.VIDEO else InputMediaPhoto
        group.append(media_class(media=source, caption=item_caption))
    return await message.answer_media_group(group)


async def _send_single(
    message: Message, kind: MediaKind, source: MediaSource, caption: str
) -> Message:
    if kind == MediaKind.VIDEO:
        return await message.answer_video(source, caption=caption)
    return await message.answer_photo(source, caption=caption)


def _file_id(message: Message, kind: MediaKind) -> str:
    if kind == MediaKind.VIDEO and message.video:
        return message.video.file_id
    if kind == MediaKind.PHOTO and message.photo:
        return message.photo[-1].file_id
    raise DownloadError("no file_id in sent message")


def _caption(title: str, url: str) -> str:
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
