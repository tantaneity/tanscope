import asyncio
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from tanscope.core.constants import (
    CAPTION_MAX_LENGTH,
    MAX_DOWNLOAD_BYTES,
    YTDLP_CONCURRENT_FRAGMENTS,
    YTDLP_RETRIES,
    YTDLP_SOCKET_TIMEOUT_SECONDS,
)
from tanscope.services.download.base import DownloadResult, DownloadSource, Platform
from tanscope.services.download.cookies import writable_cookies
from tanscope.services.download.errors import NoMediaError
from tanscope.services.download.media_files import collect_media


class _SilentLogger:
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class YtDlpSource(DownloadSource):
    def __init__(self, cookies_file: Path | None = None) -> None:
        self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        self._cookies_file = cookies_file

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        info = await asyncio.to_thread(self._run, url, dest)
        items = collect_media(dest)
        if not items:
            raise NoMediaError(url)
        return DownloadResult(
            platform=platform,
            title=self._title(info, platform),
            source_url=url,
            work_dir=dest,
            items=items,
        )

    def _run(self, url: str, dest: Path) -> dict[str, Any]:
        with writable_cookies(self._cookies_file) as cookies:
            options: dict[str, Any] = {
                "outtmpl": str(dest / "%(autonumber)03d-%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "logger": _SilentLogger(),
                "noplaylist": False,
                "ignoreerrors": False,
                "ffmpeg_location": self._ffmpeg_path,
                "merge_output_format": "mp4",
                "format": f"best[filesize<{MAX_DOWNLOAD_BYTES}]/best",
                "retries": YTDLP_RETRIES,
                "socket_timeout": YTDLP_SOCKET_TIMEOUT_SECONDS,
                "concurrent_fragment_downloads": YTDLP_CONCURRENT_FRAGMENTS,
            }
            if cookies is not None:
                options["cookiefile"] = str(cookies)
            try:
                with YoutubeDL(options) as downloader:
                    return downloader.extract_info(url, download=True)
            except YtDlpDownloadError as error:
                raise NoMediaError(url) from error

    @staticmethod
    def _title(info: dict[str, Any], platform: Platform) -> str:
        title = str(info.get("title") or info.get("description") or "").strip()
        if not title:
            return platform.value
        return title[:CAPTION_MAX_LENGTH]
