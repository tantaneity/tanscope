from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from tanscope.db.models import TrackedAccount


class TrackedRepository:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def add(self, chat_id: int, platform: str, username: str) -> bool:
        async with self._session_factory() as session:
            session.add(TrackedAccount(chat_id=chat_id, platform=platform, username=username))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
        return True

    async def remove(self, chat_id: int, platform: str, username: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(TrackedAccount).where(
                    TrackedAccount.chat_id == chat_id,
                    TrackedAccount.platform == platform,
                    TrackedAccount.username == username,
                )
            )
            await session.commit()
        return result.rowcount > 0

    async def list_for(self, chat_id: int) -> list[TrackedAccount]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TrackedAccount)
                .where(TrackedAccount.chat_id == chat_id)
                .order_by(TrackedAccount.platform, TrackedAccount.username)
            )
            return list(result.scalars().all())

    async def list_enabled(self) -> list[TrackedAccount]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TrackedAccount).where(TrackedAccount.enabled.is_(True))
            )
            return list(result.scalars().all())

    async def mark_primed(self, account_id: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(TrackedAccount).where(TrackedAccount.id == account_id).values(primed=True)
            )
            await session.commit()
