from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from tanscope.core.config import Config
from tanscope.db.models import Base


def build_engine(config: Config) -> AsyncEngine:
    config.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(config.database_url, echo=False)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
