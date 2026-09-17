"""Type 02 instant-payment-events parser — claim leg for ingest → landing.

Single-pass escape-aware pipe lexer. Money is Decimal. Privacy dies here.
Does not import Java. Does not write SFTP or frozen trees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Mapping
from zoneinfo import ZoneInfo

FILE_TYPE_CODE = "PIX_EVENTS01"
LAYOUT_VERSION = "001"
MONEY_QUANTUM = Decimal("0.01")
ZONE = ZoneInfo("America/Sao_Paulo")

BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
END_TO_END_ID_RE = re.compile(r"^E[0-9]{31}$")
TRANSACTION_ID_RE = re.compile(r"^(?=.*[A-Z])[A-Z0-9]{16}$")
RETURN_CODE_RE = re.compile(r"^[A-Z0-9]{0,4}$")
AMOUNT_RE = re.compile(r"^(0|[1-9][0-9]{0,15})\.[0-9]{2}$")
NET_AMOUNT_RE = re.compile(r"^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$")
TIMESTAMP_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$"
)
DIGIT_RUN_RE = re.compile(r"\d{11,19}")
DOCUMENT_TOKEN_RE = re.compile(r"^doc_[0-9a-f]{24}$")
FORMULA_PREFIXES = ("=", "+", "-", "@")
BIDI_CONTROLS = {
    "‎",
    "‏",
    "‪",
    "‫",
    "‬",
    "‭",
    "‮",
    "⁦",
    "⁧",
    "⁨",
    "⁩",
}
DOCUMENT_KEY_ENV = "NWP_DOCUMENT_TOKEN_KEY"
DOCUMENT_KEY_ENV_FALLBACK = "NWP_TOKENIZATION_KEY"
MAX_RECORD_BYTES = 512
MAX_SOURCE_FILE_BYTES = 5_200_000
MAX_EVENTS = 10_000

INVALID_UTF8 = "INVALID_UTF8"
INVALID_TRANSPORT = "INVALID_TRANSPORT"
INVALID_RECORD_SEQUENCE = "INVALID_RECORD_SEQUENCE"
INVALID_FIELD_COUNT = "INVALID_FIELD_COUNT"
INVALID_ESCAPE_SEQUENCE = "INVALID_ESCAPE_SEQUENCE"
INVALID_DOCUMENT = "INVALID_DOCUMENT"
INVALID_DESCRIPTION = "INVALID_DESCRIPTION"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
INVALID_AMOUNT = "INVALID_AMOUNT"
INVALID_STATUS_RETURN_CODE = "INVALID_STATUS_RETURN_CODE"
DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"
SOURCE_CONTROL_COUNT_MISMATCH = "SOURCE_CONTROL_COUNT_MISMATCH"
SOURCE_CONTROL_CREDIT_MISMATCH = "SOURCE_CONTROL_CREDIT_MISMATCH"
SOURCE_CONTROL_DEBIT_MISMATCH = "SOURCE_CONTROL_DEBIT_MISMATCH"
SOURCE_CONTROL_NET_MISMATCH = "SOURCE_CONTROL_NET_MISMATCH"
TOKENIZATION_KEY_MISSING = "TOKENIZATION_KEY_MISSING"


class ParseError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def resolve_document_key(explicit: bytes | None = None) -> bytes:
    if explicit is not None:
        return explicit
    value = os.environ.get(DOCUMENT_KEY_ENV) or os.environ.get(DOCUMENT_KEY_ENV_FALLBACK)
    if not value:
        raise ParseError(TOKENIZATION_KEY_MISSING)
    return value.encode("utf-8")


def _split_escaped(line: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "\\":
            if i + 1 >= n:
                raise ParseError(INVALID_ESCAPE_SEQUENCE)
            nxt = line[i + 1]
            if nxt in ("|", "\\"):
                current.append(nxt)
                i += 2
                continue
            raise ParseError(INVALID_ESCAPE_SEQUENCE)
        if ch == "|":
            fields.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    fields.append("".join(current))
    return fields


def _mod11_digit(digits: str, weights: list[int], *, style: str) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights))
    if style == "cpf":
        remainder = (total * 10) % 11
        return 0 if remainder == 10 else remainder
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def _valid_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit():
        return False
    digit1 = _mod11_digit(cpf[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2], style="cpf")
    if digit1 != int(cpf[9]):
        return False
    digit2 = _mod11_digit(cpf[:10], [11, 10, 9, 8, 7, 6, 5, 4, 3, 2], style="cpf")
    return digit2 == int(cpf[10])


def _valid_cnpj(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False
    digit1 = _mod11_digit(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], style="cnpj")
    if digit1 != int(cnpj[12]):
        return False
    digit2 = _mod11_digit(cnpj[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], style="cnpj")
    return digit2 == int(cnpj[13])


def validate_document(document_type: str, document: str) -> None:
    if document_type == "CPF":
        if not _valid_cpf(document):
            raise ParseError(INVALID_DOCUMENT)
    elif document_type == "CNPJ":
        if not _valid_cnpj(document):
            raise ParseError(INVALID_DOCUMENT)
    else:
        raise ParseError(INVALID_DOCUMENT)


def tokenize_document(document: str, key: bytes) -> str:
    digest = hmac.new(key, document.encode("ascii"), hashlib.sha256).hexdigest()
    token = "doc_" + digest[:24]
    if not DOCUMENT_TOKEN_RE.match(token):
        raise ParseError("TOKENIZATION_ERROR")
    return token


def mask_document(document_type: str, document: str) -> str:
    if document_type == "CPF":
        return "*******" + document[-4:]
    return "**********" + document[-4:]


def parse_timestamp(raw: str) -> tuple[datetime, str]:
    match = TIMESTAMP_RE.match(raw)
    if not match:
        raise ParseError(INVALID_TIMESTAMP)
    year, month, day, hour, minute, second, offset = match.groups()
    if offset == "+00:00" or offset == "-00:00":
        raise ParseError(INVALID_TIMESTAMP)
    if offset == "Z":
        tz = timezone.utc
    else:
        sign = 1 if offset[0] == "+" else -1
        oh, om = offset[1:].split(":")
        tz = timezone(sign * timedelta(hours=int(oh), minutes=int(om)))
    try:
        instant = datetime(
            int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=tz
        )
    except ValueError as exc:
        raise ParseError(INVALID_TIMESTAMP) from exc
    return instant, raw


def validate_description(description: str, *, payer_document: str, payee_document: str) -> None:
    if unicodedata.normalize("NFC", description) != description:
        raise ParseError(INVALID_DESCRIPTION)
    if not (1 <= len(description) <= 80):
        raise ParseError(INVALID_DESCRIPTION)
    for ch in description:
        code = ord(ch)
        if code < 0x20 or 0x7F <= code <= 0x9F:
            raise ParseError(INVALID_DESCRIPTION)
        if ch in BIDI_CONTROLS:
            raise ParseError(INVALID_DESCRIPTION)
    if description[0] in FORMULA_PREFIXES:
        raise ParseError(INVALID_DESCRIPTION)
    if DIGIT_RUN_RE.search(description):
        raise ParseError(INVALID_DESCRIPTION)
    if payer_document in description or payee_document in description:
        raise ParseError(INVALID_DESCRIPTION)


@dataclass(frozen=True)
class SanitizedEvent:
    batch_id: str
    source_record_number: int
    end_to_end_id: str
    transaction_id: str
    payer_document_token: str
    payer_document_masked: str
    payee_document_token: str
    payee_document_masked: str
    event_timestamp: str
    amount_brl: Decimal
    direction: str
    status: str
    return_code: str | None
    description: str

    def parquet_ready(self) -> Mapping[str, object]:
        return {
            "batch_id": self.batch_id,
            "source_record_number": self.source_record_number,
            "end_to_end_id": self.end_to_end_id,
            "transaction_id": self.transaction_id,
            "payer_document_token": self.payer_document_token,
            "payer_document_masked": self.payer_document_masked,
            "payee_document_token": self.payee_document_token,
            "payee_document_masked": self.payee_document_masked,
            "event_timestamp": self.event_timestamp,
            "amount_brl": self.amount_brl,
            "direction": self.direction,
            "status": self.status,
            "return_code": self.return_code,
            "description": self.description,
        }


@dataclass(frozen=True)
class ParseResult:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    declared_event_count: int | None
    computed_event_count: int | None
    declared_credit_amount: Decimal | None
    computed_credit_amount: Decimal | None
    declared_debit_amount: Decimal | None
    computed_debit_amount: Decimal | None
    declared_net_amount: Decimal | None
    computed_net_amount: Decimal | None
    events: tuple[SanitizedEvent, ...]
    landing_destination: str = "modern/landing/"


def parse_instant_payment_events(
    payload: bytes,
    *,
    filename: str | None = None,
    document_key: bytes | None = None,
) -> ParseResult:
    """Parse one Type 02 raw file. Refused batches yield zero parquet-ready rows."""
    try:
        key = resolve_document_key(document_key)
        lines = _decode_transport(payload)
        header_line, event_lines, trailer_line = _split_records(lines)
        header = _parse_header(header_line)
        trailer = _parse_trailer(trailer_line)
        _cross_check_header(header, filename)
        events = tuple(
            _parse_event(line, number, header["batch_id"], header["file_date"], key)
            for line, number in event_lines
        )
        _check_duplicates(events)
        computed_credit = sum(
            (event.amount_brl for event in events if event.direction == "C"),
            Decimal("0.00"),
        ).quantize(MONEY_QUANTUM)
        computed_debit = sum(
            (abs(event.amount_brl) for event in events if event.direction == "D"),
            Decimal("0.00"),
        ).quantize(MONEY_QUANTUM)
        computed_net = (computed_credit - computed_debit).quantize(MONEY_QUANTUM)
        computed_count = len(events)

        base = dict(
            batch_id=header["batch_id"],
            declared_event_count=trailer["event_count"],
            computed_event_count=computed_count,
            declared_credit_amount=trailer["credit_total_brl"],
            computed_credit_amount=computed_credit,
            declared_debit_amount=trailer["debit_total_brl"],
            computed_debit_amount=computed_debit,
            declared_net_amount=trailer["net_total_brl"],
            computed_net_amount=computed_net,
        )

        if trailer["event_count"] != computed_count:
            return ParseResult(
                accepted=False, rejection_code=SOURCE_CONTROL_COUNT_MISMATCH, events=(), **base
            )
        if trailer["credit_total_brl"] != computed_credit:
            return ParseResult(
                accepted=False, rejection_code=SOURCE_CONTROL_CREDIT_MISMATCH, events=(), **base
            )
        if trailer["debit_total_brl"] != computed_debit:
            return ParseResult(
                accepted=False, rejection_code=SOURCE_CONTROL_DEBIT_MISMATCH, events=(), **base
            )
        if trailer["net_total_brl"] != computed_net:
            return ParseResult(
                accepted=False, rejection_code=SOURCE_CONTROL_NET_MISMATCH, events=(), **base
            )
        return ParseResult(accepted=True, rejection_code=None, events=events, **base)
    except ParseError as exc:
        return ParseResult(
            accepted=False,
            rejection_code=exc.code,
            batch_id=None,
            declared_event_count=None,
            computed_event_count=None,
            declared_credit_amount=None,
            computed_credit_amount=None,
            declared_debit_amount=None,
            computed_debit_amount=None,
            declared_net_amount=None,
            computed_net_amount=None,
            events=(),
        )


def _decode_transport(payload: bytes) -> list[str]:
    if not payload:
        raise ParseError(INVALID_TRANSPORT)
    if len(payload) > MAX_SOURCE_FILE_BYTES:
        raise ParseError(INVALID_TRANSPORT)
    if payload.startswith(b"\xef\xbb\xbf"):
        raise ParseError(INVALID_UTF8)
    if b"\r" in payload:
        raise ParseError(INVALID_TRANSPORT)
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ParseError(INVALID_UTF8) from exc
    if not text.endswith("\n"):
        raise ParseError(INVALID_TRANSPORT)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if any(line == "" for line in lines):
        raise ParseError(INVALID_TRANSPORT)
    for line in lines:
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            raise ParseError(INVALID_TRANSPORT)
    return lines


def _split_records(lines: list[str]) -> tuple[str, list[tuple[str, int]], str]:
    if len(lines) < 3:
        raise ParseError(INVALID_RECORD_SEQUENCE)
    header = lines[0]
    trailer = lines[-1]
    events = [(line, index) for index, line in enumerate(lines[1:-1], start=2)]
    if not header.startswith("H"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not trailer.startswith("T"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not events or any(not line.startswith("D") for line, _ in events):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if len(events) > MAX_EVENTS:
        raise ParseError(INVALID_RECORD_SEQUENCE)
    return header, events, trailer


def _parse_header(line: str) -> dict[str, str]:
    fields = _split_escaped(line)
    if len(fields) != 5:
        raise ParseError(INVALID_FIELD_COUNT)
    record_type, file_type_code, layout_version, file_date, batch_id = fields
    if record_type != "H":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if file_type_code != FILE_TYPE_CODE or layout_version != LAYOUT_VERSION:
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if len(file_date) != 8 or not file_date.isdigit():
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    return {"file_date": file_date, "batch_id": batch_id}


def _parse_trailer(line: str) -> dict[str, object]:
    fields = _split_escaped(line)
    if len(fields) != 5:
        raise ParseError(INVALID_FIELD_COUNT)
    record_type, event_count, credit_total, debit_total, net_total = fields
    if record_type != "T":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not event_count.isdigit():
        raise ParseError(INVALID_AMOUNT)
    if not AMOUNT_RE.match(credit_total) and credit_total != "0.00":
        raise ParseError(INVALID_AMOUNT)
    if not AMOUNT_RE.match(debit_total) and debit_total != "0.00":
        raise ParseError(INVALID_AMOUNT)
    if not NET_AMOUNT_RE.match(net_total):
        raise ParseError(INVALID_AMOUNT)
    return {
        "event_count": int(event_count, 10),
        "credit_total_brl": Decimal(credit_total).quantize(MONEY_QUANTUM),
        "debit_total_brl": Decimal(debit_total).quantize(MONEY_QUANTUM),
        "net_total_brl": Decimal(net_total).quantize(MONEY_QUANTUM),
    }


def _cross_check_header(header: Mapping[str, str], filename: str | None) -> None:
    if filename:
        match = re.search(r"(\d{8})_(B[0-9]{15})", filename)
        if match and (
            match.group(1) != header["file_date"] or match.group(2) != header["batch_id"]
        ):
            raise ParseError(INVALID_RECORD_SEQUENCE)


def _parse_event(
    line: str,
    record_number: int,
    batch_id: str,
    header_file_date: str,
    key: bytes,
) -> SanitizedEvent:
    fields = _split_escaped(line)
    if len(fields) != 13:
        raise ParseError(INVALID_FIELD_COUNT)
    (
        record_type,
        end_to_end_id,
        transaction_id,
        payer_document_type,
        payer_document,
        payee_document_type,
        payee_document,
        event_timestamp_raw,
        amount_raw,
        direction,
        status,
        return_code,
        description,
    ) = fields

    if record_type != "D":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not END_TO_END_ID_RE.match(end_to_end_id):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not TRANSACTION_ID_RE.match(transaction_id):
        raise ParseError(INVALID_RECORD_SEQUENCE)

    validate_document(payer_document_type, payer_document)
    validate_document(payee_document_type, payee_document)

    if not AMOUNT_RE.match(amount_raw):
        raise ParseError(INVALID_AMOUNT)
    amount = Decimal(amount_raw).quantize(MONEY_QUANTUM)
    if amount <= 0:
        raise ParseError(INVALID_AMOUNT)

    if direction not in ("C", "D"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if status not in ("SETTLED", "RETURNED"):
        raise ParseError(INVALID_RECORD_SEQUENCE)
    if not RETURN_CODE_RE.match(return_code):
        raise ParseError(INVALID_STATUS_RETURN_CODE)
    if status == "SETTLED" and return_code != "":
        raise ParseError(INVALID_STATUS_RETURN_CODE)
    if status == "RETURNED" and return_code == "":
        raise ParseError(INVALID_STATUS_RETURN_CODE)

    instant, preserved_lexeme = parse_timestamp(event_timestamp_raw)
    local = instant.astimezone(ZONE)
    if local.strftime("%Y%m%d") != header_file_date:
        raise ParseError(INVALID_TIMESTAMP)

    validate_description(
        description, payer_document=payer_document, payee_document=payee_document
    )

    payer_token = tokenize_document(payer_document, key)
    payee_token = tokenize_document(payee_document, key)
    payer_masked = mask_document(payer_document_type, payer_document)
    payee_masked = mask_document(payee_document_type, payee_document)

    return SanitizedEvent(
        batch_id=batch_id,
        source_record_number=record_number,
        end_to_end_id=end_to_end_id,
        transaction_id=transaction_id,
        payer_document_token=payer_token,
        payer_document_masked=payer_masked,
        payee_document_token=payee_token,
        payee_document_masked=payee_masked,
        event_timestamp=preserved_lexeme,
        amount_brl=amount if direction == "C" else -amount,
        direction=direction,
        status=status,
        return_code=return_code or None,
        description=description,
    )


def _check_duplicates(events: tuple[SanitizedEvent, ...]) -> None:
    seen_e2e: set[str] = set()
    seen_txn: set[str] = set()
    for event in events:
        if event.end_to_end_id in seen_e2e or event.transaction_id in seen_txn:
            raise ParseError(DUPLICATE_IDENTIFIER)
        seen_e2e.add(event.end_to_end_id)
        seen_txn.add(event.transaction_id)


__all__ = [
    "ParseError",
    "ParseResult",
    "SanitizedEvent",
    "mask_document",
    "parse_instant_payment_events",
    "resolve_document_key",
    "tokenize_document",
    "validate_description",
    "validate_document",
]
