from pathlib import Path

from tanscope.services.download.gallery_dl_source import GalleryDlSource

URL = "https://vt.tiktok.com/ZS4GYQKog/"


def test_browser_profile_is_set_and_user_agent_is_not_overridden() -> None:
    args = GalleryDlSource().build_args(URL, Path("/tmp/dest"), None)
    assert "browser=firefox" in args
    assert not any(arg.startswith("user-agent=") for arg in args)
    assert args[-1] == URL


def test_cookies_are_passed_when_present() -> None:
    args = GalleryDlSource().build_args(URL, Path("/tmp/dest"), Path("/tmp/cookies.txt"))
    assert "--cookies" in args
    assert args[args.index("--cookies") + 1] == "/tmp/cookies.txt"


if __name__ == "__main__":
    test_browser_profile_is_set_and_user_agent_is_not_overridden()
    test_cookies_are_passed_when_present()
    print("ok")
