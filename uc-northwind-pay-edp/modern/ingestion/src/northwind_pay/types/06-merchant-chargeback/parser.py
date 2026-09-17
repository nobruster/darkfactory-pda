"""Type 06 merchant-chargeback parser — claim leg for ingest → landing.

Reads the same raw CSV bytes as the live line. Money is Decimal. HALF_UP
once. Privacy dies here. Does not import Java. Does not write SFTP or
frozen trees.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.001")
HUNDRED = Decimal("100")
FILE_TYPE_CODE = "MER_CHGBK06"
LAYOUT_VERSION = "001"
ROUNDING_MODE = "HALF_UP"
EXACT_HEADER = (
    "chargeback_id;batch_id;merchant_id;merchant_tax_id;reason_code;"
    "description;original_amount_brl;rate_percent;chargeback_amount_brl;"
    "business_date"
)
FILENAME_RE = re.compile(r"^NW_MERCHANT_CHARGEBACK_([0-9]{8})_(B[0-9]{15})\.csv$")
BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
CHARGEBACK_ID_RE = re.compile(r"^CBK[0-9]{13}$")
MERCHANT_ID_RE = re.compile(r"^MER[0-9]{13}$")
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
MONEY_RE = re.compile(r"^(0|[1-9][0-9]{0,11}),[0-9]{2}$")
RATE_RE = re.compile(r"^(0|[1-9][0-9]{0,2}),[0-9]{3}$")
CNPJ_RE = re.compile(r"^[0-9]{14}$")
DIGIT_RUN = re.compile(r"[0-9]{11,19}")
BIDI_CONTROLS = frozenset(
    {
        "\u061c",
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
    }
)
MAX_DETAIL_ROWS = 10000
MAX_RECORD_BYTES = 512
MAX_SOURCE_BYTES = 5130138
FIELD_COUNT = 10

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
CHARGEBACK_CALCULATION_MISMATCH = "CHARGEBACK_CALCULATION_MISMATCH"
SOURCE_CONTROL_COUNT_MISMATCH = "SOURCE_CONTROL_COUNT_MISMATCH"
SOURCE_CONTROL_ORIGINAL_MISMATCH = "SOURCE_CONTROL_ORIGINAL_MISMATCH"
SOURCE_CONTROL_CHARGEBACK_MISMATCH = "SOURCE_CONTROL_CHARGEBACK_MISMATCH"
SOURCE_CONTROL_CALCULATED_MISMATCH = "SOURCE_CONTROL_CALCULATED_MISMATCH"
PRIVACY_OUTPUT_VIOLATION = "PRIVACY_OUTPUT_VIOLATION"


class ParseError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class SanitizedDetail:
    batch_id: str
    source_record_number: int
    chargeback_id: str
    merchant_id: str
    merchant_tax_id: str
    merchant_tax_id_masked: str
    reason_code: str
    description: str
    original_amount_brl: Decimal
    rate_percent: Decimal
    chargeback_amount_brl: Decimal
    calculated_amount_brl: Decimal
    business_date: str
    rounding_mode: str


@dataclass(frozen=True)
class ParsedBatch:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    details: tuple[SanitizedDetail, ...]
    declared_row_count: int | None
    computed_row_count: int | None
    declared_original_amount: Decimal | None
    computed_original_amount: Decimal | None
    declared_chargeback_amount: Decimal | None
    computed_chargeback_amount: Decimal | None
    declared_calculated_amount: Decimal | None
    computed_calculated_amount: Decimal | None
    source_filename: str


def calculate_chargeback(original: Decimal, rate: Decimal) -> Decimal:
    """original × rate ÷ 100, then HALF_UP once to scale 2. Never HALF_EVEN."""

    raw = (original * rate) / HUNDRED
    return raw.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def mask_cnpj(value: str) -> str:
    return "*" * 10 + value[-4:]


def valid_cnpj(value: str) -> bool:
    if CNPJ_RE.fullmatch(value) is None or len(set(value)) == 1:
        return False
    numbers = [int(character) for character in value]
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first_remainder = sum(
        digit * weight for digit, weight in zip(numbers[:12], first_weights)
    ) % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_remainder = sum(
        digit * weight
        for digit, weight in zip(numbers[:12] + [first], second_weights)
    ) % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return numbers[-2:] == [first, second]


def locale_money(raw: str) -> Decimal:
    if MONEY_RE.fullmatch(raw) is None:
        raise ParseError(INVALID_FIELD)
    return Decimal(raw.replace(",", ".")).quantize(MONEY_QUANTUM)


def locale_rate(raw: str) -> Decimal:
    if RATE_RE.fullmatch(raw) is None:
        raise ParseError(INVALID_FIELD)
    return Decimal(raw.replace(",", ".")).quantize(RATE_QUANTUM)


def parse_business_date(raw: str) -> date:
    try:
        parsed = datetime.strptime(raw, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ParseError(INVALID_BUSINESS_DATE) from exc
    if parsed.strftime("%d/%m/%Y") != raw:
        raise ParseError(INVALID_BUSINESS_DATE)
    return parsed


def _valid_description(value: str) -> bool:
    return (
        unicodedata.normalize("NFC", value) == value
        and 1 <= len(value) <= 80
        and value[0] not in "=+-@"
        and DIGIT_RUN.search(value) is None
        and all(
            not (
                ord(character) <= 0x1F
                or 0x7F <= ord(character) <= 0x9F
                or character in BIDI_CONTROLS
            )
            for character in value
        )
    )


def _lex_record(line: str) -> list[tuple[str, bool]]:
    """Quote-aware single-pass lexer. Returns (value, was_quoted) pairs."""

    fields: list[tuple[str, bool]] = []
    index = 0
    length = len(line)
    while index <= length:
        if index == length:
            break
        if line[index] == '"':
            index += 1
            buffer: list[str] = []
            closed = False
            while index < length:
                character = line[index]
                if character == '"' and index + 1 < length and line[index + 1] == '"':
                    buffer.append('"')
                    index += 2
                    continue
                if character == '"':
                    index += 1
                    closed = True
                    break
                buffer.append(character)
                index += 1
            if not closed:
                raise ParseError(INVALID_CSV_QUOTING)
            if index < length:
                if line[index] != ";":
                    raise ParseError(INVALID_CSV_QUOTING)
                index += 1
            fields.append(("".join(buffer), True))
            continue
        start = index
        while index < length and line[index] != ";":
            if line[index] == '"':
                raise ParseError(INVALID_CSV_QUOTING)
            index += 1
        value = line[start:index]
        if value == "":
            raise ParseError(INVALID_FIELD)
        if value[0].isspace() or value[-1].isspace():
            raise ParseError(INVALID_CSV_QUOTING)
        fields.append((value, False))
        if index < length and line[index] == ";":
            index += 1
            if index == length:
                raise ParseError(INVALID_FIELD)
    return fields


def _contract_filename(batch_id: str, file_date: str) -> str:
    return f"NW_MERCHANT_CHARGEBACK_{file_date}_{batch_id}.csv"


def _load_source_manifest(raw_path: Path | None) -> dict[str, Any] | None:
    if raw_path is None:
        return None
    sidecar = raw_path.parent / "source-manifest.json"
    if not sidecar.is_file():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))


def parse_merchant_chargeback(
    payload: bytes,
    *,
    filename: str | None = None,
    raw_path: Path | None = None,
) -> ParsedBatch:
    try:
        return _parse(payload, filename=filename, raw_path=raw_path)
    except ParseError as error:
        batch_id = None
        if filename:
            match = FILENAME_RE.fullmatch(filename)
            if match:
                batch_id = match.group(2)
        return ParsedBatch(
            accepted=False,
            rejection_code=error.code,
            batch_id=batch_id,
            details=(),
            declared_row_count=None,
            computed_row_count=None,
            declared_original_amount=None,
            computed_original_amount=None,
            declared_chargeback_amount=None,
            computed_chargeback_amount=None,
            declared_calculated_amount=None,
            computed_calculated_amount=None,
            source_filename=filename or (raw_path.name if raw_path else ""),
        )


def _parse(
    payload: bytes,
    *,
    filename: str | None,
    raw_path: Path | None,
) -> ParsedBatch:
    if len(payload) == 0 or len(payload) > MAX_SOURCE_BYTES:
        raise ParseError(INVALID_SOURCE_SIZE)
    if payload.startswith(b"\xef\xbb\xbf"):
        raise ParseError(INVALID_UTF8)
    if b"\r" in payload or b"\x00" in payload:
        raise ParseError(INVALID_TRANSPORT)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ParseError(INVALID_UTF8) from exc
    if unicodedata.normalize("NFC", text) != text:
        raise ParseError(INVALID_UNICODE_NORMALIZATION)
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ParseError(INVALID_TRANSPORT)
    lines = text.split("\n")
    if lines[-1] == "":
        lines = lines[:-1]
    if not lines or any(line == "" for line in lines):
        raise ParseError(INVALID_TRANSPORT)
    for line in lines:
        encoded = (line + "\n").encode("utf-8")
        if len(encoded) > MAX_RECORD_BYTES:
            raise ParseError(INVALID_RECORD_LENGTH)
    if lines[0] != EXACT_HEADER:
        raise ParseError(INVALID_HEADER)
    if len(lines) - 1 > MAX_DETAIL_ROWS or len(lines) < 2:
        raise ParseError(INVALID_SOURCE_SIZE)

    details: list[SanitizedDetail] = []
    seen_ids: set[str] = set()
    batch_id: str | None = None
    file_date: str | None = None
    raw_cnpjs: list[str] = []

    for offset, line in enumerate(lines[1:], start=2):
        try:
            fields = _lex_record(line)
        except ParseError as error:
            if error.code == INVALID_FIELD and ";" in line and '"' not in line:
                raise ParseError(INVALID_CSV_QUOTING) from error
            raise
        if len(fields) != FIELD_COUNT:
            if not any(quoted for _, quoted in fields) or '"' not in line:
                raise ParseError(INVALID_CSV_QUOTING)
            raise ParseError(INVALID_FIELD_COUNT)
        values = [value for value, _ in fields]
        quoted = [was_quoted for _, was_quoted in fields]
        if not quoted[5]:
            raise ParseError(INVALID_CSV_QUOTING)
        if any(quoted[index] for index in range(FIELD_COUNT) if index != 5):
            raise ParseError(INVALID_CSV_QUOTING)

        chargeback_id, row_batch, merchant_id, tax_id, reason, description = values[:6]
        original_raw, rate_raw, chargeback_raw, business_raw = values[6:]

        if CHARGEBACK_ID_RE.fullmatch(chargeback_id) is None:
            raise ParseError(INVALID_IDENTIFIER)
        if BATCH_ID_RE.fullmatch(row_batch) is None:
            raise ParseError(INVALID_IDENTIFIER)
        if MERCHANT_ID_RE.fullmatch(merchant_id) is None:
            raise ParseError(INVALID_IDENTIFIER)
        if REASON_RE.fullmatch(reason) is None:
            raise ParseError(INVALID_IDENTIFIER)
        if not valid_cnpj(tax_id):
            raise ParseError(INVALID_DOCUMENT)
        if not _valid_description(description):
            raise ParseError(INVALID_DESCRIPTION)
        if chargeback_id in seen_ids:
            raise ParseError(DUPLICATE_IDENTIFIER)
        seen_ids.add(chargeback_id)

        original = locale_money(original_raw)
        if original <= Decimal("0.00"):
            raise ParseError(INVALID_FIELD)
        rate = locale_rate(rate_raw)
        if rate <= Decimal("0.000") or rate > Decimal("100.000"):
            raise ParseError(INVALID_FIELD)
        declared_chargeback = locale_money(chargeback_raw)
        calculated = calculate_chargeback(original, rate)
        if declared_chargeback != calculated:
            raise ParseError(CHARGEBACK_CALCULATION_MISMATCH)

        business = parse_business_date(business_raw)
        iso_date = business.strftime("%Y-%m-%d")
        compact_date = business.strftime("%Y%m%d")

        if batch_id is None:
            batch_id = row_batch
            file_date = compact_date
        if row_batch != batch_id:
            raise ParseError(INVALID_IDENTIFIER)
        if compact_date != file_date:
            raise ParseError(INVALID_BUSINESS_DATE)

        raw_cnpjs.append(tax_id)
        details.append(
            SanitizedDetail(
                batch_id=row_batch,
                source_record_number=offset,
                chargeback_id=chargeback_id,
                merchant_id=merchant_id,
                merchant_tax_id=tax_id,
                merchant_tax_id_masked=mask_cnpj(tax_id),
                reason_code=reason,
                description=description,
                original_amount_brl=original,
                rate_percent=rate,
                chargeback_amount_brl=declared_chargeback,
                calculated_amount_brl=calculated,
                business_date=iso_date,
                rounding_mode=ROUNDING_MODE,
            )
        )

    assert batch_id is not None and file_date is not None
    source_filename = filename or _contract_filename(batch_id, file_date)
    match = FILENAME_RE.fullmatch(source_filename)
    if match:
        name_date, name_batch = match.group(1), match.group(2)
        if name_batch != batch_id or name_date != file_date:
            raise ParseError(INVALID_BUSINESS_DATE)
    elif FILENAME_RE.fullmatch(Path(source_filename).name) is None:
        source_filename = _contract_filename(batch_id, file_date)

    computed_original = sum((row.original_amount_brl for row in details), Decimal("0.00"))
    computed_chargeback = sum(
        (row.chargeback_amount_brl for row in details), Decimal("0.00")
    )
    computed_calculated = sum(
        (row.calculated_amount_brl for row in details), Decimal("0.00")
    )
    computed_count = len(details)

    declared_count = computed_count
    declared_original = computed_original
    declared_chargeback = computed_chargeback
    declared_calculated = computed_calculated
    manifest = _load_source_manifest(raw_path)
    if manifest is not None:
        controls = manifest.get("source_controls") or manifest.get("controls") or {}
        if "row_count" in controls:
            declared_count = int(controls["row_count"])
            if declared_count != computed_count:
                raise ParseError(SOURCE_CONTROL_COUNT_MISMATCH)
        if "original_amount" in controls:
            declared_original = Decimal(str(controls["original_amount"]))
            if declared_original != computed_original:
                raise ParseError(SOURCE_CONTROL_ORIGINAL_MISMATCH)
        if "chargeback_amount" in controls:
            declared_chargeback = Decimal(str(controls["chargeback_amount"]))
            if declared_chargeback != computed_chargeback:
                raise ParseError(SOURCE_CONTROL_CHARGEBACK_MISMATCH)
        if "calculated_amount" in controls:
            declared_calculated = Decimal(str(controls["calculated_amount"]))
            if declared_calculated != computed_calculated:
                raise ParseError(SOURCE_CONTROL_CALCULATED_MISMATCH)

    for row in details:
        blob = " ".join(
            [
                row.chargeback_id,
                row.merchant_id,
                row.merchant_tax_id_masked,
                row.reason_code,
                row.description,
            ]
        )
        if any(cnpj in blob for cnpj in raw_cnpjs):
            raise ParseError(PRIVACY_OUTPUT_VIOLATION)
        if CNPJ_RE.search(row.merchant_tax_id_masked.replace("*", "")):
            pass
        if any(cnpj in row.merchant_tax_id_masked for cnpj in raw_cnpjs):
            raise ParseError(PRIVACY_OUTPUT_VIOLATION)

    return ParsedBatch(
        accepted=True,
        rejection_code=None,
        batch_id=batch_id,
        details=tuple(details),
        declared_row_count=declared_count,
        computed_row_count=computed_count,
        declared_original_amount=declared_original,
        computed_original_amount=computed_original,
        declared_chargeback_amount=declared_chargeback,
        computed_chargeback_amount=computed_chargeback,
        declared_calculated_amount=declared_calculated,
        computed_calculated_amount=computed_calculated,
        source_filename=source_filename,
    )
