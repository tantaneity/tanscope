import asyncio
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from tanscope.services.download import instagram_source
from tanscope.services.download.base import Platform
from tanscope.services.download.errors import NoMediaError
from tanscope.services.download.instagram_source import InstagramGraphqlSource

POST_URL = "https://www.instagram.com/p/Ddi9EVlPEPE/"


async def _download_against_login_page(dest: Path) -> None:
    async def login_page(request: web.Request) -> web.Response:
        return web.Response(text="<html>login</html>", content_type="text/html")

    app = web.Application()
    app.router.add_post("/graphql/query", login_page)
    async with TestServer(app) as server:
        instagram_source.INSTAGRAM_GRAPHQL_URL = str(server.make_url("/graphql/query"))
        await InstagramGraphqlSource().download(POST_URL, Platform.INSTAGRAM, dest)


def test_should_raise_no_media_when_graphql_answers_with_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(instagram_source, "INSTAGRAM_GRAPHQL_URL", "")
    with pytest.raises(NoMediaError):
        asyncio.run(_download_against_login_page(tmp_path))
