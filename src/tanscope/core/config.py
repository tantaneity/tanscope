from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"
