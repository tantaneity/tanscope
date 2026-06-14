import asyncio
import sys
from pathlib import Path

from tanscope.core.constants import DOWNLOAD_TIMEOUT_SECONDS
from tanscope.services.download.base import MediaItem, Platform
from tanscope.services.download.cookies import writable_cookies
from tanscope.services.download.media_files import collect_media
from tanscope.services.watch.feeds import feed_url


class ProfileWatcher:
    def __init__(self, archive_path: Path, cookies_file: Path | None, fetch_limit: int) -> None:
        self._archive_path = archive_path
        self._cookies_file = cookies_file
        self._fetch_limit = fetch_limit

    async def prime(self, platform: Platform, username: str) -> None:
        await self._run(platform, username, dest=None)

    async def fetch_new(self, platform: Platform, username: str, dest: Path) -> list[MediaItem]:
        await self._run(platform, username, dest=dest)
        return collect_media(dest)

    async def _run(self, platform: Platform, username: str, dest: Path | None) -> None:
        self._archive_path.parent.mkdir(parents=True, exist_ok=True)
        with writable_cookies(self._cookies_file) as cookies:
            args = [
                sys.executable,
                "-m",
                "gallery_dl",
                "-q",
                "--download-archive",
                str(self._archive_path),
                "--range",
                f"1-{self._fetch_limit}",
            ]
            if dest is None:
                args.append("--no-download")
            else:
                args += ["-D", str(dest)]
            if cookies is not None:
                args += ["--cookies", str(cookies)]
            args.append(feed_url(platform, username))
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(process.communicate(), timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except TimeoutError:
                process.kill()
                await process.wait()
