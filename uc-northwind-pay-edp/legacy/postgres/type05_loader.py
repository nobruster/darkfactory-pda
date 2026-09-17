"""Validate and transactionally load Type 05 merchant-fee assessments."""

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
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from types import MappingProxyType
from typing import Any

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
    "assessment_id",
    "merchant_id",
    "merchant_tax_id_masked",
    "fee_code",
    "description",
    "gross_amount_brl",
    "rate_percent",
    "assessed_fee_brl",
    "calculated_fee_brl",
    "assessment_date",
    "rounding_mode",
)
COPY_COLUMNS = ", ".join(CSV_COLUMNS)
SOURCE_FILENAME = re.compile(
    r"NW_MERCHANT_FEES_(?P<date>[0-9]{8})_"
    r"(?P<batch>B[0-9]{15})\.csv"
)
ASSESSMENT_ID = re.compile(r"FEE[0-9]{13}")
MERCHANT_ID = re.compile(r"MER[0-9]{13}")
DOCUMENT_MASK = re.compile(r"\*{10}[0-9]{4}")
FEE_CODE = re.compile(r"[A-Z][A-Z0-9_]{1,9}")
UNSIGNED_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,11})\.[0-9]{2}")
UNSIGNED_RATE = re.compile(r"(?:0|[1-9][0-9]{0,2})\.[0-9]{3}")
DIGIT_RUN = re.compile(r"[0-9]{11}")
MAX_ROW_AMOUNT = Decimal("999999999999.99")
MAX_BATCH_AGGREGATE = Decimal("9999999999999900.00")
MAX_RATE = Decimal("100.000")
PENNY = Decimal("0.01")
BIDI_CONTROLS = frozenset(
    {
        "\u061c",
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
    }
)


@dataclass(frozen=True, slots=True)
class PreparedType05Load:
    """Fully validated Type 05 CSV awaiting one PostgreSQL transaction."""

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
        """Defensively freeze both aggregate-control mappings."""

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
        """Return the exact staged assessment count."""

        value = self.stage_controls["row_count"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PostgresLoadError("Type 05 row count is not an integer")
        return value

    @property
    def assessed_fee(self) -> str:
        """Return the canonical assessed-fee aggregate."""

        value = self.stage_controls["assessed_fee"]
        if not isinstance(value, str):
            raise PostgresLoadError(
                "Type 05 assessed fee is not canonical"
            )
        return value

    @property
    def net_amount(self) -> str:
        """Expose assessed fee through the legacy compatibility scalar."""

        return self.assessed_fee


def prepare_type05_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType05Load:
    """Claim and validate one ready Type 05 CSV without database mutation."""

    if raw.file_type != "05" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 05 preparation does not match raw lineage"
        )
    outgoing = f"/csv/outgoing/{batch_id}"
    processing = f"/csv/processing/{batch_id}"
    with connect_sftp(configuration, configuration.loader) as sftp:
        outgoing_exists = exists(sftp, outgoing)
        processing_exists = exists(sftp, processing)
        if outgoing_exists and processing_exists:
            raise PostgresLoadError(
                "Type 05 CSV exists in outgoing and processing"
            )
        if outgoing_exists:
            if not exists(sftp, f"{outgoing}/sanitized-manifest.json"):
                raise PostgresLoadError("Type 05 CSV is not ready")
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/outgoing",
                target_zone="/csv/processing",
            )
        elif not processing_exists:
            raise PostgresLoadError(
                "Type 05 sanitized batch is unavailable"
            )

        try:
            if not exists(sftp, f"{processing}/sanitized-manifest.json"):
                raise PostgresLoadError(
                    "Type 05 processing batch has no readiness manifest"
                )
            with tempfile.TemporaryDirectory(
                prefix="northwind-type05-loader-"
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


def commit_type05_batch(
    prepared: PreparedType05Load,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
    reconciliation_validator: (
        Callable[[Mapping[str, object]], object] | None
    ) = None,
) -> LoadResult:
    """COPY, apply, reconcile, validate, and commit Type 05 atomically."""

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
                        prepared.assessed_fee,
                    ),
                )
                cursor.execute(
                    """
                    SELECT legacy.apply_merchant_fee_assessment_batch(%s)
                    """,
                    (raw.batch_id,),
                )
                cursor.execute(
                    """
                    SELECT reporting.refresh_merchant_fee_reconciliation(%s)
                    """,
                    (raw.batch_id,),
                )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "PostgreSQL Type 05 reconciliation is not MATCHED"
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
            net_amount=prepared.assessed_fee,
            procedure_runs=procedure_runs,
            reconciliation=reconciliation,
        )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "PostgreSQL Type 05 transaction rolled back"
        ) from exc


