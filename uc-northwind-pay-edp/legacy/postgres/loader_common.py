"""Shared PostgreSQL loader lifecycle and control-plane primitives.

Typed loader modules own their file-specific parsing, staging, procedures, and
reconciliation. This module contains only the durable batch lifecycle and
metadata operations that are identical across all file types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.types.json import Jsonb

from config import RuntimeConfiguration
from raw_publisher import PublishedRaw
from sftp_client import (
    SftpBoundaryError,
    connect_sftp,
    exists,
    move_batch,
    write_safe_json,
)


class PostgresLoadError(Exception):
    """Sanitized data could not be validated or committed safely."""


CHECKSUM_PATTERN = re.compile(
    rb"(?P<digest>[0-9a-f]{64})  (?P<filename>[^/\r\n]+)\n"
)


@dataclass(frozen=True, slots=True)
class DiagnosticControls:
    """Privacy-safe controls independently derived from a rejected raw batch."""

    computed_count: int | None = None
    computed_net_amount: str | None = None
    declared_count: int | None = None
    declared_net_amount: str | None = None


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Durable database and reconciliation result for one typed batch."""

    batch_id: str
    csv_filename: str
    csv_sha256: str
    row_count: int
    net_amount: str
    procedure_runs: tuple[dict[str, object], ...]
    reconciliation: dict[str, object]


def finalize_committed_batch(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Archive committed CSV and then mark the durable batch succeeded."""

    status = _read_batch_status(batch_id, configuration=configuration)
    if status not in {"database_committed_pending_archive", "succeeded"}:
        raise PostgresLoadError(
            "Batch is not eligible for committed finalization"
        )

    processing = f"/csv/processing/{batch_id}"
    archive = f"/csv/archive/{batch_id}"
    with connect_sftp(configuration, configuration.operator) as sftp:
        processing_exists = exists(sftp, processing)
        archive_exists = exists(sftp, archive)
        if processing_exists and archive_exists:
            raise PostgresLoadError(
                "Committed CSV exists in both processing and archive"
            )
        if processing_exists:
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/processing",
                target_zone="/csv/archive",
            )
        elif not archive_exists:
            raise PostgresLoadError(
                "Committed CSV is absent from processing and archive"
            )

    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT control.mark_batch_succeeded(%s)",
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT status
                      FROM control.batches
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                if cursor.fetchone() != ("succeeded",):
                    raise PostgresLoadError(
                        "Committed batch status changed before finalization"
                    )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "CSV was archived but database finalization remains pending"
        ) from exc


def record_rejected_batch(
    raw: PublishedRaw,
    *,
    code: str,
    diagnostic_controls: DiagnosticControls | None = None,
    status: str = "quarantined",
    configuration: RuntimeConfiguration,
) -> None:
    """Record a raw rejection without creating staging or business rows."""

    if not code or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", code):
        raise PostgresLoadError("Rejected batch code is unsafe")
    if status not in {"quarantined", "oracle_mismatch"}:
        raise PostgresLoadError("Rejected batch terminal status is unsafe")
    diagnostics = diagnostic_controls or DiagnosticControls()
    _validate_diagnostic_controls(diagnostics)
    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_rejected_batch(
                    cursor,
                    raw=raw,
                    code=code,
                    status=status,
                )
                _register_or_verify_file(
                    cursor,
                    batch_id=raw.batch_id,
                    stage="raw",
                    filename=raw.filename,
                    sha256=raw.sha256,
                    size_bytes=raw.size_bytes,
                )
                cursor.execute(
                    """
                    SELECT control.register_reject(
                        %s, 'raw_processing', %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        raw.batch_id,
                        code,
                        diagnostics.computed_count,
                        diagnostics.computed_net_amount,
                        diagnostics.declared_count,
                        diagnostics.declared_net_amount,
                    ),
                )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Rejected batch control transaction rolled back"
        ) from exc


def quarantine_prepared_batch(
    batch_id: str,
    *,
    code: str,
    configuration: RuntimeConfiguration,
) -> None:
    """Quarantine sanitized CSV before a PostgreSQL commit."""

    with connect_sftp(configuration, configuration.loader) as sftp:
        processing = f"/csv/processing/{batch_id}"
        outgoing = f"/csv/outgoing/{batch_id}"
        if exists(sftp, outgoing):
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/outgoing",
                target_zone="/csv/processing",
            )
        elif not exists(sftp, processing):
            return
        _quarantine_invalid_csv(sftp, batch_id, code=code)


