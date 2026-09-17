"""Apply immutable, versioned PostgreSQL migrations to the local legacy database.

The container entrypoint can initialize a brand-new volume, but it cannot
upgrade an existing one. This runner closes that gap by applying every SQL
migration exactly once and refusing checksum drift for an already-applied
version.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

from config import RuntimeConfiguration, RuntimeConfigurationError


MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3})_[a-z0-9_]+\.sql$")
MIGRATION_DIRECTORIES = ("migrations", "procedures")
ADVISORY_LOCK_KEY = 6_414_537_242_417


class MigrationError(Exception):
    """The database schema could not be upgraded safely."""


@dataclass(frozen=True, slots=True)
class Migration:
    """One immutable SQL migration and its content identity."""

    version: str
    name: str
    path: Path
    sha256: str
    sql: str


def _strip_psql_directives(sql: str) -> str:
    """Remove psql-only directives before sending SQL through psycopg."""

    return "\n".join(
        line
        for line in sql.splitlines()
        if not line.lstrip().startswith("\\")
    ).strip() + "\n"


def discover_migrations(postgres_root: Path) -> tuple[Migration, ...]:
    """Return ordered migrations, rejecting duplicate or malformed versions."""

    migrations: list[Migration] = []
    for directory_name in MIGRATION_DIRECTORIES:
        directory = postgres_root / directory_name
        for path in sorted(directory.glob("*.sql")):
            match = MIGRATION_NAME.fullmatch(path.name)
            if match is None:
                raise MigrationError(
                    f"Migration filename is not versioned: {path.name}"
                )
            content = path.read_bytes()
            try:
                sql = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise MigrationError(
                    f"Migration is not UTF-8: {path.name}"
                ) from exc
            migrations.append(
                Migration(
                    version=match.group("version"),
                    name=path.name,
                    path=path,
                    sha256=hashlib.sha256(content).hexdigest(),
                    sql=_strip_psql_directives(sql),
                )
            )

    migrations.sort(key=lambda migration: migration.version)
    versions = [migration.version for migration in migrations]
    if len(versions) != len(set(versions)):
        duplicates = sorted(
            version for version in set(versions) if versions.count(version) > 1
        )
        raise MigrationError(
            "Duplicate PostgreSQL migration versions: "
            + ", ".join(duplicates)
        )
    if not migrations:
        raise MigrationError("No PostgreSQL migrations were discovered")
    return tuple(migrations)


def _ensure_ledger(cursor: psycopg.Cursor[object]) -> None:
    cursor.execute(
        """
        CREATE SCHEMA IF NOT EXISTS control;

        CREATE TABLE IF NOT EXISTS control.schema_migrations (
            version text PRIMARY KEY CHECK (version ~ '^[0-9]{3}$'),
            name text NOT NULL UNIQUE,
            sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );

        ALTER TABLE control.schema_migrations
            OWNER TO northwind_legacy_owner;

        REVOKE ALL ON control.schema_migrations FROM PUBLIC;
        """
    )


def apply_migrations(
    migrations: tuple[Migration, ...],
    *,
    configuration: RuntimeConfiguration,
) -> tuple[str, ...]:
    """Apply missing migrations and return the versions changed this run."""

    applied: list[str] = []
    try:
        with psycopg.connect(configuration.postgres_admin_dsn) as connection:
            for migration in migrations:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_xact_lock(%s)",
                            (ADVISORY_LOCK_KEY,),
                        )
                        _ensure_ledger(cursor)
                        cursor.execute(
                            """
                            SELECT name, sha256
                              FROM control.schema_migrations
                             WHERE version = %s
                            """,
                            (migration.version,),
                        )
                        existing = cursor.fetchone()
                        if existing is not None:
                            if existing != (
                                migration.name,
                                migration.sha256,
                            ):
                                raise MigrationError(
                                    "Applied migration checksum drift: "
                                    f"{migration.version}"
                                )
                            continue

                        cursor.execute(
                            "SELECT set_config('northwind.app_user', %s, true)",
                            (configuration.postgres_app_user,),
                        )
                        cursor.execute(migration.sql)
                        cursor.execute(
                            """
                            INSERT INTO control.schema_migrations (
                                version, name, sha256
                            )
                            VALUES (%s, %s, %s)
                            """,
                            (
                                migration.version,
                                migration.name,
                                migration.sha256,
                            ),
                        )
                        applied.append(migration.version)
    except MigrationError:
        raise
    except (OSError, psycopg.Error) as exc:
        raise MigrationError(
            "PostgreSQL migration transaction failed"
        ) from exc
    return tuple(applied)


def main() -> int:
    """Run every pending migration using the local administrator connection."""

    try:
        configuration = RuntimeConfiguration.load()
        postgres_root = Path(__file__).resolve().parent
        migrations = discover_migrations(postgres_root)
        applied = apply_migrations(
            migrations,
            configuration=configuration,
        )
    except (MigrationError, RuntimeConfigurationError) as exc:
        print(f"database migration failed: {exc}", file=sys.stderr)
        return 2

    if applied:
        print("applied PostgreSQL migrations: " + ", ".join(applied))
    else:
        print("PostgreSQL schema is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
