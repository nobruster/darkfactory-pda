"""Type 04 ted-transfer-settlement parser — claim leg for ingest -> landing.

Reads byte-preserved heterogeneous fixed-width `.dat` transport (H/D/R/T).
Money is Decimal. Privacy dies here (tokenize/mask before anything leaves
this module). Does not import Java. Does not write SFTP or frozen trees.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping
from zoneinfo import ZoneInfo

SCALE = 2
MONEY_QUANTUM = Decimal("0.01")
ENCODING = "ascii"
FILE_TYPE_CODE = "TED_SETTLE04"
LAYOUT_VERSION = "001"
CURRENCY = "BRL"
SOURCE_ZONE = ZoneInfo("America/Sao_Paulo")

HEADER_LENGTH = 56
TRANSFER_LENGTH = 162
RETURN_LENGTH = 91
TRAILER_LENGTH = 82
RECORD_LENGTHS = {
    "H": HEADER_LENGTH,
    "D": TRANSFER_LENGTH,
    "R": RETURN_LENGTH,
    "T": TRAILER_LENGTH,
}

BATCH_ID_RE = re.compile(r"^B[0-9]{15}$")
STRUCTURED_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{15}$")
PURPOSE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
REASON_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{4}$")
BENEFICIARY_NAME_RE = re.compile(r"^[A-Z][A-Z0-9 .&/-]{0,22}$")
REASON_TEXT_RE = re.compile(r"^[A-Z][A-Z0-9 .&/-]{0,23}$")

ACCOUNT_TOKEN_KEY_ENV = "NWP_TED_ACCOUNT_TOKEN_KEY"
TOKENIZATION_KEY_FALLBACK_ENV = "NWP_TOKENIZATION_KEY"

INVALID_TRANSPORT = "INVALID_TRANSPORT"
INVALID_RECORD_LENGTH = "INVALID_RECORD_LENGTH"
INVALID_RECORD_SEQUENCE = "INVALID_RECORD_SEQUENCE"
INVALID_PADDING = "INVALID_PADDING"
INVALID_FIELD = "INVALID_FIELD"
INVALID_DOCUMENT = "INVALID_DOCUMENT"
INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
RETURN_LINK_MISMATCH = "RETURN_LINK_MISMATCH"
INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"
SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH = "SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH"
SOURCE_CONTROL_RETURN_COUNT_MISMATCH = "SOURCE_CONTROL_RETURN_COUNT_MISMATCH"
SOURCE_CONTROL_GROSS_MISMATCH = "SOURCE_CONTROL_GROSS_MISMATCH"
SOURCE_CONTROL_RETURNED_MISMATCH = "SOURCE_CONTROL_RETURNED_MISMATCH"
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


def resolve_keys(keys: Mapping[str, bytes] | None = None) -> bytes:
    keys = keys or {}
    return _resolve_key(ACCOUNT_TOKEN_KEY_ENV, keys.get("account"))


def _hmac_token(prefix: str, value: str, key: bytes) -> str:
    digest = hmac.new(key, value.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:24]}"


def tokenize_account(ispb: str, branch: str, account: str, key: bytes) -> str:
    canonical = f"{ispb}:{branch}:{account}"
    return _hmac_token("tedacct", canonical, key)


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


def mask_tax_id(party_type: str, transport_value: str) -> str:
    """Validate a 14-char tax-id transport field and return its mask."""
    if len(transport_value) != 14 or not transport_value.isdigit():
        raise ParseError(INVALID_DOCUMENT)
    if party_type == "F":
        if transport_value[:3] != "000":
            raise ParseError(INVALID_DOCUMENT)
        cpf = transport_value[3:]
        if not cpf_check_digits_valid(cpf):
            raise ParseError(INVALID_DOCUMENT)
        return "*******" + cpf[-4:]
    if party_type == "J":
        cnpj = transport_value
        if not cnpj_check_digits_valid(cnpj):
            raise ParseError(INVALID_DOCUMENT)
        return "**********" + cnpj[-4:]
    raise ParseError(INVALID_FIELD)


def decode_implied_decimal(raw: str, *, scale: int = SCALE) -> Decimal:
    if not raw.isdigit():
        raise ParseError(INVALID_FIELD)
    return (Decimal(raw) / (Decimal(10) ** scale)).quantize(MONEY_QUANTUM)


def _decode_signed(
    sign: str, magnitude_raw: str, *, allowed_signs: tuple[str, ...]
) -> Decimal:
    if sign not in allowed_signs:
        raise ParseError(INVALID_FIELD)
    magnitude = decode_implied_decimal(magnitude_raw)
    if magnitude == Decimal("0.00") and sign == "-":
        raise ParseError(INVALID_FIELD)
    return magnitude if sign == "+" else -magnitude


def _parse_ymd(raw: str) -> tuple[int, int, int]:
    if len(raw) != 8 or not raw.isdigit():
        raise ParseError(INVALID_FIELD)
    year, month, day = int(raw[0:4]), int(raw[4:6]), int(raw[6:8])
    return year, month, day


def _parse_hms(raw: str) -> tuple[int, int, int]:
    if len(raw) != 6 or not raw.isdigit():
        raise ParseError(INVALID_FIELD)
    hour, minute, second = int(raw[0:2]), int(raw[2:4]), int(raw[4:6])
    return hour, minute, second


def _local_datetime(date_raw: str, time_raw: str) -> datetime:
    year, month, day = _parse_ymd(date_raw)
    hour, minute, second = _parse_hms(time_raw)
    try:
        naive = datetime(year, month, day, hour, minute, second)
    except ValueError as exc:
        raise ParseError(INVALID_TIMESTAMP) from exc
    localized = naive.replace(tzinfo=SOURCE_ZONE)
    if localized.utcoffset() is None:
        raise ParseError(INVALID_TIMESTAMP)
    return localized


def _iso_instant(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _strip_tilde(raw: str) -> str:
    return raw.rstrip("~")


def _check_padding(raw: str, pattern: re.Pattern[str]) -> str:
    trimmed = _strip_tilde(raw)
    if not pattern.match(trimmed):
        raise ParseError(INVALID_PADDING)
    return trimmed


@dataclass(frozen=True)
class SanitizedMovement:
    batch_id: str
    source_record_number: int
    movement_id: str
    original_transfer_id: str | None
    movement_kind: str
    movement_ts: str
    amount_brl: Decimal
    payer_account_token: str
    payer_tax_id_masked: str
    beneficiary_account_token: str
    beneficiary_tax_id_masked: str
    beneficiary_ispb: str
    purpose_code: str
    status_code: str
    return_reason_code: str | None


@dataclass(frozen=True)
class ParseResult:
    accepted: bool
    rejection_code: str | None
    batch_id: str | None
    controls: dict[str, object]
    movements: tuple[SanitizedMovement, ...]
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
        if not line:
            raise ParseError(INVALID_RECORD_SEQUENCE)
        discriminator = line[0:1]
        if discriminator not in RECORD_LENGTHS:
            raise ParseError(INVALID_RECORD_SEQUENCE)
        if len(line) != RECORD_LENGTHS[discriminator]:
            raise ParseError(INVALID_RECORD_LENGTH)
    return lines


def _parse_header(record: str) -> dict[str, str]:
    if _slice(record, 1, 1) != "H":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    file_date = _slice(record, 2, 9)
    batch_id = _slice(record, 10, 25)
    file_type_code = _slice(record, 26, 37)
    layout_version = _slice(record, 38, 40)
    settlement_date = _slice(record, 41, 48)
    origin_ispb = _slice(record, 49, 56)
    _parse_ymd(file_date)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    if file_type_code != FILE_TYPE_CODE or layout_version != LAYOUT_VERSION:
        raise ParseError(INVALID_FIELD)
    _parse_ymd(settlement_date)
    if not origin_ispb.isdigit() or len(origin_ispb) != 8:
        raise ParseError(INVALID_FIELD)
    return {
        "file_date": file_date,
        "batch_id": batch_id,
        "settlement_date": settlement_date,
    }


def _parse_transfer(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "D":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    transfer_id = _slice(record, 2, 17)
    amount_sign = _slice(record, 18, 18)
    amount_magnitude = _slice(record, 19, 32)
    currency = _slice(record, 33, 35)
    transfer_date = _slice(record, 36, 43)
    transfer_time = _slice(record, 44, 49)
    payer_ispb = _slice(record, 50, 57)
    payer_branch = _slice(record, 58, 61)
    payer_account = _slice(record, 62, 73)
    payer_tax_id = _slice(record, 74, 87)
    payer_party_type = _slice(record, 88, 88)
    beneficiary_ispb = _slice(record, 89, 96)
    beneficiary_branch = _slice(record, 97, 100)
    beneficiary_account = _slice(record, 101, 112)
    beneficiary_tax_id = _slice(record, 113, 126)
    beneficiary_party_type = _slice(record, 127, 127)
    purpose_code_raw = _slice(record, 128, 137)
    status_code = _slice(record, 138, 139)
    beneficiary_name_raw = _slice(record, 140, 162)

    if not STRUCTURED_ID_RE.match(transfer_id):
        raise ParseError(INVALID_IDENTIFIER)
    amount = _decode_signed(amount_sign, amount_magnitude, allowed_signs=("+",))
    if amount <= Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    if currency != CURRENCY:
        raise ParseError(INVALID_FIELD)
    _parse_ymd(transfer_date)
    _parse_hms(transfer_time)
    if not (payer_ispb.isdigit() and len(payer_ispb) == 8):
        raise ParseError(INVALID_FIELD)
    if not (payer_branch.isdigit() and len(payer_branch) == 4):
        raise ParseError(INVALID_FIELD)
    if not (payer_account.isdigit() and len(payer_account) == 12):
        raise ParseError(INVALID_FIELD)
    if payer_party_type not in ("F", "J"):
        raise ParseError(INVALID_FIELD)
    if not (beneficiary_ispb.isdigit() and len(beneficiary_ispb) == 8):
        raise ParseError(INVALID_FIELD)
    if not (beneficiary_branch.isdigit() and len(beneficiary_branch) == 4):
        raise ParseError(INVALID_FIELD)
    if not (beneficiary_account.isdigit() and len(beneficiary_account) == 12):
        raise ParseError(INVALID_FIELD)
    if beneficiary_party_type not in ("F", "J"):
        raise ParseError(INVALID_FIELD)
    purpose_code = _check_padding(purpose_code_raw, PURPOSE_CODE_RE)
    if status_code not in ("OK", "RT"):
        raise ParseError(INVALID_FIELD)
    beneficiary_name = _check_padding(beneficiary_name_raw, BENEFICIARY_NAME_RE)

    return {
        "transfer_id": transfer_id,
        "amount_brl": amount,
        "transfer_date": transfer_date,
        "transfer_time": transfer_time,
        "payer_ispb": payer_ispb,
        "payer_branch": payer_branch,
        "payer_account": payer_account,
        "payer_tax_id": payer_tax_id,
        "payer_party_type": payer_party_type,
        "beneficiary_ispb": beneficiary_ispb,
        "beneficiary_branch": beneficiary_branch,
        "beneficiary_account": beneficiary_account,
        "beneficiary_tax_id": beneficiary_tax_id,
        "beneficiary_party_type": beneficiary_party_type,
        "purpose_code": purpose_code,
        "status_code": status_code,
        "beneficiary_name": beneficiary_name,
    }


def _parse_return(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "R":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    return_id = _slice(record, 2, 17)
    original_transfer_id = _slice(record, 18, 33)
    amount_sign = _slice(record, 34, 34)
    amount_magnitude = _slice(record, 35, 48)
    return_date = _slice(record, 49, 56)
    return_time = _slice(record, 57, 62)
    reason_code = _slice(record, 63, 67)
    reason_text_raw = _slice(record, 68, 91)

    if not STRUCTURED_ID_RE.match(return_id):
        raise ParseError(INVALID_IDENTIFIER)
    if not STRUCTURED_ID_RE.match(original_transfer_id):
        raise ParseError(INVALID_IDENTIFIER)
    amount = _decode_signed(amount_sign, amount_magnitude, allowed_signs=("-",))
    if amount >= Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    _parse_ymd(return_date)
    _parse_hms(return_time)
    if not REASON_CODE_RE.match(reason_code):
        raise ParseError(INVALID_IDENTIFIER)
    reason_text = _check_padding(reason_text_raw, REASON_TEXT_RE)

    return {
        "return_id": return_id,
        "original_transfer_id": original_transfer_id,
        "amount_brl": amount,
        "return_date": return_date,
        "return_time": return_time,
        "reason_code": reason_code,
        "reason_text": reason_text,
    }


def _parse_trailer(record: str) -> dict[str, object]:
    if _slice(record, 1, 1) != "T":
        raise ParseError(INVALID_RECORD_SEQUENCE)
    file_date = _slice(record, 2, 9)
    transfer_count_raw = _slice(record, 10, 15)
    return_count_raw = _slice(record, 16, 21)
    gross_sign = _slice(record, 22, 22)
    gross_magnitude = _slice(record, 23, 36)
    returned_sign = _slice(record, 37, 37)
    returned_magnitude = _slice(record, 38, 51)
    net_sign = _slice(record, 52, 52)
    net_magnitude = _slice(record, 53, 66)
    batch_id = _slice(record, 67, 82)

    _parse_ymd(file_date)
    if not transfer_count_raw.isdigit() or not return_count_raw.isdigit():
        raise ParseError(INVALID_FIELD)
    if not BATCH_ID_RE.match(batch_id):
        raise ParseError(INVALID_FIELD)
    gross = _decode_signed(gross_sign, gross_magnitude, allowed_signs=("+",))
    if gross <= Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    returned = _decode_signed(returned_sign, returned_magnitude, allowed_signs=("+", "-"))
    if returned > Decimal("0.00"):
        raise ParseError(INVALID_FIELD)
    net = _decode_signed(net_sign, net_magnitude, allowed_signs=("+",))
    if net < Decimal("0.00"):
        raise ParseError(INVALID_FIELD)

    return {
        "file_date": file_date,
        "transfer_count": int(transfer_count_raw, 10),
        "return_count": int(return_count_raw, 10),
        "gross_amount": gross,
        "returned_amount": returned,
        "net_amount": net,
        "batch_id": batch_id,
    }


def parse_ted_transfer_settlement(
    payload: bytes,
    *,
    filename: str | None = None,
    keys: Mapping[str, bytes] | None = None,
) -> ParseResult:
    """Parse one Type 04 raw `.dat` file. Refused batches yield zero movements."""
    try:
        account_key = resolve_keys(keys)
        text = _decode_transport(payload)
        lines = _split_records(text)

        header = _parse_header(lines[0])
        batch_id = header["batch_id"]
        if filename:
            match = re.search(
                r"NW_TED_SETTLEMENT_(\d{8})_(B[0-9]{15})\.dat$", filename
            )
            if match and (
                match.group(1) != header["file_date"] or match.group(2) != batch_id
            ):
                raise ParseError(INVALID_FIELD)

        idx = 1
        movements: list[SanitizedMovement] = []
        seen_ids: set[str] = set()
        last_transfer_instant = None
        last_transfer_id: str | None = None

        while idx < len(lines) and lines[idx][0:1] == "D":
            record_number = idx + 1
            transfer = _parse_transfer(lines[idx])
            if transfer["transfer_date"] != header["settlement_date"]:
                raise ParseError(INVALID_TIMESTAMP)
            transfer_id = transfer["transfer_id"]
            if transfer_id in seen_ids:
                raise ParseError(DUPLICATE_IDENTIFIER)
            seen_ids.add(transfer_id)
            transfer_instant = _local_datetime(
                transfer["transfer_date"], transfer["transfer_time"]
            )

            payer_token = tokenize_account(
                transfer["payer_ispb"], transfer["payer_branch"], transfer["payer_account"], account_key
            )
            payer_tax_masked = mask_tax_id(transfer["payer_party_type"], transfer["payer_tax_id"])
            beneficiary_token = tokenize_account(
                transfer["beneficiary_ispb"],
                transfer["beneficiary_branch"],
                transfer["beneficiary_account"],
                account_key,
            )
            beneficiary_tax_masked = mask_tax_id(
                transfer["beneficiary_party_type"], transfer["beneficiary_tax_id"]
            )

            movements.append(
                SanitizedMovement(
                    batch_id=batch_id,
                    source_record_number=record_number,
                    movement_id=transfer_id,
                    original_transfer_id=None,
                    movement_kind="TRANSFER",
                    movement_ts=_iso_instant(transfer_instant),
                    amount_brl=transfer["amount_brl"],
                    payer_account_token=payer_token,
                    payer_tax_id_masked=payer_tax_masked,
                    beneficiary_account_token=beneficiary_token,
                    beneficiary_tax_id_masked=beneficiary_tax_masked,
                    beneficiary_ispb=transfer["beneficiary_ispb"],
                    purpose_code=transfer["purpose_code"],
                    status_code=transfer["status_code"],
                    return_reason_code=None,
                )
            )
            idx += 1
            last_transfer_instant = transfer_instant
            last_transfer_id = transfer_id

            if transfer["status_code"] == "RT":
                if idx >= len(lines) or lines[idx][0:1] != "R":
                    raise ParseError(INVALID_RECORD_SEQUENCE)
                return_record_number = idx + 1
                ret = _parse_return(lines[idx])
                if ret["original_transfer_id"] != last_transfer_id:
                    raise ParseError(RETURN_LINK_MISMATCH)
                if -ret["amount_brl"] != transfer["amount_brl"]:
                    raise ParseError(RETURN_LINK_MISMATCH)
                return_id = ret["return_id"]
                if return_id in seen_ids:
                    raise ParseError(DUPLICATE_IDENTIFIER)
                seen_ids.add(return_id)
                return_instant = _local_datetime(ret["return_date"], ret["return_time"])
                if return_instant <= last_transfer_instant:
                    raise ParseError(INVALID_TIMESTAMP)

                movements.append(
                    SanitizedMovement(
                        batch_id=batch_id,
                        source_record_number=return_record_number,
                        movement_id=return_id,
                        original_transfer_id=last_transfer_id,
                        movement_kind="RETURN",
                        movement_ts=_iso_instant(return_instant),
                        amount_brl=ret["amount_brl"],
                        payer_account_token=payer_token,
                        payer_tax_id_masked=payer_tax_masked,
                        beneficiary_account_token=beneficiary_token,
                        beneficiary_tax_id_masked=beneficiary_tax_masked,
                        beneficiary_ispb=transfer["beneficiary_ispb"],
                        purpose_code=transfer["purpose_code"],
                        status_code=transfer["status_code"],
                        return_reason_code=ret["reason_code"],
                    )
                )
                idx += 1
            elif idx < len(lines) and lines[idx][0:1] == "R":
                raise ParseError(RETURN_LINK_MISMATCH)

        if not movements:
            raise ParseError(INVALID_RECORD_SEQUENCE)
        if idx >= len(lines) or lines[idx][0:1] != "T":
            raise ParseError(INVALID_RECORD_SEQUENCE)
        trailer = _parse_trailer(lines[idx])
        idx += 1
        if idx != len(lines):
            raise ParseError(INVALID_RECORD_SEQUENCE)
        if trailer["batch_id"] != batch_id:
            raise ParseError(INVALID_FIELD)
        if trailer["file_date"] != header["file_date"]:
            raise ParseError(INVALID_FIELD)

        transfers = tuple(m for m in movements if m.movement_kind == "TRANSFER")
        returns = tuple(m for m in movements if m.movement_kind == "RETURN")
        computed_transfer_count = len(transfers)
        computed_return_count = len(returns)
        computed_gross = sum((m.amount_brl for m in transfers), Decimal("0.00"))
        computed_returned = sum((m.amount_brl for m in returns), Decimal("0.00"))
        computed_net = computed_gross + computed_returned

        controls: dict[str, object] = {
            "declared_transfer_count": trailer["transfer_count"],
            "computed_transfer_count": computed_transfer_count,
            "declared_return_count": trailer["return_count"],
            "computed_return_count": computed_return_count,
            "declared_gross_amount": _money_text(trailer["gross_amount"]),
            "computed_gross_amount": _money_text(computed_gross),
            "declared_returned_amount": _money_text(trailer["returned_amount"]),
            "computed_returned_amount": _money_text(computed_returned),
            "declared_net_amount": _money_text(trailer["net_amount"]),
            "computed_net_amount": _money_text(computed_net),
        }

        if trailer["transfer_count"] != computed_transfer_count:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                movements=(),
            )
        if trailer["return_count"] != computed_return_count:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_RETURN_COUNT_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                movements=(),
            )
        if trailer["gross_amount"] != computed_gross:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_GROSS_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                movements=(),
            )
        if trailer["returned_amount"] != computed_returned:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_RETURNED_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                movements=(),
            )
        if trailer["net_amount"] != computed_net:
            return ParseResult(
                accepted=False,
                rejection_code=SOURCE_CONTROL_NET_MISMATCH,
                batch_id=batch_id,
                controls=controls,
                movements=(),
            )

        return ParseResult(
            accepted=True,
            rejection_code=None,
            batch_id=batch_id,
            controls=controls,
            movements=tuple(movements),
        )
    except ParseError as exc:
        return ParseResult(
            accepted=False,
            rejection_code=exc.code,
            batch_id=None,
            controls={},
            movements=(),
        )


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(MONEY_QUANTUM):.2f}"


__all__ = [
    "ParseError",
    "ParseResult",
    "SanitizedMovement",
    "cnpj_check_digits_valid",
    "cpf_check_digits_valid",
    "decode_implied_decimal",
    "mask_tax_id",
    "parse_ted_transfer_settlement",
    "resolve_keys",
    "tokenize_account",
]
