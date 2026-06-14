from pathlib import Path

from tanscope.core.constants import IMAGE_EXTENSIONS, MAX_DOWNLOAD_BYTES, VIDEO_EXTENSIONS
from tanscope.services.download.base import MediaItem, MediaKind


def collect_media(dest: Path) -> list[MediaItem]:
    items: list[MediaItem] = []
    for path in sorted(dest.rglob("*")):
        if not path.is_file():
            continue
        kind = _kind(path)
        if kind is None:
            continue
        if path.stat().st_size > MAX_DOWNLOAD_BYTES:
            continue
        items.append(MediaItem(kind=kind, path=path))
    return items


def _kind(path: Path) -> MediaKind | None:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return MediaKind.VIDEO
    if suffix in IMAGE_EXTENSIONS:
        return MediaKind.PHOTO
    return None
