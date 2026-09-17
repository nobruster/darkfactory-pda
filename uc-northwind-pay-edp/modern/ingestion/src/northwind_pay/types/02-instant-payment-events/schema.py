"""Validate privacy-safe Type 02 records and compose landing fields. No retokenize."""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

DOCUMENT_TOKEN_RE = re.compile(r"^doc_[0-9a-f]{24}$")
CPF_MASK_RE = re.compile(r"^\*{7}[0-9]{4}$")
CNPJ_MASK_RE = re.compile(r"^\*{10}[0-9]{4}$")
DOCUMENT_DIGIT_RE = re.compile(r"(?<!\d)\d{11,14}(?!\d)")


class SchemaError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def controls_of(parsed: object) -> dict[str, object]:
    declared_count = getattr(parsed, "declared_event_count", None)
    computed_count = getattr(parsed, "computed_event_count", None)
    declared_credit = getattr(parsed, "declared_credit_amount", None)
    computed_credit = getattr(parsed, "computed_credit_amount", None)
    declared_debit = getattr(parsed, "declared_debit_amount", None)
    computed_debit = getattr(parsed, "computed_debit_amount", None)
    declared_net = getattr(parsed, "declared_net_amount", None)
    computed_net = getattr(parsed, "computed_net_amount", None)
    return {
        "declared_event_count": declared_count,
        "computed_event_count": computed_count,
        "declared_credit_amount": money_text(declared_credit)
        if declared_credit is not None
        else None,
        "computed_credit_amount": money_text(computed_credit)
        if computed_credit is not None
        else None,
        "declared_debit_amount": money_text(declared_debit)
        if declared_debit is not None
        else None,
        "computed_debit_amount": money_text(computed_debit)
        if computed_debit is not None
        else None,
        "declared_net_amount": money_text(declared_net) if declared_net is not None else None,
        "computed_net_amount": money_text(computed_net) if computed_net is not None else None,
    }


def sanitize(parsed: object, *, source_filename: str) -> tuple[LandingRecord, ...]:
    if not getattr(parsed, "accepted", False):
        raise SchemaError(getattr(parsed, "rejection_code", None) or "REJECTED")
    records: list[LandingRecord] = []
    for event in getattr(parsed, "events"):
        record = LandingRecord(
            batch_id=event.batch_id,
            source_file=source_filename,
            source_record_number=event.source_record_number,
            end_to_end_id=event.end_to_end_id,
            transaction_id=event.transaction_id,
            payer_document_token=event.payer_document_token,
            payer_document_masked=event.payer_document_masked,
            payee_document_token=event.payee_document_token,
            payee_document_masked=event.payee_document_masked,
            event_timestamp=event.event_timestamp,
            amount_brl=event.amount_brl,
            direction=event.direction,
            status=event.status,
            return_code=event.return_code,
            description=event.description,
        )
        _assert_privacy(record)
        records.append(record)
    return tuple(records)


def _assert_privacy(record: LandingRecord) -> None:
    if not DOCUMENT_TOKEN_RE.match(record.payer_document_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not DOCUMENT_TOKEN_RE.match(record.payee_document_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not (
        CPF_MASK_RE.match(record.payer_document_masked)
        or CNPJ_MASK_RE.match(record.payer_document_masked)
    ):
        raise SchemaError("PRIVACY_VIOLATION")
    if not (
        CPF_MASK_RE.match(record.payee_document_masked)
        or CNPJ_MASK_RE.match(record.payee_document_masked)
    ):
        raise SchemaError("PRIVACY_VIOLATION")
    blob = " ".join(
        [
            record.payer_document_token,
            record.payer_document_masked,
            record.payee_document_token,
            record.payee_document_masked,
            record.end_to_end_id,
            record.transaction_id,
            record.description,
        ]
    )
    if DOCUMENT_DIGIT_RE.search(blob):
        raise SchemaError("PRIVACY_VIOLATION")
