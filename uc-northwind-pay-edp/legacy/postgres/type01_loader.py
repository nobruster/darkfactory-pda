"""Validate sanitized Type 01 batches and load PostgreSQL transactionally."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from jsonschema import Draft202012Validator

from config import RuntimeConfiguration
from loader_common import (
    CHECKSUM_PATTERN,
    LoadResult,
    PostgresLoadError,
    _quarantine_invalid_csv,
    _register_or_verify_batch,
    _register_or_verify_file,
    finalize_committed_batch,
)
from raw_publisher import PublishedRaw
from sftp_client import (
    connect_sftp,
    exists,
    move_batch,
)


CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "transaction_id",
    "merchant_id",
    "card_token",
    "card_last4",
    "cpf_masked",
    "transaction_ts",
    "amount_brl",
    "movement_code",
    "authorization_code",
    "nsu",
    "terminal_id",
)


@dataclass(frozen=True, slots=True)
class PreparedType01Load:
    """Validated Type 01 sanitized data that has not changed PostgreSQL."""

    batch_id: str
    raw_filename: str
    raw_sha256: str
    raw_manifest_sha256: str
    source_count: int
    source_net_amount: str
    csv_filename: str
    csv_sha256: str
    csv_size_bytes: int
    row_count: int
    net_amount: str
    rows: tuple[tuple[object, ...], ...]


def prepare_type01_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType01Load:
    """Claim and validate Type 01 CSV without opening PostgreSQL."""

    if batch_id != raw.batch_id:
        raise PostgresLoadError("Prepared batch ID does not match raw lineage")

    outgoing = f"/csv/outgoing/{batch_id}"
    processing = f"/csv/processing/{batch_id}"
    with connect_sftp(configuration, configuration.loader) as sftp:
        outgoing_exists = exists(sftp, outgoing)
        processing_exists = exists(sftp, processing)
        if outgoing_exists and processing_exists:
            raise PostgresLoadError(
                "Sanitized batch exists in both outgoing and processing"
            )
        if outgoing_exists:
            if not exists(sftp, f"{outgoing}/sanitized-manifest.json"):
                raise PostgresLoadError("Sanitized batch is not ready")
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/outgoing",
                target_zone="/csv/processing",
            )
        elif not processing_exists:
            raise PostgresLoadError(
                "Sanitized batch is unavailable for preparation"
            )

        try:
            if not exists(sftp, f"{processing}/sanitized-manifest.json"):
                raise PostgresLoadError(
                    "Processing batch has no readiness manifest"
                )
            with tempfile.TemporaryDirectory(
                prefix="northwind-csv-loader-"
            ) as temporary:
                return _download_and_validate(
                    sftp,
                    processing,
                    Path(temporary),
                    batch_id=batch_id,
                    raw=raw,
                    configuration=configuration,
                )
        except PostgresLoadError:
            _quarantine_invalid_csv(
                sftp,
                batch_id,
                code="POSTGRES_LOAD_REJECTED",
            )
            raise


def commit_type01_batch(
    prepared: PreparedType01Load,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
    reconciliation_validator: (
        Callable[[Mapping[str, object]], object] | None
    ) = None,
) -> LoadResult:
    """Commit a prepared Type 01 batch and leave CSV for finalization."""

    _validate_prepared_lineage(prepared, raw=raw)
    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_batch(cursor, raw=raw)
                _register_or_verify_file(
                    cursor,
                    batch_id=raw.batch_id,
                    stage="raw",
                    filename=raw.filename,
                    sha256=raw.sha256,
                    size_bytes=raw.size_bytes,
                )
                _register_or_verify_file(
                    cursor,
                    batch_id=raw.batch_id,
                    stage="sanitized_csv",
                    filename=prepared.csv_filename,
                    sha256=prepared.csv_sha256,
                    size_bytes=prepared.csv_size_bytes,
                )
                _insert_and_verify_staging(
                    cursor,
                    prepared.rows,
                    batch_id=raw.batch_id,
                )
                _verify_staging_controls(
                    cursor,
                    batch_id=raw.batch_id,
                    expected_count=raw.source_count,
                    expected_net_amount=raw.source_net_amount,
                )
                _register_or_verify_load(
                    cursor,
                    batch_id=raw.batch_id,
                    staged_count=prepared.row_count,
                    staged_net_amount=prepared.net_amount,
                )
                cursor.execute(
                    "SELECT legacy.apply_card_settlement_batch(%s)",
                    (raw.batch_id,),
                )
                cursor.execute(
                    """
                    SELECT reporting.refresh_card_settlement_reconciliation(%s)
                    """,
                    (raw.batch_id,),
                )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "PostgreSQL reconciliation is not MATCHED"
                    )
                if reconciliation_validator is not None:
                    reconciliation_validator(reconciliation)
                cursor.execute(
                    "SELECT control.mark_batch_committed(%s)",
                    (raw.batch_id,),
                )
        return LoadResult(
            batch_id=raw.batch_id,
            csv_filename=prepared.csv_filename,
            csv_sha256=prepared.csv_sha256,
            row_count=prepared.row_count,
            net_amount=prepared.net_amount,
            procedure_runs=procedure_runs,
            reconciliation=reconciliation,
        )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "PostgreSQL transaction rolled back"
        ) from exc


def read_type01_committed_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Read and verify a committed Type 01 batch for recovery."""

    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
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
                    (batch_id,),
                )
                batch = cursor.fetchone()
                if (
                    batch is None
                    or batch[:7]
                    != (
                        raw.file_type,
                        raw.filename,
                        raw.sha256,
                        raw.manifest_sha256,
                        raw.source_count,
                        Decimal(raw.source_net_amount),
                        dict(raw.source_controls),
                    )
                    or batch[7]
                    not in {
                        "database_committed_pending_archive",
                        "succeeded",
                    }
                    or batch[8] is not None
                ):
                    raise PostgresLoadError(
                        "Committed batch does not match raw lineage"
                    )
                cursor.execute(
                    """
                    SELECT filename, sha256
                      FROM control.files
                     WHERE batch_id = %s AND stage = 'sanitized_csv'
                    """,
                    (batch_id,),
                )
                csv_file = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT staged_count, staged_net_amount, status
                      FROM control.loads
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                load = cursor.fetchone()
                if (
                    csv_file is None
                    or load is None
                    or load[2] != "loaded"
                ):
                    raise PostgresLoadError(
                        "Committed batch metadata is incomplete"
                    )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=batch_id,
                )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Cannot read committed batch for recovery"
        ) from exc

    return LoadResult(
        batch_id=batch_id,
        csv_filename=csv_file[0],
        csv_sha256=csv_file[1],
        row_count=load[0],
        net_amount=format(load[1], ".2f"),
        procedure_runs=procedure_runs,
        reconciliation=reconciliation,
    )


