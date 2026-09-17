"""Type 03 payment-slip-settlement parser — claim leg for ingest -> landing.

Reads byte-preserved CNAB-inspired `.rem` transport. Money is Decimal.
Privacy dies here (tokenize/mask before anything leaves this module). Does
not import Java. Does not write SFTP or frozen trees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping

SCALE = 2
MONEY_QUANTUM = Decimal("0.01")
ENCODING = "ascii"
RECORD_LENGTH = 240
FILE_TYPE_CODE = "PAYSLIPSET03"
LAYOUT_VERSION = "001"
ORIGIN_BANK_CODE = "NWP00001"
SERVICE_CODE = "SLIPSETTLE01"
CURRENCY = "BRL"

BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
STRUCTURED_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{15}$")
BANK_REF_RE = re.compile(r"^[A-Z][A-Z0-9]{19}$")
ORIGINATOR_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{15}$")
NAME_AFTER_TRIM_RE = re.compile(r"^[A-Z][A-Z0-9 .&/-]{0,39}$")
PAYMENT_REFERENCE_RE = re.compile(r"^[0-9]{48}$")
LOT_NUMBER_RE = re.compile(r"^(?!000000)[0-9]{6}$")
SEQUENCE_RE = re.compile(r"^(?!000000)[0-9]{6}$")
FILE_SEQUENCE_RE = re.compile(r"^[0-9]{6}$")
BANK_CODE_RE = re.compile(r"^(?!000$)[0-9]{3}$")
BRANCH_RE = re.compile(r"^[0-9]{5}$")
ACCOUNT_RE = re.compile(r"^[0-9]{12}$")
CHECK_DIGIT_RE = re.compile(r"^[A-Z0-9]$")

PAYMENT_REFERENCE_KEY_ENV = "NWP_PAYMENT_REFERENCE_KEY"
PARTY_TOKEN_KEY_ENV = "NWP_PARTY_TOKEN_KEY"
ACCOUNT_TOKEN_KEY_ENV = "NWP_ACCOUNT_TOKEN_KEY"
TOKENIZATION_KEY_FALLBACK_ENV = "NWP_TOKENIZATION_KEY"

INVALID_TRANSPORT = "INVALID_TRANSPORT"
INVALID_RECORD_LENGTH = "INVALID_RECORD_LENGTH"
INVALID_RECORD_SEQUENCE = "INVALID_RECORD_SEQUENCE"
INVALID_FILLER = "INVALID_FILLER"
INVALID_FIELD = "INVALID_FIELD"
INVALID_DOCUMENT = "INVALID_DOCUMENT"
INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
SEGMENT_PAIR_MISMATCH = "SEGMENT_PAIR_MISMATCH"
DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"
INVALID_BUSINESS_DATE = "INVALID_BUSINESS_DATE"
SOURCE_CONTROL_LOT_COUNT_MISMATCH = "SOURCE_CONTROL_LOT_COUNT_MISMATCH"
SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH = "SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH"
SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH = "SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH"
SOURCE_CONTROL_FACE_MISMATCH = "SOURCE_CONTROL_FACE_MISMATCH"
SOURCE_CONTROL_DISCOUNT_MISMATCH = "SOURCE_CONTROL_DISCOUNT_MISMATCH"
SOURCE_CONTROL_FEE_MISMATCH = "SOURCE_CONTROL_FEE_MISMATCH"
SOURCE_CONTROL_NET_MISMATCH = "SOURCE_CONTROL_NET_MISMATCH"
TOKENIZATION_KEY_MISSING = "TOKENIZATION_KEY_MISSING"


class ParseError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def _slice(record: str, start: int, end: int) -> str:
    return record[start - 1 : end]


def _resolve_key(env_name: str, explicit: bytes | None) -> bytes:
    if explicit is not None:
        return explicit
    value = os.environ.get(env_name) or os.environ.get(TOKENIZATION_KEY_FALLBACK_ENV)
    if not value:
        raise ParseError(TOKENIZATION_KEY_MISSING)
    return value.encode("utf-8")


def resolve_keys(
    keys: Mapping[str, bytes] | None = None,
) -> tuple[bytes, bytes, bytes]:
    keys = keys or {}
    payment_reference_key = _resolve_key(
        PAYMENT_REFERENCE_KEY_ENV, keys.get("payment_reference")
    )
    party_key = _resolve_key(PARTY_TOKEN_KEY_ENV, keys.get("party"))
    account_key = _resolve_key(ACCOUNT_TOKEN_KEY_ENV, keys.get("account"))
    return payment_reference_key, party_key, account_key


def _hmac_token(prefix: str, value: str, key: bytes) -> str:
    digest = hmac.new(key, value.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:24]}"


def tokenize_payment_reference(raw: str, key: bytes) -> tuple[str, str]:
    if not PAYMENT_REFERENCE_RE.match(raw):
        raise ParseError(INVALID_FIELD)
    return _hmac_token("payref", raw, key), raw[-4:]


def tokenize_beneficiary_name(raw_padded: str, key: bytes) -> tuple[str, str]:
    trimmed = raw_padded.rstrip(" ")
    if not NAME_AFTER_TRIM_RE.match(trimmed):
        raise ParseError(INVALID_FIELD)
    return _hmac_token("party", trimmed, key), trimmed


def tokenize_bank_account(
    bank_code: str, branch_number: str, account_number: str, check_digit: str, key: bytes
) -> tuple[str, str]:
    if not BANK_CODE_RE.match(bank_code):
        raise ParseError(INVALID_FIELD)
    if not BRANCH_RE.match(branch_number):
        raise ParseError(INVALID_FIELD)
    if not ACCOUNT_RE.match(account_number):
        raise ParseError(INVALID_FIELD)
    if not CHECK_DIGIT_RE.match(check_digit):
        raise ParseError(INVALID_FIELD)
    canonical = f"{bank_code}:{branch_number}:{account_number}:{check_digit}"
    return _hmac_token("acct", canonical, key), account_number[-4:]


def _mod11_check_digits(base: str, weights: list[int]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(base, weights))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def cpf_check_digits_valid(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit():
        return False
    if cpf == cpf[0] * 11:
        return False
    d1 = _mod11_check_digits(cpf[:9], list(range(10, 1, -1)))
    d2 = _mod11_check_digits(cpf[:9] + d1, list(range(11, 1, -1)))
    return cpf[9:] == d1 + d2


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


def mask_tax_id(tax_id_type: str, transport_value: str) -> tuple[str, str, str]:
    """Validate and mask a 14-char beneficiary tax-id transport field.

    Returns (csv_type_label, masked_value, raw_document_for_privacy_scan).
    """
    if len(transport_value) != 14 or not transport_value.isdigit():
        raise ParseError(INVALID_DOCUMENT)
    if tax_id_type == "1":
        if transport_value[:3] != "000":
            raise ParseError(INVALID_DOCUMENT)
        cpf = transport_value[3:]
        if not cpf_check_digits_valid(cpf):
            raise ParseError(INVALID_DOCUMENT)
        return "CPF", "*******" + cpf[-4:], cpf
    if tax_id_type == "2":
        cnpj = transport_value
        if not cnpj_check_digits_valid(cnpj):
            raise ParseError(INVALID_DOCUMENT)
        return "CNPJ", "**********" + cnpj[-4:], cnpj
    raise ParseError(INVALID_FIELD)


def decode_implied_decimal(raw: str, *, scale: int = SCALE) -> Decimal:
    if not raw.isdigit():
        raise ParseError(INVALID_FIELD)
    return (Decimal(raw) / (Decimal(10) ** scale)).quantize(MONEY_QUANTUM)


def _parse_date(raw: str) -> date:
    if len(raw) != 8 or not raw.isdigit():
        raise ParseError(INVALID_FIELD)
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError as exc:
        raise ParseError(INVALID_FIELD) from exc


def _iso_date(raw: str) -> str:
    parsed = _parse_date(raw)
    return parsed.isoformat()


@dataclass(frozen=True)
class SanitizedSettlement:
    batch_id: str
    source_record_number_a: int
    source_record_number_b: int
    lot_number: str
    sequence: str
    settlement_id: str
    payment_reference_token: str
    payment_reference_last4: str
    beneficiary_token: str
    beneficiary_tax_id_type: str
    beneficiary_tax_id_masked: str
    bank_account_token: str
    bank_account_last4: str
    due_date: str
    payment_date: str
    face_amount_brl: Decimal
    discount_brl: Decimal
    fee_brl: Decimal
    net_amount_brl: Decimal
    status: str
    bank_reference: str
    client_reference: str

    def parquet_ready(self) -> Mapping[str, object]:
        return {
            "batch_id": self.batch_id,
            "source_record_number_a": self.source_record_number_a,
            "source_record_number_b": self.source_record_number_b,
            "lot_number": self.lot_number,
            "sequence": self.sequence,
            "settlement_id": self.settlement_id,
            "payment_reference_token": self.payment_reference_token,
            "payment_reference_last4": self.payment_reference_last4,
            "beneficiary_token": self.beneficiary_token,
            "beneficiary_tax_id_type": self.beneficiary_tax_id_type,
            "beneficiary_tax_id_masked": self.beneficiary_tax_id_masked,
            "bank_account_token": self.bank_account_token,
            "bank_account_last4": self.bank_account_last4,
            "due_date": self.due_date,
            "payment_date": self.payment_date,
            "face_amount_brl": self.face_amount_brl,
            "discount_brl": self.discount_brl,
            "fee_brl": self.fee_brl,
            "net_amount_brl": self.net_amount_brl,
            "status": self.status,
            "bank_reference": self.bank_reference,
            "client_reference": self.client_reference,
        }


@dataclass(frozen=True)
class ParseResult:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    controls: dict[str, object]
    settlements: tuple[SanitizedSettlement, ...]
    landing_destination: str = "modern/landing/"


def _decode_transport(payload: bytes) -> str:
    if not payload:
        raise ParseError(INVALID_TRANSPORT)
    try:
        text = payload.decode(ENCODING)
    except UnicodeDecodeError as exc:
        raise ParseError(INVALID_TRANSPORT) from exc
    if not text.endswith("\r\n"):
        raise ParseError(INVALID_TRANSPORT)
    return text


def _split_records(text: str) -> list[str]:
    lines = text.split("\r\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    else:
        raise ParseError(INVALID_TRANSPORT)
    if not lines:
        raise ParseError(INVALID_RECORD_SEQUENCE)
    for line in lines:
        if "\r" in line or "\n" in line:
            raise ParseError(INVALID_TRANSPORT)
        if len(line) != RECORD_LENGTH:
            raise ParseError(INVALID_RECORD_LENGTH)
    return lines


def _check_filler(record: str, start: int, end: int) -> None:
    if _slice(record, start, end) != "~" * (end - start + 1):
        raise ParseError(INVALID_FILLER)


def _parse_file_header(record: str) -> dict[str, str]:
    if _slice(record, 1, 1) != "H":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    file_date_raw = _slice(record, 2, 9)
    batch_id = _slice(record, 10, 25)
    file_type_code = _slice(record, 26, 37)
    layout_version = _slice(record, 38, 40)
    origin_bank_code = _slice(record, 41, 48)
    file_sequence = _slice(record, 49, 54)
    _check_filler(record, 55, 240)
    _parse_date(file_date_raw)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    if file_type_code != FILE_TYPE_CODE or layout_version != LAYOUT_VERSION:
        raise ParseError(INVALID_FIELD)
    if origin_bank_code != ORIGIN_BANK_CODE:
        raise ParseError(INVALID_FIELD)
    if not FILE_SEQUENCE_RE.match(file_sequence):
        raise ParseError(INVALID_FIELD)
    if file_sequence != batch_id[-6:]:
        raise ParseError(INVALID_FIELD)
    return {"file_date": file_date_raw, "batch_id": batch_id}


def _parse_lot_header(record: str) -> dict[str, str]:
    if _slice(record, 1, 1) != "L":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    lot_number = _slice(record, 2, 7)
    service_code = _slice(record, 8, 19)
    currency = _slice(record, 20, 22)
    settlement_date_raw = _slice(record, 23, 30)
    batch_id = _slice(record, 31, 46)
    originator_id = _slice(record, 47, 62)
    _check_filler(record, 63, 240)
    if not LOT_NUMBER_RE.match(lot_number):
        raise ParseError(INVALID_FIELD)
    if service_code != SERVICE_CODE:
        raise ParseError(INVALID_FIELD)
    if currency != CURRENCY:
        raise ParseError(INVALID_FIELD)
    _parse_date(settlement_date_raw)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    if not ORIGINATOR_ID_RE.match(originator_id):
        raise ParseError(INVALID_IDENTIFIER)
    return {
        "lot_number": lot_number,
        "settlement_date": settlement_date_raw,
        "batch_id": batch_id,
    }


def _parse_financial_segment(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "A":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    lot_number = _slice(record, 2, 7)
    sequence = _slice(record, 8, 13)
    settlement_id = _slice(record, 14, 29)
    payment_reference = _slice(record, 30, 77)
    face_amount = decode_implied_decimal(_slice(record, 78, 92))
    due_date_raw = _slice(record, 93, 100)
    payment_date_raw = _slice(record, 101, 108)
    discount = decode_implied_decimal(_slice(record, 109, 120))
    fee = decode_implied_decimal(_slice(record, 121, 132))
    status_code = _slice(record, 133, 134)
    bank_reference = _slice(record, 135, 154)
    _check_filler(record, 155, 240)
    if not LOT_NUMBER_RE.match(lot_number):
        raise ParseError(INVALID_FIELD)
    if not SEQUENCE_RE.match(sequence):
        raise ParseError(INVALID_FIELD)
    if not STRUCTURED_ID_RE.match(settlement_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not PAYMENT_REFERENCE_RE.match(payment_reference):
        raise ParseError(INVALID_FIELD)
    if face_amount <= Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    due_date = _parse_date(due_date_raw)
    payment_date = _parse_date(payment_date_raw)
    if discount < Decimal("0.00") or fee < Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    if discount > face_amount:
        raise ParseError(INVALID_FIELD)
    if status_code != "00":
        raise ParseError(INVALID_FIELD)
    if not BANK_REF_RE.match(bank_reference):
        raise ParseError(INVALID_IDENTIFIER)
    net_amount = (face_amount - discount + fee).quantize(MONEY_QUANTUM)
    if net_amount < Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    return {
        "lot_number": lot_number,
        "sequence": sequence,
        "settlement_id": settlement_id,
        "payment_reference": payment_reference,
        "face_amount_brl": face_amount,
        "due_date": due_date,
        "payment_date": payment_date,
        "due_date_iso": due_date.isoformat(),
        "payment_date_iso": payment_date.isoformat(),
        "discount_brl": discount,
        "fee_brl": fee,
        "bank_reference": bank_reference,
        "net_amount_brl": net_amount,
    }


def _parse_beneficiary_segment(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "B":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    lot_number = _slice(record, 2, 7)
    sequence = _slice(record, 8, 13)
    settlement_id = _slice(record, 14, 29)
    tax_id_type = _slice(record, 30, 30)
    beneficiary_tax_id = _slice(record, 31, 44)
    beneficiary_name = _slice(record, 45, 84)
    bank_code = _slice(record, 85, 87)
    branch_number = _slice(record, 88, 92)
    account_number = _slice(record, 93, 104)
    account_check_digit = _slice(record, 105, 105)
    client_reference = _slice(record, 106, 125)
    _check_filler(record, 126, 240)
    if not LOT_NUMBER_RE.match(lot_number):
        raise ParseError(INVALID_FIELD)
    if not SEQUENCE_RE.match(sequence):
        raise ParseError(INVALID_FIELD)
    if not STRUCTURED_ID_RE.match(settlement_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not BANK_CODE_RE.match(bank_code):
        raise ParseError(INVALID_FIELD)
    if not BRANCH_RE.match(branch_number):
        raise ParseError(INVALID_FIELD)
    if not ACCOUNT_RE.match(account_number):
        raise ParseError(INVALID_FIELD)
    if not CHECK_DIGIT_RE.match(account_check_digit):
        raise ParseError(INVALID_FIELD)
    if not BANK_REF_RE.match(client_reference):
        raise ParseError(INVALID_IDENTIFIER)
    return {
        "lot_number": lot_number,
        "sequence": sequence,
        "settlement_id": settlement_id,
        "tax_id_type": tax_id_type,
        "beneficiary_tax_id": beneficiary_tax_id,
        "beneficiary_name": beneficiary_name,
        "bank_code": bank_code,
        "branch_number": branch_number,
        "account_number": account_number,
        "account_check_digit": account_check_digit,
        "client_reference": client_reference,
    }


def _parse_lot_trailer(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "T":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    lot_number = _slice(record, 2, 7)
    logical_count_raw = _slice(record, 8, 13)
    face_raw = _slice(record, 14, 28)
    discount_raw = _slice(record, 29, 43)
    fee_raw = _slice(record, 44, 58)
    net_raw = _slice(record, 59, 73)
    batch_id = _slice(record, 74, 89)
    _check_filler(record, 90, 240)
    if not LOT_NUMBER_RE.match(lot_number):
        raise ParseError(INVALID_FIELD)
    if not logical_count_raw.isdigit():
        raise ParseError(INVALID_FIELD)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    return {
        "lot_number": lot_number,
        "logical_count": int(logical_count_raw, 10),
        "face_amount_brl": decode_implied_decimal(face_raw),
        "discount_brl": decode_implied_decimal(discount_raw),
        "fee_brl": decode_implied_decimal(fee_raw),
        "net_amount_brl": decode_implied_decimal(net_raw),
        "batch_id": batch_id,
    }


def _parse_file_trailer(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "Z":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    lot_count_raw = _slice(record, 2, 7)
    physical_count_raw = _slice(record, 8, 13)
    logical_count_raw = _slice(record, 14, 19)
    net_raw = _slice(record, 20, 34)
    batch_id = _slice(record, 35, 50)
    _check_filler(record, 51, 240)
    if not lot_count_raw.isdigit() or not physical_count_raw.isdigit() or not logical_count_raw.isdigit():
        raise ParseError(INVALID_FIELD)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    return {
        "lot_count": int(lot_count_raw, 10),
        "physical_record_count": int(physical_count_raw, 10),
        "logical_count": int(logical_count_raw, 10),
        "net_amount_brl": decode_implied_decimal(net_raw),
        "batch_id": batch_id,
    }


def parse_payment_slip_settlement(
    payload: bytes,
    *,
    filename: str | None = None,
    keys: Mapping[str, bytes] | None = None,
) -> ParseResult:
    """Parse one Type 03 raw `.rem` file. Refused batches yield zero settlements."""
    try:
        payment_reference_key, party_key, account_key = resolve_keys(keys)
        text = _decode_transport(payload)
        lines = _split_records(text)
        header = _parse_file_header(lines[0])
        batch_id = header["batch_id"]
        if filename:
            match = re.search(r"(\d{8})_(B[0-9]{15})\.rem$", filename)
            if match and (
                match.group(1) != header["file_date"] or match.group(2) != batch_id
            ):
                raise ParseError(INVALID_FIELD)

        idx = 1
        lots: list[dict[str, object]] = []
        seen_settlement_ids: set[str] = set()
        while idx < len(lines) and lines[idx][0:1] == "L":
            lot_header = _parse_lot_header(lines[idx])
            if lot_header["batch_id"] != batch_id:
                raise ParseError(INVALID_FIELD)
            idx += 1
            pairs: list[SanitizedSettlement] = []
            while (
                idx + 1 < len(lines)
                and lines[idx][0:1] == "A"
                and lines[idx + 1][0:1] == "B"
            ):
                a_number = idx + 1
                b_number = idx + 2
                a_fields = _parse_financial_segment(lines[idx])
                b_fields = _parse_beneficiary_segment(lines[idx + 1])
                if (
                    a_fields["lot_number"] != b_fields["lot_number"]
                    or a_fields["sequence"] != b_fields["sequence"]
                    or a_fields["settlement_id"] != b_fields["settlement_id"]
                    or a_fields["lot_number"] != lot_header["lot_number"]
                ):
                    raise ParseError(SEGMENT_PAIR_MISMATCH)
                if a_fields["payment_date_iso"] != _iso_date(lot_header["settlement_date"]):
                    raise ParseError(INVALID_BUSINESS_DATE)
                if a_fields["payment_date"] > a_fields["due_date"]:
                    raise ParseError(INVALID_BUSINESS_DATE)
                settlement_id = a_fields["settlement_id"]
                if settlement_id in seen_settlement_ids:
                    raise ParseError(DUPLICATE_IDENTIFIER)
                seen_settlement_ids.add(settlement_id)

                payment_reference_token, payment_reference_last4 = tokenize_payment_reference(
                    a_fields["payment_reference"], payment_reference_key
                )
                beneficiary_token, _ = tokenize_beneficiary_name(
                    b_fields["beneficiary_name"], party_key
                )
                tax_id_label, tax_id_masked, _ = mask_tax_id(
                    b_fields["tax_id_type"], b_fields["beneficiary_tax_id"]
                )
                bank_account_token, bank_account_last4 = tokenize_bank_account(
                    b_fields["bank_code"],
                    b_fields["branch_number"],
                    b_fields["account_number"],
                    b_fields["account_check_digit"],
                    account_key,
                )
                pairs.append(
                    SanitizedSettlement(
                        batch_id=batch_id,
                        source_record_number_a=a_number,
                        source_record_number_b=b_number,
                        lot_number=a_fields["lot_number"],
                        sequence=a_fields["sequence"],
                        settlement_id=settlement_id,
                        payment_reference_token=payment_reference_token,
                        payment_reference_last4=payment_reference_last4,
                        beneficiary_token=beneficiary_token,
                        beneficiary_tax_id_type=tax_id_label,
                        beneficiary_tax_id_masked=tax_id_masked,
                        bank_account_token=bank_account_token,
                        bank_account_last4=bank_account_last4,
                        due_date=a_fields["due_date_iso"],
                        payment_date=a_fields["payment_date_iso"],
                        face_amount_brl=a_fields["face_amount_brl"],
                        discount_brl=a_fields["discount_brl"],
                        fee_brl=a_fields["fee_brl"],
                        net_amount_brl=a_fields["net_amount_brl"],
                        status="SETTLED",
                        bank_reference=a_fields["bank_reference"],
                        client_reference=b_fields["client_reference"],
                    )
                )
                idx += 2
            if not pairs:
                raise ParseError(INVALID_RECORD_SEQUENCE)
            if idx >= len(lines) or lines[idx][0:1] != "T":
                raise ParseError(INVALID_RECORD_SEQUENCE)
            lot_trailer = _parse_lot_trailer(lines[idx])
            if lot_trailer["lot_number"] != lot_header["lot_number"]:
                raise ParseError(INVALID_FIELD)
            if lot_trailer["batch_id"] != batch_id:
                raise ParseError(INVALID_FIELD)
            computed_face = sum((row.face_amount_brl for row in pairs), Decimal("0.00"))
            computed_discount = sum((row.discount_brl for row in pairs), Decimal("0.00"))
            computed_fee = sum((row.fee_brl for row in pairs), Decimal("0.00"))
            computed_net = sum((row.net_amount_brl for row in pairs), Decimal("0.00"))
            if lot_trailer["logical_count"] != len(pairs):
                raise ParseError(SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH)
            if lot_trailer["face_amount_brl"] != computed_face:
                raise ParseError(SOURCE_CONTROL_FACE_MISMATCH)
            if lot_trailer["discount_brl"] != computed_discount:
                raise ParseError(SOURCE_CONTROL_DISCOUNT_MISMATCH)
            if lot_trailer["fee_brl"] != computed_fee:
                raise ParseError(SOURCE_CONTROL_FEE_MISMATCH)
            if lot_trailer["net_amount_brl"] != computed_net:
                raise ParseError(SOURCE_CONTROL_NET_MISMATCH)
            idx += 1
            lots.append({"pairs": pairs})

        if not lots:
            raise ParseError(INVALID_RECORD_SEQUENCE)
        if idx >= len(lines) or lines[idx][0:1] != "Z":
            raise ParseError(INVALID_RECORD_SEQUENCE)
        file_trailer = _parse_file_trailer(lines[idx])
        idx += 1
        if idx != len(lines):
            raise ParseError(INVALID_RECORD_SEQUENCE)
        if file_trailer["batch_id"] != batch_id:
            raise ParseError(INVALID_FIELD)

        all_pairs: tuple[SanitizedSettlement, ...] = tuple(
            row for lot in lots for row in lot["pairs"]
        )
        computed_lot_count = len(lots)
        computed_physical_record_count = len(lines)
        computed_logical_count = len(all_pairs)
        computed_net = sum((row.net_amount_brl for row in all_pairs), Decimal("0.00"))

        controls: dict[str, object] = {
            "declared_lot_count": file_trailer["lot_count"],
            "computed_lot_count": computed_lot_count,
            "declared_physical_record_count": file_trailer["physical_record_count"],
            "computed_physical_record_count": computed_physical_record_count,
            "declared_logical_count": file_trailer["logical_count"],
            "computed_logical_count": computed_logical_count,
            "declared_net_amount": _money_text(file_trailer["net_amount_brl"]),
            "computed_net_amount": _money_text(computed_net),
        }

        if file_trailer["lot_count"] != computed_lot_count:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_LOT_COUNT_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                settlements=(),
            )
        if file_trailer["physical_record_count"] != computed_physical_record_count:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                settlements=(),
            )
        if file_trailer["logical_count"] != computed_logical_count:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                settlements=(),
            )
        if file_trailer["net_amount_brl"] != computed_net:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_NET_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                settlements=(),
            )

        return ParseResult(
            accepted=True,
            rejection_code=None,
            batch_id=batch_id,
            controls=controls,
            settlements=all_pairs,
        )
    except ParseError as exc:
        return ParseResult(
            accepted=False,
            rejection_code=exc.code,
            batch_id=None,
            controls={},
            settlements=(),
        )


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(MONEY_QUANTUM):.2f}"


__all__ = [
    "ParseError",
    "ParseResult",
    "SanitizedSettlement",
    "cnpj_check_digits_valid",
    "cpf_check_digits_valid",
    "decode_implied_decimal",
    "mask_tax_id",
    "parse_payment_slip_settlement",
    "resolve_keys",
    "tokenize_bank_account",
    "tokenize_beneficiary_name",
    "tokenize_payment_reference",
]
