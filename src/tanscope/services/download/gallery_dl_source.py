import asyncio
import sys
from pathlib import Path

from tanscope.core.constants import DOWNLOAD_TIMEOUT_SECONDS
from tanscope.services.download.base import DownloadResult, DownloadSource, Platform
from tanscope.services.download.cookies import writable_cookies
from tanscope.services.download.errors import NoMediaError
from tanscope.services.download.media_files import collect_media


class GalleryDlSource(DownloadSource):
    def __init__(self, cookies_file: Path | None = None) -> None:
        self._cookies_file = cookies_file

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        with writable_cookies(self._cookies_file) as cookies:
            await self._run(url, dest, cookies)
        items = collect_media(dest)
        if not items:
            raise NoMediaError(url)
        return DownloadResult(
            platform=platform,
            title=platform.value,
            source_url=url,
            work_dir=dest,
            items=items,
        )

    async def _run(self, url: str, dest: Path, cookies: Path | None) -> None:
        args = [sys.executable, "-m", "gallery_dl", "-q", "-D", str(dest)]
        if cookies is not None:
            args += ["--cookies", str(cookies)]
        args.append(url)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(process.communicate(), timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise NoMediaError(url) from error
