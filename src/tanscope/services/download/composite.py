import logging
import shutil
from pathlib import Path

from tanscope.services.download.base import DownloadResult, DownloadSource, Platform
from tanscope.services.download.errors import NoMediaError
from tanscope.services.download.short_links import expand_short_link

logger = logging.getLogger(__name__)

PHOTO_POST_MARKER = "/photo/"


class CompositeDownloadSource(DownloadSource):
    def __init__(self, primary: DownloadSource, fallback: DownloadSource) -> None:
        self._primary = primary
        self._fallback = fallback

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        target = await expand_short_link(url)
        first, second = self.order_for(target)
        try:
            return await first.download(target, platform, dest)
        except NoMediaError as error:
            logger.info("first source failed for %s, trying the other: %s", target, error)
            self._empty(dest)
            return await second.download(target, platform, dest)

    def order_for(self, url: str) -> tuple[DownloadSource, DownloadSource]:
        if PHOTO_POST_MARKER in url:
            return self._fallback, self._primary
        return self._primary, self._fallback

    @staticmethod
    def _empty(dest: Path) -> None:
        for path in dest.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path, ignore_errors=True)
