"""Landing records for Type 06. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number: int
    chargeback_id: str
    merchant_id: str
    merchant_tax_id_masked: str
    reason_code: str
    description: str
    original_amount_brl: Decimal
    rate_percent: Decimal
    chargeback_amount_brl: Decimal
    calculated_amount_brl: Decimal
    business_date: str
    rounding_mode: str
