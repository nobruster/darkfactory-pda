"""Validate privacy-safe Type 03 records and compose landing fields. No retokenize."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

PAYMENT_REFERENCE_TOKEN_RE = re.compile(r"^payref_[0-9a-f]{24}$")
PARTY_TOKEN_RE = re.compile(r"^party_[0-9a-f]{24}$")
ACCOUNT_TOKEN_RE = re.compile(r"^acct_[0-9a-f]{24}$")
CPF_MASK_RE = re.compile(r"^\*{7}[0-9]{4}$")
CNPJ_MASK_RE = re.compile(r"^\*{10}[0-9]{4}$")


class SchemaError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def sanitize(parsed: object, *, source_filename: str) -> tuple[LandingRecord, ...]:
    if not getattr(parsed, "accepted", False):
        raise SchemaError(getattr(parsed, "rejection_code", None) or "REJECTED")
    records: list[LandingRecord] = []
    for settlement in getattr(parsed, "settlements"):
        record = LandingRecord(
            batch_id=settlement.batch_id,
            source_file=source_filename,
            source_record_number_a=settlement.source_record_number_a,
            source_record_number_b=settlement.source_record_number_b,
            lot_number=settlement.lot_number,
            sequence=settlement.sequence,
            settlement_id=settlement.settlement_id,
            payment_reference_token=settlement.payment_reference_token,
            payment_reference_last4=settlement.payment_reference_last4,
            beneficiary_token=settlement.beneficiary_token,
            beneficiary_tax_id_type=settlement.beneficiary_tax_id_type,
            beneficiary_tax_id_masked=settlement.beneficiary_tax_id_masked,
            bank_account_token=settlement.bank_account_token,
            bank_account_last4=settlement.bank_account_last4,
            due_date=settlement.due_date,
            payment_date=settlement.payment_date,
            face_amount_brl=settlement.face_amount_brl,
            discount_brl=settlement.discount_brl,
            fee_brl=settlement.fee_brl,
            net_amount_brl=settlement.net_amount_brl,
            status=settlement.status,
            bank_reference=settlement.bank_reference,
            client_reference=settlement.client_reference,
        )
        _assert_privacy(record)
        records.append(record)
    return tuple(records)


def _assert_privacy(record: LandingRecord) -> None:
    if not PAYMENT_REFERENCE_TOKEN_RE.match(record.payment_reference_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not PARTY_TOKEN_RE.match(record.beneficiary_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not ACCOUNT_TOKEN_RE.match(record.bank_account_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if record.beneficiary_tax_id_type == "CPF":
        if not CPF_MASK_RE.match(record.beneficiary_tax_id_masked):
            raise SchemaError("PRIVACY_VIOLATION")
    elif record.beneficiary_tax_id_type == "CNPJ":
        if not CNPJ_MASK_RE.match(record.beneficiary_tax_id_masked):
            raise SchemaError("PRIVACY_VIOLATION")
    else:
        raise SchemaError("PRIVACY_VIOLATION")
    if len(record.payment_reference_last4) != 4 or not record.payment_reference_last4.isdigit():
        raise SchemaError("PRIVACY_VIOLATION")
    if len(record.bank_account_last4) != 4 or not record.bank_account_last4.isdigit():
        raise SchemaError("PRIVACY_VIOLATION")
