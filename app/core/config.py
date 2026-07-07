from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsSchema(BaseSettings):
    """Схема настроек приложения"""

    # PostgreSQL
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_ASYNCPG: str = Field(
        default="asyncpg", description="PostgreSQL async driver"
    )
    POSTGRES_DB: str = Field(default="postgres", description="PostgreSQL database name")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    POSTGRES_PORT: int = Field(default=5433, description="PostgreSQL port")

    # Redis
    REDIS_PORT: int = Field(default=6380, description="Redis host")

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+{self.POSTGRES_ASYNCPG}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=True,
    )


# Глобальный экземпляр настроек
settings = SettingsSchema()
