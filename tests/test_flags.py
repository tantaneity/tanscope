from tanscope.services.delivery import strip_no_caption
from tanscope.services.download.base import Platform
from tanscope.services.download.resolver import PlatformResolver

LINK = "https://www.tiktok.com/@user/photo/123"


def test_flag_is_stripped_and_link_still_resolves() -> None:
    for query in (f"{LINK} -nc", f"-nc {LINK}", f"{LINK} --no-caption"):
        text, wants_caption = strip_no_caption(query)
        assert wants_caption is False, query
        assert PlatformResolver().find(text) == (Platform.TIKTOK, LINK), query


def test_plain_query_keeps_caption() -> None:
    text, wants_caption = strip_no_caption(f"  {LINK}  ")
    assert wants_caption is True
    assert text == LINK
    assert strip_no_caption("cute cats") == ("cute cats", True)


if __name__ == "__main__":
    test_flag_is_stripped_and_link_still_resolves()
    test_plain_query_keeps_caption()
    print("ok")
