import logging

import aiohttp

from tanscope.core.constants import SHORT_LINK_RESOLVE_TIMEOUT_SECONDS, SHORT_LINK_USER_AGENT

logger = logging.getLogger(__name__)

SHORT_LINK_HOSTS = ("vt.tiktok.com", "vm.tiktok.com")


def is_short_link(url: str) -> bool:
    return any(host in url for host in SHORT_LINK_HOSTS)


async def expand_short_link(url: str) -> str:
    if not is_short_link(url):
        return url
    timeout = aiohttp.ClientTimeout(total=SHORT_LINK_RESOLVE_TIMEOUT_SECONDS)
    headers = {"User-Agent": SHORT_LINK_USER_AGENT}
    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.head(url, allow_redirects=True, headers=headers) as response,
        ):
            expanded = str(response.url)
    except (aiohttp.ClientError, TimeoutError) as error:
        logger.info("could not expand %s, using it as is: %s", url, error)
        return url
    return expanded.partition("?")[0]
