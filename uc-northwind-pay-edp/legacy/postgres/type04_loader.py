"""Validate and transactionally load Type 04 TED transfer movements."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
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
    "movement_id",
    "original_transfer_id",
    "movement_kind",
    "movement_ts",
    "amount_brl",
    "payer_account_token",
    "payer_tax_id_masked",
    "beneficiary_account_token",
    "beneficiary_tax_id_masked",
    "beneficiary_ispb",
    "purpose_code",
    "status_code",
    "return_reason_code",
)
COPY_COLUMNS = ", ".join(CSV_COLUMNS)
SOURCE_FILENAME = re.compile(
    r"NW_TED_SETTLEMENT_(?P<date>[0-9]{8})_"
    r"(?P<batch>B[0-9]{15})\.dat"
)
MOVEMENT_ID = re.compile(r"[A-Z][A-Z0-9]{15}")
ACCOUNT_TOKEN = re.compile(r"tedacct_[0-9a-f]{24}")
DOCUMENT_MASK = re.compile(r"(?:\*{7}|\*{10})[0-9]{4}")
ISPB = re.compile(r"[0-9]{8}")
PURPOSE = re.compile(r"[A-Z][A-Z0-9_]{1,9}")
REASON_CODE = re.compile(r"[A-Z][A-Z0-9]{4}")
SIGNED_MONEY = re.compile(r"-?(?:0|[1-9][0-9]{0,11})\.[0-9]{2}")
MAX_AMOUNT = Decimal("999999999999.99")
SOURCE_ZONE = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True, slots=True)
class PreparedType04Load:
    """Fully validated Type 04 CSV awaiting one PostgreSQL transaction."""

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
        value = self.stage_controls["row_count"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise PostgresLoadError("Type 04 row count is not an integer")
        return value

    @property
    def net_amount(self) -> str:
        value = self.stage_controls["net_amount"]
        if not isinstance(value, str):
            raise PostgresLoadError("Type 04 net amount is not canonical")
        return value


def prepare_type04_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType04Load:
    """Claim and validate one ready Type 04 CSV without database mutation."""

    if raw.file_type != "04" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 04 preparation does not match raw lineage"
        )
    outgoing = f"/csv/outgoing/{batch_id}"
    processing = f"/csv/processing/{batch_id}"
    with connect_sftp(configuration, configuration.loader) as sftp:
        outgoing_exists = exists(sftp, outgoing)
        processing_exists = exists(sftp, processing)
        if outgoing_exists and processing_exists:
            raise PostgresLoadError(
                "Type 04 CSV exists in outgoing and processing"
            )
        if outgoing_exists:
            if not exists(sftp, f"{outgoing}/sanitized-manifest.json"):
                raise PostgresLoadError("Type 04 CSV is not ready")
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/outgoing",
                target_zone="/csv/processing",
            )
        elif not processing_exists:
            raise PostgresLoadError(
                "Type 04 sanitized batch is unavailable"
            )

        try:
            if not exists(sftp, f"{processing}/sanitized-manifest.json"):
                raise PostgresLoadError(
                    "Type 04 processing batch has no readiness manifest"
                )
            with tempfile.TemporaryDirectory(
                prefix="northwind-type04-loader-"
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


def commit_type04_batch(
    prepared: PreparedType04Load,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
    reconciliation_validator: (
        Callable[[Mapping[str, object]], object] | None
    ) = None,
) -> LoadResult:
    """COPY, apply, reconcile, validate, and commit Type 04 atomically."""

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
                    "SELECT legacy.apply_ted_transfer_batch(%s)",
                    (raw.batch_id,),
                )
                cursor.execute(
                    "SELECT reporting.refresh_ted_transfer_reconciliation(%s)",
                    (raw.batch_id,),
                )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "PostgreSQL Type 04 reconciliation is not MATCHED"
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
            "PostgreSQL Type 04 transaction rolled back"
        ) from exc


def load_type04_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Run the complete synchronous Type 04 loader lifecycle."""

    prepared = prepare_type04_sanitized_batch(
        batch_id,
        raw=raw,
        configuration=configuration,
    )
    result = commit_type04_batch(
        prepared,
        raw=raw,
        configuration=configuration,
    )
    finalize_committed_batch(batch_id, configuration=configuration)
    return result


