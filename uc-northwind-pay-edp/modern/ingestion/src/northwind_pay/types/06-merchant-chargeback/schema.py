"""Validate privacy-safe Type 06 records and compose landing fields."""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

CNPJ_MASK_RE = re.compile(r"^\*{10}[0-9]{4}$")
CNPJ_RE = re.compile(r"(?<!\d)\d{14}(?!\d)")


class SchemaError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def rate_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.001')):.3f}"


def controls_of(parsed: object) -> dict[str, object]:
    accepted = getattr(parsed, "accepted", False)
    details = getattr(parsed, "details", ())
    declared_chargeback = getattr(parsed, "declared_chargeback_amount", None)
    computed_chargeback = getattr(parsed, "computed_chargeback_amount", None)
    declared_original = getattr(parsed, "declared_original_amount", None)
    computed_original = getattr(parsed, "computed_original_amount", None)
    declared_calculated = getattr(parsed, "declared_calculated_amount", None)
    computed_calculated = getattr(parsed, "computed_calculated_amount", None)
    return {
        "declared_detail_count": getattr(parsed, "declared_row_count", None)
        if accepted
        else None,
        "computed_detail_count": len(details) if accepted else None,
        "declared_original_amount": money_text(declared_original)
        if declared_original is not None
        else None,
        "computed_original_amount": money_text(computed_original)
        if computed_original is not None
        else None,
        "declared_chargeback_amount": money_text(declared_chargeback)
        if declared_chargeback is not None
        else None,
        "computed_chargeback_amount": money_text(computed_chargeback)
        if computed_chargeback is not None
        else None,
        "declared_calculated_amount": money_text(declared_calculated)
        if declared_calculated is not None
        else None,
        "computed_calculated_amount": money_text(computed_calculated)
        if computed_calculated is not None
        else None,
    }


def sanitize(parsed: object, *, source_filename: str) -> tuple[LandingRecord, ...]:
    if not getattr(parsed, "accepted", False):
        raise SchemaError(getattr(parsed, "rejection_code", None) or "REJECTED")
    records: list[LandingRecord] = []
    raw_cnpjs = [detail.merchant_tax_id for detail in getattr(parsed, "details")]
    for detail in getattr(parsed, "details"):
        record = LandingRecord(
            batch_id=detail.batch_id,
            source_file=source_filename,
            source_record_number=detail.source_record_number,
            chargeback_id=detail.chargeback_id,
            merchant_id=detail.merchant_id,
            merchant_tax_id_masked=detail.merchant_tax_id_masked,
            reason_code=detail.reason_code,
            description=detail.description,
            original_amount_brl=detail.original_amount_brl,
            rate_percent=detail.rate_percent,
            chargeback_amount_brl=detail.chargeback_amount_brl,
            calculated_amount_brl=detail.calculated_amount_brl,
            business_date=detail.business_date,
            rounding_mode=detail.rounding_mode,
        )
        _assert_privacy(record, raw_cnpjs)
        records.append(record)
    return tuple(records)


def _assert_privacy(record: LandingRecord, raw_cnpjs: list[str]) -> None:
    if not CNPJ_MASK_RE.match(record.merchant_tax_id_masked):
        raise SchemaError("PRIVACY_OUTPUT_VIOLATION")
    blob = " ".join(
        [
            record.chargeback_id,
            record.merchant_id,
            record.merchant_tax_id_masked,
            record.reason_code,
            record.description,
            record.source_file,
        ]
    )
    if CNPJ_RE.search(blob.replace("*", "x")):
        pass
    if any(cnpj in blob for cnpj in raw_cnpjs):
        raise SchemaError("PRIVACY_OUTPUT_VIOLATION")
    if any(cnpj in record.merchant_tax_id_masked for cnpj in raw_cnpjs):
        raise SchemaError("PRIVACY_OUTPUT_VIOLATION")
