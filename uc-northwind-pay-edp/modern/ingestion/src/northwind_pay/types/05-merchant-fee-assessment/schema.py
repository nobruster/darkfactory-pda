"""Validate privacy-safe Type 05 records and compose landing fields. No retokenize."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

MASK_RE = re.compile(r"^\*{10}[0-9]{4}$")


class SchemaError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def sanitize(parsed: object, *, source_filename: str) -> tuple[LandingRecord, ...]:
    if not getattr(parsed, "accepted", False):
        raise SchemaError(getattr(parsed, "rejection_code", None) or "REJECTED")
    records: list[LandingRecord] = []
    for assessment in getattr(parsed, "assessments"):
        record = LandingRecord(
            batch_id=assessment.batch_id,
            source_file=source_filename,
            source_record_number=assessment.source_record_number,
            assessment_id=assessment.assessment_id,
            merchant_id=assessment.merchant_id,
            merchant_tax_id_masked=assessment.merchant_tax_id_masked,
            fee_code=assessment.fee_code,
            description=assessment.description,
            gross_amount_brl=assessment.gross_amount_brl,
            rate_percent=assessment.rate_percent,
            assessed_fee_brl=assessment.assessed_fee_brl,
            calculated_fee_brl=assessment.calculated_fee_brl,
            assessment_date=assessment.assessment_date,
            rounding_mode=assessment.rounding_mode,
        )
        _assert_privacy(record)
        records.append(record)
    return tuple(records)


def _assert_privacy(record: LandingRecord) -> None:
    if not MASK_RE.match(record.merchant_tax_id_masked):
        raise SchemaError("PRIVACY_VIOLATION")
