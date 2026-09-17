"""Landing records for Type 02. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number: int
    end_to_end_id: str
    transaction_id: str
    payer_document_token: str
    payer_document_masked: str
    payee_document_token: str
    payee_document_masked: str
    event_timestamp: str
    amount_brl: Decimal
    direction: str
    status: str
    return_code: str | None
    description: str
