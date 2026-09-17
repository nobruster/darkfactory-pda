"""Validate privacy-safe Type 04 records and compose landing fields. No retokenize."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

ACCOUNT_TOKEN_RE = re.compile(r"^tedacct_[0-9a-f]{24}$")
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
    for movement in getattr(parsed, "movements"):
        record = LandingRecord(
            batch_id=movement.batch_id,
            source_file=source_filename,
            source_record_number=movement.source_record_number,
            movement_id=movement.movement_id,
            original_transfer_id=movement.original_transfer_id,
            movement_kind=movement.movement_kind,
            movement_ts=movement.movement_ts,
            amount_brl=movement.amount_brl,
            payer_account_token=movement.payer_account_token,
            payer_tax_id_masked=movement.payer_tax_id_masked,
            beneficiary_account_token=movement.beneficiary_account_token,
            beneficiary_tax_id_masked=movement.beneficiary_tax_id_masked,
            beneficiary_ispb=movement.beneficiary_ispb,
            purpose_code=movement.purpose_code,
            status_code=movement.status_code,
            return_reason_code=movement.return_reason_code,
        )
        _assert_privacy(record)
        records.append(record)
    return tuple(records)


def _assert_mask(masked: str) -> None:
    if not (CPF_MASK_RE.match(masked) or CNPJ_MASK_RE.match(masked)):
        raise SchemaError("PRIVACY_VIOLATION")


def _assert_privacy(record: LandingRecord) -> None:
    if not ACCOUNT_TOKEN_RE.match(record.payer_account_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not ACCOUNT_TOKEN_RE.match(record.beneficiary_account_token):
        raise SchemaError("PRIVACY_VIOLATION")
    _assert_mask(record.payer_tax_id_masked)
    _assert_mask(record.beneficiary_tax_id_masked)
    if record.movement_kind == "TRANSFER":
        if record.original_transfer_id is not None or record.return_reason_code is not None:
            raise SchemaError("PRIVACY_VIOLATION")
    elif record.movement_kind == "RETURN":
        if record.original_transfer_id is None or record.return_reason_code is None:
            raise SchemaError("PRIVACY_VIOLATION")
    else:
        raise SchemaError("PRIVACY_VIOLATION")
