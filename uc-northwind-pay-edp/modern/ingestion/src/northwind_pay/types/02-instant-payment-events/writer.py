"""Deterministic Type 02 Parquet schema. Column order matches the sanitized CSV contract."""

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
    ("end_to_end_id", pa.string()),
    ("transaction_id", pa.string()),
    ("payer_document_token", pa.string()),
    ("payer_document_masked", pa.string()),
    ("payee_document_token", pa.string()),
    ("payee_document_masked", pa.string()),
    ("event_timestamp", pa.string()),
    ("amount_brl", pa.decimal128(18, 2)),
    ("direction", pa.string()),
    ("status", pa.string()),
    ("return_code", pa.string()),
    ("description", pa.string()),
)


def schema(
    *,
    batch_id: str,
    raw_sha256: str,
    contract_version: int = 1,
    layout_version: str = "001",
) -> pa.Schema:
    fields = []
    for name, kind in SCHEMA_FIELDS:
        nullable = name == "return_code"
        fields.append(pa.field(name, kind, nullable=nullable))
    return pa.schema(
        fields,
        metadata=canonical_metadata(
            batch_id=batch_id,
            type_number="02",
            contract_code="PIX_EVENTS01",
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
        "end_to_end_id": [record.end_to_end_id for record in ordered],
        "transaction_id": [record.transaction_id for record in ordered],
        "payer_document_token": [record.payer_document_token for record in ordered],
        "payer_document_masked": [record.payer_document_masked for record in ordered],
        "payee_document_token": [record.payee_document_token for record in ordered],
        "payee_document_masked": [record.payee_document_masked for record in ordered],
        "event_timestamp": [record.event_timestamp for record in ordered],
        "amount_brl": [record.amount_brl for record in ordered],
        "direction": [record.direction for record in ordered],
        "status": [record.status for record in ordered],
        "return_code": [record.return_code for record in ordered],
        "description": [record.description for record in ordered],
    }
    target = schema(batch_id=batch_id, raw_sha256=raw_sha256)
    return pa.Table.from_pydict(columns, schema=target)
