"""Validate and transactionally load Type 03 payment-slip settlements."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
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
    "source_record_number_a",
    "source_record_number_b",
    "lot_number",
    "sequence",
    "settlement_id",
    "payment_reference_token",
    "payment_reference_last4",
    "beneficiary_token",
    "beneficiary_tax_id_type",
    "beneficiary_tax_id_masked",
    "bank_account_token",
    "bank_account_last4",
    "due_date",
    "payment_date",
    "face_amount_brl",
    "discount_brl",
    "fee_brl",
    "net_amount_brl",
    "status",
    "bank_reference",
    "client_reference",
)
COPY_COLUMNS = ", ".join(CSV_COLUMNS)
SOURCE_FILENAME = re.compile(
    r"NW_PAYMENT_SLIP_(?P<date>[0-9]{8})_"
    r"(?P<batch>B[0-9]{15})\.rem"
)
LOT_OR_SEQUENCE = re.compile(r"(?!000000)[0-9]{6}")
SETTLEMENT_ID = re.compile(r"[A-Z][A-Z0-9]{15}")
PAYMENT_REFERENCE_TOKEN = re.compile(r"payref_[0-9a-f]{24}")
PAYMENT_REFERENCE_LAST4 = re.compile(r"[0-9]{4}")
BENEFICIARY_TOKEN = re.compile(r"party_[0-9a-f]{24}")
CPF_MASK = re.compile(r"\*{7}[0-9]{4}")
CNPJ_MASK = re.compile(r"\*{10}[0-9]{4}")
ACCOUNT_TOKEN = re.compile(r"acct_[0-9a-f]{24}")
ACCOUNT_LAST4 = re.compile(r"[0-9]{4}")
SAFE_REFERENCE = re.compile(r"[A-Z][A-Z0-9]{19}")
UNSIGNED_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,15})\.[0-9]{2}")
MAX_FACE_OR_NET = Decimal("9999999999999.99")
MAX_DISCOUNT_OR_FEE = Decimal("9999999999.99")


@dataclass(frozen=True, slots=True)
class PreparedType03Load:
    """Fully validated Type 03 CSV awaiting one PostgreSQL transaction."""

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
            raise PostgresLoadError("Type 03 row count is not an integer")
        return value

    @property
    def net_amount(self) -> str:
        value = self.stage_controls["net_amount"]
        if not isinstance(value, str):
            raise PostgresLoadError("Type 03 net amount is not canonical")
        return value


def prepare_type03_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> PreparedType03Load:
    """Claim and validate one ready Type 03 CSV without database mutation."""

    if raw.file_type != "03" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 03 preparation does not match raw lineage"
        )
    outgoing = f"/csv/outgoing/{batch_id}"
    processing = f"/csv/processing/{batch_id}"
    with connect_sftp(configuration, configuration.loader) as sftp:
        outgoing_exists = exists(sftp, outgoing)
        processing_exists = exists(sftp, processing)
        if outgoing_exists and processing_exists:
            raise PostgresLoadError(
                "Type 03 CSV exists in outgoing and processing"
            )
        if outgoing_exists:
            if not exists(sftp, f"{outgoing}/sanitized-manifest.json"):
                raise PostgresLoadError("Type 03 CSV is not ready")
            move_batch(
                sftp,
                batch_id,
                source_zone="/csv/outgoing",
                target_zone="/csv/processing",
            )
        elif not processing_exists:
            raise PostgresLoadError(
                "Type 03 sanitized batch is unavailable"
            )

        try:
            if not exists(sftp, f"{processing}/sanitized-manifest.json"):
                raise PostgresLoadError(
                    "Type 03 processing batch has no readiness manifest"
                )
            with tempfile.TemporaryDirectory(
                prefix="northwind-type03-loader-"
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


def commit_type03_batch(
    prepared: PreparedType03Load,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
    reconciliation_validator: (
        Callable[[Mapping[str, object]], object] | None
    ) = None,
) -> LoadResult:
    """COPY, apply, reconcile, validate, and commit Type 03 atomically."""

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
                    """
                    SELECT legacy.apply_payment_slip_settlement_batch(%s)
                    """,
                    (raw.batch_id,),
                )
                cursor.execute(
                    """
                    SELECT reporting
                        .refresh_payment_slip_settlement_reconciliation(%s)
                    """,
                    (raw.batch_id,),
                )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                if reconciliation["status"] != "MATCHED":
                    raise PostgresLoadError(
                        "PostgreSQL Type 03 reconciliation is not MATCHED"
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
            "PostgreSQL Type 03 transaction rolled back"
        ) from exc


def load_type03_sanitized_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Run the complete synchronous Type 03 loader lifecycle."""

    prepared = prepare_type03_sanitized_batch(
        batch_id,
        raw=raw,
        configuration=configuration,
    )
    result = commit_type03_batch(
        prepared,
        raw=raw,
        configuration=configuration,
    )
    finalize_committed_batch(batch_id, configuration=configuration)
    return result


