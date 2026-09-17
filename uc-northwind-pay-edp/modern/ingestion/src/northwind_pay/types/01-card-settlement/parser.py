"""Type 01 card-settlement parser — claim leg for ingest → landing.

Reads the same raw bytes as the live line. Money is Decimal. Privacy dies
here. Does not import Java. Does not write SFTP or frozen trees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

POSITIVE_OVERPUNCH = "{ABCDEFGHI"
NEGATIVE_OVERPUNCH = "}JKLMNOPQR"
SCALE = 2
MONEY_QUANTUM = Decimal("0.01")
ENCODING = "iso-8859-1"
HEADER_LENGTH = 40
DETAIL_LENGTH = 124
TRAILER_LENGTH = 46
FILE_TYPE_CODE = "CRD_SETTLE01"
LAYOUT_VERSION = "001"
BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
TRANSACTION_ID_RE = re.compile(r"^[A-Z0-9]{16}$")
MERCHANT_ID_RE = re.compile(r"^[A-Z0-9]{16}$")
AUTHORIZATION_RE = re.compile(r"^[A-Z0-9]{6}$")
TERMINAL_ID_RE = re.compile(r"^[A-Z0-9]{16}$")
TOKEN_RE = re.compile(r"^tok_[0-9a-f]{24}$")
KEY_ENV = "NWP_TOKENIZATION_KEY"

SOURCE_CONTROL_TOTAL_MISMATCH = "SOURCE_CONTROL_TOTAL_MISMATCH"
TOKENIZATION_KEY_MISSING = "TOKENIZATION_KEY_MISSING"
INVALID_OVERPUNCH = "INVALID_OVERPUNCH"
INVALID_RECORD_SEQUENCE = "INVALID_RECORD_SEQUENCE"
INVALID_RECORD_LENGTH = "INVALID_RECORD_LENGTH"
INVALID_TRANSPORT = "INVALID_TRANSPORT"
INVALID_DETAIL = "INVALID_DETAIL"
INVALID_TRAILER = "INVALID_TRAILER"
HEADER_MISMATCH = "HEADER_MISMATCH"
TRAILER_MISMATCH = "TRAILER_MISMATCH"
INVALID_MOVEMENT_AMOUNT = "INVALID_MOVEMENT_AMOUNT"
INVALID_BATCH_ID = "INVALID_BATCH_ID"


class ParseError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def decode_overpunch(raw: str, *, scale: int = SCALE) -> Decimal:
    if not raw:
        raise ParseError(INVALID_OVERPUNCH)
    last = raw[-1]
    body = raw[:-1]
    if last in POSITIVE_OVERPUNCH:
        digit = POSITIVE_OVERPUNCH.index(last)
        sign = 1
    elif last in NEGATIVE_OVERPUNCH:
        digit = NEGATIVE_OVERPUNCH.index(last)
        sign = -1
    else:
        raise ParseError(INVALID_OVERPUNCH)
    if not body.isdigit():
        raise ParseError(INVALID_OVERPUNCH)
    digits = body + str(digit)
    magnitude = Decimal(digits) / (Decimal(10) ** scale)
    value = magnitude if sign > 0 else -magnitude
    return value.quantize(MONEY_QUANTUM)


def tokenize_pan(pan: str, key: bytes) -> tuple[str, str]:
    if not (len(pan) == 16 and pan.isdigit()):
        raise ParseError(INVALID_DETAIL)
    digest = hmac.new(key, pan.encode("ascii"), hashlib.sha256).hexdigest()
    token = "tok_" + digest[:24]
    if not TOKEN_RE.match(token):
        raise ParseError("TOKENIZATION_ERROR")
    last4 = pan[-4:]
    return token, last4


def mask_cpf(cpf: str) -> str:
    if not (len(cpf) == 11 and cpf.isdigit()):
        raise ParseError(INVALID_DETAIL)
    return "*******" + cpf[-4:]


def resolve_tokenization_key(explicit: bytes | None = None) -> bytes:
    if explicit is not None:
        return explicit
    value = os.environ.get(KEY_ENV)
    if not value:
        raise ParseError(TOKENIZATION_KEY_MISSING)
    return value.encode("utf-8")


def _slice(record: str, start: int, end: int) -> str:
    return record[start - 1 : end]


@dataclass(frozen=True)
class SanitizedDetail:
    batch_id: str
    source_record_number: int
    transaction_id: str
    merchant_id: str
    card_token: str
    card_last4: str
    cpf_masked: str
    transaction_date: str
    transaction_time: str
    amount_brl: Decimal
    movement_code: str
    authorization_code: str
    nsu: str
    terminal_id: str

    def parquet_ready(self) -> Mapping[str, object]:
        return {
            "batch_id": self.batch_id,
            "source_record_number": self.source_record_number,
            "transaction_id": self.transaction_id,
            "merchant_id": self.merchant_id,
            "card_token": self.card_token,
            "card_last4": self.card_last4,
            "cpf_masked": self.cpf_masked,
            "amount_brl": self.amount_brl,
            "movement_code": self.movement_code,
            "authorization_code": self.authorization_code,
            "nsu": self.nsu,
            "terminal_id": self.terminal_id,
        }


@dataclass(frozen=True)
class ParseResult:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    declared_net_amount: Decimal | None
    computed_net_amount: Decimal | None
    details: tuple[SanitizedDetail, ...]
    landing_destination: str = "modern/landing/"

    @property
    def parquet_ready_rows(self) -> tuple[Mapping[str, object], ...]:
        if not self.accepted:
            return ()
        return tuple(detail.parquet_ready() for detail in self.details)


def parse_card_settlement(
    payload: bytes,
    *,
    filename: str | None = None,
    tokenization_key: bytes | None = None,
) -> ParseResult:
    """Parse one Type 01 raw file. Refused batches yield zero parquet-ready rows."""
    try:
        key = resolve_tokenization_key(tokenization_key)
        text = _decode_transport(payload)
        header, details_raw, trailer, _ = _split_records(text)
        header_fields = _parse_header(header)
        trailer_fields = _parse_trailer(trailer)
        _cross_check(header_fields, trailer_fields, filename)
        details = tuple(
            _parse_detail(record, record_number, header_fields["batch_id"], key)
            for record, record_number in details_raw
        )
        computed_net = sum((row.amount_brl for row in details), Decimal("0.00")).quantize(
            MONEY_QUANTUM
        )
        declared_net = trailer_fields["net_amount_brl"]
        if trailer_fields["detail_count"] != len(details):
            raise ParseError(TRAILER_MISMATCH)
        if declared_net != computed_net:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_TOTAL_MISMATCH,
                batch_id=header_fields["batch_id"],
                declared_net_amount=declared_net,
                computed_net_amount=computed_net,
                details=(),
            )
        return ParseResult(
            accepted=True,
            rejection_code=None,
            batch_id=header_fields["batch_id"],
            declared_net_amount=declared_net,
            computed_net_amount=computed_net,
            details=details,
        )
    except ParseError as exc:
        return ParseResult(
            accepted=False,
            rejection_code=exc.code,
            batch_id=None,
            declared_net_amount=None,
            computed_net_amount=None,
            details=(),
        )


def _decode_transport(payload: bytes) -> str:
    if not payload:
        raise ParseError(INVALID_TRANSPORT)
    if payload.endswith(b"\r\n") or b"\r" in payload:
        raise ParseError(INVALID_TRANSPORT)
    try:
        text = payload.decode(ENCODING)
    except UnicodeDecodeError as exc:
        raise ParseError(INVALID_TRANSPORT) from exc
    if not text.endswith("\n"):
        raise ParseError(INVALID_TRANSPORT)
    return text


def _split_records(text: str) -> tuple[str, list[tuple[str, int]], str, int]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if any(line == "" for line in lines):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if len(lines) < 3:
        raise ParseError(INVALID_RECORD_SEQUENCE)
    header = lines[0]
    trailer = lines[-1]
    details = [(line, index) for index, line in enumerate(lines[1:-1], start=2)]
    if not header.startswith("H"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not trailer.startswith("T"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not details or any(not line.startswith("D") for line, _ in details):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if len(header) != HEADER_LENGTH:
        raise ParseError(INVALID_RECORD_LENGTH)
    if len(trailer) != TRAILER_LENGTH:
        raise ParseError(INVALID_RECORD_LENGTH)
    if any(len(line) != DETAIL_LENGTH for line, _ in details):
        raise ParseError(INVALID_RECORD_LENGTH)
    return header, details, trailer, len(lines)


def _parse_header(record: str) -> dict[str, str]:
    file_date = _slice(record, 2, 9)
    batch_id = _slice(record, 10, 25)
    file_type = _slice(record, 26, 37)
    layout = _slice(record, 38, 40)
    if file_type != FILE_TYPE_CODE or layout != LAYOUT_VERSION:
        raise ParseError(HEADER_MISMATCH)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_BATCH_ID)
    if len(file_date) != 8 or not file_date.isdigit():
        raise ParseError(HEADER_MISMATCH)
    return {"file_date": file_date, "batch_id": batch_id}


def _parse_trailer(record: str) -> dict[str, object]:
    file_date = _slice(record, 2, 9)
    count_raw = _slice(record, 10, 15)
    net_raw = _slice(record, 16, 30)
    batch_id = _slice(record, 31, 46)
    if not count_raw.isdigit():
        raise ParseError(INVALID_TRAILER)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_BATCH_ID)
    return {
        "file_date": file_date,
        "detail_count": int(count_raw, 10),
        "net_amount_brl": decode_overpunch(net_raw),
        "batch_id": batch_id,
    }


def _cross_check(
    header: Mapping[str, str],
    trailer: Mapping[str, object],
    filename: str | None,
) -> None:
    if header["file_date"] != trailer["file_date"] or header["batch_id"] != trailer["batch_id"]:
        raise ParseError(HEADER_MISMATCH)
    if filename:
        match = re.search(r"(\d{8})_(B[0-9]{15})", filename)
        if match and (
            match.group(1) != header["file_date"] or match.group(2) != header["batch_id"]
        ):
            raise ParseError(HEADER_MISMATCH)


def _parse_detail(
    record: str,
    record_number: int,
    batch_id: str,
    key: bytes,
) -> SanitizedDetail:
    transaction_id = _slice(record, 2, 17)
    merchant_id = _slice(record, 18, 33)
    pan = _slice(record, 34, 49)
    cpf = _slice(record, 50, 60)
    transaction_date = _slice(record, 61, 68)
    transaction_time = _slice(record, 69, 74)
    amount = decode_overpunch(_slice(record, 75, 86))
    currency = _slice(record, 87, 89)
    movement = _slice(record, 90, 90)
    authorization = _slice(record, 91, 96)
    nsu = _slice(record, 97, 108)
    terminal_id = _slice(record, 109, 124)
    if currency != "BRL":
        raise ParseError(INVALID_DETAIL)
    if movement == "P" and amount <= 0:
        raise ParseError(INVALID_MOVEMENT_AMOUNT)
    if movement == "R" and amount >= 0:
        raise ParseError(INVALID_MOVEMENT_AMOUNT)
    if movement not in {"P", "R"}:
        raise ParseError(INVALID_DETAIL)
    if not TRANSACTION_ID_RE.match(transaction_id):
        raise ParseError(INVALID_DETAIL)
    if not MERCHANT_ID_RE.match(merchant_id):
        raise ParseError(INVALID_DETAIL)
    if not AUTHORIZATION_RE.match(authorization):
        raise ParseError(INVALID_DETAIL)
    if not nsu.isdigit() or len(nsu) != 12:
        raise ParseError(INVALID_DETAIL)
    if not TERMINAL_ID_RE.match(terminal_id):
        raise ParseError(INVALID_DETAIL)
    if len(transaction_date) != 8 or not transaction_date.isdigit():
        raise ParseError(INVALID_DETAIL)
    if len(transaction_time) != 6 or not transaction_time.isdigit():
        raise ParseError(INVALID_DETAIL)
    card_token, card_last4 = tokenize_pan(pan, key)
    cpf_masked = mask_cpf(cpf)
    return SanitizedDetail(
        batch_id=batch_id,
        source_record_number=record_number,
        transaction_id=transaction_id,
        merchant_id=merchant_id,
        card_token=card_token,
        card_last4=card_last4,
        cpf_masked=cpf_masked,
        transaction_date=transaction_date,
        transaction_time=transaction_time,
        amount_brl=amount,
        movement_code=movement,
        authorization_code=authorization,
        nsu=nsu,
        terminal_id=terminal_id,
    )


__all__ = [
    "ParseError",
    "ParseResult",
    "SanitizedDetail",
    "decode_overpunch",
    "mask_cpf",
    "parse_card_settlement",
    "tokenize_pan",
]
