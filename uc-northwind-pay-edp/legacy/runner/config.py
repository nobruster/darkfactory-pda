from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from psycopg.conninfo import make_conninfo


class RuntimeConfigurationError(Exception):
    """Local runtime configuration is missing or unsafe."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeConfigurationError(
                f"Invalid environment line: {path.name}:{line_number}"
            )
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeConfigurationError(
            f"Required environment setting is missing: {name}"
        )
    return value


def required_port(name: str) -> int:
    value = required_environment(name)
    try:
        port = int(value)
    except ValueError as exc:
        raise RuntimeConfigurationError(
            f"Environment setting is not a valid port: {name}"
        ) from exc
    if not 1 <= port <= 65535:
        raise RuntimeConfigurationError(
            f"Environment setting is outside the port range: {name}"
        )
    return port


@dataclass(frozen=True, slots=True)
class SftpRole:
    """Credentials for one least-privilege SFTP actor."""

    username: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    """Validated connection settings for the local legacy topology."""

    root: Path
    sftp_host: str
    sftp_port: int
    known_hosts: Path
    raw_publisher: SftpRole
    processor: SftpRole
    loader: SftpRole
    operator: SftpRole
    postgres_app_user: str
    postgres_dsn: str
    postgres_admin_dsn: str = field(repr=False)

    @classmethod
    def load(cls) -> RuntimeConfiguration:
        root = repository_root()
        load_dotenv(root / ".env")
        return cls(
            root=root,
            sftp_host=required_environment("SFTP_HOST"),
            sftp_port=required_port("SFTP_PORT"),
            known_hosts=root / ".runtime" / "known_hosts",
            raw_publisher=SftpRole(
                required_environment("SFTP_RAW_PUBLISHER_USER"),
                required_environment("SFTP_RAW_PUBLISHER_PASSWORD"),
            ),
            processor=SftpRole(
                required_environment("SFTP_PROCESSOR_USER"),
                required_environment("SFTP_PROCESSOR_PASSWORD"),
            ),
            loader=SftpRole(
                required_environment("SFTP_LOADER_USER"),
                required_environment("SFTP_LOADER_PASSWORD"),
            ),
            operator=SftpRole(
                required_environment("SFTP_OPERATOR_USER"),
                required_environment("SFTP_OPERATOR_PASSWORD"),
            ),
            postgres_app_user=required_environment("POSTGRES_USER"),
            postgres_dsn=(
                make_conninfo(
                    host=required_environment("POSTGRES_HOST"),
                    port=required_port("POSTGRES_PORT"),
                    dbname=required_environment("POSTGRES_DB"),
                    user=required_environment("POSTGRES_USER"),
                    password=required_environment("POSTGRES_PASSWORD"),
                    connect_timeout=10,
                )
            ),
            postgres_admin_dsn=(
                make_conninfo(
                    host=required_environment("POSTGRES_HOST"),
                    port=required_port("POSTGRES_PORT"),
                    dbname=required_environment("POSTGRES_DB"),
                    user=required_environment("POSTGRES_ADMIN_USER"),
                    password=required_environment("POSTGRES_ADMIN_PASSWORD"),
                    connect_timeout=10,
                )
            ),
        )
