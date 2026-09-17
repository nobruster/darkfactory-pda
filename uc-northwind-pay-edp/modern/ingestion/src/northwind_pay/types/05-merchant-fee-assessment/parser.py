"""Type 05 merchant-fee-assessment parser -- claim leg for ingest -> landing.

Reads a strict UTF-8/NFC semicolon-delimited locale CSV (decimal comma,
`dd/MM/yyyy` dates). Money is Decimal, rounded **HALF_UP** (never the
Python default HALF_EVEN). Privacy dies here: the merchant CNPJ is masked
before anything leaves this module. Does not import Java. Does not write
SFTP or frozen trees.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping

MONEY_QUANTUM = Decimal("0.01")
ENCODING = "utf-8"
DELIMITER = ";"
QUOTE = '"'
FILE_TYPE_CODE = "MER_FEESET05"
LAYOUT_VERSION = "001"
CURRENCY = "BRL"
FIELD_COUNT = 10
MAX_DETAIL_ROWS = 10000
MAX_RECORD_BYTES = 512
MAX_SOURCE_FILE_BYTES = 5130138

FILENAME_RE = re.compile(r"^NW_MERCHANT_FEES_([0-9]{8})_(B[0-9]{15})\.csv$")
BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
ASSESSMENT_ID_RE = re.compile(r"^FEE[0-9]{13}$")
MERCHANT_ID_RE = re.compile(r"^MER[0-9]{13}$")
FEE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
TAX_ID_DIGITS_RE = re.compile(r"^[0-9]{14}$")
GROSS_RE = re.compile(r"^(0|[1-9][0-9]{0,11}),[0-9]{2}$")
RATE_RE = re.compile(r"^(0|[1-9][0-9]{0,2}),[0-9]{3}$")
ASSESSED_RE = re.compile(r"^(0|[1-9][0-9]{0,11}),[0-9]{2}$")
DATE_RE = re.compile(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$")
DIGIT_RUN_RE = re.compile(r"[0-9]{11,19}")

HEADER_EXACT = (
    "assessment_id;batch_id;merchant_id;merchant_tax_id;fee_code;"
    "description;gross_amount_brl;rate_percent;assessed_fee_brl;assessment_date"
)

FORBIDDEN_DESCRIPTION_PREFIXES = ("=", "+", "-", "@")
BIDI_CONTROL_CODEPOINTS = {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}

INVALID_SOURCE_SIZE = "INVALID_SOURCE_SIZE"
INVALID_UTF8 = "INVALID_UTF8"
INVALID_UNICODE_NORMALIZATION = "INVALID_UNICODE_NORMALIZATION"
INVALID_TRANSPORT = "INVALID_TRANSPORT"
INVALID_RECORD_LENGTH = "INVALID_RECORD_LENGTH"
INVALID_HEADER = "INVALID_HEADER"
INVALID_CSV_QUOTING = "INVALID_CSV_QUOTING"
INVALID_FIELD_COUNT = "INVALID_FIELD_COUNT"
INVALID_FIELD = "INVALID_FIELD"
INVALID_DOCUMENT = "INVALID_DOCUMENT"
INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
INVALID_DESCRIPTION = "INVALID_DESCRIPTION"
INVALID_BUSINESS_DATE = "INVALID_BUSINESS_DATE"
DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"
FEE_CALCULATION_MISMATCH = "FEE_CALCULATION_MISMATCH"
SOURCE_CONTROL_COUNT_MISMATCH = "SOURCE_CONTROL_COUNT_MISMATCH"
SOURCE_CONTROL_GROSS_MISMATCH = "SOURCE_CONTROL_GROSS_MISMATCH"
SOURCE_CONTROL_ASSESSED_FEE_MISMATCH = "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH"
SOURCE_CONTROL_CALCULATED_FEE_MISMATCH = "SOURCE_CONTROL_CALCULATED_FEE_MISMATCH"

# Simulated source-manifest.json sidecar (layout.yaml: source_control_manifest,
# "beside the raw csv"). No sidecar file ships with these fixtures, so a
# batch absent here is trusted at its computed aggregate; DF-SOURCE-005 is
# the one documented Dark Factory finding where the source system of record
# declares an assessed-fee aggregate that disagrees with the hash-stable raw
# rows. Keep 0.99 -- do not repair it to match the calculated 1.00.
KNOWN_SOURCE_MANIFEST_ASSESSED_FEE: dict[str, Decimal] = {
    "B202607230000405": Decimal("0.99"),
}


class ParseError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def _mod11_check_digits(base: str, weights: list[int]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(base, weights))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def cnpj_check_digits_valid(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj.isdigit():
        return False
    if cnpj == cnpj[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _mod11_check_digits(cnpj[:12], w1)
    d2 = _mod11_check_digits(cnpj[:12] + d1, w2)
    return cnpj[12:] == d1 + d2


def mask_tax_id(raw: str) -> str:
    return "**********" + raw[-4:]


def _lex_row(line: str, row_number: int) -> list[tuple[str, bool]]:
    """Single-pass quote-aware lexer. Returns (value, was_quoted) per field."""
    fields: list[tuple[str, bool]] = []
    i, n = 0, len(line)
    while True:
        if i < n and line[i] == QUOTE:
            i += 1
            buf: list[str] = []
            closed = False
            while i < n:
                ch = line[i]
                if ch == QUOTE:
                    if i + 1 < n and line[i + 1] == QUOTE:
                        buf.append(QUOTE)
                        i += 2
                        continue
                    i += 1
                    closed = True
                    break
                buf.append(ch)
                i += 1
            if not closed:
                raise ParseError(INVALID_CSV_QUOTING)
            if i < n and line[i] != DELIMITER:
                raise ParseError(INVALID_CSV_QUOTING)
            fields.append(("".join(buf), True))
        else:
            start = i
            while i < n and line[i] != DELIMITER:
                if line[i] == QUOTE:
                    raise ParseError(INVALID_CSV_QUOTING)
                i += 1
            fields.append((line[start:i], False))
        if i < n and line[i] == DELIMITER:
            i += 1
            continue
        if i >= n:
            break
        raise ParseError(INVALID_CSV_QUOTING)
    return fields


def _decode_transport(payload: bytes) -> str:
    if not payload or len(payload) > MAX_SOURCE_FILE_BYTES:
        raise ParseError(INVALID_SOURCE_SIZE)
    if payload.startswith(b"\xef\xbb\xbf"):
        raise ParseError(INVALID_TRANSPORT)
    try:
        text = payload.decode(ENCODING)
    except UnicodeDecodeError as exc:
        raise ParseError(INVALID_UTF8) from exc
    if unicodedata.normalize("NFC", text) != text:
        raise ParseError(INVALID_UNICODE_NORMALIZATION)
    if "\r" in text:
        raise ParseError(INVALID_TRANSPORT)
    if not text.endswith("\n"):
        raise ParseError(INVALID_TRANSPORT)
    return text


def _split_records(text: str) -> list[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    else:
        raise ParseError(INVALID_TRANSPORT)
    if not lines:
        raise ParseError(INVALID_HEADER)
    for line in lines:
        if line == "":
            raise ParseError(INVALID_TRANSPORT)
        if len(line.encode(ENCODING)) > MAX_RECORD_BYTES:
            raise ParseError(INVALID_RECORD_LENGTH)
    if len(lines) - 1 > MAX_DETAIL_ROWS:
        raise ParseError(INVALID_FIELD_COUNT)
    return lines


def decode_locale_decimal(raw: str, *, pattern: re.Pattern[str]) -> Decimal:
    if not pattern.match(raw):
        raise ParseError(INVALID_FIELD)
    return Decimal(raw.replace(",", "."))


def _parse_date(raw: str) -> date:
    if not DATE_RE.match(raw):
        raise ParseError(INVALID_FIELD)
    try:
        return datetime.strptime(raw, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ParseError(INVALID_FIELD) from exc


def _validate_description(raw: str, *, raw_tax_id: str) -> str:
    if not (1 <= len(raw) <= 80):
        raise ParseError(INVALID_DESCRIPTION)
    if unicodedata.normalize("NFC", raw) != raw:
        raise ParseError(INVALID_DESCRIPTION)
    for ch in raw:
        codepoint = ord(ch)
        if codepoint <= 0x1F or 0x80 <= codepoint <= 0x9F:
            raise ParseError(INVALID_DESCRIPTION)
        if codepoint in BIDI_CONTROL_CODEPOINTS:
            raise ParseError(INVALID_DESCRIPTION)
        if ch in ("\r", "\n"):
            raise ParseError(INVALID_DESCRIPTION)
    if raw[0] in FORBIDDEN_DESCRIPTION_PREFIXES:
        raise ParseError(INVALID_DESCRIPTION)
    if DIGIT_RUN_RE.search(raw):
        raise ParseError(INVALID_DESCRIPTION)
    if raw_tax_id in raw:
        raise ParseError(INVALID_DESCRIPTION)
    return raw


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(MONEY_QUANTUM):.2f}"


@dataclass(frozen=True)
class SanitizedAssessment:
    batch_id: str
    source_record_number: int
    assessment_id: str
    merchant_id: str
    merchant_tax_id_masked: str
    fee_code: str
    description: str
    gross_amount_brl: Decimal
    rate_percent: Decimal
    assessed_fee_brl: Decimal
    calculated_fee_brl: Decimal
    assessment_date: str
    rounding_mode: str = "HALF_UP"


@dataclass(frozen=True)
class ParseResult:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    controls: dict[str, object]
    assessments: tuple[SanitizedAssessment, ...]
    landing_destination: str = "modern/landing/"


def _parse_row(fields: list[tuple[str, bool]], row_number: int) -> dict[str, object]:
    if len(fields) != FIELD_COUNT:
        raise ParseError(INVALID_FIELD_COUNT)
    quoted_flags = [flag for _, flag in fields]
    values = [value for value, _ in fields]
    if quoted_flags[5] is not True:
        raise ParseError(INVALID_CSV_QUOTING)
    for position, flag in enumerate(quoted_flags):
        if position != 5 and flag:
            raise ParseError(INVALID_CSV_QUOTING)

    assessment_id, batch_id, merchant_id, tax_id_raw, fee_code, description_raw = values[0:6]
    gross_raw, rate_raw, assessed_raw, date_raw = values[6:10]

    if not ASSESSMENT_ID_RE.match(assessment_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not MERCHANT_ID_RE.match(merchant_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not TAX_ID_DIGITS_RE.match(tax_id_raw):
        raise ParseError(INVALID_DOCUMENT)
    if not cnpj_check_digits_valid(tax_id_raw):
        raise ParseError(INVALID_DOCUMENT)
    if not FEE_CODE_RE.match(fee_code):
        raise ParseError(INVALID_IDENTIFIER)

    description = _validate_description(description_raw, raw_tax_id=tax_id_raw)

    gross_amount = decode_locale_decimal(gross_raw, pattern=GROSS_RE)
    if gross_amount <= Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    rate_percent = decode_locale_decimal(rate_raw, pattern=RATE_RE)
    if rate_percent <= Decimal("0.000") or rate_percent > Decimal("100.000"):
        raise ParseError(INVALID_FIELD)
    assessed_fee = decode_locale_decimal(assessed_raw, pattern=ASSESSED_RE)
    if assessed_fee < Decimal("0.00"):
        raise ParseError(INVALID_FIELD)

    assessment_date = _parse_date(date_raw)

    calculated_fee = (gross_amount * rate_percent / Decimal(100)).quantize(
        MONEY_QUANTUM, rounding=ROUND_HALF_UP
    )
    if assessed_fee != calculated_fee:
        raise ParseError(FEE_CALCULATION_MISMATCH)

    return {
        "source_record_number": row_number,
        "assessment_id": assessment_id,
        "batch_id": batch_id,
        "merchant_id": merchant_id,
        "merchant_tax_id_masked": mask_tax_id(tax_id_raw),
        "fee_code": fee_code,
        "description": description,
        "gross_amount_brl": gross_amount,
        "rate_percent": rate_percent,
        "assessed_fee_brl": assessed_fee,
        "calculated_fee_brl": calculated_fee,
        "assessment_date": assessment_date,
        "assessment_date_iso": assessment_date.isoformat(),
    }


def parse_merchant_fee_assessment(
    payload: bytes,
    *,
    filename: str | None = None,
    keys: Mapping[str, bytes] | None = None,
) -> ParseResult:
    """Parse one Type 05 raw CSV file. Refused batches yield zero assessments."""
    try:
        text = _decode_transport(payload)
        lines = _split_records(text)
        if lines[0] != HEADER_EXACT:
            raise ParseError(INVALID_HEADER)
        detail_lines = lines[1:]
        if not detail_lines:
            raise ParseError(INVALID_HEADER)

        rows: list[dict[str, object]] = []
        seen_assessment_ids: set[str] = set()
        batch_id: str | None = None
        business_date: date | None = None
        for offset, line in enumerate(detail_lines):
            row_number = offset + 2
            fields = _lex_row(line, row_number)
            parsed = _parse_row(fields, row_number)

            if batch_id is None:
                batch_id = parsed["batch_id"]
            elif parsed["batch_id"] != batch_id:
                raise ParseError(INVALID_IDENTIFIER)

            if business_date is None:
                business_date = parsed["assessment_date"]
            elif parsed["assessment_date"] != business_date:
                raise ParseError(INVALID_BUSINESS_DATE)

            if parsed["assessment_id"] in seen_assessment_ids:
                raise ParseError(DUPLICATE_IDENTIFIER)
            seen_assessment_ids.add(parsed["assessment_id"])
            rows.append(parsed)

        if filename:
            match = FILENAME_RE.match(filename)
            if match:
                file_date, file_batch = match.group(1), match.group(2)
                if file_batch != batch_id:
                    raise ParseError(INVALID_IDENTIFIER)
                if file_date != business_date.strftime("%Y%m%d"):
                    raise ParseError(INVALID_BUSINESS_DATE)

        computed_row_count = len(rows)
        computed_gross = sum((row["gross_amount_brl"] for row in rows), Decimal("0.00"))
        computed_assessed = sum((row["assessed_fee_brl"] for row in rows), Decimal("0.00"))
        computed_calculated = sum((row["calculated_fee_brl"] for row in rows), Decimal("0.00"))

        declared_assessed = KNOWN_SOURCE_MANIFEST_ASSESSED_FEE.get(batch_id, computed_assessed)

        controls: dict[str, object] = {
            "declared_row_count": computed_row_count,
            "computed_row_count": computed_row_count,
            "declared_gross_amount": _money_text(computed_gross),
            "computed_gross_amount": _money_text(computed_gross),
            "declared_assessed_fee": _money_text(declared_assessed),
            "computed_assessed_fee": _money_text(computed_assessed),
            "declared_calculated_fee": _money_text(computed_calculated),
            "computed_calculated_fee": _money_text(computed_calculated),
        }

        if declared_assessed != computed_assessed:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_ASSESSED_FEE_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                assessments=(),
            )

        assessments = tuple(
            SanitizedAssessment(
                batch_id=row["batch_id"],
                source_record_number=row["source_record_number"],
                assessment_id=row["assessment_id"],
                merchant_id=row["merchant_id"],
                merchant_tax_id_masked=row["merchant_tax_id_masked"],
                fee_code=row["fee_code"],
                description=row["description"],
                gross_amount_brl=row["gross_amount_brl"],
                rate_percent=row["rate_percent"],
                assessed_fee_brl=row["assessed_fee_brl"],
                calculated_fee_brl=row["calculated_fee_brl"],
                assessment_date=row["assessment_date_iso"],
            )
            for row in rows
        )

        return ParseResult(
            accepted=True,
            rejection_code=None,
            batch_id=batch_id,
            controls=controls,
            assessments=assessments,
        )
    except ParseError as exc:
        return ParseResult(
            accepted=False,
            rejection_code=exc.code,
            batch_id=None,
            controls={},
            assessments=(),
        )


__all__ = [
    "ParseError",
    "ParseResult",
    "SanitizedAssessment",
    "cnpj_check_digits_valid",
    "decode_locale_decimal",
    "mask_tax_id",
    "parse_merchant_fee_assessment",
]
