import os
from pathlib import Path

import dotenv
from pydantic_settings import BaseSettings


def load_env(base_dir: str) -> None:
    dotenv.load_dotenv(os.path.join(base_dir, ".env"), override=True)
    dotenv.load_dotenv(os.path.join(base_dir, ".env.dev"), override=True)


def get_db_urls():
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgres":
        engine = os.getenv("POSTGRES_ENGINE", "asyncpg")
        db_name = os.getenv("POSTGRES_DB", "fastapi")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        return f"postgresql+{engine}://{user}:{password}@{host}:{port}/{db_name}"
    else:
        db_path = os.getenv("SQLITE_PATH", "data/fastapi.db")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"


class Settings(BaseSettings):
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent.parent)
    load_env(BASE_DIR)

    DEBUG: bool = str(os.getenv("DEBUG", "False")) == "True"

    db_url: str = get_db_urls()

    db_echo: bool = DEBUG


settings = Settings()

