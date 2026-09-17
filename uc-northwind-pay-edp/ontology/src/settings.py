"""Plant-scoped crawl settings. Postgres only. Never default to public."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PLANT_SCHEMAS: tuple[str, ...] = ("control", "staging", "legacy", "reporting")
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    connector_type: str = "postgres"

    postgres_connection_string: str = ""
    postgres_schema_filter: str = "control,staging,legacy,reporting"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 54329
    postgres_db: str = "northwind_legacy"
    postgres_admin_user: str = ""
    postgres_admin_password: str = ""

    definition_sql_max_chars: int = Field(default=8000, ge=256, le=100_000)

    def schema_names(self) -> tuple[str, ...]:
        parts = tuple(
            p.strip()
            for p in self.postgres_schema_filter.split(",")
            if p.strip()
        )
        if not parts or parts == ("public",):
            return PLANT_SCHEMAS
        return parts

    def dsn(self) -> str:
        if self.postgres_connection_string.strip():
            return self.postgres_connection_string.strip()
        user = self.postgres_admin_user
        password = self.postgres_admin_password
        if not user or not password:
            raise RuntimeError(
                "Postgres admin credentials are missing. "
                "Run `make init` then `make deploy` so .env exists and the plant is up."
            )
        return (
            f"postgresql://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