def read_type03_committed_batch(
    batch_id: str,
    *,
    raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> LoadResult:
    """Read and verify an already committed Type 03 batch for recovery."""

    if raw.file_type != "03" or batch_id != raw.batch_id:
        raise PostgresLoadError(
            "Type 03 committed recovery does not match raw lineage"
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
                        "Committed Type 03 batch does not match raw lineage"
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
                        "Committed Type 03 metadata is incomplete"
                    )
                procedure_runs, reconciliation = _read_database_results(
                    cursor,
                    batch_id=batch_id,
                )
    except PostgresLoadError:
        raise
    except psycopg.Error as exc:
        raise PostgresLoadError(
            "Cannot read committed Type 03 batch for recovery"
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
) -> PreparedType03Load:
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
            "Type 03 sanitized manifest violates its schema"
        ) from exc
    if (
        manifest["batch_id"] != batch_id
        or manifest["file_type"]["number"] != "03"
        or manifest["source_lineage"]["raw_file"] != raw.filename
        or manifest["source_lineage"]["raw_sha256"] != raw.sha256
        or manifest["source_lineage"]["manifest_sha256"]
        != raw.manifest_sha256
    ):
        raise PostgresLoadError(
            "Type 03 sanitized lineage does not match raw input"
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
            "Type 03 sanitized bundle is incomplete"
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
        raise PostgresLoadError("Type 03 sanitized CSV integrity failed")

    lot_count = _required_control_int(raw, "lot_count")
    physical_count = _required_control_int(
        raw,
        "physical_record_count",
    )
    stage_controls = _parse_csv(
        csv_bytes,
        batch_id=batch_id,
        source_filename=raw.filename,
        expected_lot_count=lot_count,
        expected_physical_record_count=physical_count,
    )
    expected_source_controls: dict[str, int | str] = {
        "currency": "BRL",
        "discount_amount": stage_controls["discount_amount"],
        "face_amount": stage_controls["face_amount"],
        "fee_amount": stage_controls["fee_amount"],
        "logical_count": stage_controls["row_count"],
        "lot_count": lot_count,
        "net_amount": stage_controls["net_amount"],
        "orphan_segment_count": stage_controls[
            "orphan_segment_count"
        ],
        "physical_record_count": physical_count,
    }
    if (
        manifest["csv_file"]["row_count"] != stage_controls["row_count"]
        or manifest["stage_controls"] != stage_controls
        or dict(raw.source_controls) != expected_source_controls
    ):
        raise PostgresLoadError(
            "Type 03 CSV controls do not match source controls"
        )

    return PreparedType03Load(
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


def _required_control_int(raw: PublishedRaw, name: str) -> int:
    value = raw.source_controls.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise PostgresLoadError(
            f"Type 03 source control is not an integer: {name}"
        )
    return value


def _parse_csv(
    content: bytes,
    *,
    batch_id: str,
    source_filename: str,
    expected_lot_count: int | None = None,
    expected_physical_record_count: int | None = None,
) -> dict[str, int | str]:
    """Parse strict sanitized bytes and independently recompute controls."""

    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PostgresLoadError("Type 03 CSV is not strict UTF-8") from exc
    if (
        len(content) > 8_000_000
        or text.startswith("\ufeff")
        or not text.endswith("\n")
        or "\r" in text
        or "\x00" in text
        or "\n\n" in text
    ):
        raise PostgresLoadError("Type 03 CSV transport is invalid")
    source_match = SOURCE_FILENAME.fullmatch(source_filename)
    if source_match is None or source_match.group("batch") != batch_id:
        raise PostgresLoadError("Type 03 source filename is inconsistent")
    try:
        source_date = datetime.strptime(
            source_match.group("date"),
            "%Y%m%d",
        ).date()
    except ValueError as exc:
        raise PostgresLoadError(
            "Type 03 source filename date is invalid"
        ) from exc

    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise PostgresLoadError(
                "Sanitized CSV header does not match Type 03"
            )

        row_count = 0
        face = Decimal("0.00")
        discount = Decimal("0.00")
        fee = Decimal("0.00")
        net = Decimal("0.00")
        settlement_ids: set[str] = set()
        lot_sequences: set[tuple[str, str]] = set()
        closed_lots: set[str] = set()
        active_lot: str | None = None
        prior_record_b: int | None = None
        lot_count = 0
        for row in reader:
            if any(
                not isinstance(row.get(name), str)
                for name in CSV_COLUMNS
            ) or set(row) != set(CSV_COLUMNS):
                raise PostgresLoadError(
                    "Type 03 CSV row has missing or extra fields"
                )
            record_a, record_b = _validate_row(
                row,
                batch_id=batch_id,
                source_filename=source_filename,
                source_date=source_date,
                settlement_ids=settlement_ids,
                lot_sequences=lot_sequences,
            )
            lot_number = row["lot_number"]
            if active_lot is None:
                expected_record_a = 3
                active_lot = lot_number
                lot_count = 1
            elif lot_number == active_lot:
                assert prior_record_b is not None
                expected_record_a = prior_record_b + 1
            else:
                if lot_number in closed_lots:
                    raise PostgresLoadError(
                        "Type 03 CSV returns to a completed lot"
                    )
                closed_lots.add(active_lot)
                active_lot = lot_number
                lot_count += 1
                assert prior_record_b is not None
                expected_record_a = prior_record_b + 3
            if record_a != expected_record_a:
                raise PostgresLoadError(
                    "Type 03 CSV physical record order is inconsistent"
                )
            prior_record_b = record_b
            row_count += 1
            face += Decimal(row["face_amount_brl"])
            discount += Decimal(row["discount_brl"])
            fee += Decimal(row["fee_brl"])
            net += Decimal(row["net_amount_brl"])
    except csv.Error as exc:
        raise PostgresLoadError("Type 03 CSV quoting is invalid") from exc

    if not 1 <= row_count <= 10_000 or prior_record_b is None:
        raise PostgresLoadError("Type 03 CSV row count is outside bounds")
    physical_record_count = prior_record_b + 2
    if (
        expected_lot_count is not None
        and lot_count != expected_lot_count
    ) or (
        expected_physical_record_count is not None
        and physical_record_count != expected_physical_record_count
    ):
        raise PostgresLoadError(
            "Type 03 CSV physical controls differ from raw input"
        )
    return {
        "currency": "BRL",
        "discount_amount": format(discount, ".2f"),
        "face_amount": format(face, ".2f"),
        "fee_amount": format(fee, ".2f"),
        "net_amount": format(net, ".2f"),
        "orphan_segment_count": 0,
        "row_count": row_count,
    }


def _validate_row(
    row: dict[str, str | None],
    *,
    batch_id: str,
    source_filename: str,
    source_date: date,
    settlement_ids: set[str],
    lot_sequences: set[tuple[str, str]],
) -> tuple[int, int]:
    values = {name: row.get(name) for name in CSV_COLUMNS}
    if any(not isinstance(value, str) for value in values.values()):
        raise PostgresLoadError("Type 03 CSV row is incomplete")
    typed = {name: str(value) for name, value in values.items()}
    try:
        record_a = int(typed["source_record_number_a"])
        record_b = int(typed["source_record_number_b"])
        due_date = date.fromisoformat(typed["due_date"])
        payment_date = date.fromisoformat(typed["payment_date"])
        face = _money(typed["face_amount_brl"])
        discount = _money(typed["discount_brl"])
        fee = _money(typed["fee_brl"])
        net = _money(typed["net_amount_brl"])
    except (InvalidOperation, ValueError) as exc:
        raise PostgresLoadError(
            "Type 03 CSV contains an invalid typed field"
        ) from exc

    lot_sequence = (typed["lot_number"], typed["sequence"])
    settlement = typed["settlement_id"]
    tax_type = typed["beneficiary_tax_id_type"]
    mask = typed["beneficiary_tax_id_masked"]
    if (
        typed["batch_id"] != batch_id
        or typed["source_file"] != source_filename
        or not 3 <= record_a <= 22_000
        or not 4 <= record_b <= 22_001
        or record_b != record_a + 1
        or LOT_OR_SEQUENCE.fullmatch(typed["lot_number"]) is None
        or LOT_OR_SEQUENCE.fullmatch(typed["sequence"]) is None
        or lot_sequence in lot_sequences
        or SETTLEMENT_ID.fullmatch(settlement) is None
        or settlement in settlement_ids
        or PAYMENT_REFERENCE_TOKEN.fullmatch(
            typed["payment_reference_token"]
        )
        is None
        or PAYMENT_REFERENCE_LAST4.fullmatch(
            typed["payment_reference_last4"]
        )
        is None
        or BENEFICIARY_TOKEN.fullmatch(typed["beneficiary_token"]) is None
        or tax_type not in {"CPF", "CNPJ"}
        or (
            tax_type == "CPF"
            and CPF_MASK.fullmatch(mask) is None
        )
        or (
            tax_type == "CNPJ"
            and CNPJ_MASK.fullmatch(mask) is None
        )
        or ACCOUNT_TOKEN.fullmatch(typed["bank_account_token"]) is None
        or ACCOUNT_LAST4.fullmatch(typed["bank_account_last4"]) is None
        or typed["due_date"] != due_date.isoformat()
        or typed["payment_date"] != payment_date.isoformat()
        or payment_date != source_date
        or payment_date > due_date
        or not Decimal("0.00") < face <= MAX_FACE_OR_NET
        or not Decimal("0.00") <= discount <= MAX_DISCOUNT_OR_FEE
        or not Decimal("0.00") <= fee <= MAX_DISCOUNT_OR_FEE
        or discount > face
        or not Decimal("0.00") <= net <= MAX_FACE_OR_NET
        or net != face - discount + fee
        or typed["status"] != "SETTLED"
        or SAFE_REFERENCE.fullmatch(typed["bank_reference"]) is None
        or SAFE_REFERENCE.fullmatch(typed["client_reference"]) is None
    ):
        raise PostgresLoadError("Type 03 CSV row violates its contract")
    settlement_ids.add(settlement)
    lot_sequences.add(lot_sequence)
    return record_a, record_b


def _money(value: str) -> Decimal:
    if UNSIGNED_MONEY.fullmatch(value) is None:
        raise InvalidOperation
    amount = Decimal(value)
    if not amount.is_finite():
        raise InvalidOperation
    return amount


def _validate_prepared_lineage(
    prepared: PreparedType03Load,
    *,
    raw: PublishedRaw,
) -> None:
    expected_csv_filename = raw.filename.removesuffix(".rem") + ".csv"
    recomputed_stage_controls = _parse_csv(
        prepared.csv_bytes,
        batch_id=raw.batch_id,
        source_filename=raw.filename,
        expected_lot_count=_required_control_int(raw, "lot_count"),
        expected_physical_record_count=_required_control_int(
            raw,
            "physical_record_count",
        ),
    )
    if (
        raw.file_type != "03"
        or prepared.batch_id != raw.batch_id
        or prepared.raw_filename != raw.filename
        or prepared.raw_sha256 != raw.sha256
        or prepared.raw_manifest_sha256 != raw.manifest_sha256
        or dict(prepared.source_controls) != dict(raw.source_controls)
        or prepared.csv_filename != expected_csv_filename
        or dict(prepared.stage_controls) != recomputed_stage_controls
        or prepared.row_count != raw.source_count
        or prepared.net_amount != raw.source_net_amount
        or hashlib.sha256(prepared.csv_bytes).hexdigest()
        != prepared.csv_sha256
        or len(prepared.csv_bytes) != prepared.csv_size_bytes
    ):
        raise PostgresLoadError(
            "Prepared Type 03 data no longer matches raw lineage"
        )


def _copy_and_verify_staging(
    cursor: psycopg.Cursor[Any],
    prepared: PreparedType03Load,
) -> None:
    cursor.execute(
        """
        CREATE TEMPORARY TABLE type03_copy_buffer (
            LIKE staging.payment_slip_settlement INCLUDING ALL
        ) ON COMMIT DROP
        """
    )
    with cursor.copy(
        "COPY type03_copy_buffer ("
        + COPY_COLUMNS
        + ") FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
    ) as copy:
        copy.write(prepared.csv_bytes)
    cursor.execute(
        """
        INSERT INTO staging.payment_slip_settlement
        SELECT * FROM type03_copy_buffer
        ON CONFLICT (batch_id, lot_number, sequence) DO NOTHING
        """
    )
    cursor.execute(
        """
        SELECT
            count(*),
            coalesce(sum(face_amount_brl), 0.00),
            coalesce(sum(discount_brl), 0.00),
            coalesce(sum(fee_brl), 0.00),
            coalesce(sum(net_amount_brl), 0.00)
          FROM staging.payment_slip_settlement
         WHERE batch_id = %s
        """,
        (prepared.batch_id,),
    )
    controls = cursor.fetchone()
    if controls is None:
        raise PostgresLoadError(
            "Type 03 PostgreSQL staging controls are unavailable"
        )
    count, face, discount, fee, net = controls
    expected = prepared.stage_controls
    if (
        count != expected["row_count"]
        or format(face, ".2f") != expected["face_amount"]
        or format(discount, ".2f") != expected["discount_amount"]
        or format(fee, ".2f") != expected["fee_amount"]
        or format(net, ".2f") != expected["net_amount"]
    ):
        raise PostgresLoadError(
            "Type 03 PostgreSQL staging controls changed"
        )
    cursor.execute(
        """
        SELECT EXISTS (
            (
                SELECT * FROM type03_copy_buffer
                EXCEPT
                SELECT *
                  FROM staging.payment_slip_settlement
                 WHERE batch_id = %s
            )
            UNION ALL
            (
                SELECT *
                  FROM staging.payment_slip_settlement
                 WHERE batch_id = %s
                EXCEPT
                SELECT * FROM type03_copy_buffer
            )
        )
        """,
        (prepared.batch_id, prepared.batch_id),
    )
    if cursor.fetchone() != (False,):
        raise PostgresLoadError(
            "Type 03 staging row identity changed on replay"
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
            source_face_amount,
            staged_face_amount,
            applied_face_amount,
            source_discount_amount,
            staged_discount_amount,
            applied_discount_amount,
            source_fee_amount,
            staged_fee_amount,
            applied_fee_amount,
            source_net_amount,
            staged_net_amount,
            applied_net_amount,
            source_orphan_segment_count,
            staged_orphan_segment_count,
            applied_orphan_segment_count,
            count_delta,
            face_amount_delta,
            discount_amount_delta,
            fee_amount_delta,
            net_amount_delta,
            orphan_segment_count_delta,
            reject_count,
            status
          FROM reporting.payment_slip_settlement_reconciliation
         WHERE batch_id = %s
        """,
        (batch_id,),
    )
    report = cursor.fetchone()
    if report is None:
        raise PostgresLoadError(
            "Type 03 reconciliation produced no report"
        )
    names = (
        "batch_id",
        "currency",
        "source_count",
        "staged_count",
        "applied_count",
        "source_face_amount",
        "staged_face_amount",
        "applied_face_amount",
        "source_discount_amount",
        "staged_discount_amount",
        "applied_discount_amount",
        "source_fee_amount",
        "staged_fee_amount",
        "applied_fee_amount",
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "source_orphan_segment_count",
        "staged_orphan_segment_count",
        "applied_orphan_segment_count",
        "count_delta",
        "face_amount_delta",
        "discount_amount_delta",
        "fee_amount_delta",
        "net_amount_delta",
        "orphan_segment_count_delta",
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
            14,
            15,
            16,
            21,
            22,
            23,
            24,
        }
    )
    reconciliation = {
        name: format(value, ".2f") if index in money_indexes else value
        for index, (name, value) in enumerate(zip(names, report, strict=True))
    }
    return procedure_runs, reconciliation
