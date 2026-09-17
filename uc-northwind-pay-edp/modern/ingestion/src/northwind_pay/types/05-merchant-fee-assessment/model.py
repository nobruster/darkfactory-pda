"""Landing records for Type 05. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number: int
    assessment_id: str
    merchant_id: str
    merchant_tax_id_masked: str
    fee_code: str
    description: str
    gross_amount_brl: Decimal
    rate_percent: Decimal
    assessed_fee_brl: Decimal
    calculated_fee_brl: Decimal
    assessment_date: str
    rounding_mode: str
