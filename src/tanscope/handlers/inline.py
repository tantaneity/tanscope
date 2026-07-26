import asyncio
import logging

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResult,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InlineQueryResultPhoto,
    InputTextMessageContent,
)
from dishka.integrations.aiogram import FromDishka

from tanscope.core.config import Config
from tanscope.core.constants import (
    INLINE_CACHE_TIME_SECONDS,
    INLINE_NOTICE_CACHE_TIME_SECONDS,
    INLINE_QUERY_MIN_LENGTH,
    INLINE_RESULTS_LIMIT,
)
from tanscope.db.models import EventKind
from tanscope.db.stats_repository import StatsRepository
from tanscope.services.delivery import MediaDelivery, build_caption, strip_no_caption
from tanscope.services.download.base import CachedMedia, MediaKind, Platform
from tanscope.services.download.errors import DownloadError
from tanscope.services.download.service import DownloadService
from tanscope.services.image_search.base import ImageResult
from tanscope.services.image_search.service import ImageSearchService

logger = logging.getLogger(__name__)
router = Router()

PENDING_TITLE = "📥 Downloading…"
PENDING_TEXT = "Media is being fetched, send the same link again in a few seconds."
UNAVAILABLE_TITLE = "❌ Link downloads are off"
UNAVAILABLE_TEXT = "Set MEDIA_CHAT_ID (or ADMIN_IDS) to enable inline downloads."

# ponytail: in-process dedup, fine for one bot instance. Redis lock if it ever scales out.
_prefetching: dict[str, asyncio.Task[None]] = {}


@router.inline_query()
async def handle_inline(
    query: InlineQuery,
    search: FromDishka[ImageSearchService],
    download: FromDishka[DownloadService],
    delivery: FromDishka[MediaDelivery],
    config: FromDishka[Config],
) -> None:
    text, wants_caption = strip_no_caption(query.query.strip())
    match = download.find(text)
    if match is not None:
        platform, url = match
        await _answer_link(query, download, delivery, config, platform, url, wants_caption)
        return
    if len(text) < INLINE_QUERY_MIN_LENGTH:
        await query.answer([], cache_time=INLINE_CACHE_TIME_SECONDS)
        return
    results = await search.search(text, INLINE_RESULTS_LIMIT)
    photos = [_to_photo(index, item) for index, item in enumerate(results)]
    await query.answer(photos, cache_time=INLINE_CACHE_TIME_SECONDS)


@router.chosen_inline_result()
async def handle_chosen(
    chosen: ChosenInlineResult,
    stats: FromDishka[StatsRepository],
    download: FromDishka[DownloadService],
) -> None:
    text, _ = strip_no_caption(chosen.query.strip())
    match = download.find(text)
    if match is not None:
        platform, url = match
        await stats.record(
            user_id=chosen.from_user.id,
            kind=EventKind.DOWNLOAD,
            target=url,
            platform=platform.value,
            cached=True,
        )
        return
    await stats.record(
        user_id=chosen.from_user.id,
        kind=EventKind.IMAGE_SEARCH,
        target=chosen.query,
    )


async def _answer_link(
    query: InlineQuery,
    download: DownloadService,
    delivery: MediaDelivery,
    config: Config,
    platform: Platform,
    url: str,
    wants_caption: bool,
) -> None:
    cached = await download.get_cached(url)
    if cached is not None:
        caption = build_caption(platform.value, url) if wants_caption else None
        results: list[InlineQueryResult] = [
            _to_cached_result(index, item, platform.value, caption)
            for index, item in enumerate(cached)
        ]
        await query.answer(results, cache_time=INLINE_CACHE_TIME_SECONDS)
        return

    chat_id = config.media_cache_chat_id
    if chat_id is None:
        await query.answer(
            [_notice(UNAVAILABLE_TITLE, UNAVAILABLE_TEXT)],
            cache_time=INLINE_NOTICE_CACHE_TIME_SECONDS,
        )
        return

    _schedule_prefetch(download, delivery, chat_id, platform, url)
    await query.answer(
        [_notice(PENDING_TITLE, PENDING_TEXT)],
        cache_time=INLINE_NOTICE_CACHE_TIME_SECONDS,
    )


def _schedule_prefetch(
    download: DownloadService,
    delivery: MediaDelivery,
    chat_id: int,
    platform: Platform,
    url: str,
) -> None:
    if url in _prefetching:
        return
    task = asyncio.create_task(_prefetch(download, delivery, chat_id, platform, url))
    _prefetching[url] = task
    task.add_done_callback(lambda _: _prefetching.pop(url, None))


async def _prefetch(
    download: DownloadService,
    delivery: MediaDelivery,
    chat_id: int,
    platform: Platform,
    url: str,
) -> None:
    try:
        result = await download.download(url, platform)
    except DownloadError as error:
        logger.warning("inline download failed for %s: %s", url, error)
        return
    except Exception:
        logger.exception("unexpected inline download error for %s", url)
        return
    try:
        stored = await delivery.send_paths(chat_id, result.items, build_caption(result.title, url))
        await download.store(url, stored)
    finally:
        download.cleanup(result)


def _to_cached_result(
    index: int, item: CachedMedia, title: str, caption: str | None
) -> InlineQueryResult:
    if item.kind == MediaKind.VIDEO:
        return InlineQueryResultCachedVideo(
            id=str(index),
            video_file_id=item.file_id,
            title=title,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    return InlineQueryResultCachedPhoto(
        id=str(index),
        photo_file_id=item.file_id,
        caption=caption,
        parse_mode=ParseMode.HTML,
    )


def _notice(title: str, text: str) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=title,
        title=title,
        description=text,
        input_message_content=InputTextMessageContent(message_text=text),
    )


def _to_photo(index: int, item: ImageResult) -> InlineQueryResultPhoto:
    return InlineQueryResultPhoto(
        id=str(index),
        photo_url=item.image_url,
        thumbnail_url=item.thumbnail_url,
        photo_width=item.width or None,
        photo_height=item.height or None,
        title=item.title or None,
    )
