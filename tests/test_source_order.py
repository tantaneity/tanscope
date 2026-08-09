from pathlib import Path

from tanscope.services.download.base import DownloadResult, DownloadSource, Platform
from tanscope.services.download.composite import CompositeDownloadSource
from tanscope.services.download.short_links import expand_short_link, is_short_link


class StubSource(DownloadSource):
    async def download(self, url: str, platform: Platform, dest: Path) -> DownloadResult:
        raise NotImplementedError


def test_photo_posts_skip_the_video_only_source() -> None:
    video_source, image_source = StubSource(), StubSource()
    composite = CompositeDownloadSource(video_source, image_source)

    first, second = composite.order_for("https://www.tiktok.com/@user/photo/123")
    assert (first, second) == (image_source, video_source)

    first, second = composite.order_for("https://www.tiktok.com/@user/video/123")
    assert (first, second) == (video_source, image_source)


def test_only_known_short_hosts_are_expanded() -> None:
    assert is_short_link("https://vt.tiktok.com/ZS4GYQKog/")
    assert is_short_link("https://vm.tiktok.com/ZS4GYQKog/")
    assert not is_short_link("https://www.tiktok.com/@user/photo/123")


def test_expanding_a_long_link_makes_no_request() -> None:
    import asyncio

    url = "https://www.tiktok.com/@user/photo/123"
    assert asyncio.run(expand_short_link(url)) == url


if __name__ == "__main__":
    test_photo_posts_skip_the_video_only_source()
    test_only_known_short_hosts_are_expanded()
    test_expanding_a_long_link_makes_no_request()
    print("ok")
