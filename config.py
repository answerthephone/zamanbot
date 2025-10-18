from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")

    # Database
    DB_USER: str = Field(..., description="Database username")
    DB_PASSWORD: str = Field(..., description="Database password")
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(..., description="Database port")
    DB_NAME: str = Field(..., description="Database name")

    # Computed property for DATABASE_URL
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",  # no prefix required
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached app settings."""
    return Settings() # type: ignore
