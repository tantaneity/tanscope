import logging

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka
from sqlalchemy.ext.asyncio import AsyncEngine

from tanscope.core.container import AppProvider
from tanscope.db.engine import init_db
from tanscope.handlers import commands, download, inline


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    container = make_async_container(AppProvider())

    engine = await container.get(AsyncEngine)
    await init_db(engine)

    bot = await container.get(Bot)
    dispatcher = Dispatcher()
    dispatcher.include_routers(commands.router, inline.router, download.router)
    setup_dishka(container=container, router=dispatcher, auto_inject=True)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(
            bot, allowed_updates=dispatcher.resolve_used_update_types()
        )
    finally:
        await container.close()
