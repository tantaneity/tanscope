import logging
import shutil
from pathlib import Path

from tanscope.services.download.base import DownloadResult, DownloadSource, Platform
from tanscope.services.download.errors import NoMediaError

logger = logging.getLogger(__name__)


class CompositeDownloadSource(DownloadSource):
    def __init__(self, primary: DownloadSource, fallback: DownloadSource) -> None:
        self._primary = primary
        self._fallback = fallback

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        try:
            return await self._primary.download(url, platform, dest)
        except NoMediaError:
            logger.info("primary source produced no media, falling back for %s", url)
            self._empty(dest)
            return await self._fallback.download(url, platform, dest)

    @staticmethod
    def _empty(dest: Path) -> None:
        for path in dest.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path, ignore_errors=True)
