from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from tanscope.core.config import Config
from tanscope.handlers.permissions import is_admin
from tanscope.services.download.base import Platform
from tanscope.services.watch.service import WatchService

router = Router()

USAGE_TEXT = "Usage: /track <tiktok|instagram|pinterest|twitter> <username>"


@router.message(Command("track"))
async def handle_track(
    message: Message,
    command: CommandObject,
    service: FromDishka[WatchService],
    config: FromDishka[Config],
) -> None:
    if not is_admin(message.from_user, config) or message.from_user is None:
        return
    parsed = _parse(command.args)
    if parsed is None:
        await message.answer(USAGE_TEXT)
        return
    platform, username = parsed
    added = await service.track(message.from_user.id, platform, username)
    if added:
        await message.answer(f"✅ Tracking {platform.value} @{username}")
    else:
        await message.answer(f"Already tracking {platform.value} @{username}")


@router.message(Command("untrack"))
async def handle_untrack(
    message: Message,
    command: CommandObject,
    service: FromDishka[WatchService],
    config: FromDishka[Config],
) -> None:
    if not is_admin(message.from_user, config) or message.from_user is None:
        return
    parsed = _parse(command.args)
    if parsed is None:
        await message.answer(USAGE_TEXT.replace("/track", "/untrack"))
        return
    platform, username = parsed
    removed = await service.untrack(message.from_user.id, platform, username)
    await message.answer(
        f"🗑 Untracked {platform.value} @{username}" if removed else "Not tracked"
    )


@router.message(Command("tracked"))
async def handle_tracked(
    message: Message,
    service: FromDishka[WatchService],
    config: FromDishka[Config],
) -> None:
    if not is_admin(message.from_user, config) or message.from_user is None:
        return
    accounts = await service.list_for(message.from_user.id)
    if not accounts:
        await message.answer("No tracked accounts.")
        return
    lines = ["<b>Tracked</b>"]
    lines.extend(f"• {account.platform} @{account.username}" for account in accounts)
    await message.answer("\n".join(lines))


def _parse(args: str | None) -> tuple[Platform, str] | None:
    if not args:
        return None
    parts = args.split()
    if len(parts) != 2:
        return None
    raw_platform, username = parts
    try:
        platform = Platform(raw_platform.lower())
    except ValueError:
        return None
    return platform, username.lstrip("@")
