"""Landing records for Type 04. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number: int
    movement_id: str
    original_transfer_id: str | None
    movement_kind: str
    movement_ts: str
    amount_brl: Decimal
    payer_account_token: str
    payer_tax_id_masked: str
    beneficiary_account_token: str
    beneficiary_tax_id_masked: str
    beneficiary_ispb: str
    purpose_code: str
    status_code: str
    return_reason_code: str | None
