from __future__ import annotations

import json
import sys

import psycopg

from config import RuntimeConfiguration, RuntimeConfigurationError
from sftp_client import SftpBoundaryError, connect_sftp


def main() -> int:
    try:
        configuration = RuntimeConfiguration.load()
        role_status: dict[str, str] = {}
        for name, role in (
            ("raw-publisher", configuration.raw_publisher),
            ("processor", configuration.processor),
            ("loader", configuration.loader),
            ("operator", configuration.operator),
        ):
            with connect_sftp(configuration, role) as sftp:
                sftp.listdir(".")
            role_status[name] = "healthy"
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('server_version')")
                postgres_version = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT current_user, rolsuper
                      FROM pg_roles
                     WHERE rolname = current_user
                    """
                )
                postgres_role, postgres_superuser = cursor.fetchone()
                if postgres_superuser:
                    raise RuntimeConfigurationError(
                        "Application PostgreSQL role must not be a superuser"
                    )
        print(
            json.dumps(
                {
                    "postgres": {
                        "status": "healthy",
                        "role": postgres_role,
                        "superuser": postgres_superuser,
                        "version": postgres_version,
                    },
                    "sftp_roles": role_status,
                    "status": "healthy",
                },
                sort_keys=True,
            )
        )
        return 0
    except (
        OSError,
        psycopg.Error,
        RuntimeConfigurationError,
        SftpBoundaryError,
    ) as exc:
        print(f"runtime status failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
