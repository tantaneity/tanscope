# tanscope

Telegram bot that does two things well. Search images inline (not Yandex, so Ukrainians can actually use it), and pull media down from TikTok, Instagram, Pinterest and X (Twitter) by link.

Think of it as @pic without the Yandex baggage, plus a downloader bolted on.

## What it does

Type `@your_bot cats` in any chat and pick from a grid of photos. The search runs on DuckDuckGo, no API key, nothing logged to a search giant.

Drop a TikTok, Instagram, Pinterest or X link into the bot and it sends back the video or photos. Carousels come through as an album. Second time someone shares the same link, it ships from Telegram's own cache instantly (no re-download).

Links work inline too. Type `@your_bot <link>` in any chat, pick the single result, and the media lands in the chat. One step, no need to DM the bot first.

Telegram won't let a bot upload a file straight into an inline answer, so what actually gets sent is a dark placeholder frame captioned "Downloading…". The download starts the moment you type, and once the file is up the bot swaps the media inside that same message. Usually a couple of seconds. Already-seen links skip all of it and come straight from the 30-day `file_id` cache. Carousels are the one compromise: an inline message holds one photo or video, so you get the first item and a hint to send the link to the bot directly for the whole album.

The swap needs a chat to upload through: `MEDIA_CHAT_ID`, or your lowest admin id if you leave it empty. Turn on `/setinlinefeedback` in BotFather, otherwise Telegram never tells the bot which result got picked and the placeholder just sits there.

Don't want the source link glued under the media? Add `-nc` (or `--no-caption`) anywhere in the message or the inline query:

```
https://www.tiktok.com/@user/video/123 -nc
@your_bot https://pin.it/abc --no-caption
```

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
ADMIN_IDS=...          comma-separated Telegram ids for admin commands
MEDIA_CHAT_ID=...      chat the bot uploads to when caching inline links (defaults to lowest admin id)
COOKIES_FILE=...       optional yt-dlp cookies.txt, needed for Instagram
WATCH_INTERVAL_SECONDS=...  how often to poll tracked accounts (default 1800)
WATCH_FETCH_LIMIT=...       newest N posts checked per poll (default 15)
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

## Deploy

The box that runs this sits at home behind NAT, so nothing pushes into it from outside. A GitHub self-hosted runner lives on that machine and pulls on every push to `main`.

One-time setup on the host, in Settings → Actions → Runners → New self-hosted runner (copy the token from there):

```
mkdir ~/actions-runner && cd ~/actions-runner
curl -o r.tar.gz -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64.tar.gz
tar xzf r.tar.gz
./config.sh --url https://github.com/tantaneity/tanscope --token <TOKEN> --labels tanscope
sudo ./svc.sh install && sudo ./svc.sh start
```

Then point the workflow at the existing clone (Settings → Actions → Variables):

```
DEPLOY_DIR=/home/you/tanscope
```

That's deliberate. Deploys land in the clone you already set up, so `.env`, `cookies/cookies.txt` and the SQLite volume stay where they are (all three are gitignored, and a hard reset leaves untracked files alone). Local edits to tracked files on that box do get thrown away, the runner treats `origin/main` as truth.

Push to `main`, the runner rebuilds and restarts. Manual run works too, `workflow_dispatch` is on.

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

## Watching accounts

Admins can follow specific people on a platform and get new posts in DM. Handy if you run a channel and want first dibs on what someone posts.

```
/track tiktok someuser
/track instagram someuser
/untrack instagram someuser
/tracked
```

New posts land in your DM, so you decide what actually goes to the channel. Nothing auto-posts.

Under the hood it polls each account on an interval (default 30 min) and leans on gallery-dl's download archive to tell what's new, so you never get the same post twice. The first poll after `/track` just records a baseline, no backfill flood. Same `ADMIN_IDS` gate, same cookies: Instagram and X need them, TikTok and Pinterest mostly don't.

These commands are admin-only and invisible to regular users, same as `/stats`.

## Limits

Bot uploads top out at 50 MB (Telegram's rule for bots), so oversized videos get skipped rather than sent half-broken.

Instagram is the awkward one. It gates media behind a login now, so anonymous fetches come back with zero items even for public posts. Feed the bot a cookies file and it works (same file helps with rate-limited TikTok too).

Export your cookies with a browser extension like "Get cookies.txt LOCALLY", save it as `cookies/cookies.txt`, and that's it. Compose mounts the `cookies/` folder read-only and points `COOKIES_FILE` at it. No cookies, no Instagram, everything else still runs.

X (Twitter) is the same deal. It gates guest access now, so anonymous fetches fail. Add your `x.com` cookies to the same `cookies.txt` and it works.

Keep that file private. It's your session. `cookies/*.txt` is gitignored.

DuckDuckGo can rate-limit if you really lean on it. For most chats it's fine.

## Notes

Architecture mirrors tantunes: same dishka DI, same yt-dlp + Redis file_id pattern, same SQLite-on-a-volume approach. If you know one, you know this.
