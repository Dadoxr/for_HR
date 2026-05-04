from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DEBUG: bool = False
    DB_TYPE: str = "sqlite"

    # PostgreSQL
    POSTGRES_ENGINE: str = "asyncpg"
    POSTGRES_DB: str = "fastapi"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    # SQLite
    SQLITE_PATH: str = "data/fastapi.db"

    @property
    def db_url(self) -> str:
        if self.DB_TYPE.lower() == "postgres":
            return (
                f"postgresql+{self.POSTGRES_ENGINE}://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        db_dir = Path(self.SQLITE_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"

    @property
    def db_echo(self) -> bool:
        return self.DEBUG


settings = Settings()