def load_type01_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Compatibility helper around the split Type 01 loader API."""

    prepared = prepare_type01_sanitized_batch(
        batch_id,
        raw=raw,
        configuration=configuration,
    )
    result = commit_type01_batch(
        prepared,
        raw=raw,
        configuration=configuration,
    )
    finalize_committed_batch(batch_id, configuration=configuration)
    return result


def _download_and_validate(
    sftp,
    remote_directory: str,
    temporary_root: Path,
    *,
    batch_id: str,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType01Load:
    manifest_path = temporary_root / "sanitized-manifest.json"
    sftp.get(
        f"{remote_directory}/sanitized-manifest.json",
        str(manifest_path),
    )
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        schema = json.loads(
            (
                configuration.root
                / "contracts"
                / "common"
                / "sanitized-manifest.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(manifest)
    except Exception as exc:
        raise PostgresLoadError(
            "Sanitized manifest violates its executable schema"
        ) from exc

    if (
        manifest["batch_id"] != batch_id
        or manifest["source_lineage"]["raw_file"] != raw.filename
        or manifest["source_lineage"]["raw_sha256"] != raw.sha256
        or manifest["source_lineage"]["manifest_sha256"]
        != raw.manifest_sha256
    ):
        raise PostgresLoadError("Sanitized lineage does not match the raw batch")

    csv_filename = manifest["csv_file"]["name"]
    csv_path = temporary_root / csv_filename
    checksum_path = temporary_root / f"{csv_filename}.sha256"
    sftp.get(f"{remote_directory}/{csv_filename}", str(csv_path))
    sftp.get(
        f"{remote_directory}/{csv_filename}.sha256",
        str(checksum_path),
    )
    csv_bytes = csv_path.read_bytes()
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
    checksum = CHECKSUM_PATTERN.fullmatch(checksum_path.read_bytes())
    if (
        csv_sha256 != manifest["csv_file"]["sha256"]
        or len(csv_bytes) != manifest["csv_file"]["size_bytes"]
        or checksum is None
        or checksum.group("digest").decode("ascii") != csv_sha256
        or checksum.group("filename").decode("ascii") != csv_filename
    ):
        raise PostgresLoadError("Sanitized CSV integrity validation failed")

    rows, row_count, net_amount = _parse_csv(
        csv_bytes,
        batch_id=batch_id,
        source_filename=raw.filename,
    )
    net_amount_string = format(net_amount, ".2f")
    if (
        row_count != manifest["csv_file"]["row_count"]
        or row_count != manifest["stage_controls"]["row_count"]
        or net_amount_string != manifest["stage_controls"]["net_amount"]
        or row_count != raw.source_count
        or net_amount_string != raw.source_net_amount
    ):
        raise PostgresLoadError(
            "Sanitized CSV controls do not match the source controls"
        )

    return PreparedType01Load(
        batch_id=batch_id,
        raw_filename=raw.filename,
        raw_sha256=raw.sha256,
        raw_manifest_sha256=raw.manifest_sha256,
        source_count=raw.source_count,
        source_net_amount=raw.source_net_amount,
        csv_filename=csv_filename,
        csv_sha256=csv_sha256,
        csv_size_bytes=len(csv_bytes),
        row_count=row_count,
        net_amount=net_amount_string,
        rows=rows,
    )


def _parse_csv(
    content: bytes,
    *,
    batch_id: str,
    source_filename: str,
) -> tuple[tuple[tuple[object, ...], ...], int, Decimal]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PostgresLoadError("Sanitized CSV is not UTF-8") from exc
    if not text.endswith("\n") or "\r" in text:
        raise PostgresLoadError("Sanitized CSV transport formatting is invalid")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
        raise PostgresLoadError("Sanitized CSV header does not match Type 01")

    parsed: list[tuple[object, ...]] = []
    net_amount = Decimal("0.00")
    seen_transaction_ids: set[str] = set()
    expected_record_number = 2
    for row in reader:
        try:
            record_number = int(row["source_record_number"])
            amount = Decimal(row["amount_brl"])
            transaction_timestamp = datetime.fromisoformat(
                row["transaction_ts"]
            )
        except (ValueError, InvalidOperation) as exc:
            raise PostgresLoadError(
                "Sanitized CSV contains an invalid typed field"
            ) from exc
        if (
            row["batch_id"] != batch_id
            or row["source_file"] != source_filename
            or record_number != expected_record_number
            or row["transaction_id"] in seen_transaction_ids
            or transaction_timestamp.tzinfo is None
            or not amount.is_finite()
            or not re.fullmatch(r"tok_[0-9a-f]{24}", row["card_token"])
            or not re.fullmatch(r"[0-9]{4}", row["card_last4"])
            or not re.fullmatch(r"\*{7}[0-9]{4}", row["cpf_masked"])
            or format(amount, ".2f") != row["amount_brl"]
            or (
                row["movement_code"] == "P"
                and amount <= Decimal("0.00")
            )
            or (
                row["movement_code"] == "R"
                and amount >= Decimal("0.00")
            )
            or row["movement_code"] not in {"P", "R"}
        ):
            raise PostgresLoadError(
                "Sanitized CSV row violates the Type 01 contract"
            )
        seen_transaction_ids.add(row["transaction_id"])
        expected_record_number += 1
        net_amount += amount
        parsed.append(
            (
                row["batch_id"],
                row["source_file"],
                record_number,
                row["transaction_id"],
                row["merchant_id"],
                row["card_token"],
                row["card_last4"],
                row["cpf_masked"],
                transaction_timestamp,
                amount,
                row["movement_code"],
                row["authorization_code"],
                row["nsu"],
                row["terminal_id"],
            )
        )
    if not parsed:
        raise PostgresLoadError("Sanitized CSV contains no detail rows")
    return tuple(parsed), len(parsed), net_amount


def _validate_prepared_lineage(
    prepared: PreparedType01Load,
    *,
    raw: PublishedRaw,
) -> None:
    if (
        prepared.batch_id != raw.batch_id
        or prepared.raw_filename != raw.filename
        or prepared.raw_sha256 != raw.sha256
        or prepared.raw_manifest_sha256 != raw.manifest_sha256
        or prepared.source_count != raw.source_count
        or prepared.source_net_amount != raw.source_net_amount
        or prepared.row_count != raw.source_count
        or prepared.net_amount != raw.source_net_amount
    ):
        raise PostgresLoadError(
            "Prepared sanitized data no longer matches raw lineage"
        )


def _insert_and_verify_staging(
    cursor,
    rows: tuple[tuple[object, ...], ...],
    *,
    batch_id: str,
) -> None:
    cursor.execute(
        """
        CREATE TEMPORARY TABLE type01_copy_buffer (
            LIKE staging.card_settlement INCLUDING ALL
        ) ON COMMIT DROP
        """
    )
    copy_columns = (
        "batch_id",
        "source_file",
        "source_record_number",
        "transaction_id",
        "merchant_id",
        "card_token",
        "card_last4",
        "cpf_masked",
        "transaction_ts",
        "amount_brl",
        "movement_code",
        "authorization_code",
        "nsu",
        "terminal_id",
    )
    copy_statement = (
        "COPY type01_copy_buffer ("
        + ", ".join(copy_columns)
        + ") FROM STDIN"
    )
    with cursor.copy(copy_statement) as copy:
        for row in rows:
            copy.write_row(row)

    cursor.execute(
        """
        INSERT INTO staging.card_settlement (
            batch_id,
            source_file,
            source_record_number,
            transaction_id,
            merchant_id,
            card_token,
            card_last4,
            cpf_masked,
            transaction_ts,
            amount_brl,
            movement_code,
            authorization_code,
            nsu,
            terminal_id
        )
        SELECT
            batch_id,
            source_file,
            source_record_number,
            transaction_id,
            merchant_id,
            card_token,
            card_last4,
            cpf_masked,
            transaction_ts,
            amount_brl,
            movement_code,
            authorization_code,
            nsu,
            terminal_id
          FROM type01_copy_buffer
        ON CONFLICT (batch_id, source_record_number) DO NOTHING
        """
    )
    cursor.execute(
        """
        SELECT
            batch_id,
            source_file,
            source_record_number,
            transaction_id,
            merchant_id,
            card_token,
            card_last4,
            cpf_masked,
            transaction_ts,
            amount_brl,
            movement_code,
            authorization_code,
            nsu,
            terminal_id
          FROM staging.card_settlement
         WHERE batch_id = %s
         ORDER BY source_record_number
        """,
        (batch_id,),
    )
    if tuple(cursor.fetchall()) != rows:
        raise PostgresLoadError(
            "Full staging row identity changed on replay"
        )


def _register_or_verify_load(
    cursor,
    *,
    batch_id: str,
    staged_count: int,
    staged_net_amount: str,
) -> None:
    cursor.execute(
        """
        SELECT control.register_load(%s, %s, %s)
        """,
        (batch_id, staged_count, staged_net_amount),
    )
    cursor.execute(
        """
        SELECT staged_count, staged_net_amount, status
          FROM control.loads
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    if cursor.fetchone() != (
        staged_count,
        Decimal(staged_net_amount),
        "loaded",
    ):
        raise PostgresLoadError(
            "Batch load controls changed on replay"
        )


