"""Validate privacy-safe Type 01 records and compose landing fields. No retokenize."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from model import LandingRecord

TOKEN_RE = re.compile(r"^tok_[0-9a-f]{24}$")
CPF_MASK_RE = re.compile(r"^\*{7}[0-9]{4}$")
PAN_RE = re.compile(r"(?<!\d)\d{16}(?!\d)")
CPF_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
ZONE = ZoneInfo("America/Sao_Paulo")


class SchemaError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def transaction_ts(date_yyyymmdd: str, time_hhmmss: str) -> str:
    instant = datetime.strptime(date_yyyymmdd + time_hhmmss, "%Y%m%d%H%M%S").replace(
        tzinfo=ZONE
    )
    return instant.isoformat(timespec="seconds")


def controls_of(parsed: object) -> dict[str, object]:
    declared = getattr(parsed, "declared_net_amount", None)
    computed = getattr(parsed, "computed_net_amount", None)
    details = getattr(parsed, "details", ())
    return {
        "declared_detail_count": len(details)
        if getattr(parsed, "accepted", False)
        else None,
        "computed_detail_count": len(details)
        if getattr(parsed, "accepted", False)
        else None,
        "declared_net_amount": money_text(declared) if declared is not None else None,
        "computed_net_amount": money_text(computed) if computed is not None else None,
    }


def sanitize(parsed: object, *, source_filename: str) -> tuple[LandingRecord, ...]:
    if not getattr(parsed, "accepted", False):
        raise SchemaError(getattr(parsed, "rejection_code", None) or "REJECTED")
    records: list[LandingRecord] = []
    for detail in getattr(parsed, "details"):
        record = LandingRecord(
            batch_id=detail.batch_id,
            source_file=source_filename,
            source_record_number=detail.source_record_number,
            transaction_id=detail.transaction_id,
            merchant_id=detail.merchant_id,
            card_token=detail.card_token,
            card_last4=detail.card_last4,
            cpf_masked=detail.cpf_masked,
            transaction_ts=transaction_ts(detail.transaction_date, detail.transaction_time),
            amount_brl=detail.amount_brl,
            movement_code=detail.movement_code,
            authorization_code=detail.authorization_code,
            nsu=detail.nsu,
            terminal_id=detail.terminal_id,
        )
        _assert_privacy(record)
        records.append(record)
    return tuple(records)


def _assert_privacy(record: LandingRecord) -> None:
    if not TOKEN_RE.match(record.card_token):
        raise SchemaError("PRIVACY_VIOLATION")
    if not CPF_MASK_RE.match(record.cpf_masked):
        raise SchemaError("PRIVACY_VIOLATION")
    if len(record.card_last4) != 4 or not record.card_last4.isdigit():
        raise SchemaError("PRIVACY_VIOLATION")
    blob = " ".join(
        [
            record.card_token,
            record.card_last4,
            record.cpf_masked,
            record.transaction_id,
            record.merchant_id,
        ]
    )
    if PAN_RE.search(blob) or CPF_RE.search(blob):
        raise SchemaError("PRIVACY_VIOLATION")
