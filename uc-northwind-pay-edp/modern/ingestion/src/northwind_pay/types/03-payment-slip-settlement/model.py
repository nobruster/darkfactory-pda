"""Landing records for Type 03. Schema/writer see these; parser never writes Parquet."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LandingRecord:
    batch_id: str
    source_file: str
    source_record_number_a: int
    source_record_number_b: int
    lot_number: str
    sequence: str
    settlement_id: str
    payment_reference_token: str
    payment_reference_last4: str
    beneficiary_token: str
    beneficiary_tax_id_type: str
    beneficiary_tax_id_masked: str
    bank_account_token: str
    bank_account_last4: str
    due_date: str
    payment_date: str
    face_amount_brl: Decimal
    discount_brl: Decimal
    fee_brl: Decimal
    net_amount_brl: Decimal
    status: str
    bank_reference: str
    client_reference: str
