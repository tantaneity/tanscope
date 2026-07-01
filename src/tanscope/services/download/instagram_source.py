import http.cookiejar
import json
import re
from pathlib import Path
from typing import Any

import aiohttp

from tanscope.core.constants import (
    DOWNLOAD_TIMEOUT_SECONDS,
    INSTAGRAM_APP_ID,
    INSTAGRAM_GRAPHQL_URL,
    INSTAGRAM_POST_DOC_ID,
    INSTAGRAM_USER_AGENT,
    MAX_DOWNLOAD_BYTES,
)
from tanscope.services.download.base import DownloadResult, DownloadSource, MediaKind, Platform
from tanscope.services.download.errors import NoMediaError
from tanscope.services.download.media_files import collect_media

SHORTCODE_PATTERN = re.compile(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")


class InstagramGraphqlSource(DownloadSource):
    def __init__(self, cookies_file: Path | None = None) -> None:
        self._cookies_file = cookies_file

    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        if platform is not Platform.INSTAGRAM:
            raise NoMediaError(url)
        match = SHORTCODE_PATTERN.search(url)
        if match is None:
            raise NoMediaError(url)
        shortcode = match.group(1)
        cookies = self._load_cookies()
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            node = await self._fetch_node(session, shortcode, cookies)
            media = extract_media_urls(node)
            if not media:
                raise NoMediaError(f"instagram graphql returned no media for {shortcode}")
            await self._download_all(session, media, dest)
        items = collect_media(dest)
        if not items:
            raise NoMediaError(url)
        return DownloadResult(
            platform=platform,
            title=_owner(node),
            source_url=url,
            work_dir=dest,
            items=items,
        )

    async def _fetch_node(
        self, session: aiohttp.ClientSession, shortcode: str, cookies: dict[str, str]
    ) -> dict[str, Any]:
        headers = {
            "User-Agent": INSTAGRAM_USER_AGENT,
            "X-IG-App-ID": INSTAGRAM_APP_ID,
            "X-CSRFToken": cookies.get("csrftoken", ""),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/p/{shortcode}/",
            "Origin": "https://www.instagram.com",
        }
        if cookies:
            headers["Cookie"] = "; ".join(f"{name}={value}" for name, value in cookies.items())
        payload = {
            "doc_id": INSTAGRAM_POST_DOC_ID,
            "variables": json.dumps({"shortcode": shortcode}),
        }
        async with session.post(INSTAGRAM_GRAPHQL_URL, data=payload, headers=headers) as response:
            if response.status != 200:
                raise NoMediaError(f"instagram graphql status {response.status} for {shortcode}")
            body = await response.json()
        node: dict[str, Any] | None = (body.get("data") or {}).get("xdt_shortcode_media")
        if not node:
            raise NoMediaError(f"instagram post unavailable: {shortcode}")
        return node

    async def _download_all(
        self, session: aiohttp.ClientSession, media: list["Media"], dest: Path
    ) -> None:
        headers = {"User-Agent": INSTAGRAM_USER_AGENT}
        for index, item in enumerate(media):
            suffix = ".mp4" if item.kind is MediaKind.VIDEO else ".jpg"
            target = dest / f"{index:03d}{suffix}"
            async with session.get(item.url, headers=headers) as response:
                if response.status != 200:
                    continue
                written = 0
                with target.open("wb") as file:
                    async for chunk in response.content.iter_chunked(1 << 16):
                        written += len(chunk)
                        if written > MAX_DOWNLOAD_BYTES:
                            file.close()
                            target.unlink(missing_ok=True)
                            break
                        file.write(chunk)

    def _load_cookies(self) -> dict[str, str]:
        if self._cookies_file is None or not self._cookies_file.exists():
            return {}
        jar = http.cookiejar.MozillaCookieJar(str(self._cookies_file))
        jar.load(ignore_discard=True, ignore_expires=True)
        return {
            cookie.name: cookie.value or ""
            for cookie in jar
            if "instagram.com" in cookie.domain
        }


class Media:
    __slots__ = ("kind", "url")

    def __init__(self, kind: MediaKind, url: str) -> None:
        self.kind = kind
        self.url = url


def extract_media_urls(node: dict[str, Any]) -> list[Media]:
    children = (node.get("edge_sidecar_to_children") or {}).get("edges")
    nodes = [edge["node"] for edge in children] if children else [node]
    return [media for media in map(_media, nodes) if media is not None]


def _media(node: dict[str, Any]) -> Media | None:
    if node.get("is_video"):
        url = node.get("video_url")
        if url:
            return Media(MediaKind.VIDEO, url)
    url = node.get("display_url")
    if url:
        return Media(MediaKind.PHOTO, url)
    return None


def _owner(node: dict[str, Any]) -> str:
    owner = (node.get("owner") or {}).get("username")
    return owner or Platform.INSTAGRAM.value


def _demo() -> None:
    carousel = {
        "edge_sidecar_to_children": {
            "edges": [
                {"node": {"is_video": False, "display_url": "https://cdn/a.jpg"}},
                {"node": {"is_video": True, "video_url": "https://cdn/b.mp4",
                          "display_url": "https://cdn/b.jpg"}},
            ]
        }
    }
    items = extract_media_urls(carousel)
    assert [m.kind for m in items] == [MediaKind.PHOTO, MediaKind.VIDEO], items
    assert items[1].url == "https://cdn/b.mp4"

    video = {"is_video": True, "video_url": "https://cdn/v.mp4", "display_url": "https://cdn/v.jpg"}
    assert extract_media_urls(video)[0].url == "https://cdn/v.mp4"

    image = {"is_video": False, "display_url": "https://cdn/i.jpg"}
    assert extract_media_urls(image)[0].kind is MediaKind.PHOTO

    assert extract_media_urls({"is_video": True}) == []
    print("ok")


if __name__ == "__main__":
    _demo()
