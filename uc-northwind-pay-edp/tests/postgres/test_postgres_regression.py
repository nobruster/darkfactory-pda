"""Live rollback-only PostgreSQL regression tests for completed loader slices."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "postgres",
):
    sys.path.insert(0, str(module_directory))

from config import RuntimeConfiguration  # noqa: E402
from loader_common import (  # noqa: E402
    _register_or_verify_batch,
    _register_or_verify_file,
)
from migrate import discover_migrations  # noqa: E402
from raw_publisher import PublishedRaw  # noqa: E402
from type01_loader import (  # noqa: E402
    _insert_and_verify_staging,
    _parse_csv as parse_type01_csv,
    _read_database_results as read_type01_database_results,
    _register_or_verify_load as register_type01_load,
)
from type02_loader import (  # noqa: E402
    PreparedType02Load,
    _copy_and_verify_staging,
    _parse_csv as parse_type02_csv,
    _read_database_results,
)


TYPE01_PROBE_BATCH = "B202607230008901"
TYPE02_PROBE_BATCH = "B202607230008902"
TYPE03_PROBE_BATCH = "B202607230008903"
TYPE04_PROBE_BATCH = "B202607230008904"
TYPE05_PROBE_BATCH = "B202607230008905"
TYPE05_HALF_UP_PROBE_BATCH = "B202607230008995"
CONTROL_RELATIONS = (
    "control.batches",
    "control.files",
    "control.loads",
    "control.procedure_runs",
)


def _published_probe(
    *,
    batch_id: str,
    file_type: str,
    filename: str,
    raw_bytes: bytes,
    source_controls: Mapping[str, int | str],
) -> PublishedRaw:
    """Build deterministic identity hashes from the exact probe source."""

    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    manifest_bytes = (
        json.dumps(
            {
                "batch_id": batch_id,
                "file_type": file_type,
                "source_controls": dict(source_controls),
                "source_file": {
                    "name": filename,
                    "sha256": raw_sha256,
                    "size_bytes": len(raw_bytes),
                },
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    return PublishedRaw(
        batch_id=batch_id,
        file_type=file_type,
        filename=filename,
        sha256=raw_sha256,
        size_bytes=len(raw_bytes),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        source_controls=source_controls,
    )


def _replace_exact(
    content: bytes,
    replacements: Mapping[bytes, bytes],
) -> bytes:
    """Apply length-preserving fixture substitutions for a reserved probe."""

    transformed = content
    for original, replacement in replacements.items():
        if len(original) != len(replacement):
            raise AssertionError(
                "Probe substitutions must preserve the source layout"
            )
        if original not in transformed:
            raise AssertionError(
                f"Probe source is missing expected token {original!r}"
            )
        transformed = transformed.replace(original, replacement)
    return transformed


class PostgreSqlRegressionTest(unittest.TestCase):
    """Prove COPY, permissions, procedures, and reconciliation on live Postgres."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def assert_probe_absent(
        self,
        batch_id: str,
        *relations: str,
    ) -> None:
        """Assert a rollback-only probe left no rows in named relations."""

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                for relation in relations:
                    with self.subTest(
                        batch_id=batch_id,
                        relation=relation,
                    ):
                        cursor.execute(
                            f"SELECT count(*) FROM {relation} "
                            "WHERE batch_id = %s",
                            (batch_id,),
                        )
                        self.assertEqual(cursor.fetchone(), (0,))

    def test_application_role_is_non_superuser_and_migrations_are_current(
        self,
    ) -> None:
        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT current_user, rolsuper
                      FROM pg_roles
                     WHERE rolname = current_user
                    """
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (self.configuration.postgres_app_user, False),
                )
        with psycopg.connect(
            self.configuration.postgres_admin_dsn
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT version, name, sha256
                      FROM control.schema_migrations
                     ORDER BY version
                    """
                )
                ledger = tuple(cursor.fetchall())
                expected_migrations = discover_migrations(
                    ROOT / "legacy" / "postgres"
                )
                expected_ledger = tuple(
                    (
                        migration.version,
                        migration.name,
                        migration.sha256,
                    )
                    for migration in expected_migrations
                )
                self.assertEqual(
                    tuple(
                        migration.version
                        for migration in expected_migrations
                    ),
                    tuple(f"{version:03d}" for version in range(1, 11)),
                )
                self.assertEqual(ledger, expected_ledger)

    def test_type01_copy_procedures_and_reconciliation_match(self) -> None:
        contract_root = (
            ROOT
            / "contracts"
            / "types"
            / "01-card-settlement"
            / "main"
        )
        canonical_batch = "B202607230000001"
        probe_batch = TYPE01_PROBE_BATCH
        probe_source_file = (
            f"NW_CARD_SETTLEMENT_20260723_{probe_batch}.dat"
        )
        replacements = {
            canonical_batch.encode(): probe_batch.encode(),
            b"TXN0000000000001": b"TXN0000000008901",
            b"TXN0000000000002": b"TXN0000000008902",
        }
        csv_bytes = _replace_exact(
            (contract_root / "expected-sanitized.csv").read_bytes(),
            replacements,
        )
        rows, count, net = parse_type01_csv(
            csv_bytes,
            batch_id=probe_batch,
            source_filename=probe_source_file,
        )
        net_amount = format(net, ".2f")
        raw_bytes = _replace_exact(
            (contract_root / "valid-minimal.dat").read_bytes(),
            replacements,
        )
        raw = _published_probe(
            batch_id=probe_batch,
            file_type="01",
            filename=probe_source_file,
            raw_bytes=raw_bytes,
            source_controls={
                "currency": "BRL",
                "detail_count": count,
                "net_amount": net_amount,
            },
        )

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
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
                csv_filename = (
                    probe_source_file.removesuffix(".dat") + ".csv"
                )
                csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
                _register_or_verify_file(
                    cursor,
                    batch_id=raw.batch_id,
                    stage="sanitized_csv",
                    filename=csv_filename,
                    sha256=csv_sha256,
                    size_bytes=len(csv_bytes),
                )
                _insert_and_verify_staging(
                    cursor,
                    rows,
                    batch_id=probe_batch,
                )
                register_type01_load(
                    cursor,
                    batch_id=probe_batch,
                    staged_count=count,
                    staged_net_amount=net_amount,
                )
                cursor.execute(
                    """
                    SELECT count(*), sum(amount_brl)
                      FROM staging.card_settlement
                     WHERE batch_id = %s
                    """,
                    (probe_batch,),
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (2, Decimal("173.45")),
                )
                cursor.execute(
                    "SELECT legacy.apply_card_settlement_batch(%s)",
                    (probe_batch,),
                )
                cursor.execute(
                    """
                    SELECT
                        reporting.refresh_card_settlement_reconciliation(%s)
                    """,
                    (probe_batch,),
                )
                procedures, reconciliation = read_type01_database_results(
                    cursor,
                    batch_id=probe_batch,
                )
                self.assertEqual(
                    procedures,
                    (
                        {
                            "sequence": 1,
                            "procedure": (
                                "legacy.apply_card_settlement_batch"
                            ),
                            "status": "succeeded",
                        },
                        {
                            "sequence": 2,
                            "procedure": (
                                "reporting."
                                "refresh_card_settlement_reconciliation"
                            ),
                            "status": "succeeded",
                        },
                    ),
                )
                self.assertEqual(
                    reconciliation,
                    {
                        "batch_id": probe_batch,
                        "currency": "BRL",
                        "source_count": 2,
                        "staged_count": 2,
                        "applied_count": 2,
                        "source_net_amount": "173.45",
                        "staged_net_amount": "173.45",
                        "applied_net_amount": "173.45",
                        "count_delta": 0,
                        "amount_delta": "0.00",
                        "reject_count": 0,
                        "status": "MATCHED",
                    },
                )
            connection.rollback()
        self.assert_probe_absent(
            probe_batch,
            *CONTROL_RELATIONS,
            "staging.card_settlement",
            "legacy.card_settlement",
            "reporting.card_settlement_reconciliation",
        )

    def test_type02_copy_procedures_and_reconciliation_match(self) -> None:
        contract_root = (
            ROOT
            / "contracts"
            / "types"
            / "02-instant-payment-events"
            / "main"
        )
        canonical_batch = "B202607230000101"
        batch_id = TYPE02_PROBE_BATCH
        source_filename = (
            f"NW_INSTANT_PAYMENT_20260723_{batch_id}.txt"
        )
        replacements = {
            canonical_batch.encode(): batch_id.encode(),
            b"E2026072300000000000000000000001": (
                b"E2026072300000000000000000008901"
            ),
            b"E2026072300000000000000000000002": (
                b"E2026072300000000000000000008902"
            ),
            b"PIXTXN0000000001": b"PIXTXN0000008901",
            b"PIXTXN0000000002": b"PIXTXN0000008902",
        }
        controls: dict[str, int | str] = {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "26.55",
            "event_count": 2,
            "net_amount": "173.45",
        }
        raw_bytes = _replace_exact(
            (contract_root / "valid-minimal.txt").read_bytes(),
            replacements,
        )
        raw = _published_probe(
            batch_id=batch_id,
            file_type="02",
            filename=source_filename,
            raw_bytes=raw_bytes,
            source_controls=controls,
        )
        csv_bytes = _replace_exact(
            (contract_root / "expected-sanitized.csv").read_bytes(),
            replacements,
        )
        stage_controls = parse_type02_csv(
            csv_bytes,
            batch_id=batch_id,
            source_filename=source_filename,
        )
        prepared = PreparedType02Load(
            batch_id=batch_id,
            raw_filename=source_filename,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=raw.source_controls,
            csv_filename=source_filename.removesuffix(".txt") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=stage_controls,
            csv_bytes=csv_bytes,
        )

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
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
                    """
                    SELECT control.register_load_v2(%s, %s, %s, %s)
                    """,
                    (
                        raw.batch_id,
                        Jsonb(dict(stage_controls)),
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
                procedures, reconciliation = _read_database_results(
                    cursor,
                    batch_id=raw.batch_id,
                )
                self.assertEqual(
                    tuple(run["sequence"] for run in procedures),
                    (1, 2),
                )
                self.assertEqual(reconciliation["status"], "MATCHED")
                self.assertEqual(
                    reconciliation["applied_net_amount"],
                    "173.45",
                )
                self.assertEqual(
                    reconciliation["applied_returned_count"],
                    1,
                )
            connection.rollback()
        self.assert_probe_absent(
            batch_id,
            *CONTROL_RELATIONS,
            "staging.instant_payment_event",
            "legacy.instant_payment_event",
            "reporting.instant_payment_reconciliation",
        )

    def test_type03_copy_procedures_and_reconciliation_match(self) -> None:
        canonical_batch = "B202607230000201"
        batch_id = TYPE03_PROBE_BATCH
        source_filename = (
            f"NW_PAYMENT_SLIP_20260723_{batch_id}.rem"
        )
        contract_root = (
            ROOT
            / "contracts"
            / "types"
            / "03-payment-slip-settlement"
            / "main"
        )
        controls: dict[str, int | str] = {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "logical_count": 2,
            "lot_count": 1,
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "physical_record_count": 8,
        }
        replacements = {
            canonical_batch.encode(): batch_id.encode(),
            b"PSL0000000000001": b"PSL0000000008903",
            b"PSL0000000000002": b"PSL0000000008904",
        }
        raw_bytes = _replace_exact(
            (contract_root / "valid-minimal.rem").read_bytes(),
            replacements,
        )
        raw = _published_probe(
            batch_id=batch_id,
            file_type="03",
            filename=source_filename,
            raw_bytes=raw_bytes,
            source_controls=controls,
        )
        csv_bytes = _replace_exact(
            (contract_root / "expected-sanitized.csv").read_bytes(),
            replacements,
        )
        csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
        stage_controls: dict[str, int | str] = {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "row_count": 2,
        }

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_batch(cursor, raw=raw)
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="raw",
                    filename=source_filename,
                    sha256=raw.sha256,
                    size_bytes=raw.size_bytes,
                )
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="sanitized_csv",
                    filename=source_filename.removesuffix(".rem") + ".csv",
                    sha256=csv_sha256,
                    size_bytes=len(csv_bytes),
                )
                with cursor.copy(
                    """
                    COPY staging.payment_slip_settlement (
                        batch_id,
                        source_file,
                        source_record_number_a,
                        source_record_number_b,
                        lot_number,
                        sequence,
                        settlement_id,
                        payment_reference_token,
                        payment_reference_last4,
                        beneficiary_token,
                        beneficiary_tax_id_type,
                        beneficiary_tax_id_masked,
                        bank_account_token,
                        bank_account_last4,
                        due_date,
                        payment_date,
                        face_amount_brl,
                        discount_brl,
                        fee_brl,
                        net_amount_brl,
                        status,
                        bank_reference,
                        client_reference
                    )
                    FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
                    """
                ) as copy:
                    copy.write(csv_bytes)
                cursor.execute(
                    "SELECT control.register_load_v2(%s, %s, %s, %s)",
                    (
                        batch_id,
                        Jsonb(stage_controls),
                        2,
                        Decimal("198.50"),
                    ),
                )
                cursor.execute(
                    """
                    SELECT
                        legacy.apply_payment_slip_settlement_batch(%s)
                    """,
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        reporting.refresh_payment_slip_settlement_reconciliation(
                            %s
                        )
                    """,
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        status,
                        applied_count,
                        applied_face_amount,
                        applied_discount_amount,
                        applied_fee_amount,
                        applied_net_amount,
                        applied_orphan_segment_count
                      FROM reporting
                        .payment_slip_settlement_reconciliation
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (
                        "MATCHED",
                        2,
                        Decimal("200.00"),
                        Decimal("5.00"),
                        Decimal("3.50"),
                        Decimal("198.50"),
                        0,
                    ),
                )
                cursor.execute(
                    """
                    SELECT sequence_number, procedure_name
                      FROM control.procedure_runs
                     WHERE batch_id = %s
                     ORDER BY sequence_number
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchall(),
                    [
                        (
                            1,
                            "legacy.apply_payment_slip_settlement_batch",
                        ),
                        (
                            2,
                            "reporting."
                            "refresh_payment_slip_settlement_reconciliation",
                        ),
                    ],
                )
            connection.rollback()
        self.assert_probe_absent(
            batch_id,
            *CONTROL_RELATIONS,
            "staging.payment_slip_settlement",
            "legacy.payment_slip_settlement",
            "reporting.payment_slip_settlement_reconciliation",
        )

    def test_type04_copy_procedures_and_reconciliation_match(self) -> None:
        canonical_batch = "B202607230000301"
        batch_id = TYPE04_PROBE_BATCH
        source_filename = (
            f"NW_TED_SETTLEMENT_20260723_{batch_id}.dat"
        )
        contract_root = (
            ROOT
            / "contracts"
            / "types"
            / "04-ted-transfer-settlement"
            / "main"
        )
        replacements = {
            canonical_batch.encode(): batch_id.encode(),
            b"TED2026072300301": b"TED2026072308904",
            b"TED2026072301301": b"TED2026072318904",
            b"RET2026072300301": b"RET2026072308904",
        }
        raw_bytes = _replace_exact(
            (contract_root / "valid-minimal.dat").read_bytes(),
            replacements,
        )
        controls: dict[str, int | str] = {
            "currency": "BRL",
            "gross_amount": "1250.00",
            "net_amount": "1000.00",
            "return_amount": "-250.00",
            "return_count": 1,
            "transfer_count": 2,
        }
        raw = _published_probe(
            batch_id=batch_id,
            file_type="04",
            filename=source_filename,
            raw_bytes=raw_bytes,
            source_controls=controls,
        )
        csv_bytes = _replace_exact(
            (contract_root / "expected-sanitized.csv").read_bytes(),
            replacements,
        )
        csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
        stage_controls: dict[str, int | str] = {
            "currency": "BRL",
            "gross_amount": "1250.00",
            "net_amount": "1000.00",
            "return_amount": "-250.00",
            "return_count": 1,
            "row_count": 3,
            "transfer_count": 2,
        }

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_batch(cursor, raw=raw)
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="raw",
                    filename=source_filename,
                    sha256=raw.sha256,
                    size_bytes=raw.size_bytes,
                )
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="sanitized_csv",
                    filename=source_filename.removesuffix(".dat") + ".csv",
                    sha256=csv_sha256,
                    size_bytes=len(csv_bytes),
                )
                with cursor.copy(
                    """
                    COPY staging.ted_transfer_movement (
                        batch_id,
                        source_file,
                        source_record_number,
                        movement_id,
                        original_transfer_id,
                        movement_kind,
                        movement_ts,
                        amount_brl,
                        payer_account_token,
                        payer_tax_id_masked,
                        beneficiary_account_token,
                        beneficiary_tax_id_masked,
                        beneficiary_ispb,
                        purpose_code,
                        status_code,
                        return_reason_code
                    )
                    FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
                    """
                ) as copy:
                    copy.write(csv_bytes)
                cursor.execute(
                    "SELECT control.register_load_v2(%s, %s, %s, %s)",
                    (
                        batch_id,
                        Jsonb(stage_controls),
                        3,
                        Decimal("1000.00"),
                    ),
                )
                cursor.execute(
                    "SELECT legacy.apply_ted_transfer_batch(%s)",
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT reporting.refresh_ted_transfer_reconciliation(%s)
                    """,
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        status,
                        applied_transfer_count,
                        applied_return_count,
                        applied_gross_amount,
                        applied_return_amount,
                        applied_net_amount
                      FROM reporting.ted_transfer_reconciliation
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (
                        "MATCHED",
                        2,
                        1,
                        Decimal("1250.00"),
                        Decimal("-250.00"),
                        Decimal("1000.00"),
                    ),
                )
                cursor.execute(
                    """
                    SELECT sequence_number, procedure_name
                      FROM control.procedure_runs
                     WHERE batch_id = %s
                     ORDER BY sequence_number
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchall(),
                    [
                        (
                            1,
                            "legacy.apply_ted_transfer_batch",
                        ),
                        (
                            2,
                            "reporting."
                            "refresh_ted_transfer_reconciliation",
                        ),
                    ],
                )
            connection.rollback()
        self.assert_probe_absent(
            batch_id,
            *CONTROL_RELATIONS,
            "staging.ted_transfer_movement",
            "legacy.ted_transfer_movement",
            "reporting.ted_transfer_reconciliation",
        )

    def test_type05_copy_procedures_and_reconciliation_match(self) -> None:
        canonical_batch = "B202607230000401"
        batch_id = TYPE05_PROBE_BATCH
        source_filename = (
            f"NW_MERCHANT_FEES_20260723_{batch_id}.csv"
        )
        contract_root = (
            ROOT
            / "contracts"
            / "types"
            / "05-merchant-fee-assessment"
            / "main"
        )
        replacements = {
            canonical_batch.encode(): batch_id.encode(),
            b"FEE2026072304001": b"FEE2026072308905",
            b"FEE2026072304002": b"FEE2026072318905",
        }
        raw_bytes = _replace_exact(
            (contract_root / "valid-minimal.csv").read_bytes(),
            replacements,
        )
        controls: dict[str, int | str] = {
            "currency": "BRL",
            "row_count": 2,
            "gross_amount": "1001.00",
            "assessed_fee": "12.36",
            "calculated_fee": "12.36",
        }
        raw = _published_probe(
            batch_id=batch_id,
            file_type="05",
            filename=source_filename,
            raw_bytes=raw_bytes,
            source_controls=controls,
        )
        self.assertEqual(raw.source_count, 2)
        self.assertEqual(raw.source_net_amount, "12.36")
        csv_bytes = _replace_exact(
            (contract_root / "expected-sanitized.csv").read_bytes(),
            replacements,
        )
        csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
        stage_controls: dict[str, int | str] = {
            "currency": "BRL",
            "row_count": 2,
            "gross_amount": "1001.00",
            "assessed_fee": "12.36",
            "calculated_fee": "12.36",
        }

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_batch(cursor, raw=raw)
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="raw",
                    filename=source_filename,
                    sha256=raw.sha256,
                    size_bytes=raw.size_bytes,
                )
                _register_or_verify_file(
                    cursor,
                    batch_id=batch_id,
                    stage="sanitized_csv",
                    filename=(
                        source_filename.removesuffix(".csv")
                        + "_SANITIZED.csv"
                    ),
                    sha256=csv_sha256,
                    size_bytes=len(csv_bytes),
                )
                with cursor.copy(
                    """
                    COPY staging.merchant_fee_assessment (
                        batch_id,
                        source_file,
                        source_record_number,
                        assessment_id,
                        merchant_id,
                        merchant_tax_id_masked,
                        fee_code,
                        description,
                        gross_amount_brl,
                        rate_percent,
                        assessed_fee_brl,
                        calculated_fee_brl,
                        assessment_date,
                        rounding_mode
                    )
                    FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
                    """
                ) as copy:
                    copy.write(csv_bytes)
                cursor.execute(
                    "SELECT control.register_load_v2(%s, %s, %s, %s)",
                    (
                        batch_id,
                        Jsonb(stage_controls),
                        2,
                        Decimal("12.36"),
                    ),
                )
                cursor.execute(
                    """
                    SELECT
                        legacy.apply_merchant_fee_assessment_batch(%s)
                    """,
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        reporting.refresh_merchant_fee_reconciliation(%s)
                    """,
                    (batch_id,),
                )
                cursor.execute(
                    """
                    SELECT
                        status,
                        applied_count,
                        applied_gross_amount,
                        applied_assessed_fee,
                        applied_calculated_fee,
                        assessment_calculation_delta
                      FROM reporting.merchant_fee_reconciliation
                     WHERE batch_id = %s
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (
                        "MATCHED",
                        2,
                        Decimal("1001.00"),
                        Decimal("12.36"),
                        Decimal("12.36"),
                        Decimal("0.00"),
                    ),
                )
                cursor.execute(
                    """
                    SELECT sequence_number, procedure_name
                      FROM control.procedure_runs
                     WHERE batch_id = %s
                     ORDER BY sequence_number
                    """,
                    (batch_id,),
                )
                self.assertEqual(
                    cursor.fetchall(),
                    [
                        (
                            1,
                            "legacy.apply_merchant_fee_assessment_batch",
                        ),
                        (
                            2,
                            "reporting."
                            "refresh_merchant_fee_reconciliation",
                        ),
                    ],
                )
            connection.rollback()
        self.assert_probe_absent(
            batch_id,
            *CONTROL_RELATIONS,
            "staging.merchant_fee_assessment",
            "legacy.merchant_fee_assessment",
            "reporting.merchant_fee_reconciliation",
        )

    def test_type05_copy_rejects_non_half_up_fee(self) -> None:
        batch_id = TYPE05_HALF_UP_PROBE_BATCH
        source_filename = (
            f"NW_MERCHANT_FEES_20260723_{batch_id}.csv"
        )
        assessment_id = "FEE2026072308995"
        controls: dict[str, int | str] = {
            "currency": "BRL",
            "row_count": 1,
            "gross_amount": "1.00",
            "assessed_fee": "0.00",
            "calculated_fee": "0.00",
        }
        raw_bytes = (
            "assessment_id;batch_id;merchant_id;merchant_tax_id;"
            "fee_code;description;gross_amount_brl;rate_percent;"
            "assessed_fee_brl;assessment_date\n"
            f"{assessment_id};{batch_id};MER0000000000001;"
            "12345678000195;TIE;Half up probe;1,00;0,500;0,00;"
            "23/07/2026\n"
        ).encode("utf-8")
        raw = _published_probe(
            batch_id=batch_id,
            file_type="05",
            filename=source_filename,
            raw_bytes=raw_bytes,
            source_controls=controls,
        )

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                _register_or_verify_batch(cursor, raw=raw)
                with self.assertRaises(psycopg.errors.CheckViolation):
                    cursor.execute(
                        """
                        INSERT INTO staging.merchant_fee_assessment (
                            batch_id,
                            source_file,
                            source_record_number,
                            assessment_id,
                            merchant_id,
                            merchant_tax_id_masked,
                            fee_code,
                            description,
                            gross_amount_brl,
                            rate_percent,
                            assessed_fee_brl,
                            calculated_fee_brl,
                            assessment_date,
                            rounding_mode
                        )
                        VALUES (
                            %s,
                            %s,
                            2,
                            %s,
                            'MER0000000000001',
                            '**********0195',
                            'TIE',
                            'Half up probe',
                            1.00,
                            0.500,
                            0.00,
                            0.00,
                            DATE '2026-07-23',
                            'HALF_UP'
                        )
                        """,
                        (batch_id, source_filename, assessment_id),
                    )
            connection.rollback()
        self.assert_probe_absent(
            batch_id,
            *CONTROL_RELATIONS,
            "staging.merchant_fee_assessment",
        )

    def test_loader_cannot_mutate_operational_or_reporting_tables(self) -> None:
        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        has_table_privilege(
                            current_user,
                            'legacy.instant_payment_event',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'reporting.instant_payment_reconciliation',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'control.procedure_runs',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'legacy.payment_slip_settlement',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'reporting.payment_slip_settlement_reconciliation',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'legacy.ted_transfer_movement',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'reporting.ted_transfer_reconciliation',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'legacy.merchant_fee_assessment',
                            'INSERT,UPDATE,DELETE'
                        ),
                        has_table_privilege(
                            current_user,
                            'reporting.merchant_fee_reconciliation',
                            'INSERT,UPDATE,DELETE'
                        )
                    """
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
