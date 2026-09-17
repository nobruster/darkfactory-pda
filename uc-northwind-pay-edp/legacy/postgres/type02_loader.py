"""Validate and load privacy-safe Type 02 instant-payment CSV batches.

The module owns Type 02 row semantics while reusing the established SFTP
lifecycle and control-plane registration. Sanitized bytes are validated before
opening PostgreSQL, then loaded with ``COPY`` and reconciled in one transaction.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from psycopg.types.json import Jsonb

from config import RuntimeConfiguration  # type: ignore[import-untyped]
from loader_common import (
    CHECKSUM_PATTERN,
    LoadResult,
    PostgresLoadError,
    _quarantine_invalid_csv,
    _register_or_verify_batch,
    _register_or_verify_file,
    finalize_committed_batch,
)
from raw_publisher import PublishedRaw  # type: ignore[import-untyped]
from sftp_client import (  # type: ignore[import-untyped]
    connect_sftp,
    exists,
    move_batch,
)


CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "end_to_end_id",
    "transaction_id",
    "payer_document_token",
    "payer_document_masked",
    "payee_document_token",
    "payee_document_masked",
    "event_timestamp",
    "amount_brl",
    "direction",
    "status",
    "return_code",
    "description",
)
COPY_COLUMNS = ", ".join(CSV_COLUMNS)
END_TO_END_ID = re.compile(r"E[0-9]{31}")
TRANSACTION_ID = re.compile(r"(?=.*[A-Z])[A-Z0-9]{16}")
DOCUMENT_TOKEN = re.compile(r"doc_[0-9a-f]{24}")
DOCUMENT_MASK = re.compile(r"(?:\*{7}|\*{10})[0-9]{4}")
RETURN_CODE = re.compile(r"[A-Z0-9]{1,4}")
MONEY = re.compile(r"-?(?:0|[1-9][0-9]{0,15})\.[0-9]{2}")
TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
SOURCE_FILENAME = re.compile(
    r"NW_INSTANT_PAYMENT_(?P<date>[0-9]{8})_"
    r"(?P<batch>B[0-9]{15})\.txt"
)
ASCII_LONG_DIGIT_RUN = re.compile(r"[0-9]{11,19}")
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
BIDI_CONTROLS = frozenset(
    chr(value)
    for start, end in (
        (0x061C, 0x061C),
        (0x200E, 0x200F),
        (0x202A, 0x202E),
        (0x2066, 0x2069),
    )
    for value in range(start, end + 1)
)


@dataclass(frozen=True, slots=True)
class PreparedType02Load:
    """Fully validated Type 02 CSV awaiting its PostgreSQL transaction."""

    batch_id: str
    raw_filename: str
    raw_sha256: str
    raw_manifest_sha256: str
    source_controls: Mapping[str, int | str]
    csv_filename: str
    csv_sha256: str
    csv_size_bytes: int
    stage_controls: Mapping[str, int | str]
    csv_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Freeze control maps so validation cannot drift before commit."""

        object.__setattr__(
            self,
            "source_controls",
            MappingProxyType(dict(self.source_controls)),
        )
        object.__setattr__(
            self,
            "stage_controls",
            MappingProxyType(dict(self.stage_controls)),
        )

    @property
    def row_count(self) -> int:
        """Return the validated number of business events."""

        value = self.stage_controls["row_count"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PostgresLoadError("Type 02 row count is not an integer")
        return value

    @property
    def net_amount(self) -> str:
        """Return the validated signed net amount in canonical BRL text."""

        value = self.stage_controls["net_amount"]
        if not isinstance(value, str):
            raise PostgresLoadError("Type 02 net amount is not canonical")
        return value


def prepare_type02_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType02Load:
    """Atomically claim and validate one ready Type 02 sanitized bundle.

    Invalid sanitized data is quarantined before any PostgreSQL connection is
    opened. A ready manifest is required in accordance with manifest-last
    publication.
    """

    if raw.file_type != "02" or batch_id != raw.batch_id:
        raise PostgresLoadError("Type 02 preparation does not match raw lineage")

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
                prefix="northwind-type02-loader-"
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


def commit_type02_batch(
    prepared: PreparedType02Load,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
    reconciliation_validator: (
        Callable[[Mapping[str, object]], object] | None
    ) = None,
) -> LoadResult:
    """COPY, apply, reconcile, and commit Type 02 in one transaction."""

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
                _copy_and_verify_staging(cursor, prepared)
                cursor.execute(
                    "SELECT control.register_load_v2(%s, %s, %s, %s)",
                    (
                        raw.batch_id,
                        Jsonb(dict(prepared.stage_controls)),
                        prepared.row_count,
                        prepared.net_amount,
                    ),
                )
                cursor.execute(
                    "SELECT legacy.apply_instant_payment_batch(%s)",
                    (raw.batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        reporting.refresh_instant_payment_reconciliation(%s)
                    """,
                    (raw.batch_id,),
                )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "PostgreSQL Type 02 reconciliation is not MATCHED"
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
            "PostgreSQL Type 02 transaction rolled back"
        ) from exc


def load_type02_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Run the complete Type 02 loader lifecycle synchronously."""

    prepared = prepare_type02_sanitized_batch(
        batch_id,
        raw=raw,
        configuration=configuration,
    )
    result = commit_type02_batch(
        prepared,
        raw=raw,
        configuration=configuration,
    )
    finalize_committed_batch(batch_id, configuration=configuration)
    return result


def read_type02_committed_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Read and verify a committed Type 02 batch for exact recovery."""

    if raw.file_type != "02" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 02 committed recovery does not match raw lineage"
        )
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
                        "Committed Type 02 batch does not match raw lineage"
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
                        "Committed Type 02 metadata is incomplete"
                    )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=batch_id,
                )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Cannot read committed Type 02 batch for recovery"
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


def _download_and_validate(
    sftp: Any,
    remote_directory: str,
    temporary_root: Path,
    *,
    batch_id: str,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType02Load:
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
        or manifest["file_type"]["number"] != "02"
        or manifest["source_lineage"]["raw_file"] != raw.filename
        or manifest["source_lineage"]["raw_sha256"] != raw.sha256
        or manifest["source_lineage"]["manifest_sha256"]
        != raw.manifest_sha256
    ):
        raise PostgresLoadError(
            "Type 02 sanitized lineage does not match the raw batch"
        )

    csv_filename = manifest["csv_file"]["name"]
    csv_path = temporary_root / csv_filename
    checksum_path = temporary_root / f"{csv_filename}.sha256"
    sftp.get(f"{remote_directory}/{csv_filename}", str(csv_path))
    sftp.get(
        f"{remote_directory}/{csv_filename}.sha256",
        str(checksum_path),
    )
    try:
        csv_bytes = csv_path.read_bytes()
        checksum_bytes = checksum_path.read_bytes()
    except OSError as exc:
        raise PostgresLoadError(
            "Type 02 sanitized bundle is incomplete"
        ) from exc
    csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
    checksum = CHECKSUM_PATTERN.fullmatch(checksum_bytes)
    if (
        csv_sha256 != manifest["csv_file"]["sha256"]
        or len(csv_bytes) != manifest["csv_file"]["size_bytes"]
        or checksum is None
        or checksum.group("digest").decode("ascii") != csv_sha256
        or checksum.group("filename").decode("ascii") != csv_filename
    ):
        raise PostgresLoadError("Type 02 sanitized CSV integrity failed")

    stage_controls = _parse_csv(
        csv_bytes,
        batch_id=batch_id,
        source_filename=raw.filename,
    )
    if (
        manifest["csv_file"]["row_count"] != stage_controls["row_count"]
        or manifest["stage_controls"] != stage_controls
        or raw.source_controls.get("event_count")
        != stage_controls["row_count"]
        or raw.source_controls.get("credit_amount")
        != stage_controls["credit_amount"]
        or raw.source_controls.get("debit_amount")
        != stage_controls["debit_amount"]
        or raw.source_controls.get("net_amount")
        != stage_controls["net_amount"]
    ):
        raise PostgresLoadError(
            "Type 02 CSV controls do not match source controls"
        )

    return PreparedType02Load(
        batch_id=batch_id,
        raw_filename=raw.filename,
        raw_sha256=raw.sha256,
        raw_manifest_sha256=raw.manifest_sha256,
        source_controls=raw.source_controls,
        csv_filename=csv_filename,
        csv_sha256=csv_sha256,
        csv_size_bytes=len(csv_bytes),
        stage_controls=stage_controls,
        csv_bytes=csv_bytes,
    )


def _parse_csv(
    content: bytes,
    *,
    batch_id: str,
    source_filename: str,
) -> dict[str, int | str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PostgresLoadError("Type 02 CSV is not strict UTF-8") from exc
    if (
        text.startswith("\ufeff")
        or not text.endswith("\n")
        or "\r" in text
        or "\x00" in text
    ):
        raise PostgresLoadError("Type 02 CSV transport is invalid")

    source_match = SOURCE_FILENAME.fullmatch(source_filename)
    if source_match is None or source_match.group("batch") != batch_id:
        raise PostgresLoadError("Type 02 source filename is inconsistent")
    file_date = datetime.strptime(
        source_match.group("date"),
        "%Y%m%d",
    ).date()

    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise PostgresLoadError(
                "Sanitized CSV header does not match Type 02"
            )

        row_count = 0
        credit = Decimal("0.00")
        debit = Decimal("0.00")
        net = Decimal("0.00")
        returned_count = 0
        end_to_end_ids: set[str] = set()
        transaction_ids: set[str] = set()
        expected_record_number = 2
        for row in reader:
            _validate_row(
                row,
                batch_id=batch_id,
                source_filename=source_filename,
                file_date=file_date,
                expected_record_number=expected_record_number,
                end_to_end_ids=end_to_end_ids,
                transaction_ids=transaction_ids,
            )
            amount = Decimal(row["amount_brl"])
            row_count += 1
            expected_record_number += 1
            net += amount
            if row["direction"] == "C":
                credit += amount
            else:
                debit += abs(amount)
            if row["status"] == "RETURNED":
                returned_count += 1
    except csv.Error as exc:
        raise PostgresLoadError("Type 02 CSV quoting is invalid") from exc

    if row_count < 1 or row_count > 10_000:
        raise PostgresLoadError("Type 02 CSV row count is outside bounds")
    return {
        "currency": "BRL",
        "row_count": row_count,
        "credit_amount": format(credit, ".2f"),
        "debit_amount": format(debit, ".2f"),
        "net_amount": format(net, ".2f"),
        "returned_count": returned_count,
    }


def _validate_row(
    row: dict[str, str],
    *,
    batch_id: str,
    source_filename: str,
    file_date: date,
    expected_record_number: int,
    end_to_end_ids: set[str],
    transaction_ids: set[str],
) -> None:
    try:
        record_number = int(row["source_record_number"])
        amount = Decimal(row["amount_brl"])
        event_timestamp = datetime.fromisoformat(row["event_timestamp"])
    except (InvalidOperation, ValueError) as exc:
        raise PostgresLoadError(
            "Type 02 CSV contains an invalid typed field"
        ) from exc

    description = row["description"]
    end_to_end_id = row["end_to_end_id"]
    transaction_id = row["transaction_id"]
    return_code = row["return_code"]
    if (
        row["batch_id"] != batch_id
        or row["source_file"] != source_filename
        or record_number != expected_record_number
        or END_TO_END_ID.fullmatch(end_to_end_id) is None
        or end_to_end_id in end_to_end_ids
        or TRANSACTION_ID.fullmatch(transaction_id) is None
        or transaction_id in transaction_ids
        or DOCUMENT_TOKEN.fullmatch(row["payer_document_token"]) is None
        or DOCUMENT_MASK.fullmatch(row["payer_document_masked"]) is None
        or DOCUMENT_TOKEN.fullmatch(row["payee_document_token"]) is None
        or DOCUMENT_MASK.fullmatch(row["payee_document_masked"]) is None
        or TIMESTAMP.fullmatch(row["event_timestamp"]) is None
        or row["event_timestamp"].endswith(("+00:00", "-00:00"))
        or event_timestamp.tzinfo is None
        or event_timestamp.astimezone(SAO_PAULO).date() != file_date
        or MONEY.fullmatch(row["amount_brl"]) is None
        or row["amount_brl"] == "-0.00"
        or not amount.is_finite()
        or amount == Decimal("0.00")
        or (
            row["direction"] == "C"
            and amount <= Decimal("0.00")
        )
        or (
            row["direction"] == "D"
            and amount >= Decimal("0.00")
        )
        or row["direction"] not in {"C", "D"}
        or row["status"] not in {"SETTLED", "RETURNED"}
        or (
            row["status"] == "SETTLED"
            and return_code != ""
        )
        or (
            row["status"] == "RETURNED"
            and RETURN_CODE.fullmatch(return_code) is None
        )
        or not _safe_description(description)
    ):
        raise PostgresLoadError("Type 02 CSV row violates its contract")
    end_to_end_ids.add(end_to_end_id)
    transaction_ids.add(transaction_id)


def _safe_description(value: str) -> bool:
    if (
        not value
        or len(value) > 80
        or unicodedata.normalize("NFC", value) != value
        or value[0] in "=+-@"
        or ASCII_LONG_DIGIT_RUN.search(value) is not None
    ):
        return False
    return not any(
        ord(character) < 32
        or 127 <= ord(character) <= 159
        or character in BIDI_CONTROLS
        for character in value
    )


def _validate_prepared_lineage(
    prepared: PreparedType02Load,
    *,
    raw: PublishedRaw,
) -> None:
    if (
        raw.file_type != "02"
        or prepared.batch_id != raw.batch_id
        or prepared.raw_filename != raw.filename
        or prepared.raw_sha256 != raw.sha256
        or prepared.raw_manifest_sha256 != raw.manifest_sha256
        or dict(prepared.source_controls) != dict(raw.source_controls)
        or prepared.row_count != raw.source_count
        or prepared.net_amount != raw.source_net_amount
        or hashlib.sha256(prepared.csv_bytes).hexdigest()
        != prepared.csv_sha256
        or len(prepared.csv_bytes) != prepared.csv_size_bytes
    ):
        raise PostgresLoadError(
            "Prepared Type 02 data no longer matches raw lineage"
        )


def _copy_and_verify_staging(
    cursor: psycopg.Cursor[Any],
    prepared: PreparedType02Load,
) -> None:
    cursor.execute(
        """
        CREATE TEMPORARY TABLE type02_copy_buffer (
            LIKE staging.instant_payment_event INCLUDING ALL
        ) ON COMMIT DROP
        """
    )
    with cursor.copy(
        "COPY type02_copy_buffer ("
        + COPY_COLUMNS
        + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ) as copy:
        copy.write(prepared.csv_bytes)

    cursor.execute(
        """
        INSERT INTO staging.instant_payment_event
        SELECT * FROM type02_copy_buffer
        ON CONFLICT (batch_id, source_record_number) DO NOTHING
        """
    )
    cursor.execute(
        """
        SELECT
            count(*),
            coalesce(
                sum(amount_brl) FILTER (WHERE direction = 'C'),
                0.00
            ),
            coalesce(
                sum(abs(amount_brl)) FILTER (WHERE direction = 'D'),
                0.00
            ),
            coalesce(sum(amount_brl), 0.00),
            count(*) FILTER (WHERE status = 'RETURNED')
          FROM staging.instant_payment_event
         WHERE batch_id = %s
        """,
        (prepared.batch_id,),
    )
    controls_row = cursor.fetchone()
    if controls_row is None:
        raise PostgresLoadError(
            "Type 02 PostgreSQL staging controls are unavailable"
        )
    count, credit, debit, net, returned = controls_row
    expected = prepared.stage_controls
    if (
        count != expected["row_count"]
        or format(credit, ".2f") != expected["credit_amount"]
        or format(debit, ".2f") != expected["debit_amount"]
        or format(net, ".2f") != expected["net_amount"]
        or returned != expected["returned_count"]
    ):
        raise PostgresLoadError(
            "Type 02 PostgreSQL staging controls changed"
        )

    cursor.execute(
        """
        SELECT EXISTS (
            (
                SELECT * FROM type02_copy_buffer
                EXCEPT
                SELECT *
                  FROM staging.instant_payment_event
                 WHERE batch_id = %s
            )
            UNION ALL
            (
                SELECT *
                  FROM staging.instant_payment_event
                 WHERE batch_id = %s
                EXCEPT
                SELECT * FROM type02_copy_buffer
            )
        )
        """,
        (prepared.batch_id, prepared.batch_id),
    )
    if cursor.fetchone() != (False,):
        raise PostgresLoadError(
            "Type 02 staging row identity changed on replay"
        )


def _read_database_results(
    cursor: psycopg.Cursor[Any],
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
            source_credit_amount,
            staged_credit_amount,
            applied_credit_amount,
            source_debit_amount,
            staged_debit_amount,
            applied_debit_amount,
            source_net_amount,
            staged_net_amount,
            applied_net_amount,
            source_returned_count,
            staged_returned_count,
            applied_returned_count,
            count_delta,
            credit_amount_delta,
            debit_amount_delta,
            net_amount_delta,
            returned_count_delta,
            reject_count,
            status
          FROM reporting.instant_payment_reconciliation
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    report = cursor.fetchone()
    if report is None:
        raise PostgresLoadError(
            "Type 02 reconciliation produced no report"
        )
    money_indexes = frozenset({5, 6, 7, 8, 9, 10, 11, 12, 13, 18, 19, 20})
    names = (
        "batch_id",
        "currency",
        "source_count",
        "staged_count",
        "applied_count",
        "source_credit_amount",
        "staged_credit_amount",
        "applied_credit_amount",
        "source_debit_amount",
        "staged_debit_amount",
        "applied_debit_amount",
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "source_returned_count",
        "staged_returned_count",
        "applied_returned_count",
        "count_delta",
        "credit_amount_delta",
        "debit_amount_delta",
        "net_amount_delta",
        "returned_count_delta",
        "reject_count",
        "status",
    )
    reconciliation = {
        name: format(value, ".2f") if index in money_indexes else value
        for index, (name, value) in enumerate(zip(names, report, strict=True))
    }
    return procedure_runs, reconciliation
