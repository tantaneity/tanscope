from aiogram.types import User

from tanscope.core.config import Config


def is_admin(user: User | None, config: Config) -> bool:
    return user is not None and user.id in config.admin_ids
