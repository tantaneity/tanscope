import re

from tanscope.services.download.base import Platform

_URL_PATTERN = re.compile(r"https?://\S+")

_PLATFORM_PATTERNS: dict[Platform, re.Pattern[str]] = {
    Platform.TIKTOK: re.compile(r"https?://(?:[\w-]+\.)?tiktok\.com/", re.IGNORECASE),
    Platform.INSTAGRAM: re.compile(r"https?://(?:[\w-]+\.)?instagram\.com/", re.IGNORECASE),
    Platform.PINTEREST: re.compile(
        r"https?://(?:[\w-]+\.)?(?:pinterest\.[\w.]+|pin\.it)/", re.IGNORECASE
    ),
    Platform.TWITTER: re.compile(
        r"https?://(?:[\w-]+\.)?(?:twitter\.com|x\.com)/", re.IGNORECASE
    ),
}

_URL_TRAILING_CHARS = ").,>'\""


class PlatformResolver:
    def find(self, text: str) -> tuple[Platform, str] | None:
        for raw_url in _URL_PATTERN.findall(text):
            url = raw_url.rstrip(_URL_TRAILING_CHARS)
            platform = self._match(url)
            if platform is not None:
                return platform, url
        return None

    @staticmethod
    def _match(url: str) -> Platform | None:
        for platform, pattern in _PLATFORM_PATTERNS.items():
            if pattern.search(url):
                return platform
        return None
