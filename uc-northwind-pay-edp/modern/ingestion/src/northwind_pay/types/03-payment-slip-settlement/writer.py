"""Deterministic Type 03 Parquet schema. Column order matches the sanitized CSV contract."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import pyarrow as pa

_HERE = Path(__file__).resolve().parent
_SRC = Path(__file__).resolve().parents[3]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from northwind_pay.common.parquet import canonical_metadata
from model import LandingRecord

WRITER_VERSION = "1.0.0"

SCHEMA_FIELDS: tuple[tuple[str, pa.DataType], ...] = (
    ("batch_id", pa.string()),
    ("source_file", pa.string()),
    ("source_record_number_a", pa.int32()),
    ("source_record_number_b", pa.int32()),
    ("lot_number", pa.string()),
    ("sequence", pa.string()),
    ("settlement_id", pa.string()),
    ("payment_reference_token", pa.string()),
    ("payment_reference_last4", pa.string()),
    ("beneficiary_token", pa.string()),
    ("beneficiary_tax_id_type", pa.string()),
    ("beneficiary_tax_id_masked", pa.string()),
    ("bank_account_token", pa.string()),
    ("bank_account_last4", pa.string()),
    ("due_date", pa.string()),
    ("payment_date", pa.string()),
    ("face_amount_brl", pa.decimal128(18, 2)),
    ("discount_brl", pa.decimal128(18, 2)),
    ("fee_brl", pa.decimal128(18, 2)),
    ("net_amount_brl", pa.decimal128(18, 2)),
    ("status", pa.string()),
    ("bank_reference", pa.string()),
    ("client_reference", pa.string()),
)


def schema(
    *,
    batch_id: str,
    raw_sha256: str,
    contract_version: int = 1,
    layout_version: str = "001",
) -> pa.Schema:
    return pa.schema(
        [pa.field(name, kind, nullable=False) for name, kind in SCHEMA_FIELDS],
        metadata=canonical_metadata(
            batch_id=batch_id,
            type_number="03",
            contract_code="PAYSLIPSET03",
            contract_version=contract_version,
            layout_version=layout_version,
            raw_sha256=raw_sha256,
            writer_version=WRITER_VERSION,
        ),
    )


def table(
    records: Sequence[LandingRecord],
    *,
    batch_id: str,
    raw_sha256: str,
) -> pa.Table:
    ordered = sorted(records, key=lambda record: record.source_record_number_a)
    columns = {
        "batch_id": [record.batch_id for record in ordered],
        "source_file": [record.source_file for record in ordered],
        "source_record_number_a": [record.source_record_number_a for record in ordered],
        "source_record_number_b": [record.source_record_number_b for record in ordered],
        "lot_number": [record.lot_number for record in ordered],
        "sequence": [record.sequence for record in ordered],
        "settlement_id": [record.settlement_id for record in ordered],
        "payment_reference_token": [record.payment_reference_token for record in ordered],
        "payment_reference_last4": [record.payment_reference_last4 for record in ordered],
        "beneficiary_token": [record.beneficiary_token for record in ordered],
        "beneficiary_tax_id_type": [record.beneficiary_tax_id_type for record in ordered],
        "beneficiary_tax_id_masked": [record.beneficiary_tax_id_masked for record in ordered],
        "bank_account_token": [record.bank_account_token for record in ordered],
        "bank_account_last4": [record.bank_account_last4 for record in ordered],
        "due_date": [record.due_date for record in ordered],
        "payment_date": [record.payment_date for record in ordered],
        "face_amount_brl": [record.face_amount_brl for record in ordered],
        "discount_brl": [record.discount_brl for record in ordered],
        "fee_brl": [record.fee_brl for record in ordered],
        "net_amount_brl": [record.net_amount_brl for record in ordered],
        "status": [record.status for record in ordered],
        "bank_reference": [record.bank_reference for record in ordered],
        "client_reference": [record.client_reference for record in ordered],
    }
    target = schema(batch_id=batch_id, raw_sha256=raw_sha256)
    return pa.Table.from_pydict(columns, schema=target)
