import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str
    app_env: str
    cors_origins: list[str]


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        app_env=os.getenv("APP_ENV", "development"),
        cors_origins=[o.strip() for o in origins],
    )