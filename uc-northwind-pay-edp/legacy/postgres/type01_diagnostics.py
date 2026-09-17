"""Run privacy-safe Type 01, read-only PostgreSQL control diagnostics."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import psycopg

from config import RuntimeConfiguration


class DiagnosticError(Exception):
    """A privacy-safe, non-posting database diagnostic could not complete."""


def calculate_detail_controls(
    amounts: object,
    *,
    configuration: RuntimeConfiguration,
) -> dict[str, object]:
    """Recompute count and BRL net from already sanitized amount controls.

    The database connection is read-only and no identifiers or business rows
    are accepted. Money must be canonical scale-two decimal text.
    """

    if not isinstance(amounts, list) or not amounts:
        raise DiagnosticError("Diagnostic detail amounts are unavailable")
    try:
        normalized = [Decimal(str(value)) for value in amounts]
    except InvalidOperation as exc:
        raise DiagnosticError("Diagnostic detail amount is invalid") from exc
    if any(format(value, ".2f") != str(source) for value, source in zip(normalized, amounts)):
        raise DiagnosticError("Diagnostic detail amount is not exact BRL")

    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*), coalesce(sum(value), 0.00)
                      FROM unnest(%s::numeric[]) AS detail(value)
                    """,
                    (normalized,),
                )
                detail_count, net_amount = cursor.fetchone()
    except psycopg.Error as exc:
        raise DiagnosticError(
            "Read-only PostgreSQL diagnostic failed"
        ) from exc

    return {
        "business_state_committed": False,
        "computed_detail_count": detail_count,
        "computed_net_amount": format(net_amount, ".2f"),
        "input": "privacy-safe-derived-detail-amounts",
        "mode": "read_only",
        "status": "completed",
    }
