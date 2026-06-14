import asyncio
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from yt_dlp import YoutubeDL

from tanscope.core.constants import (
    CAPTION_MAX_LENGTH,
    IMAGE_EXTENSIONS,
    MAX_DOWNLOAD_BYTES,
    VIDEO_EXTENSIONS,
    YTDLP_CONCURRENT_FRAGMENTS,
    YTDLP_RETRIES,
    YTDLP_SOCKET_TIMEOUT_SECONDS,
)
from tanscope.services.download.base import (
    DownloadResult,
    DownloadSource,
    MediaItem,
    MediaKind,
    Platform,
)
from tanscope.services.download.errors import NoMediaError


class YtDlpSource(DownloadSource):
    def __init__(self) -> None:
        self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        info = await asyncio.to_thread(self._run, url, dest)
        items = self._collect(dest)
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
        options = {
            "outtmpl": str(dest / "%(autonumber)03d-%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": False,
            "ignoreerrors": False,
            "ffmpeg_location": self._ffmpeg_path,
            "merge_output_format": "mp4",
            "format": f"best[filesize<{MAX_DOWNLOAD_BYTES}]/best",
            "retries": YTDLP_RETRIES,
            "socket_timeout": YTDLP_SOCKET_TIMEOUT_SECONDS,
            "concurrent_fragment_downloads": YTDLP_CONCURRENT_FRAGMENTS,
        }
        with YoutubeDL(options) as downloader:
            return downloader.extract_info(url, download=True)

    @staticmethod
    def _collect(dest: Path) -> list[MediaItem]:
        items: list[MediaItem] = []
        for path in sorted(dest.iterdir()):
            if not path.is_file():
                continue
            kind = YtDlpSource._kind(path)
            if kind is None:
                continue
            if path.stat().st_size > MAX_DOWNLOAD_BYTES:
                continue
            items.append(MediaItem(kind=kind, path=path))
        return items

    @staticmethod
    def _kind(path: Path) -> MediaKind | None:
        suffix = path.suffix.lower()
        if suffix in VIDEO_EXTENSIONS:
            return MediaKind.VIDEO
        if suffix in IMAGE_EXTENSIONS:
            return MediaKind.PHOTO
        return None

    @staticmethod
    def _title(info: dict[str, Any], platform: Platform) -> str:
        title = str(info.get("title") or info.get("description") or "").strip()
        if not title:
            return platform.value
        return title[:CAPTION_MAX_LENGTH]
