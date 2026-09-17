from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from generation import generate


ROOT = Path(__file__).resolve().parents[2]
TYPE_ROOT = ROOT / "contracts" / "types" / "03-payment-slip-settlement"
MAIN = TYPE_ROOT / "main"
COMMON = ROOT / "contracts" / "common"
CONTRACTS_ROOT = ROOT / "contracts" / "types"
PAYMENT_REFERENCE_KEY = (
    b"northwind-pay-edp-fixture-payment-reference-key-v1"
)
PARTY_KEY = b"northwind-pay-edp-fixture-party-key-v1"
ACCOUNT_KEY = b"northwind-pay-edp-fixture-account-key-v1"
CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number_a",
    "source_record_number_b",
    "lot_number",
    "sequence",
    "settlement_id",
    "payment_reference_token",
    "payment_reference_last4",
    "beneficiary_token",
    "beneficiary_tax_id_type",
    "beneficiary_tax_id_masked",
    "bank_account_token",
    "bank_account_last4",
    "due_date",
    "payment_date",
    "face_amount_brl",
    "discount_brl",
    "fee_brl",
    "net_amount_brl",
    "status",
    "bank_reference",
    "client_reference",
)
SUCCESS_SCENARIOS = {
    "valid-minimal": (
        "valid-minimal.rem",
        "expected-sanitized.csv",
        "expected-reconciliation.yaml",
    ),
    "valid-boundary": (
        "valid-boundary.rem",
        "expected-valid-boundary-sanitized.csv",
        "expected-valid-boundary-reconciliation.yaml",
    ),
    "multi-lot": (
        "multi-lot.rem",
        "expected-multi-lot-sanitized.csv",
        "expected-multi-lot-reconciliation.yaml",
    ),
}
RAW_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.rem",
        "e1fc88f1363b1dd2dd44ed8c0389991a88d6aa4be71008d8a360e750b8e8d243",
    ),
    "valid-boundary": (
        "valid-boundary.rem",
        "59c7d152fa627ab3689d7d1b3b3e439e4c3e723b7b6759db1bfc7be731e86dc8",
    ),
    "malformed": (
        "malformed.rem",
        "327e6a24665ab48bc7d7130dddf389baaabf990d077db5a905284ec814048de1",
    ),
    "multi-lot": (
        "multi-lot.rem",
        "b0738ac5d795319c53f9b2ab9eec136f99162ca6a8a59ea1af35e424c72ef83a",
    ),
    "DF-SOURCE-003": (
        "df-source-003.rem",
        "25f36326988699045755164c65be92c77df3bbf5f2c2ac8afd7289d666025505",
    ),
}
SAFE_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9]{15}$")
SAFE_REFERENCE = re.compile(r"^[A-Z][A-Z0-9]{19}$")


@dataclass(frozen=True, slots=True)
class Settlement:
    source_record_number_a: int
    source_record_number_b: int
    lot_number: str
    sequence: str
    settlement_id: str
    payment_reference: str
    face_amount: Decimal
    due_date: str
    payment_date: str
    discount: Decimal
    fee: Decimal
    bank_reference: str
    tax_id_type: str
    tax_id_transport: str
    beneficiary_name: str
    bank_code: str
    branch_number: str
    account_number: str
    account_check_digit: str
    client_reference: str

    @property
    def document(self) -> str:
        if self.tax_id_type == "1":
            return self.tax_id_transport[3:]
        return self.tax_id_transport

    @property
    def net_amount(self) -> Decimal:
        return self.face_amount - self.discount + self.fee

    @property
    def canonical_account(self) -> str:
        return (
            f"{self.bank_code}:{self.branch_number}:"
            f"{self.account_number}:{self.account_check_digit}"
        )


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    file_date: str
    batch_id: str
    settlements: tuple[Settlement, ...]
    declared_lot_count: int
    computed_lot_count: int
    declared_physical_record_count: int
    computed_physical_record_count: int
    declared_logical_count: int
    computed_logical_count: int
    declared_face_amount: Decimal
    computed_face_amount: Decimal
    declared_discount_amount: Decimal
    computed_discount_amount: Decimal
    declared_fee_amount: Decimal
    computed_fee_amount: Decimal
    declared_net_amount: Decimal
    computed_net_amount: Decimal
    computed_orphan_segment_count: int

    @property
    def source_filename(self) -> str:
        return f"NW_PAYMENT_SLIP_{self.file_date}_{self.batch_id}.rem"


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"Expected a mapping in {path.name}")
    return loaded


def _date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("INVALID_FIELD") from exc


def _digits(value: str) -> None:
    if not value.isascii() or not value.isdigit():
        raise ValueError("INVALID_FIELD")


def _money(value: str) -> Decimal:
    _digits(value)
    return Decimal(value) / 100


def _cpf_is_valid(value: str) -> bool:
    if len(value) != 11 or not value.isascii() or not value.isdigit():
        return False
    if len(set(value)) == 1:
        return False
    digits = [int(character) for character in value]
    first_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:9], range(10, 1, -1))
    )
    first_remainder = first_sum % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_sum = sum(
        digit * weight
        for digit, weight in zip(
            digits[:9] + [first],
            range(11, 1, -1),
        )
    )
    second_remainder = second_sum % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return digits[-2:] == [first, second]


def _cnpj_is_valid(value: str) -> bool:
    if len(value) != 14 or not value.isascii() or not value.isdigit():
        return False
    if len(set(value)) == 1:
        return False
    digits = [int(character) for character in value]
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first_remainder = sum(
        digit * weight
        for digit, weight in zip(digits[:12], first_weights)
    ) % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_remainder = sum(
        digit * weight
        for digit, weight in zip(
            digits[:12] + [first],
            second_weights,
        )
    ) % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return digits[-2:] == [first, second]