def _register_or_verify_batch(cursor, *, raw: PublishedRaw) -> None:
    cursor.execute(
        """
        SELECT control.register_batch_v2(
            %s, %s, %s, %s, %s, %s, %s, %s, 'claimed', NULL
        )
        """,
        (
            raw.batch_id,
            raw.file_type,
            raw.filename,
            raw.sha256,
            raw.manifest_sha256,
            Jsonb(dict(raw.source_controls)),
            raw.source_count,
            raw.source_net_amount,
        ),
    )
    cursor.execute(
        """
        SELECT
            file_type,
            source_filename,
            source_sha256,
            source_manifest_sha256,
            source_count,
            source_net_amount,
            source_controls,
            status,
            failure_code
          FROM control.batches
         WHERE batch_id = %s
        """,
        (raw.batch_id,),
    )
    existing = cursor.fetchone()
    expected_prefix = (
        raw.file_type,
        raw.filename,
        raw.sha256,
        raw.manifest_sha256,
        raw.source_count,
        Decimal(raw.source_net_amount),
        dict(raw.source_controls),
    )
    if (
        existing is None
        or existing[:7] != expected_prefix
        or existing[7]
        not in {
            "claimed",
            "database_committed_pending_archive",
            "succeeded",
        }
        or existing[8] is not None
    ):
        raise PostgresLoadError(
            "Batch ID was previously used for different source state"
        )


def _register_or_verify_rejected_batch(
    cursor,
    *,
    raw: PublishedRaw,
    code: str,
    status: str,
) -> None:
    cursor.execute(
        """
        SELECT control.register_batch_v2(
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            raw.batch_id,
            raw.file_type,
            raw.filename,
            raw.sha256,
            raw.manifest_sha256,
            Jsonb(dict(raw.source_controls)),
            raw.source_count,
            raw.source_net_amount,
            status,
            code,
        ),
    )
    cursor.execute(
        """
        SELECT
            file_type,
            source_filename,
            source_sha256,
            source_manifest_sha256,
            source_count,
            source_net_amount,
            source_controls,
            status,
            failure_code
          FROM control.batches
         WHERE batch_id = %s
        """,
        (raw.batch_id,),
    )
    existing = cursor.fetchone()
    expected = (
        raw.file_type,
        raw.filename,
        raw.sha256,
        raw.manifest_sha256,
        raw.source_count,
        Decimal(raw.source_net_amount),
        dict(raw.source_controls),
        status,
        code,
    )
    if existing != expected:
        raise PostgresLoadError(
            "Rejected batch state changed on replay"
        )


def _register_or_verify_file(
    cursor,
    *,
    batch_id: str,
    stage: str,
    filename: str,
    sha256: str,
    size_bytes: int,
) -> None:
    cursor.execute(
        """
        SELECT control.register_file(%s, %s, %s, %s, %s)
        """,
        (batch_id, stage, filename, sha256, size_bytes),
    )
    cursor.execute(
        """
        SELECT filename, sha256, size_bytes
          FROM control.files
         WHERE batch_id = %s AND stage = %s
        """,
        (batch_id, stage),
    )
    if cursor.fetchone() != (filename, sha256, size_bytes):
        raise PostgresLoadError(
            f"Batch {stage} file identity changed on replay"
        )


def _read_batch_status(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> str:
    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status
                      FROM control.batches
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise PostgresLoadError(
                        "Committed batch control row does not exist"
                    )
                return str(row[0])
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Cannot read committed batch status"
        ) from exc


def _validate_diagnostic_controls(
    controls: DiagnosticControls,
) -> None:
    for count in (controls.computed_count, controls.declared_count):
        if count is not None and count < 0:
            raise PostgresLoadError("Diagnostic count cannot be negative")
    for amount in (
        controls.computed_net_amount,
        controls.declared_net_amount,
    ):
        if amount is None:
            continue
        try:
            parsed = Decimal(amount)
        except InvalidOperation as exc:
            raise PostgresLoadError(
                "Diagnostic net amount is not decimal"
            ) from exc
        if not parsed.is_finite() or format(parsed, ".2f") != amount:
            raise PostgresLoadError(
                "Diagnostic net amount must use exact scale two"
            )


def _quarantine_invalid_csv(
    sftp,
    batch_id: str,
    *,
    code: str,
) -> None:
    try:
        move_batch(
            sftp,
            batch_id,
            source_zone="/csv/processing",
            target_zone="/csv/quarantine",
        )
        write_safe_json(
            sftp,
            f"/csv/quarantine/{batch_id}/quarantine-reason.json",
            {
                "batch_id": batch_id,
                "code": code,
                "scope": "batch",
                "status": "quarantined",
            },
        )
    except SftpBoundaryError:
        raise
