"""Landing records for Type 01. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number: int
    transaction_id: str
    merchant_id: str
    card_token: str
    card_last4: str
    cpf_masked: str
    transaction_ts: str
    amount_brl: Decimal
    movement_code: str
    authorization_code: str
    nsu: str
    terminal_id: str
