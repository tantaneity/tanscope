from aiogram import Router
from aiogram.types import ChosenInlineResult, InlineQuery, InlineQueryResultPhoto
from dishka.integrations.aiogram import FromDishka

from tanscope.core.constants import (
    INLINE_CACHE_TIME_SECONDS,
    INLINE_QUERY_MIN_LENGTH,
    INLINE_RESULTS_LIMIT,
)
from tanscope.db.models import EventKind
from tanscope.db.stats_repository import StatsRepository
from tanscope.services.image_search.base import ImageResult
from tanscope.services.image_search.service import ImageSearchService

router = Router()


@router.inline_query()
async def handle_inline(query: InlineQuery, service: FromDishka[ImageSearchService]) -> None:
    text = query.query.strip()
    if len(text) < INLINE_QUERY_MIN_LENGTH:
        await query.answer([], cache_time=INLINE_CACHE_TIME_SECONDS)
        return
    results = await service.search(text, INLINE_RESULTS_LIMIT)
    photos = [_to_photo(index, item) for index, item in enumerate(results)]
    await query.answer(photos, cache_time=INLINE_CACHE_TIME_SECONDS)


@router.chosen_inline_result()
async def handle_chosen(chosen: ChosenInlineResult, stats: FromDishka[StatsRepository]) -> None:
    await stats.record(
        user_id=chosen.from_user.id,
        kind=EventKind.IMAGE_SEARCH,
        target=chosen.query,
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
