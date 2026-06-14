from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from tanscope.core.config import Config
from tanscope.db.stats_repository import StatsRepository, StatsSummary

router = Router()

START_TEXT = (
    "🔍 Type my @username + a query in any chat to search images.\n"
    "📥 Send a TikTok, Instagram, Pinterest or X link to download."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("stats"))
async def handle_stats(
    message: Message,
    stats: FromDishka[StatsRepository],
    config: FromDishka[Config],
) -> None:
    user = message.from_user
    if user is None or user.id not in config.admin_ids:
        return
    summary = await stats.summary()
    await message.answer(_render(summary))


def _render(summary: StatsSummary) -> str:
    lines = [
        "<b>Stats</b>",
        f"Events: {summary.total_events}",
        f"Image searches: {summary.image_searches}",
        f"Downloads: {summary.downloads}",
        f"Cache hits: {summary.cached_hits}",
        f"Unique users: {summary.unique_users}",
    ]
    if summary.top_platforms:
        lines.append("")
        lines.extend(f"{platform}: {count}" for platform, count in summary.top_platforms)
    return "\n".join(lines)