def _records(raw: bytes) -> list[str]:
    if len(raw) > 5_324_484:
        raise ValueError("INVALID_SOURCE_SIZE")
    try:
        raw.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("INVALID_ASCII") from exc
    if (
        not raw.endswith(b"\r\n")
        or raw.endswith(b"\r\n\r\n")
        or b"\r" in raw.replace(b"\r\n", b"")
        or b"\n" in raw.replace(b"\r\n", b"")
    ):
        raise ValueError("INVALID_TRANSPORT")
    physical = raw[:-2].split(b"\r\n")
    if not 6 <= len(physical) <= 22_002 or b"" in physical:
        raise ValueError("INVALID_RECORD_SEQUENCE")
    if any(len(record) != 240 for record in physical):
        raise ValueError("INVALID_RECORD_LENGTH")
    return [record.decode("ascii") for record in physical]


def _filler(record: str, start: int) -> None:
    if record[start:] != "~" * (240 - start):
        raise ValueError("INVALID_FILLER")


def _parse_header(record: str) -> tuple[str, str]:
    if record[0] != "H":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    _filler(record, 54)
    file_date = record[1:9]
    batch_id = record[9:25]
    _date(file_date)
    if not re.fullmatch(r"B[0-9]{15}", batch_id):
        raise ValueError("INVALID_FIELD")
    if (
        record[25:37] != "PAYSLIPSET03"
        or record[37:40] != "001"
        or record[40:48] != "NWP00001"
        or record[48:54] != batch_id[-6:]
    ):
        raise ValueError("INVALID_FIELD")
    return file_date, batch_id


def _parse_lot_header(
    record: str,
    *,
    file_date: str,
    batch_id: str,
) -> tuple[str, str]:
    if record[0] != "L":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    _filler(record, 62)
    lot_number = record[1:7]
    settlement_date = record[22:30]
    if (
        not re.fullmatch(r"(?!000000)[0-9]{6}", lot_number)
        or record[7:19] != "SLIPSETTLE01"
        or record[19:22] != "BRL"
        or record[30:46] != batch_id
    ):
        raise ValueError("INVALID_FIELD")
    _date(settlement_date)
    if not SAFE_IDENTIFIER.fullmatch(record[46:62]):
        raise ValueError("INVALID_IDENTIFIER")
    if settlement_date != file_date:
        raise ValueError("INVALID_BUSINESS_DATE")
    return lot_number, settlement_date


def _parse_financial(record: str, record_number: int) -> dict[str, object]:
    if record[0] != "A":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    _filler(record, 154)
    lot_number = record[1:7]
    sequence = record[7:13]
    settlement_id = record[13:29]
    payment_reference = record[29:77]
    due_date = record[92:100]
    payment_date = record[100:108]
    bank_reference = record[134:154]
    if (
        not re.fullmatch(r"(?!000000)[0-9]{6}", lot_number)
        or not re.fullmatch(r"(?!000000)[0-9]{6}", sequence)
        or not re.fullmatch(r"[0-9]{48}", payment_reference)
        or record[132:134] != "00"
    ):
        raise ValueError("INVALID_FIELD")
    _date(due_date)
    _date(payment_date)
    face = _money(record[77:92])
    discount = _money(record[108:120])
    fee = _money(record[120:132])
    if face <= 0 or discount > face or face - discount + fee < 0:
        raise ValueError("INVALID_FIELD")
    if (
        not SAFE_IDENTIFIER.fullmatch(settlement_id)
        or not SAFE_REFERENCE.fullmatch(bank_reference)
    ):
        raise ValueError("INVALID_IDENTIFIER")
    return {
        "record_number": record_number,
        "lot_number": lot_number,
        "sequence": sequence,
        "settlement_id": settlement_id,
        "payment_reference": payment_reference,
        "face_amount": face,
        "due_date": due_date,
        "payment_date": payment_date,
        "discount": discount,
        "fee": fee,
        "bank_reference": bank_reference,
    }


def _parse_beneficiary(record: str, record_number: int) -> dict[str, str | int]:
    if record[0] != "B":
        raise ValueError("SEGMENT_PAIR_MISMATCH")
    _filler(record, 125)
    lot_number = record[1:7]
    sequence = record[7:13]
    settlement_id = record[13:29]
    tax_id_type = record[29]
    tax_id = record[30:44]
    padded_name = record[44:84]
    beneficiary_name = padded_name.rstrip(" ")
    bank_code = record[84:87]
    branch = record[87:92]
    account = record[92:104]
    check_digit = record[104]
    client_reference = record[105:125]
    if (
        not re.fullmatch(r"(?!000000)[0-9]{6}", lot_number)
        or not re.fullmatch(r"(?!000000)[0-9]{6}", sequence)
        or tax_id_type not in {"1", "2"}
        or not re.fullmatch(r"[0-9]{14}", tax_id)
        or padded_name != beneficiary_name.ljust(40)
        or not re.fullmatch(r"[A-Z][A-Z0-9 .&/-]{0,39}", beneficiary_name)
        or not re.fullmatch(r"(?!000)[0-9]{3}", bank_code)
        or not re.fullmatch(r"[0-9]{5}", branch)
        or not re.fullmatch(r"[0-9]{12}", account)
    ):
        raise ValueError("INVALID_FIELD")
    if tax_id_type == "1":
        valid_document = tax_id.startswith("000") and _cpf_is_valid(tax_id[3:])
    else:
        valid_document = _cnpj_is_valid(tax_id)
    if not valid_document:
        raise ValueError("INVALID_DOCUMENT")
    if (
        not SAFE_IDENTIFIER.fullmatch(settlement_id)
        or not re.fullmatch(r"[A-Z0-9]", check_digit)
        or not SAFE_REFERENCE.fullmatch(client_reference)
    ):
        raise ValueError("INVALID_IDENTIFIER")
    return {
        "record_number": record_number,
        "lot_number": lot_number,
        "sequence": sequence,
        "settlement_id": settlement_id,
        "tax_id_type": tax_id_type,
        "tax_id_transport": tax_id,
        "beneficiary_name": beneficiary_name,
        "bank_code": bank_code,
        "branch_number": branch,
        "account_number": account,
        "account_check_digit": check_digit,
        "client_reference": client_reference,
    }


