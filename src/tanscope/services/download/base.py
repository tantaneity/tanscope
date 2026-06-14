from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Platform(StrEnum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    TWITTER = "twitter"


class MediaKind(StrEnum):
    VIDEO = "video"
    PHOTO = "photo"


@dataclass(frozen=True, slots=True)
class MediaItem:
    kind: MediaKind
    path: Path


@dataclass(frozen=True, slots=True)
class DownloadResult:
    platform: Platform
    title: str
    source_url: str
    work_dir: Path
    items: list[MediaItem]


@dataclass(frozen=True, slots=True)
class CachedMedia:
    kind: MediaKind
    file_id: str


class DownloadSource(ABC):
    @abstractmethod
    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult: ...
