# tanscope

Telegram bot that does two things well. Search images inline (not Yandex, so Ukrainians can actually use it), and pull media down from TikTok, Instagram, Pinterest and X (Twitter) by link.

Think of it as @pic without the Yandex baggage, plus a downloader bolted on.

## What it does

Type `@your_bot cats` in any chat and pick from a grid of photos. The search runs on DuckDuckGo, no API key, nothing logged to a search giant.

Drop a TikTok, Instagram, Pinterest or X link into the bot and it sends back the video or photos. Carousels come through as an album. Second time someone shares the same link, it ships from Telegram's own cache instantly (no re-download).

## Stack

```
Bot          aiogram 3 · dishka DI
Image search DuckDuckGo (ddgs, no key)
Download     yt-dlp (video) · gallery-dl (images) · ffmpeg
Cache        Redis
DB           SQLite · SQLAlchemy async
Config       pydantic-settings
Deploy       Docker · Docker Compose
```

## Setup

Grab a token from [@BotFather](https://t.me/BotFather), then two more switches there, both easy to forget:

```
/setinline          enable inline mode, set a placeholder
/setinlinefeedback  enable it, otherwise download stats for picked images stay empty
```

Copy the env template and fill it in:

```
cp .env.example .env
```

```
BOT_TOKEN=...          your token
REDIS_URL=...          redis://localhost:6379/0 by default
SQLITE_PATH=...        data/tanscope.sqlite3 by default
ADMIN_IDS=...          comma-separated Telegram ids that can run /stats
COOKIES_FILE=...       optional yt-dlp cookies.txt, needed for Instagram
```

Missing or empty `BOT_TOKEN` and the bot refuses to start. Fails loud at boot, not somewhere deep in a handler.

## Run

Docker is the happy path. Brings up the bot and Redis together, SQLite lives on a named volume so stats survive restarts.

```
docker compose up -d --build
```

Logs:

```
docker compose logs -f bot
```

## Local dev

Need Python 3.12+ and a Redis running somewhere.

```
uv venv --python 3.12
uv pip install -e .
python -m tanscope
```

## How it works

Image search caches each query in Redis for 15 minutes, so repeated searches don't hammer DuckDuckGo. Results come back as native inline photos.

Downloads use two engines behind one interface. yt-dlp goes first, great for video (TikTok, reels). When a link has no video (Instagram photos, Pinterest pins), it falls back to gallery-dl, which actually grabs images and carousels. Files land in a temp dir, get sent, then cleaned up. The interesting bit is the file_id cache: once a link's media is uploaded, Telegram hands back a `file_id`, and that's stored against the link for 30 days. Same link again means an instant resend, zero bandwidth, zero disk.

Concurrent downloads are capped (a semaphore) so a flood of links can't exhaust the box.

Stats land in SQLite: searches, downloads, cache hits, unique users, top platforms. Admins pull them with `/stats` (anyone in `ADMIN_IDS`). For everyone else the command stays invisible, no reply, not advertised.

## Limits

Bot uploads top out at 50 MB (Telegram's rule for bots), so oversized videos get skipped rather than sent half-broken.

Instagram is the awkward one. It gates media behind a login now, so anonymous fetches come back with zero items even for public posts. Feed the bot a cookies file and it works (same file helps with rate-limited TikTok too).

Export your cookies with a browser extension like "Get cookies.txt LOCALLY", save it as `cookies/cookies.txt`, and that's it. Compose mounts the `cookies/` folder read-only and points `COOKIES_FILE` at it. No cookies, no Instagram, everything else still runs.

X (Twitter) is the same deal. It gates guest access now, so anonymous fetches fail. Add your `x.com` cookies to the same `cookies.txt` and it works.

Keep that file private. It's your session. `cookies/*.txt` is gitignored.

DuckDuckGo can rate-limit if you really lean on it. For most chats it's fine.

## Notes

Architecture mirrors tantunes: same dishka DI, same yt-dlp + Redis file_id pattern, same SQLite-on-a-volume approach. If you know one, you know this.