def _parse_lot_trailer(
    record: str,
    *,
    lot_number: str,
    batch_id: str,
) -> dict[str, object]:
    if record[0] != "T":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    _filler(record, 89)
    if record[1:7] != lot_number or record[73:89] != batch_id:
        raise ValueError("INVALID_FIELD")
    count_lexeme = record[7:13]
    if (
        not re.fullmatch(r"[0-9]{6}", count_lexeme)
        or not 1 <= int(count_lexeme) <= 10_000
    ):
        raise ValueError("INVALID_FIELD")
    return {
        "count": int(count_lexeme),
        "face": _money(record[13:28]),
        "discount": _money(record[28:43]),
        "fee": _money(record[43:58]),
        "net": _money(record[58:73]),
    }


def _parse_file_trailer(record: str, *, batch_id: str) -> dict[str, object]:
    if record[0] != "Z":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    _filler(record, 50)
    if record[34:50] != batch_id:
        raise ValueError("INVALID_FIELD")
    lot_count_lexeme = record[1:7]
    physical_count_lexeme = record[7:13]
    logical_count_lexeme = record[13:19]
    if (
        not re.fullmatch(r"[0-9]{6}", lot_count_lexeme)
        or not 1 <= int(lot_count_lexeme) <= 1_000
        or not re.fullmatch(r"[0-9]{6}", physical_count_lexeme)
        or not 6 <= int(physical_count_lexeme) <= 22_002
        or not re.fullmatch(r"[0-9]{6}", logical_count_lexeme)
        or not 1 <= int(logical_count_lexeme) <= 10_000
    ):
        raise ValueError("INVALID_FIELD")
    return {
        "lot_count": int(lot_count_lexeme),
        "physical_count": int(physical_count_lexeme),
        "logical_count": int(logical_count_lexeme),
        "net": _money(record[19:34]),
    }


def _parse_source(
    raw: bytes,
    *,
    enforce_file_controls: bool = True,
) -> ParsedBatch:
    physical = _records(raw)
    file_date, batch_id = _parse_header(physical[0])
    index = 1
    settlements: list[Settlement] = []
    lot_numbers: set[str] = set()
    settlement_ids: set[str] = set()
    lot_trailers: list[dict[str, object]] = []

    while index < len(physical) - 1 and physical[index][0] != "Z":
        lot_number, settlement_date = _parse_lot_header(
            physical[index],
            file_date=file_date,
            batch_id=batch_id,
        )
        if lot_number in lot_numbers or len(lot_numbers) >= 1000:
            raise ValueError("DUPLICATE_IDENTIFIER")
        lot_numbers.add(lot_number)
        index += 1
        lot_settlements: list[Settlement] = []
        sequences: set[str] = set()
        while index < len(physical) and physical[index][0] != "T":
            financial = _parse_financial(physical[index], index + 1)
            if index + 1 >= len(physical):
                raise ValueError("SEGMENT_PAIR_MISMATCH")
            beneficiary = _parse_beneficiary(physical[index + 1], index + 2)
            if (
                financial["lot_number"] != lot_number
                or beneficiary["lot_number"] != lot_number
                or beneficiary["sequence"] != financial["sequence"]
                or beneficiary["settlement_id"] != financial["settlement_id"]
            ):
                raise ValueError("SEGMENT_PAIR_MISMATCH")
            sequence = str(financial["sequence"])
            settlement_id = str(financial["settlement_id"])
            if sequence in sequences or settlement_id in settlement_ids:
                raise ValueError("DUPLICATE_IDENTIFIER")
            if (
                financial["payment_date"] != settlement_date
                or str(financial["payment_date"]) > str(financial["due_date"])
            ):
                raise ValueError("INVALID_BUSINESS_DATE")
            sequences.add(sequence)
            settlement_ids.add(settlement_id)
            settlement = Settlement(
                source_record_number_a=int(financial["record_number"]),
                source_record_number_b=int(beneficiary["record_number"]),
                lot_number=lot_number,
                sequence=sequence,
                settlement_id=settlement_id,
                payment_reference=str(financial["payment_reference"]),
                face_amount=Decimal(financial["face_amount"]),
                due_date=str(financial["due_date"]),
                payment_date=str(financial["payment_date"]),
                discount=Decimal(financial["discount"]),
                fee=Decimal(financial["fee"]),
                bank_reference=str(financial["bank_reference"]),
                tax_id_type=str(beneficiary["tax_id_type"]),
                tax_id_transport=str(beneficiary["tax_id_transport"]),
                beneficiary_name=str(beneficiary["beneficiary_name"]),
                bank_code=str(beneficiary["bank_code"]),
                branch_number=str(beneficiary["branch_number"]),
                account_number=str(beneficiary["account_number"]),
                account_check_digit=str(beneficiary["account_check_digit"]),
                client_reference=str(beneficiary["client_reference"]),
            )
            lot_settlements.append(settlement)
            settlements.append(settlement)
            if len(settlements) > 10_000:
                raise ValueError("INVALID_SOURCE_SIZE")
            index += 2
        if not lot_settlements or index >= len(physical):
            raise ValueError("INVALID_RECORD_SEQUENCE")
        trailer = _parse_lot_trailer(
            physical[index],
            lot_number=lot_number,
            batch_id=batch_id,
        )
        computed_count = len(lot_settlements)
        computed_face = sum(
            (item.face_amount for item in lot_settlements),
            Decimal("0.00"),
        )
        computed_discount = sum(
            (item.discount for item in lot_settlements),
            Decimal("0.00"),
        )
        computed_fee = sum(
            (item.fee for item in lot_settlements),
            Decimal("0.00"),
        )
        computed_net = sum(
            (item.net_amount for item in lot_settlements),
            Decimal("0.00"),
        )
        if trailer["count"] != computed_count:
            raise ValueError("SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH")
        if trailer["face"] != computed_face:
            raise ValueError("SOURCE_CONTROL_FACE_MISMATCH")
        if trailer["discount"] != computed_discount:
            raise ValueError("SOURCE_CONTROL_DISCOUNT_MISMATCH")
        if trailer["fee"] != computed_fee:
            raise ValueError("SOURCE_CONTROL_FEE_MISMATCH")
        if trailer["net"] != computed_net:
            raise ValueError("SOURCE_CONTROL_NET_MISMATCH")
        lot_trailers.append(trailer)
        index += 1

    if index != len(physical) - 1:
        raise ValueError("INVALID_RECORD_SEQUENCE")
    file_trailer = _parse_file_trailer(
        physical[index],
        batch_id=batch_id,
    )
    computed_face = sum(
        (item.face_amount for item in settlements),
        Decimal("0.00"),
    )
    computed_discount = sum(
        (item.discount for item in settlements),
        Decimal("0.00"),
    )
    computed_fee = sum(
        (item.fee for item in settlements),
        Decimal("0.00"),
    )
    computed_net = sum(
        (item.net_amount for item in settlements),
        Decimal("0.00"),
    )
    declared_face = sum(
        (Decimal(item["face"]) for item in lot_trailers),
        Decimal("0.00"),
    )
    declared_discount = sum(
        (Decimal(item["discount"]) for item in lot_trailers),
        Decimal("0.00"),
    )
    declared_fee = sum(
        (Decimal(item["fee"]) for item in lot_trailers),
        Decimal("0.00"),
    )
    if enforce_file_controls:
        if file_trailer["lot_count"] != len(lot_numbers):
            raise ValueError("SOURCE_CONTROL_LOT_COUNT_MISMATCH")
        if file_trailer["physical_count"] != len(physical):
            raise ValueError("SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH")
        if file_trailer["logical_count"] != len(settlements):
            raise ValueError("SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH")
        if file_trailer["net"] != computed_net:
            raise ValueError("SOURCE_CONTROL_NET_MISMATCH")
    return ParsedBatch(
        file_date=file_date,
        batch_id=batch_id,
        settlements=tuple(settlements),
        declared_lot_count=int(file_trailer["lot_count"]),
        computed_lot_count=len(lot_numbers),
        declared_physical_record_count=int(file_trailer["physical_count"]),
        computed_physical_record_count=len(physical),
        declared_logical_count=int(file_trailer["logical_count"]),
        computed_logical_count=len(settlements),
        declared_face_amount=declared_face,
        computed_face_amount=computed_face,
        declared_discount_amount=declared_discount,
        computed_discount_amount=computed_discount,
        declared_fee_amount=declared_fee,
        computed_fee_amount=computed_fee,
        declared_net_amount=Decimal(file_trailer["net"]),
        computed_net_amount=computed_net,
        computed_orphan_segment_count=0,
    )


