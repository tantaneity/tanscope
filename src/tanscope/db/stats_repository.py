from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tanscope.core.constants import STATS_TOP_LIMIT
from tanscope.db.models import Event, EventKind


@dataclass(frozen=True, slots=True)
class StatsSummary:
    total_events: int
    image_searches: int
    downloads: int
    cached_hits: int
    unique_users: int
    top_platforms: list[tuple[str, int]]


class StatsRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        user_id: int,
        kind: EventKind,
        target: str,
        platform: str | None = None,
        cached: bool = False,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                Event(
                    user_id=user_id,
                    kind=kind.value,
                    target=target[:512],
                    platform=platform,
                    cached=cached,
                )
            )
            await session.commit()

    async def summary(self) -> StatsSummary:
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(Event)) or 0
            images = (
                await session.scalar(
                    select(func.count()).where(Event.kind == EventKind.IMAGE_SEARCH.value)
                )
                or 0
            )
            downloads = (
                await session.scalar(
                    select(func.count()).where(Event.kind == EventKind.DOWNLOAD.value)
                )
                or 0
            )
            cached_hits = (
                await session.scalar(select(func.count()).where(Event.cached.is_(True))) or 0
            )
            unique_users = (
                await session.scalar(select(func.count(func.distinct(Event.user_id)))) or 0
            )
            platform_rows = await session.execute(
                select(Event.platform, func.count())
                .where(Event.platform.is_not(None))
                .group_by(Event.platform)
                .order_by(func.count().desc())
                .limit(STATS_TOP_LIMIT)
            )
            top_platforms = [(row[0], row[1]) for row in platform_rows.all()]

        return StatsSummary(
            total_events=total,
            image_searches=images,
            downloads=downloads,
            cached_hits=cached_hits,
            unique_users=unique_users,
            top_platforms=top_platforms,
        )
