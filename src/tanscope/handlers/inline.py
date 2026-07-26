import asyncio
import logging

from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResult,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InlineQueryResultPhoto,
    InputMediaPhoto,
    InputMediaVideo,
    InputTextMessageContent,
)
from dishka.integrations.aiogram import FromDishka

from tanscope.core.config import Config
from tanscope.core.constants import (
    DOWNLOAD_TIMEOUT_SECONDS,
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

PENDING_CAPTION = "📥 Downloading…"
FAILED_CAPTION = "❌ Couldn't download this one."
SOURCE_BUTTON_TEXT = "Source"
LINK_RESULT_ID = "link"
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
    delivery: FromDishka[MediaDelivery],
    config: FromDishka[Config],
    bot: FromDishka[Bot],
) -> None:
    text, wants_caption = strip_no_caption(chosen.query.strip())
    match = download.find(text)
    if match is None:
        await stats.record(
            user_id=chosen.from_user.id,
            kind=EventKind.IMAGE_SEARCH,
            target=chosen.query,
        )
        return
    platform, url = match
    was_cached = chosen.result_id != LINK_RESULT_ID
    await stats.record(
        user_id=chosen.from_user.id,
        kind=EventKind.DOWNLOAD,
        target=url,
        platform=platform.value,
        cached=was_cached,
    )
    if chosen.inline_message_id is None or was_cached:
        return
    await _fill_inline_message(
        bot, download, delivery, config, chosen.inline_message_id, platform, url, wants_caption
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
    placeholder = InlineQueryResultCachedPhoto(
        id=LINK_RESULT_ID,
        photo_file_id=await delivery.placeholder_photo_id(chat_id),
        title=platform.value,
        caption=PENDING_CAPTION,
        reply_markup=_source_keyboard(url),
    )
    await query.answer([placeholder], cache_time=INLINE_NOTICE_CACHE_TIME_SECONDS)


async def _fill_inline_message(
    bot: Bot,
    download: DownloadService,
    delivery: MediaDelivery,
    config: Config,
    inline_message_id: str,
    platform: Platform,
    url: str,
    wants_caption: bool,
) -> None:
    cached = await download.get_cached(url)
    if cached is None:
        chat_id = config.media_cache_chat_id
        if chat_id is None:
            return
        _schedule_prefetch(download, delivery, chat_id, platform, url)
        await _wait_for_prefetch(url)
        cached = await download.get_cached(url)
    if not cached:
        await _mark_failed(bot, inline_message_id, url)
        return

    caption = build_caption(platform.value, url) if wants_caption else None
    extra_items = len(cached) - 1
    if caption is not None and extra_items > 0:
        caption = f"{caption} (+{extra_items} more, send the link to the bot for the album)"
    try:
        await bot.edit_message_media(
            media=_to_input_media(cached[0], caption),
            inline_message_id=inline_message_id,
        )
    except TelegramBadRequest as error:
        logger.warning("inline edit failed for %s: %s", url, error)


async def _mark_failed(bot: Bot, inline_message_id: str, url: str) -> None:
    try:
        await bot.edit_message_caption(
            inline_message_id=inline_message_id, caption=FAILED_CAPTION
        )
    except TelegramBadRequest as error:
        logger.warning("inline failure notice not delivered for %s: %s", url, error)


async def _wait_for_prefetch(url: str) -> None:
    task = _prefetching.get(url)
    if task is None:
        return
    await asyncio.wait({task}, timeout=DOWNLOAD_TIMEOUT_SECONDS)


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


def _source_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=SOURCE_BUTTON_TEXT, url=url)]]
    )


def _to_input_media(item: CachedMedia, caption: str | None) -> InputMediaPhoto | InputMediaVideo:
    media_class = InputMediaVideo if item.kind == MediaKind.VIDEO else InputMediaPhoto
    return media_class(media=item.file_id, caption=caption, parse_mode=ParseMode.HTML)


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
