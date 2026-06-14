import html

from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo, Message

from tanscope.core.constants import MEDIA_GROUP_MAX_ITEMS
from tanscope.services.download.base import CachedMedia, MediaItem, MediaKind
from tanscope.services.download.errors import DownloadError

MediaSource = FSInputFile | str
MediaPair = tuple[MediaKind, MediaSource]


class MediaDelivery:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_paths(
        self, chat_id: int, items: list[MediaItem], caption: str
    ) -> list[CachedMedia]:
        pairs: list[MediaPair] = [
            (item.kind, FSInputFile(item.path)) for item in items[:MEDIA_GROUP_MAX_ITEMS]
        ]
        sent = await self._deliver(chat_id, pairs, caption)
        return [
            CachedMedia(kind=kind, file_id=_file_id(message, kind))
            for (kind, _), message in zip(pairs, sent)
        ]

    async def send_cached(self, chat_id: int, cached: list[CachedMedia], caption: str) -> None:
        pairs: list[MediaPair] = [(item.kind, item.file_id) for item in cached[:MEDIA_GROUP_MAX_ITEMS]]
        await self._deliver(chat_id, pairs, caption)

    async def _deliver(self, chat_id: int, pairs: list[MediaPair], caption: str) -> list[Message]:
        if not pairs:
            return []
        if len(pairs) == 1:
            kind, source = pairs[0]
            return [await self._send_single(chat_id, kind, source, caption)]
        group: list[InputMediaPhoto | InputMediaVideo] = []
        for index, (kind, source) in enumerate(pairs):
            item_caption = caption if index == 0 else None
            media_class = InputMediaVideo if kind == MediaKind.VIDEO else InputMediaPhoto
            group.append(media_class(media=source, caption=item_caption))
        return await self._bot.send_media_group(chat_id, group)

    async def _send_single(
        self, chat_id: int, kind: MediaKind, source: MediaSource, caption: str
    ) -> Message:
        if kind == MediaKind.VIDEO:
            return await self._bot.send_video(chat_id, source, caption=caption)
        return await self._bot.send_photo(chat_id, source, caption=caption)


def _file_id(message: Message, kind: MediaKind) -> str:
    if kind == MediaKind.VIDEO and message.video:
        return message.video.file_id
    if kind == MediaKind.PHOTO and message.photo:
        return message.photo[-1].file_id
    raise DownloadError("no file_id in sent message")


def build_caption(title: str, url: str | None = None) -> str:
    safe_title = html.escape(title)
    if url is None:
        return safe_title
    return f'<a href="{html.escape(url, quote=True)}">{safe_title}</a>'
