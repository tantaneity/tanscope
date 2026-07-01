from asyncio import Semaphore
from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import Provider, Scope, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from tanscope.cache.redis_cache import Cache
from tanscope.core.config import Config
from tanscope.core.constants import MAX_CONCURRENT_DOWNLOADS
from tanscope.db.engine import build_engine, build_session_factory
from tanscope.db.stats_repository import StatsRepository
from tanscope.db.tracked_repository import TrackedRepository
from tanscope.services.delivery import MediaDelivery
from tanscope.services.download.base import DownloadSource
from tanscope.services.download.composite import CompositeDownloadSource
from tanscope.services.download.gallery_dl_source import GalleryDlSource
from tanscope.services.download.instagram_source import InstagramGraphqlSource
from tanscope.services.download.resolver import PlatformResolver
from tanscope.services.download.service import DownloadService
from tanscope.services.download.ytdlp_source import YtDlpSource
from tanscope.services.image_search.base import ImageSearchProvider
from tanscope.services.image_search.duckduckgo import DuckDuckGoImageSearch
from tanscope.services.image_search.service import ImageSearchService
from tanscope.services.watch.poller import ProfileWatcher
from tanscope.services.watch.scheduler import WatchScheduler
from tanscope.services.watch.service import WatchService


class AppProvider(Provider):
    scope = Scope.APP

    @provide
    def config(self) -> Config:
        return Config()

    @provide
    async def redis(self, config: Config) -> AsyncIterator[Redis]:
        client: Redis = Redis.from_url(config.redis_url, decode_responses=True)
        yield client
        await client.aclose()

    @provide
    def cache(self, redis: Redis) -> Cache:
        return Cache(redis)

    @provide
    async def engine(self, config: Config) -> AsyncIterator[AsyncEngine]:
        engine = build_engine(config)
        yield engine
        await engine.dispose()

    @provide
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker:
        return build_session_factory(engine)

    @provide
    def stats_repository(self, session_factory: async_sessionmaker) -> StatsRepository:
        return StatsRepository(session_factory)

    @provide
    def tracked_repository(self, session_factory: async_sessionmaker) -> TrackedRepository:
        return TrackedRepository(session_factory)

    @provide
    def image_provider(self) -> ImageSearchProvider:
        return DuckDuckGoImageSearch()

    @provide
    def image_search_service(
        self, provider: ImageSearchProvider, cache: Cache
    ) -> ImageSearchService:
        return ImageSearchService(provider, cache)

    @provide
    def resolver(self) -> PlatformResolver:
        return PlatformResolver()

    @provide
    def download_source(self, config: Config) -> DownloadSource:
        return CompositeDownloadSource(
            primary=InstagramGraphqlSource(config.cookies_file),
            fallback=CompositeDownloadSource(
                primary=YtDlpSource(config.cookies_file),
                fallback=GalleryDlSource(config.cookies_file),
            ),
        )

    @provide
    def download_semaphore(self) -> Semaphore:
        return Semaphore(MAX_CONCURRENT_DOWNLOADS)

    @provide
    def download_service(
        self,
        source: DownloadSource,
        resolver: PlatformResolver,
        cache: Cache,
        semaphore: Semaphore,
        config: Config,
    ) -> DownloadService:
        return DownloadService(source, resolver, cache, semaphore, config.downloads_dir)

    @provide
    async def bot(self, config: Config) -> AsyncIterator[Bot]:
        instance = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        yield instance
        await instance.session.close()

    @provide
    def media_delivery(self, bot: Bot) -> MediaDelivery:
        return MediaDelivery(bot)

    @provide
    def profile_watcher(self, config: Config) -> ProfileWatcher:
        return ProfileWatcher(
            archive_path=config.watch_archive_path,
            cookies_file=config.cookies_file,
            fetch_limit=config.watch_fetch_limit,
        )

    @provide
    def watch_service(
        self, repo: TrackedRepository, watcher: ProfileWatcher, config: Config
    ) -> WatchService:
        return WatchService(repo, watcher, config.downloads_dir)

    @provide
    def watch_scheduler(
        self, service: WatchService, delivery: MediaDelivery, config: Config
    ) -> WatchScheduler:
        return WatchScheduler(service, delivery, config.watch_interval_seconds)
