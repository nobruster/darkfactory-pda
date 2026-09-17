"""Deterministic Type 04 Parquet schema. Column order matches the sanitized CSV contract."""

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

SCHEMA_FIELDS: tuple[tuple[str, pa.DataType, bool], ...] = (
    ("batch_id", pa.string(), False),
    ("source_file", pa.string(), False),
    ("source_record_number", pa.int32(), False),
    ("movement_id", pa.string(), False),
    ("original_transfer_id", pa.string(), True),
    ("movement_kind", pa.string(), False),
    ("movement_ts", pa.string(), False),
    ("amount_brl", pa.decimal128(18, 2), False),
    ("payer_account_token", pa.string(), False),
    ("payer_tax_id_masked", pa.string(), False),
    ("beneficiary_account_token", pa.string(), False),
    ("beneficiary_tax_id_masked", pa.string(), False),
    ("beneficiary_ispb", pa.string(), False),
    ("purpose_code", pa.string(), False),
    ("status_code", pa.string(), False),
    ("return_reason_code", pa.string(), True),
)


def schema(
    *,
    batch_id: str,
    raw_sha256: str,
    contract_version: int = 1,
    layout_version: str = "001",
) -> pa.Schema:
    return pa.schema(
        [pa.field(name, kind, nullable=nullable) for name, kind, nullable in SCHEMA_FIELDS],
        metadata=canonical_metadata(
            batch_id=batch_id,
            type_number="04",
            contract_code="TED_SETTLE04",
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
    ordered = sorted(records, key=lambda record: record.source_record_number)
    columns = {
        "batch_id": [record.batch_id for record in ordered],
        "source_file": [record.source_file for record in ordered],
        "source_record_number": [record.source_record_number for record in ordered],
        "movement_id": [record.movement_id for record in ordered],
        "original_transfer_id": [record.original_transfer_id for record in ordered],
        "movement_kind": [record.movement_kind for record in ordered],
        "movement_ts": [record.movement_ts for record in ordered],
        "amount_brl": [record.amount_brl for record in ordered],
        "payer_account_token": [record.payer_account_token for record in ordered],
        "payer_tax_id_masked": [record.payer_tax_id_masked for record in ordered],
        "beneficiary_account_token": [record.beneficiary_account_token for record in ordered],
        "beneficiary_tax_id_masked": [record.beneficiary_tax_id_masked for record in ordered],
        "beneficiary_ispb": [record.beneficiary_ispb for record in ordered],
        "purpose_code": [record.purpose_code for record in ordered],
        "status_code": [record.status_code for record in ordered],
        "return_reason_code": [record.return_reason_code for record in ordered],
    }
    target = schema(batch_id=batch_id, raw_sha256=raw_sha256)
    return pa.Table.from_pydict(columns, schema=target)
