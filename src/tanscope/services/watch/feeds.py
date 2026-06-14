from tanscope.services.download.base import Platform

_FEED_TEMPLATES: dict[Platform, str] = {
    Platform.TIKTOK: "https://www.tiktok.com/@{username}",
    Platform.INSTAGRAM: "https://www.instagram.com/{username}/",
    Platform.PINTEREST: "https://www.pinterest.com/{username}/_created/",
    Platform.TWITTER: "https://x.com/{username}/media",
}


def feed_url(platform: Platform, username: str) -> str:
    return _FEED_TEMPLATES[platform].format(username=username.lstrip("@"))