def _token(prefix: str, key: bytes, value: str) -> str:
    digest = hmac.new(key, value.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:24]}"


def _iso_date(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _render_csv(batch: ParsedBatch) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(
        output,
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(CSV_COLUMNS)
    for settlement in batch.settlements:
        document_type = "CPF" if settlement.tax_id_type == "1" else "CNPJ"
        mask = ("*" * (7 if document_type == "CPF" else 10)) + (
            settlement.document[-4:]
        )
        writer.writerow(
            (
                batch.batch_id,
                batch.source_filename,
                settlement.source_record_number_a,
                settlement.source_record_number_b,
                settlement.lot_number,
                settlement.sequence,
                settlement.settlement_id,
                _token(
                    "payref",
                    PAYMENT_REFERENCE_KEY,
                    settlement.payment_reference,
                ),
                settlement.payment_reference[-4:],
                _token("party", PARTY_KEY, settlement.beneficiary_name),
                document_type,
                mask,
                _token(
                    "acct",
                    ACCOUNT_KEY,
                    settlement.canonical_account,
                ),
                settlement.account_number[-4:],
                _iso_date(settlement.due_date),
                _iso_date(settlement.payment_date),
                format(settlement.face_amount, ".2f"),
                format(settlement.discount, ".2f"),
                format(settlement.fee, ".2f"),
                format(settlement.net_amount, ".2f"),
                "SETTLED",
                settlement.bank_reference,
                settlement.client_reference,
            )
        )
    rendered = output.getvalue().encode("utf-8")
    for settlement in batch.settlements:
        prohibited = {
            settlement.payment_reference,
            settlement.beneficiary_name,
            settlement.tax_id_transport,
            settlement.document,
            settlement.canonical_account,
            settlement.account_number,
        }
        for clear_value in prohibited:
            if clear_value.encode("ascii") in rendered:
                raise AssertionError(
                    f"Restricted value leaked from record "
                    f"{settlement.source_record_number_b}"
                )
    return rendered


def _expected_reconciliation(batch: ParsedBatch) -> dict[str, object]:
    count = len(batch.settlements)
    face = format(batch.computed_face_amount, ".2f")
    discount = format(batch.computed_discount_amount, ".2f")
    fee = format(batch.computed_fee_amount, ".2f")
    net = format(batch.computed_net_amount, ".2f")
    return {
        "batch_id": batch.batch_id,
        "currency": "BRL",
        "source_count": count,
        "staged_count": count,
        "applied_count": count,
        "source_face_amount": face,
        "staged_face_amount": face,
        "applied_face_amount": face,
        "source_discount_amount": discount,
        "staged_discount_amount": discount,
        "applied_discount_amount": discount,
        "source_fee_amount": fee,
        "staged_fee_amount": fee,
        "applied_fee_amount": fee,
        "source_net_amount": net,
        "staged_net_amount": net,
        "applied_net_amount": net,
        "source_orphan_segment_count": 0,
        "staged_orphan_segment_count": 0,
        "applied_orphan_segment_count": 0,
        "count_delta": 0,
        "face_amount_delta": "0.00",
        "discount_amount_delta": "0.00",
        "fee_amount_delta": "0.00",
        "net_amount_delta": "0.00",
        "orphan_segment_count_delta": 0,
        "reject_count": 0,
        "status": "MATCHED",
    }


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _type03_source_artifact() -> dict[str, object]:
    return {
        "batch_id": "B202607230000201",
        "file_type": {
            "code": "PAYSLIPSET03",
            "contract_version": 1,
            "layout_version": "001",
            "number": "03",
        },
        "schema_version": 1,
        "source_controls": {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "logical_count": 2,
            "lot_count": 1,
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "physical_record_count": 8,
        },
        "source_file": {
            "encoding": "US-ASCII",
            "final_newline": "required",
            "line_ending": "CRLF",
            "name": "NW_PAYMENT_SLIP_20260723_B202607230000201.rem",
            "record_length_bytes": 240,
            "sha256": "a" * 64,
            "size_bytes": 1936,
        },
    }


def _type03_receipt(
    *,
    scenario: str = "valid-minimal",
) -> dict[str, object]:
    scenario_values = {
        "valid-minimal": {
            "batch_id": "B202607230000201",
            "date": "20260723",
            "lot_count": 1,
            "physical_count": 8,
            "logical_count": 2,
            "face": "200.00",
            "discount": "5.00",
            "fee": "3.50",
            "declared_net": "198.50",
            "computed_net": "198.50",
        },
        "valid-boundary": {
            "batch_id": "B202402290000202",
            "date": "20240229",
            "lot_count": 1,
            "physical_count": 6,
            "logical_count": 1,
            "face": "9999999999999.99",
            "discount": "9999999999.99",
            "fee": "9999999999.99",
            "declared_net": "9999999999999.99",
            "computed_net": "9999999999999.99",
        },
        "malformed": {
            "batch_id": "B202607230000203",
            "date": "20260723",
            "lot_count": 1,
            "physical_count": 6,
            "logical_count": 1,
            "face": "10.00",
            "discount": "0.00",
            "fee": "0.00",
            "declared_net": "10.00",
            "computed_net": "10.00",
        },
        "multi-lot": {
            "batch_id": "B202607230000204",
            "date": "20260723",
            "lot_count": 2,
            "physical_count": 10,
            "logical_count": 2,
            "face": "200.00",
            "discount": "5.00",
            "fee": "3.50",
            "declared_net": "198.50",
            "computed_net": "198.50",
        },
        "DF-SOURCE-003": {
            "batch_id": "B202607230000205",
            "date": "20260723",
            "lot_count": 1,
            "physical_count": 8,
            "logical_count": 2,
            "face": "200.00",
            "discount": "5.00",
            "fee": "3.50",
            "declared_net": "198.49",
            "computed_net": "198.50",
        },
    }
    values = scenario_values[scenario]
    batch_id = str(values["batch_id"])
    file_date = str(values["date"])
    raw_filename = f"NW_PAYMENT_SLIP_{file_date}_{batch_id}.rem"
    expected: dict[str, object] = {
        "status": "ACCEPTED",
        "violation": None,
    }
    fault: dict[str, object] | None = None
    if scenario == "malformed":
        expected = {
            "status": "REJECTED",
            "violation": "SEGMENT_PAIR_MISMATCH",
        }
        fault = {
            "code": "SEGMENT_PAIR_MISMATCH",
            "expected_stage": "java-validation",
            "injected": True,
        }
    elif scenario == "DF-SOURCE-003":
        expected = {
            "status": "REJECTED",
            "violation": "SOURCE_CONTROL_NET_MISMATCH",
        }
        fault = {
            "code": "SOURCE_CONTROL_NET_MISMATCH",
            "expected_stage": "java-validation",
            "injected": True,
        }
    return {
        "artifacts": {
            "checksum_file": f"{raw_filename}.sha256",
            "data_file": raw_filename,
            "data_sha256": "a" * 64,
            "source_manifest": "source-manifest.json",
            "source_manifest_sha256": "b" * 64,
        },
        "batch_id": batch_id,
        "contract": {
            "layout_sha256": "c" * 64,
            "layout_version": "001",
            "registry_sha256": "d" * 64,
            "type_number": "03",
            "version": 1,
        },
        "controls": {
            "computed_discount_amount": values["discount"],
            "computed_face_amount": values["face"],
            "computed_fee_amount": values["fee"],
            "computed_logical_count": values["logical_count"],
            "computed_lot_count": values["lot_count"],
            "computed_net_amount": values["computed_net"],
            "computed_orphan_segment_count": 0,
            "computed_physical_record_count": values["physical_count"],
            "declared_discount_amount": values["discount"],
            "declared_face_amount": values["face"],
            "declared_fee_amount": values["fee"],
            "declared_logical_count": values["logical_count"],
            "declared_lot_count": values["lot_count"],
            "declared_net_amount": values["declared_net"],
            "declared_physical_record_count": values["physical_count"],
        },
        "expected_contract_result": expected,
        "fault": fault,
        "generator": {
            "name": "northwind-pay-datagen",
            "version": "0.1.0",
        },
        "scenario": scenario,
        "schema_version": 1,
        "status": "generated",
    }


def _type03_sanitized_artifact() -> dict[str, object]:
    return {
        "batch_id": "B202607230000201",
        "csv_file": {
            "encoding": "UTF-8",
            "name": "NW_PAYMENT_SLIP_20260723_B202607230000201.csv",
            "row_count": 2,
            "sha256": "e" * 64,
            "size_bytes": 1,
        },
        "file_type": {
            "code": "PAYSLIPSET03",
            "contract_version": 1,
            "layout_version": "001",
            "number": "03",
        },
        "schema_version": 1,
        "source_lineage": {
            "manifest_sha256": "f" * 64,
            "raw_file": (
                "NW_PAYMENT_SLIP_20260723_B202607230000201.rem"
            ),
            "raw_sha256": "a" * 64,
        },
        "stage_controls": {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "row_count": 2,
        },
    }


class Type03ContractTest(unittest.TestCase):
    def test_contract_is_closed_and_declares_required_safety(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        privacy = _load_yaml(TYPE_ROOT / "privacy.yaml")
        csv_contract = _load_yaml(TYPE_ROOT / "csv.yaml")
        reconciliation = _load_yaml(TYPE_ROOT / "reconciliation.yaml")

        file_type = layout["file_type"]
        self.assertEqual(file_type["number"], "03")
        self.assertEqual(file_type["decoding"], "strict")
        self.assertEqual(file_type["line_ending"], "CRLF")
        self.assertEqual(file_type["record_length_bytes"], 240)
        self.assertEqual(file_type["max_logical_rows"], 10_000)
        self.assertEqual(file_type["max_source_file_bytes"], 5_324_484)
        self.assertEqual(
            layout["record_sequence"]["grammar"],
            "H (L (A B)+ T)+ Z",
        )
        self.assertEqual(
            layout["canonical_rejection_codes"]["segment_pair_mismatch"],
            "SEGMENT_PAIR_MISMATCH",
        )
        self.assertEqual(
            layout["validation_order"][-1],
            "file_net_control",
        )
        transformations = privacy["transformations"]
        key_names = {
            transformations[name]["key_environment_variable"]
            for name in (
                "payment_reference",
                "beneficiary_name",
                "bank_account",
            )
        }
        self.assertEqual(len(key_names), 3)
        for name in (
            "payment_reference",
            "beneficiary_name",
            "bank_account",
        ):
            self.assertEqual(
                transformations[name]["missing_key_behavior"],
                "fail_closed",
            )
        self.assertEqual(
            privacy["whole_output_validation"]["failure_behavior"],
            "reject_entire_batch_without_publishing_csv",
        )
        self.assertEqual(csv_contract["format"]["max_rows"], 10_000)
        self.assertEqual(csv_contract["format"]["max_file_bytes"], 8_000_000)
        self.assertEqual(
            reconciliation["semantics"]["global_batch_id"],
            "unique_across_all_file_types",
        )
        self.assertEqual(
            reconciliation["semantics"]["global_settlement_id"],
            "unique_across_accepted_batches",
        )

    def test_three_success_oracles_are_independently_reproduced(self) -> None:
        all_settlement_ids: set[str] = set()
        for scenario, filenames in SUCCESS_SCENARIOS.items():
            with self.subTest(scenario=scenario):
                raw_name, csv_name, reconciliation_name = filenames
                batch = _parse_source((MAIN / raw_name).read_bytes())
                self.assertEqual(
                    _render_csv(batch),
                    (MAIN / csv_name).read_bytes(),
                )
                self.assertEqual(
                    _expected_reconciliation(batch),
                    _load_yaml(MAIN / reconciliation_name),
                )
                scenario_ids = {
                    settlement.settlement_id
                    for settlement in batch.settlements
                }
                self.assertTrue(all_settlement_ids.isdisjoint(scenario_ids))
                all_settlement_ids.update(scenario_ids)
                self.assertEqual(
                    batch.declared_face_amount,
                    batch.computed_face_amount,
                )
                self.assertEqual(
                    batch.declared_discount_amount,
                    batch.computed_discount_amount,
                )
                self.assertEqual(
                    batch.declared_fee_amount,
                    batch.computed_fee_amount,
                )
                self.assertEqual(
                    batch.declared_net_amount,
                    batch.computed_net_amount,
                )

    def test_five_raw_fixtures_have_stable_exact_transport(self) -> None:
        seen_batches: set[str] = set()
        for scenario, (filename, expected_hash) in RAW_FIXTURES.items():
            with self.subTest(scenario=scenario):
                raw = (MAIN / filename).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_hash)
                self.assertTrue(raw.endswith(b"\r\n"))
                self.assertNotIn(b"\r", raw.replace(b"\r\n", b""))
                self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
                records = raw[:-2].split(b"\r\n")
                self.assertTrue(all(len(record) == 240 for record in records))
                batch_id = records[0][9:25].decode("ascii")
                self.assertNotIn(batch_id, seen_batches)
                seen_batches.add(batch_id)
        self.assertEqual(
            seen_batches,
            {
                "B202607230000201",
                "B202402290000202",
                "B202607230000203",
                "B202607230000204",
                "B202607230000205",
            },
        )
        for path in (ROOT / "contracts" / "types").glob("*/main/*"):
            if (
                not path.is_file()
                or path.parent == MAIN
                or path.name.startswith("expected-")
            ):
                continue
            payload = path.read_bytes()
            for batch_id in seen_batches:
                self.assertNotIn(batch_id.encode("ascii"), payload, path)

    def test_malformed_has_only_the_named_pairing_defect(self) -> None:
        raw = (MAIN / "malformed.rem").read_bytes()
        with self.assertRaisesRegex(ValueError, "SEGMENT_PAIR_MISMATCH"):
            _parse_source(raw)

        records = raw[:-2].split(b"\r\n")
        corrected_b = bytearray(records[3])
        corrected_b[7:13] = b"000001"
        corrected = b"\r\n".join(
            records[:3] + [bytes(corrected_b)] + records[4:]
        ) + b"\r\n"
        fixed_batch = _parse_source(corrected)
        self.assertEqual(fixed_batch.computed_logical_count, 1)
        self.assertEqual(
            fixed_batch.declared_net_amount,
            fixed_batch.computed_net_amount,
        )

        expected = _load_yaml(MAIN / "expected-malformed-rejection.yaml")
        self.assertEqual(expected["expected_code"], "SEGMENT_PAIR_MISMATCH")
        self.assertEqual(expected["source_record_number"], 4)
        self.assertFalse(expected["csv_produced"])
        self.assertFalse(expected["postgres_business_mutation"])
        self.assertNotIn("settlement_id", expected)

    def test_dark_factory_has_only_the_named_file_net_defect(self) -> None:
        raw = (MAIN / "df-source-003.rem").read_bytes()
        batch = _parse_source(raw, enforce_file_controls=False)
        self.assertEqual(
            batch.declared_lot_count,
            batch.computed_lot_count,
        )
        self.assertEqual(
            batch.declared_physical_record_count,
            batch.computed_physical_record_count,
        )
        self.assertEqual(
            batch.declared_logical_count,
            batch.computed_logical_count,
        )
        self.assertEqual(
            batch.declared_face_amount,
            batch.computed_face_amount,
        )
        self.assertEqual(
            batch.declared_discount_amount,
            batch.computed_discount_amount,
        )
        self.assertEqual(
            batch.declared_fee_amount,
            batch.computed_fee_amount,
        )
        self.assertEqual(batch.declared_net_amount, Decimal("198.49"))
        self.assertEqual(batch.computed_net_amount, Decimal("198.50"))
        self.assertEqual(batch.computed_orphan_segment_count, 0)
        with self.assertRaisesRegex(
            ValueError,
            "SOURCE_CONTROL_NET_MISMATCH",
        ):
            _parse_source(raw)

        records = raw[:-2].split(b"\r\n")
        corrected_z = bytearray(records[-1])
        corrected_z[19:34] = b"000000000019850"
        corrected = b"\r\n".join(
            records[:-1] + [bytes(corrected_z)]
        ) + b"\r\n"
        _parse_source(corrected)

        finding = _load_yaml(
            MAIN / "expected-df-source-003-finding.yaml"
        )
        self.assertEqual(
            finding["expected_code"],
            "SOURCE_CONTROL_NET_MISMATCH",
        )
        self.assertEqual(finding["source_system_role"], "system_of_record")
        self.assertEqual(finding["declared_net_amount"], "198.49")
        self.assertEqual(finding["computed_net_amount"], "198.50")
        self.assertFalse(finding["csv_produced"])
        self.assertFalse(finding["postgres_business_mutation"])

    def test_unsigned_counts_are_lexically_validated_before_int(self) -> None:
        raw = (MAIN / "valid-minimal.rem").read_bytes()
        records = raw[:-2].split(b"\r\n")
        count_fields = {
            "lot_logical_count": (6, 7, 13),
            "file_lot_count": (7, 1, 7),
            "file_physical_count": (7, 7, 13),
            "file_logical_count": (7, 13, 19),
        }
        invalid_prefixes = {
            "positive_sign": b"+",
            "negative_sign": b"-",
            "whitespace": b" ",
            "non_digit": b"X",
        }

        for field_name, (record_index, start, end) in count_fields.items():
            for mutation_name, prefix in invalid_prefixes.items():
                with self.subTest(
                    field=field_name,
                    mutation=mutation_name,
                ):
                    mutated_records = list(records)
                    record = bytearray(mutated_records[record_index])
                    record[start:end] = prefix + record[start + 1 : end]
                    mutated_records[record_index] = bytes(record)
                    mutated = b"\r\n".join(mutated_records) + b"\r\n"
                    with self.assertRaises(ValueError) as raised:
                        _parse_source(mutated)
                    self.assertEqual(str(raised.exception), "INVALID_FIELD")

    def test_all_safe_identifier_fields_use_the_identifier_code(self) -> None:
        raw = (MAIN / "valid-minimal.rem").read_bytes()
        records = raw[:-2].split(b"\r\n")
        identifier_fields = {
            "lot_originator_id": (1, 46, b"1"),
            "financial_settlement_id": (2, 13, b"1"),
            "financial_bank_reference": (2, 134, b"1"),
            "beneficiary_settlement_id": (3, 13, b"1"),
            "beneficiary_account_check_digit": (3, 104, b"-"),
            "beneficiary_client_reference": (3, 105, b"1"),
        }

        for field_name, (record_index, offset, replacement) in (
            identifier_fields.items()
        ):
            with self.subTest(field=field_name):
                mutated_records = list(records)
                record = bytearray(mutated_records[record_index])
                record[offset : offset + 1] = replacement
                mutated_records[record_index] = bytes(record)
                mutated = b"\r\n".join(mutated_records) + b"\r\n"
                with self.assertRaises(ValueError) as raised:
                    _parse_source(mutated)
                self.assertEqual(
                    str(raised.exception),
                    "INVALID_IDENTIFIER",
                )

        invalid_document_and_identifier = list(records)
        beneficiary = bytearray(invalid_document_and_identifier[3])
        beneficiary[30:44] = b"00011122233344"
        beneficiary[105] = ord("1")
        invalid_document_and_identifier[3] = bytes(beneficiary)
        with self.assertRaises(ValueError) as raised:
            _parse_source(
                b"\r\n".join(invalid_document_and_identifier) + b"\r\n"
            )
        self.assertEqual(str(raised.exception), "INVALID_DOCUMENT")

    def test_every_declared_rejection_phase_has_oracle_coverage(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        self.assertEqual(
            layout["validation_order"],
            [
                "source_size_and_ascii",
                "exact_crlf_transport_and_final_crlf",
                "exact_240_byte_record_lengths",
                "record_grammar",
                "discriminators_literals_dates_and_filler",
                "field_lexical_and_numeric_rules",
                "CPF_CNPJ_Mod11",
                "safe_identifier_rules",
                "segment_pairing",
                "uniqueness_and_business_dates",
                "lot_controls",
                "file_count_controls",
                "file_face_discount_fee_controls",
                "file_net_control",
            ],
        )
        raw = (MAIN / "valid-minimal.rem").read_bytes()
        records = raw[:-2].split(b"\r\n")

        def mutate(
            record_index: int,
            start: int,
            end: int,
            replacement: bytes,
        ) -> bytes:
            mutated_records = list(records)
            record = bytearray(mutated_records[record_index])
            record[start:end] = replacement
            mutated_records[record_index] = bytes(record)
            return b"\r\n".join(mutated_records) + b"\r\n"

        duplicate_records = list(records)
        first_identifier = records[2][13:29]
        for record_index in (4, 5):
            record = bytearray(duplicate_records[record_index])
            record[13:29] = first_identifier
            duplicate_records[record_index] = bytes(record)

        oversized = b"A" * 5_324_485
        invalid_ascii = bytearray(raw)
        invalid_ascii[239] = 0xFF
        cases = {
            "INVALID_SOURCE_SIZE": oversized,
            "INVALID_ASCII": bytes(invalid_ascii),
            "INVALID_TRANSPORT": raw.replace(b"\r\n", b"\n", 1),
            "INVALID_RECORD_LENGTH": mutate(3, 239, 240, b""),
            "INVALID_RECORD_SEQUENCE": mutate(1, 0, 1, b"A"),
            "INVALID_FILLER": mutate(3, 239, 240, b"!"),
            "INVALID_FIELD": mutate(1, 7, 19, b"SLIPSETTLE02"),
            "INVALID_DOCUMENT": mutate(
                3,
                30,
                44,
                b"00011122233344",
            ),
            "INVALID_IDENTIFIER": mutate(1, 46, 47, b"1"),
            "SEGMENT_PAIR_MISMATCH": mutate(3, 7, 13, b"000009"),
            "DUPLICATE_IDENTIFIER": (
                b"\r\n".join(duplicate_records) + b"\r\n"
            ),
            "INVALID_BUSINESS_DATE": mutate(
                2,
                100,
                108,
                b"20260722",
            ),
            "SOURCE_CONTROL_LOT_COUNT_MISMATCH": mutate(
                7,
                1,
                7,
                b"000002",
            ),
            "SOURCE_CONTROL_PHYSICAL_COUNT_MISMATCH": mutate(
                7,
                7,
                13,
                b"000009",
            ),
            "SOURCE_CONTROL_LOGICAL_COUNT_MISMATCH": mutate(
                6,
                7,
                13,
                b"000003",
            ),
            "SOURCE_CONTROL_FACE_MISMATCH": mutate(
                6,
                13,
                28,
                b"000000000020001",
            ),
            "SOURCE_CONTROL_DISCOUNT_MISMATCH": mutate(
                6,
                28,
                43,
                b"000000000000501",
            ),
            "SOURCE_CONTROL_FEE_MISMATCH": mutate(
                6,
                43,
                58,
                b"000000000000351",
            ),
            "SOURCE_CONTROL_NET_MISMATCH": mutate(
                7,
                19,
                34,
                b"000000000019851",
            ),
        }
        declared_codes = set(layout["canonical_rejection_codes"].values())
        self.assertEqual(set(cases), declared_codes)

        for expected_code, mutated in cases.items():
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(mutated)
                self.assertEqual(str(raised.exception), expected_code)

    def test_type03_common_schema_branches_are_closed(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        sanitized_validator = _validator("sanitized-manifest.schema.json")

        type03_source = _type03_source_artifact()
        source_validator.validate(type03_source)
        cross_source = json.loads(json.dumps(type03_source))
        cross_source["source_controls"] = {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "1.50",
            "event_count": 2,
            "net_amount": "198.50",
        }
        self.assertTrue(list(source_validator.iter_errors(cross_source)))
        invalid_size = json.loads(json.dumps(type03_source))
        invalid_size["source_file"]["size_bytes"] = 1937
        self.assertTrue(list(source_validator.iter_errors(invalid_size)))
        oversized = json.loads(json.dumps(type03_source))
        oversized["source_file"]["size_bytes"] = 5_324_726
        self.assertTrue(list(source_validator.iter_errors(oversized)))
        orphaned = json.loads(json.dumps(type03_source))
        orphaned["source_controls"]["orphan_segment_count"] = 1
        self.assertTrue(list(source_validator.iter_errors(orphaned)))

        for scenario in (
            "valid-minimal",
            "valid-boundary",
            "multi-lot",
            "malformed",
            "DF-SOURCE-003",
        ):
            receipt_validator.validate(_type03_receipt(scenario=scenario))
        contradictory = _type03_receipt()
        contradictory["fault"] = {
            "code": "SEGMENT_PAIR_MISMATCH",
            "expected_stage": "java-validation",
            "injected": True,
        }
        self.assertTrue(list(receipt_validator.iter_errors(contradictory)))
        cross_receipt = _type03_receipt()
        cross_receipt["artifacts"]["data_file"] = (
            "NW_INSTANT_PAYMENT_20260723_B202607230000201.txt"
        )
        cross_receipt["artifacts"]["checksum_file"] = (
            "NW_INSTANT_PAYMENT_20260723_"
            "B202607230000201.txt.sha256"
        )
        self.assertTrue(list(receipt_validator.iter_errors(cross_receipt)))
        oversized_receipt = _type03_receipt()
        oversized_receipt["controls"]["computed_logical_count"] = 10_001
        self.assertTrue(
            list(receipt_validator.iter_errors(oversized_receipt))
        )

        type03_sanitized = _type03_sanitized_artifact()
        sanitized_validator.validate(type03_sanitized)
        cross_lineage = json.loads(json.dumps(type03_sanitized))
        cross_lineage["source_lineage"]["raw_file"] = (
            "NW_CARD_SETTLEMENT_20260723_B202607230000201.dat"
        )
        self.assertTrue(
            list(sanitized_validator.iter_errors(cross_lineage))
        )
        cross_stage = json.loads(json.dumps(type03_sanitized))
        cross_stage["stage_controls"] = {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "1.50",
            "net_amount": "198.50",
            "returned_count": 0,
            "row_count": 2,
        }
        self.assertTrue(list(sanitized_validator.iter_errors(cross_stage)))
        oversized_rows = json.loads(json.dumps(type03_sanitized))
        oversized_rows["csv_file"]["row_count"] = 10_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_rows))
        )

        with tempfile.TemporaryDirectory() as output:
            bundle = generate(
                type_number="01",
                scenario="valid-minimal",
                output_root=Path(output),
                contracts_root=CONTRACTS_ROOT,
            )
            source_validator.validate(
                json.loads(
                    bundle.manifest_file.read_text(encoding="utf-8")
                )
            )
            receipt_validator.validate(
                json.loads(
                    bundle.receipt_file.read_text(encoding="utf-8")
                )
            )

    def test_artifact_semantic_links_are_mandatory(self) -> None:
        source = _type03_source_artifact()
        match = re.fullmatch(
            r"NW_PAYMENT_SLIP_([0-9]{8})_(B[0-9]{15})\.rem",
            source["source_file"]["name"],
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(2), source["batch_id"])
        self.assertEqual(
            source["source_file"]["size_bytes"],
            source["source_controls"]["physical_record_count"] * 242,
        )
        self.assertLessEqual(
            source["source_controls"]["lot_count"],
            source["source_controls"]["logical_count"],
        )

        sanitized = _type03_sanitized_artifact()
        raw_match = re.fullmatch(
            r"NW_PAYMENT_SLIP_([0-9]{8})_(B[0-9]{15})\.rem",
            sanitized["source_lineage"]["raw_file"],
        )
        csv_match = re.fullmatch(
            r"NW_PAYMENT_SLIP_([0-9]{8})_(B[0-9]{15})\.csv",
            sanitized["csv_file"]["name"],
        )
        self.assertIsNotNone(raw_match)
        self.assertIsNotNone(csv_match)
        assert raw_match is not None and csv_match is not None
        self.assertEqual(raw_match.groups(), csv_match.groups())
        self.assertEqual(raw_match.group(2), sanitized["batch_id"])
        self.assertEqual(
            sanitized["csv_file"]["row_count"],
            sanitized["stage_controls"]["row_count"],
        )


if __name__ == "__main__":
    unittest.main()