def _verify_staging_controls(
    cursor,
    *,
    batch_id: str,
    expected_count: int,
    expected_net_amount: str,
) -> None:
    cursor.execute(
        """
        SELECT count(*), coalesce(sum(amount_brl), 0.00)
          FROM staging.card_settlement
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    staged_count, staged_net = cursor.fetchone()
    if (
        staged_count != expected_count
        or Decimal(staged_net) != Decimal(expected_net_amount)
    ):
        raise PostgresLoadError(
            "Staging controls do not match the source controls"
        )


def _read_database_results(
    cursor,
    *,
    batch_id: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    cursor.execute(
        """
        SELECT sequence_number, procedure_name, status
          FROM control.procedure_runs
         WHERE batch_id = %s
         ORDER BY sequence_number
        """,
        (batch_id,),
    )
    procedure_runs = tuple(
        {
            "sequence": sequence,
            "procedure": name,
            "status": status,
        }
        for sequence, name, status in cursor.fetchall()
    )
    cursor.execute(
        """
        SELECT
            batch_id,
            currency,
            source_count,
            staged_count,
            applied_count,
            source_net_amount,
            staged_net_amount,
            applied_net_amount,
            count_delta,
            amount_delta,
            reject_count,
            status
          FROM reporting.card_settlement_reconciliation
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    report = cursor.fetchone()
    if report is None:
        raise PostgresLoadError(
            "Reconciliation procedure produced no report"
        )
    reconciliation = {
        "batch_id": report[0],
        "currency": report[1],
        "source_count": report[2],
        "staged_count": report[3],
        "applied_count": report[4],
        "source_net_amount": format(report[5], ".2f"),
        "staged_net_amount": format(report[6], ".2f"),
        "applied_net_amount": format(report[7], ".2f"),
        "count_delta": report[8],
        "amount_delta": format(report[9], ".2f"),
        "reject_count": report[10],
        "status": report[11],
    }
    return procedure_runs, reconciliation
