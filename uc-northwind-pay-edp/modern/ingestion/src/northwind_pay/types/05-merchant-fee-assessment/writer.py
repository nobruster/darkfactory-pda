"""Deterministic Type 05 Parquet schema. Column order matches the sanitized CSV contract."""

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
    ("source_record_number", pa.int32()),
    ("assessment_id", pa.string()),
    ("merchant_id", pa.string()),
    ("merchant_tax_id_masked", pa.string()),
    ("fee_code", pa.string()),
    ("description", pa.string()),
    ("gross_amount_brl", pa.decimal128(18, 2)),
    ("rate_percent", pa.decimal128(9, 3)),
    ("assessed_fee_brl", pa.decimal128(18, 2)),
    ("calculated_fee_brl", pa.decimal128(18, 2)),
    ("assessment_date", pa.string()),
    ("rounding_mode", pa.string()),
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
            type_number="05",
            contract_code="MER_FEESET05",
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
        "assessment_id": [record.assessment_id for record in ordered],
        "merchant_id": [record.merchant_id for record in ordered],
        "merchant_tax_id_masked": [record.merchant_tax_id_masked for record in ordered],
        "fee_code": [record.fee_code for record in ordered],
        "description": [record.description for record in ordered],
        "gross_amount_brl": [record.gross_amount_brl for record in ordered],
        "rate_percent": [record.rate_percent for record in ordered],
        "assessed_fee_brl": [record.assessed_fee_brl for record in ordered],
        "calculated_fee_brl": [record.calculated_fee_brl for record in ordered],
        "assessment_date": [record.assessment_date for record in ordered],
        "rounding_mode": [record.rounding_mode for record in ordered],
    }
    target = schema(batch_id=batch_id, raw_sha256=raw_sha256)
    return pa.Table.from_pydict(columns, schema=target)