def load_type05_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Run the complete synchronous Type 05 loader lifecycle."""

    prepared = prepare_type05_sanitized_batch(
        batch_id,
        raw=raw,
        configuration=configuration,
    )
    result = commit_type05_batch(
        prepared,
        raw=raw,
        configuration=configuration,
    )
    finalize_committed_batch(batch_id, configuration=configuration)
    return result


def read_type05_committed_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Read and fully verify an already committed Type 05 batch."""

    if raw.file_type != "05" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 05 committed recovery does not match raw lineage"
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
                        "Committed Type 05 batch does not match raw lineage"
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
                    SELECT
                        staged_count,
                        staged_net_amount,
                        stage_controls,
                        status
                      FROM control.loads
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                load = cursor.fetchone()
                if (
                    csv_file is None
                    or csv_file[0]
                    != raw.filename.removesuffix(".csv")
                    + "_SANITIZED.csv"
                    or load is None
                    or load[3] != "loaded"
                ):
                    raise PostgresLoadError(
                        "Committed Type 05 metadata is incomplete"
                    )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=batch_id,
                )
                expected_stage_controls: dict[str, int | str] = {
                    "assessed_fee": str(
                        reconciliation["staged_assessed_fee"]
                    ),
                    "calculated_fee": str(
                        reconciliation["staged_calculated_fee"]
                    ),
                    "currency": "BRL",
                    "gross_amount": str(
                        reconciliation["staged_gross_amount"]
                    ),
                    "row_count": int(reconciliation["staged_count"]),
                }
                if (
                    reconciliation["status"] != "MATCHED"
                    or load[0] != expected_stage_controls["row_count"]
                    or format(load[1], ".2f")
                    != expected_stage_controls["assessed_fee"]
                    or not isinstance(load[2], Mapping)
                    or dict(load[2]) != expected_stage_controls
                ):
                    raise PostgresLoadError(
                        "Committed Type 05 controls are inconsistent"
                    )
    except PostgresLoadError:
        raise
    except (psycopg.Error, TypeError, ValueError) as exc:
        raise PostgresLoadError(
            "Cannot read committed Type 05 batch for recovery"
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
) -> PreparedType05Load:
    manifest_path = temporary_root / "sanitized-manifest.json"
    sftp.get(
        f"{remote_directory}/sanitized-manifest.json",
        str(manifest_path),
    )
    try:
        manifest = json.loads(manifest_path.read_bytes())
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
            "Type 05 sanitized manifest violates its schema"
        ) from exc
    if (
        manifest["batch_id"] != batch_id
        or manifest["file_type"]["number"] != "05"
        or manifest["source_lineage"]["raw_file"] != raw.filename
        or manifest["source_lineage"]["raw_sha256"] != raw.sha256
        or manifest["source_lineage"]["manifest_sha256"]
        != raw.manifest_sha256
    ):
        raise PostgresLoadError(
            "Type 05 sanitized lineage does not match raw input"
        )

    csv_filename = manifest["csv_file"]["name"]
    expected_filename = (
        raw.filename.removesuffix(".csv") + "_SANITIZED.csv"
    )
    if csv_filename != expected_filename:
        raise PostgresLoadError(
            "Type 05 sanitized filename does not match raw input"
        )
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
            "Type 05 sanitized bundle is incomplete"
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
        raise PostgresLoadError("Type 05 sanitized CSV integrity failed")

    stage_controls = _parse_csv(
        csv_bytes,
        batch_id=batch_id,
        source_filename=raw.filename,
    )
    if (
        manifest["csv_file"]["row_count"] != stage_controls["row_count"]
        or manifest["stage_controls"] != stage_controls
        or dict(raw.source_controls) != stage_controls
    ):
        raise PostgresLoadError(
            "Type 05 CSV controls do not match source controls"
        )

    return PreparedType05Load(
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
    """Parse strict normalized bytes and independently recompute controls."""

    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PostgresLoadError("Type 05 CSV is not strict UTF-8") from exc
    if (
        len(content) > 10_000_000
        or text.startswith("\ufeff")
        or unicodedata.normalize("NFC", text) != text
        or not text.endswith("\n")
        or "\r" in text
        or "\x00" in text
        or "\n\n" in text
    ):
        raise PostgresLoadError("Type 05 CSV transport is invalid")
    source_match = SOURCE_FILENAME.fullmatch(source_filename)
    if source_match is None or source_match.group("batch") != batch_id:
        raise PostgresLoadError("Type 05 source filename is inconsistent")
    try:
        source_date = date(
            int(source_match.group("date")[0:4]),
            int(source_match.group("date")[4:6]),
            int(source_match.group("date")[6:8]),
        )
    except ValueError as exc:
        raise PostgresLoadError(
            "Type 05 source filename date is invalid"
        ) from exc

    canonical_rows: list[list[str]] = []
    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise PostgresLoadError(
                "Sanitized CSV header does not match Type 05"
            )
        row_count = 0
        gross = Decimal("0.00")
        assessed = Decimal("0.00")
        calculated = Decimal("0.00")
        assessment_ids: set[str] = set()
        for row in reader:
            if any(
                not isinstance(row.get(name), str)
                for name in CSV_COLUMNS
            ) or set(row) != set(CSV_COLUMNS):
                raise PostgresLoadError(
                    "Type 05 CSV row has missing or extra fields"
                )
            typed = {name: str(row[name]) for name in CSV_COLUMNS}
            row_gross, row_assessed, row_calculated = _validate_row(
                typed,
                batch_id=batch_id,
                source_filename=source_filename,
                source_date=source_date,
                expected_record_number=row_count + 2,
                assessment_ids=assessment_ids,
            )
            canonical_rows.append([typed[name] for name in CSV_COLUMNS])
            gross += row_gross
            assessed += row_assessed
            calculated += row_calculated
            assessment_ids.add(typed["assessment_id"])
            row_count += 1
    except csv.Error as exc:
        raise PostgresLoadError("Type 05 CSV quoting is invalid") from exc

    canonical = io.StringIO(newline="")
    writer = csv.writer(
        canonical,
        delimiter=",",
        quotechar='"',
        doublequote=True,
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(CSV_COLUMNS)
    writer.writerows(canonical_rows)
    if canonical.getvalue().encode("utf-8") != content:
        raise PostgresLoadError("Type 05 CSV is not canonically encoded")
    if (
        text.count("\n") != row_count + 1
        or not 1 <= row_count <= 10_000
        or gross <= Decimal("0.00")
        or gross > MAX_BATCH_AGGREGATE
        or assessed < Decimal("0.00")
        or assessed > MAX_BATCH_AGGREGATE
        or calculated < Decimal("0.00")
        or calculated > MAX_BATCH_AGGREGATE
        or assessed != calculated
    ):
        raise PostgresLoadError("Type 05 CSV controls are outside bounds")
    return {
        "assessed_fee": format(assessed, ".2f"),
        "calculated_fee": format(calculated, ".2f"),
        "currency": "BRL",
        "gross_amount": format(gross, ".2f"),
        "row_count": row_count,
    }


def _validate_row(
    row: Mapping[str, str],
    *,
    batch_id: str,
    source_filename: str,
    source_date: date,
    expected_record_number: int,
    assessment_ids: set[str],
) -> tuple[Decimal, Decimal, Decimal]:
    try:
        record_number = int(row["source_record_number"])
        assessment_date = date.fromisoformat(row["assessment_date"])
        gross = _money(row["gross_amount_brl"])
        rate = _rate(row["rate_percent"])
        assessed = _money(row["assessed_fee_brl"])
        calculated = _money(row["calculated_fee_brl"])
    except (InvalidOperation, ValueError) as exc:
        raise PostgresLoadError(
            "Type 05 CSV contains an invalid typed field"
        ) from exc
    independent = (gross * rate / Decimal("100")).quantize(
        PENNY,
        rounding=ROUND_HALF_UP,
    )
    if (
        row["batch_id"] != batch_id
        or row["source_file"] != source_filename
        or row["source_record_number"] != str(record_number)
        or record_number != expected_record_number
        or not 2 <= record_number <= 10_001
        or ASSESSMENT_ID.fullmatch(row["assessment_id"]) is None
        or row["assessment_id"] in assessment_ids
        or MERCHANT_ID.fullmatch(row["merchant_id"]) is None
        or DOCUMENT_MASK.fullmatch(row["merchant_tax_id_masked"]) is None
        or FEE_CODE.fullmatch(row["fee_code"]) is None
        or not _valid_description(row["description"])
        or gross <= Decimal("0.00")
        or rate <= Decimal("0.000")
        or rate > MAX_RATE
        or assessed < Decimal("0.00")
        or calculated < Decimal("0.00")
        or assessed != calculated
        or calculated != independent
        or assessment_date != source_date
        or assessment_date.isoformat() != row["assessment_date"]
        or row["rounding_mode"] != "HALF_UP"
    ):
        raise PostgresLoadError("Type 05 CSV row violates its contract")
    return gross, assessed, calculated


def _valid_description(value: str) -> bool:
    return (
        unicodedata.normalize("NFC", value) == value
        and 1 <= len(value) <= 80
        and value[0] not in "=+-@"
        and DIGIT_RUN.search(value) is None
        and all(
            not (
                ord(character) <= 0x1F
                or 0x7F <= ord(character) <= 0x9F
                or character in BIDI_CONTROLS
            )
            for character in value
        )
    )


def _money(value: str) -> Decimal:
    if UNSIGNED_MONEY.fullmatch(value) is None:
        raise InvalidOperation
    amount = Decimal(value)
    if not amount.is_finite() or amount > MAX_ROW_AMOUNT:
        raise InvalidOperation
    return amount


def _rate(value: str) -> Decimal:
    if UNSIGNED_RATE.fullmatch(value) is None:
        raise InvalidOperation
    rate = Decimal(value)
    if not rate.is_finite() or rate > MAX_RATE:
        raise InvalidOperation
    return rate


def _validate_prepared_lineage(
    prepared: PreparedType05Load,
    *,
    raw: PublishedRaw,
) -> None:
    if raw.file_type != "05":
        raise PostgresLoadError(
            "Prepared Type 05 data no longer matches raw lineage"
        )
    expected_csv_filename = (
        raw.filename.removesuffix(".csv") + "_SANITIZED.csv"
    )
    recomputed_stage_controls = _parse_csv(
        prepared.csv_bytes,
        batch_id=raw.batch_id,
        source_filename=raw.filename,
    )
    if (
        prepared.batch_id != raw.batch_id
        or prepared.raw_filename != raw.filename
        or prepared.raw_sha256 != raw.sha256
        or prepared.raw_manifest_sha256 != raw.manifest_sha256
        or dict(prepared.source_controls) != dict(raw.source_controls)
        or dict(prepared.source_controls) != recomputed_stage_controls
        or prepared.csv_filename != expected_csv_filename
        or dict(prepared.stage_controls) != recomputed_stage_controls
        or prepared.row_count != raw.source_count
        or prepared.assessed_fee != raw.source_net_amount
        or hashlib.sha256(prepared.csv_bytes).hexdigest()
        != prepared.csv_sha256
        or len(prepared.csv_bytes) != prepared.csv_size_bytes
    ):
        raise PostgresLoadError(
            "Prepared Type 05 data no longer matches raw lineage"
        )


def _copy_and_verify_staging(
    cursor: psycopg.Cursor[Any],
    prepared: PreparedType05Load,
) -> None:
    cursor.execute(
        """
        CREATE TEMPORARY TABLE type05_copy_buffer (
            LIKE staging.merchant_fee_assessment INCLUDING ALL
        ) ON COMMIT DROP
        """
    )
    with cursor.copy(
        "COPY type05_copy_buffer ("
        + COPY_COLUMNS
        + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ) as copy:
        copy.write(prepared.csv_bytes)
    cursor.execute(
        """
        INSERT INTO staging.merchant_fee_assessment
        SELECT * FROM type05_copy_buffer
        ON CONFLICT (batch_id, assessment_id) DO NOTHING
        """
    )
    cursor.execute(
        """
        SELECT
            count(*),
            coalesce(sum(gross_amount_brl), 0.00),
            coalesce(sum(assessed_fee_brl), 0.00),
            coalesce(sum(calculated_fee_brl), 0.00)
          FROM staging.merchant_fee_assessment
         WHERE batch_id = %s
        """,
        (prepared.batch_id,),
    )
    controls = cursor.fetchone()
    if controls is None:
        raise PostgresLoadError(
            "Type 05 PostgreSQL staging controls are unavailable"
        )
    row_count, gross, assessed, calculated = controls
    expected = prepared.stage_controls
    if (
        row_count != expected["row_count"]
        or format(gross, ".2f") != expected["gross_amount"]
        or format(assessed, ".2f") != expected["assessed_fee"]
        or format(calculated, ".2f") != expected["calculated_fee"]
    ):
        raise PostgresLoadError(
            "Type 05 PostgreSQL staging controls changed"
        )
    cursor.execute(
        """
        SELECT EXISTS (
            (
                SELECT * FROM type05_copy_buffer
                EXCEPT
                SELECT *
                  FROM staging.merchant_fee_assessment
                 WHERE batch_id = %s
            )
            UNION ALL
            (
                SELECT *
                  FROM staging.merchant_fee_assessment
                 WHERE batch_id = %s
                EXCEPT
                SELECT * FROM type05_copy_buffer
            )
        )
        """,
        (prepared.batch_id, prepared.batch_id),
    )
    if cursor.fetchone() != (False,):
        raise PostgresLoadError(
            "Type 05 staging row identity changed on replay"
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
            source_gross_amount,
            staged_gross_amount,
            applied_gross_amount,
            source_assessed_fee,
            staged_assessed_fee,
            applied_assessed_fee,
            source_calculated_fee,
            staged_calculated_fee,
            applied_calculated_fee,
            count_delta,
            gross_amount_delta,
            assessed_fee_delta,
            calculated_fee_delta,
            assessment_calculation_delta,
            reject_count,
            status
          FROM reporting.merchant_fee_reconciliation
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    report = cursor.fetchone()
    if report is None:
        raise PostgresLoadError(
            "Type 05 reconciliation produced no report"
        )
    names = (
        "batch_id",
        "currency",
        "source_count",
        "staged_count",
        "applied_count",
        "source_gross_amount",
        "staged_gross_amount",
        "applied_gross_amount",
        "source_assessed_fee",
        "staged_assessed_fee",
        "applied_assessed_fee",
        "source_calculated_fee",
        "staged_calculated_fee",
        "applied_calculated_fee",
        "count_delta",
        "gross_amount_delta",
        "assessed_fee_delta",
        "calculated_fee_delta",
        "assessment_calculation_delta",
        "reject_count",
        "status",
    )
    money_indexes = frozenset(
        {
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            15,
            16,
            17,
            18,
        }
    )
    reconciliation = {
        name: format(value, ".2f") if index in money_indexes else value
        for index, (name, value) in enumerate(zip(names, report, strict=True))
    }
    return procedure_runs, reconciliation
