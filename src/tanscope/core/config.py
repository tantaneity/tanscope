from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from tanscope.core.constants import WATCH_FETCH_LIMIT, WATCH_INTERVAL_SECONDS


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(min_length=1)
    redis_url: str = "redis://localhost:6379/0"
    sqlite_path: Path = Path("data/tanscope.sqlite3")
    downloads_dir: Path = Path("downloads")
    admin_ids: Annotated[frozenset[int], NoDecode] = frozenset()
    cookies_file: Path | None = None
    watch_archive_path: Path = Path("data/watch-archive.sqlite")
    watch_interval_seconds: int = WATCH_INTERVAL_SECONDS
    watch_fetch_limit: int = WATCH_FETCH_LIMIT

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: Any) -> Any:
        if isinstance(value, str):
            return frozenset(int(part) for part in value.split(",") if part.strip())
        return value

    @field_validator("cookies_file", mode="before")
    @classmethod
    def _empty_cookies_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"