def read_type04_committed_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Read and verify an already committed Type 04 batch for recovery."""

    if raw.file_type != "04" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 04 committed recovery does not match raw lineage"
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
                        "Committed Type 04 batch does not match raw lineage"
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
                        "Committed Type 04 metadata is incomplete"
                    )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "Committed Type 04 reconciliation is not MATCHED"
                    )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Cannot read committed Type 04 batch for recovery"
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
) -> PreparedType04Load:
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
            "Type 04 sanitized manifest violates its schema"
        ) from exc
    if (
        manifest["batch_id"] != batch_id
        or manifest["file_type"]["number"] != "04"
        or manifest["source_lineage"]["raw_file"] != raw.filename
        or manifest["source_lineage"]["raw_sha256"] != raw.sha256
        or manifest["source_lineage"]["manifest_sha256"]
        != raw.manifest_sha256
    ):
        raise PostgresLoadError(
            "Type 04 sanitized lineage does not match raw input"
        )

    csv_filename = manifest["csv_file"]["name"]
    if csv_filename != raw.filename.removesuffix(".dat") + ".csv":
        raise PostgresLoadError(
            "Type 04 sanitized filename does not match raw input"
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
            "Type 04 sanitized bundle is incomplete"
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
        raise PostgresLoadError("Type 04 sanitized CSV integrity failed")

    stage_controls = _parse_csv(
        csv_bytes,
        batch_id=batch_id,
        source_filename=raw.filename,
    )
    expected_source_controls: dict[str, int | str] = {
        "currency": "BRL",
        "gross_amount": stage_controls["gross_amount"],
        "net_amount": stage_controls["net_amount"],
        "return_amount": stage_controls["return_amount"],
        "return_count": stage_controls["return_count"],
        "transfer_count": stage_controls["transfer_count"],
    }
    if (
        manifest["csv_file"]["row_count"] != stage_controls["row_count"]
        or manifest["stage_controls"] != stage_controls
        or dict(raw.source_controls) != expected_source_controls
    ):
        raise PostgresLoadError(
            "Type 04 CSV controls do not match source controls"
        )

    return PreparedType04Load(
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
    """Parse strict sanitized bytes and independently recompute controls."""

    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PostgresLoadError("Type 04 CSV is not strict UTF-8") from exc
    if (
        len(content) > 10_000_000
        or text.startswith("\ufeff")
        or not text.endswith("\n")
        or "\r" in text
        or "\x00" in text
        or "\n\n" in text
    ):
        raise PostgresLoadError("Type 04 CSV transport is invalid")
    source_match = SOURCE_FILENAME.fullmatch(source_filename)
    if source_match is None or source_match.group("batch") != batch_id:
        raise PostgresLoadError("Type 04 source filename is inconsistent")
    try:
        source_date = datetime.strptime(
            source_match.group("date"),
            "%Y%m%d",
        ).date()
    except ValueError as exc:
        raise PostgresLoadError(
            "Type 04 source filename date is invalid"
        ) from exc

    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise PostgresLoadError(
                "Sanitized CSV header does not match Type 04"
            )
        row_count = 0
        transfer_count = 0
        return_count = 0
        gross = Decimal("0.00")
        returned = Decimal("0.00")
        net = Decimal("0.00")
        movement_ids: set[str] = set()
        pending_return: dict[str, object] | None = None
        for row in reader:
            if any(
                not isinstance(row.get(name), str)
                for name in CSV_COLUMNS
            ) or set(row) != set(CSV_COLUMNS):
                raise PostgresLoadError(
                    "Type 04 CSV row has missing or extra fields"
                )
            typed = {name: str(row[name]) for name in CSV_COLUMNS}
            record_number, movement_ts, amount = _validate_common_row(
                typed,
                batch_id=batch_id,
                source_filename=source_filename,
                expected_record_number=row_count + 2,
                movement_ids=movement_ids,
            )
            del record_number
            if typed["movement_kind"] == "TRANSFER":
                if pending_return is not None:
                    raise PostgresLoadError(
                        "Type 04 RT transfer has no immediate return"
                    )
                _validate_transfer_row(
                    typed,
                    movement_ts=movement_ts,
                    amount=amount,
                    source_date=source_date,
                )
                transfer_count += 1
                gross += amount
                if typed["status_code"] == "RT":
                    pending_return = {
                        "amount": amount,
                        "movement_id": typed["movement_id"],
                        "movement_ts": movement_ts,
                        "payer_account_token": typed[
                            "payer_account_token"
                        ],
                        "payer_tax_id_masked": typed[
                            "payer_tax_id_masked"
                        ],
                        "beneficiary_account_token": typed[
                            "beneficiary_account_token"
                        ],
                        "beneficiary_tax_id_masked": typed[
                            "beneficiary_tax_id_masked"
                        ],
                        "beneficiary_ispb": typed["beneficiary_ispb"],
                        "purpose_code": typed["purpose_code"],
                        "status_code": typed["status_code"],
                    }
            else:
                if pending_return is None:
                    raise PostgresLoadError(
                        "Type 04 return has no immediately preceding transfer"
                    )
                _validate_return_row(
                    typed,
                    movement_ts=movement_ts,
                    amount=amount,
                    pending=pending_return,
                )
                return_count += 1
                returned += amount
                pending_return = None
            net += amount
            movement_ids.add(typed["movement_id"])
            row_count += 1
    except csv.Error as exc:
        raise PostgresLoadError("Type 04 CSV quoting is invalid") from exc

    if pending_return is not None:
        raise PostgresLoadError("Type 04 RT transfer has no immediate return")
    if (
        not 1 <= transfer_count <= 10_000
        or not 0 <= return_count <= 10_000
        or row_count != transfer_count + return_count
        or not 1 <= row_count <= 20_000
        or gross <= Decimal("0.00")
        or gross > MAX_AMOUNT
        or returned > Decimal("0.00")
        or abs(returned) > MAX_AMOUNT
        or net < Decimal("0.00")
        or net > MAX_AMOUNT
    ):
        raise PostgresLoadError("Type 04 CSV controls are outside bounds")
    return {
        "currency": "BRL",
        "gross_amount": format(gross, ".2f"),
        "net_amount": format(net, ".2f"),
        "return_amount": format(returned, ".2f"),
        "return_count": return_count,
        "row_count": row_count,
        "transfer_count": transfer_count,
    }


def _validate_common_row(
    row: Mapping[str, str],
    *,
    batch_id: str,
    source_filename: str,
    expected_record_number: int,
    movement_ids: set[str],
) -> tuple[int, datetime, Decimal]:
    try:
        record_number = int(row["source_record_number"])
        movement_ts = datetime.fromisoformat(row["movement_ts"])
        amount = _money(row["amount_brl"])
    except (InvalidOperation, ValueError) as exc:
        raise PostgresLoadError(
            "Type 04 CSV contains an invalid typed field"
        ) from exc
    if movement_ts.tzinfo is None:
        raise PostgresLoadError(
            "Type 04 timestamp has no explicit numeric offset"
        )
    local = movement_ts.astimezone(SOURCE_ZONE)
    naive = movement_ts.replace(tzinfo=None)
    valid_candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=SOURCE_ZONE, fold=fold)
        if (
            candidate.astimezone(UTC)
            .astimezone(SOURCE_ZONE)
            .replace(tzinfo=None)
            == naive
        ):
            valid_candidates.append(candidate)
    expected_local = valid_candidates[0] if valid_candidates else None
    if (
        row["batch_id"] != batch_id
        or row["source_file"] != source_filename
        or row["source_record_number"] != str(record_number)
        or record_number != expected_record_number
        or not 2 <= record_number <= 20_001
        or MOVEMENT_ID.fullmatch(row["movement_id"]) is None
        or row["movement_id"] in movement_ids
        or row["movement_kind"] not in {"TRANSFER", "RETURN"}
        or movement_ts.isoformat() != row["movement_ts"]
        or local.replace(tzinfo=None) != movement_ts.replace(tzinfo=None)
        or local.utcoffset() != movement_ts.utcoffset()
        or expected_local is None
        or expected_local.utcoffset() != movement_ts.utcoffset()
        or ACCOUNT_TOKEN.fullmatch(row["payer_account_token"]) is None
        or DOCUMENT_MASK.fullmatch(row["payer_tax_id_masked"]) is None
        or ACCOUNT_TOKEN.fullmatch(
            row["beneficiary_account_token"]
        )
        is None
        or DOCUMENT_MASK.fullmatch(
            row["beneficiary_tax_id_masked"]
        )
        is None
        or ISPB.fullmatch(row["beneficiary_ispb"]) is None
        or PURPOSE.fullmatch(row["purpose_code"]) is None
        or row["status_code"] not in {"OK", "RT"}
        or abs(amount) > MAX_AMOUNT
    ):
        raise PostgresLoadError("Type 04 CSV row violates its contract")
    return record_number, movement_ts, amount


def _validate_transfer_row(
    row: Mapping[str, str],
    *,
    movement_ts: datetime,
    amount: Decimal,
    source_date: date,
) -> None:
    if (
        row["original_transfer_id"] != ""
        or row["return_reason_code"] != ""
        or amount <= Decimal("0.00")
        or movement_ts.date() != source_date
    ):
        raise PostgresLoadError(
            "Type 04 transfer row violates its contract"
        )


def _validate_return_row(
    row: Mapping[str, str],
    *,
    movement_ts: datetime,
    amount: Decimal,
    pending: Mapping[str, object],
) -> None:
    inherited_names = (
        "payer_account_token",
        "payer_tax_id_masked",
        "beneficiary_account_token",
        "beneficiary_tax_id_masked",
        "beneficiary_ispb",
        "purpose_code",
        "status_code",
    )
    transfer_amount = pending["amount"]
    transfer_timestamp = pending["movement_ts"]
    if (
        not isinstance(transfer_amount, Decimal)
        or not isinstance(transfer_timestamp, datetime)
        or row["original_transfer_id"] != pending["movement_id"]
        or REASON_CODE.fullmatch(row["return_reason_code"]) is None
        or amount >= Decimal("0.00")
        or amount != -transfer_amount
        or movement_ts <= transfer_timestamp
        or any(row[name] != pending[name] for name in inherited_names)
    ):
        raise PostgresLoadError(
            "Type 04 return row violates its inherited contract"
        )


def _money(value: str) -> Decimal:
    if SIGNED_MONEY.fullmatch(value) is None or value == "-0.00":
        raise InvalidOperation
    amount = Decimal(value)
    if not amount.is_finite():
        raise InvalidOperation
    return amount


def _validate_prepared_lineage(
    prepared: PreparedType04Load,
    *,
    raw: PublishedRaw,
) -> None:
    expected_csv_filename = raw.filename.removesuffix(".dat") + ".csv"
    recomputed_stage_controls = _parse_csv(
        prepared.csv_bytes,
        batch_id=raw.batch_id,
        source_filename=raw.filename,
    )
    if (
        raw.file_type != "04"
        or prepared.batch_id != raw.batch_id
        or prepared.raw_filename != raw.filename
        or prepared.raw_sha256 != raw.sha256
        or prepared.raw_manifest_sha256 != raw.manifest_sha256
        or dict(prepared.source_controls) != dict(raw.source_controls)
        or prepared.csv_filename != expected_csv_filename
        or dict(prepared.stage_controls) != recomputed_stage_controls
        or prepared.row_count
        != _required_row_count(raw.source_controls)
        or prepared.net_amount != raw.source_net_amount
        or hashlib.sha256(prepared.csv_bytes).hexdigest()
        != prepared.csv_sha256
        or len(prepared.csv_bytes) != prepared.csv_size_bytes
    ):
        raise PostgresLoadError(
            "Prepared Type 04 data no longer matches raw lineage"
        )


def _required_row_count(controls: Mapping[str, int | str]) -> int:
    transfer_count = controls.get("transfer_count")
    return_count = controls.get("return_count")
    if (
        not isinstance(transfer_count, int)
        or isinstance(transfer_count, bool)
        or not isinstance(return_count, int)
        or isinstance(return_count, bool)
    ):
        raise PostgresLoadError(
            "Type 04 source counts are not integers"
        )
    return transfer_count + return_count


def _copy_and_verify_staging(
    cursor: psycopg.Cursor[Any],
    prepared: PreparedType04Load,
) -> None:
    cursor.execute(
        """
        CREATE TEMPORARY TABLE type04_copy_buffer (
            LIKE staging.ted_transfer_movement INCLUDING ALL
        ) ON COMMIT DROP
        """
    )
    with cursor.copy(
        "COPY type04_copy_buffer ("
        + COPY_COLUMNS
        + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ) as copy:
        copy.write(prepared.csv_bytes)
    cursor.execute(
        """
        INSERT INTO staging.ted_transfer_movement
        SELECT * FROM type04_copy_buffer
        ON CONFLICT (batch_id, movement_id) DO NOTHING
        """
    )
    cursor.execute(
        """
        SELECT
            count(*),
            count(*) FILTER (WHERE movement_kind = 'TRANSFER'),
            count(*) FILTER (WHERE movement_kind = 'RETURN'),
            coalesce(
                sum(amount_brl) FILTER (
                    WHERE movement_kind = 'TRANSFER'
                ),
                0.00
            ),
            coalesce(
                sum(amount_brl) FILTER (
                    WHERE movement_kind = 'RETURN'
                ),
                0.00
            ),
            coalesce(sum(amount_brl), 0.00)
          FROM staging.ted_transfer_movement
         WHERE batch_id = %s
        """,
        (prepared.batch_id,),
    )
    controls = cursor.fetchone()
    if controls is None:
        raise PostgresLoadError(
            "Type 04 PostgreSQL staging controls are unavailable"
        )
    row_count, transfer_count, return_count, gross, returned, net = controls
    expected = prepared.stage_controls
    if (
        row_count != expected["row_count"]
        or transfer_count != expected["transfer_count"]
        or return_count != expected["return_count"]
        or format(gross, ".2f") != expected["gross_amount"]
        or format(returned, ".2f") != expected["return_amount"]
        or format(net, ".2f") != expected["net_amount"]
    ):
        raise PostgresLoadError(
            "Type 04 PostgreSQL staging controls changed"
        )
    cursor.execute(
        """
        SELECT EXISTS (
            (
                SELECT * FROM type04_copy_buffer
                EXCEPT
                SELECT *
                  FROM staging.ted_transfer_movement
                 WHERE batch_id = %s
            )
            UNION ALL
            (
                SELECT *
                  FROM staging.ted_transfer_movement
                 WHERE batch_id = %s
                EXCEPT
                SELECT * FROM type04_copy_buffer
            )
        )
        """,
        (prepared.batch_id, prepared.batch_id),
    )
    if cursor.fetchone() != (False,):
        raise PostgresLoadError(
            "Type 04 staging row identity changed on replay"
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
            source_transfer_count,
            staged_transfer_count,
            applied_transfer_count,
            source_return_count,
            staged_return_count,
            applied_return_count,
            source_gross_amount,
            staged_gross_amount,
            applied_gross_amount,
            source_return_amount,
            staged_return_amount,
            applied_return_amount,
            source_net_amount,
            staged_net_amount,
            applied_net_amount,
            transfer_count_delta,
            return_count_delta,
            gross_amount_delta,
            return_amount_delta,
            net_amount_delta,
            reject_count,
            status
          FROM reporting.ted_transfer_reconciliation
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    report = cursor.fetchone()
    if report is None:
        raise PostgresLoadError(
            "Type 04 reconciliation produced no report"
        )
    names = (
        "batch_id",
        "currency",
        "source_transfer_count",
        "staged_transfer_count",
        "applied_transfer_count",
        "source_return_count",
        "staged_return_count",
        "applied_return_count",
        "source_gross_amount",
        "staged_gross_amount",
        "applied_gross_amount",
        "source_return_amount",
        "staged_return_amount",
        "applied_return_amount",
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "transfer_count_delta",
        "return_count_delta",
        "gross_amount_delta",
        "return_amount_delta",
        "net_amount_delta",
        "reject_count",
        "status",
    )
    money_indexes = frozenset(
        {
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            19,
            20,
            21,
        }
    )
    reconciliation = {
        name: format(value, ".2f") if index in money_indexes else value
        for index, (name, value) in enumerate(zip(names, report, strict=True))
    }
    return procedure_runs, reconciliation
