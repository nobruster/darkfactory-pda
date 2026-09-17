from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
TYPE_ROOT = ROOT / "contracts" / "types" / "04-ted-transfer-settlement"
MAIN = TYPE_ROOT / "main"
COMMON = ROOT / "contracts" / "common"
ACCOUNT_KEY = b"northwind-pay-edp-fixture-ted-account-key-v1"
CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "movement_id",
    "original_transfer_id",
    "movement_kind",
    "movement_ts",
    "amount_brl",
    "payer_account_token",
    "payer_tax_id_masked",
    "beneficiary_account_token",
    "beneficiary_tax_id_masked",
    "beneficiary_ispb",
    "purpose_code",
    "status_code",
    "return_reason_code",
)
SUCCESS_SCENARIOS = {
    "valid-minimal": (
        "valid-minimal.dat",
        "expected-sanitized.csv",
        "expected-reconciliation.yaml",
    ),
    "valid-boundary": (
        "valid-boundary.dat",
        "expected-valid-boundary-sanitized.csv",
        "expected-valid-boundary-reconciliation.yaml",
    ),
    "all-returned-zero-net": (
        "all-returned-zero-net.dat",
        "expected-all-returned-zero-net-sanitized.csv",
        "expected-all-returned-zero-net-reconciliation.yaml",
    ),
}
RAW_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.dat",
        "f853e3a48cc7e2b4741f4651596b9ff28346b5a4b0ecec44abc80e7595af3c87",
    ),
    "valid-boundary": (
        "valid-boundary.dat",
        "7d09630e3c70c497786cd3aa9b885b75b92c951b94fad652ec6764b9c26f5ab7",
    ),
    "malformed": (
        "malformed.dat",
        "3387ce34995f5c07c25423e5737fc5808d8ec18f050f97b3680386a48ceb2c91",
    ),
    "all-returned-zero-net": (
        "all-returned-zero-net.dat",
        "ae868704360982a462d602545770f1d4219accc987883982e79d16dad1da8452",
    ),
    "DF-SOURCE-004": (
        "df-source-004.dat",
        "2668b4b6d757a3a0a52aaf1b30a0ff5421630b3e49f5e4fd823e5eef7162f333",
    ),
}
SAFE_ID = re.compile(r"^[A-Z][A-Z0-9]{15}$")


@dataclass(frozen=True, slots=True)
class ReturnRecord:
    source_record_number: int
    return_id: str
    original_transfer_id: str
    amount: Decimal
    timestamp: datetime
    reason_code: str
    reason_text: str


@dataclass(frozen=True, slots=True)
class Transfer:
    source_record_number: int
    transfer_id: str
    amount: Decimal
    timestamp: datetime
    payer_ispb: str
    payer_branch: str
    payer_account: str
    payer_tax_id: str
    payer_party_type: str
    beneficiary_ispb: str
    beneficiary_branch: str
    beneficiary_account: str
    beneficiary_tax_id: str
    beneficiary_party_type: str
    purpose_code: str
    status_code: str
    beneficiary_name: str
    return_record: ReturnRecord | None

    @property
    def payer_account_input(self) -> str:
        return f"{self.payer_ispb}:{self.payer_branch}:{self.payer_account}"

    @property
    def beneficiary_account_input(self) -> str:
        return (
            f"{self.beneficiary_ispb}:"
            f"{self.beneficiary_branch}:{self.beneficiary_account}"
        )


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    file_date: str
    batch_id: str
    transfers: tuple[Transfer, ...]
    declared_transfer_count: int
    computed_transfer_count: int
    declared_return_count: int
    computed_return_count: int
    declared_gross_amount: Decimal
    computed_gross_amount: Decimal
    declared_return_amount: Decimal
    computed_return_amount: Decimal
    declared_net_amount: Decimal
    computed_net_amount: Decimal

    @property
    def source_filename(self) -> str:
        return f"NW_TED_SETTLEMENT_{self.file_date}_{self.batch_id}.dat"


def _load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"Expected a mapping in {path.name}")
    return value


def _digits(value: str) -> None:
    if not value.isascii() or not value.isdigit():
        raise ValueError("INVALID_FIELD")


def _money(value: str) -> Decimal:
    _digits(value)
    return Decimal(value) / 100


def _cpf_is_valid(value: str) -> bool:
    if len(value) != 11 or not value.isdigit() or len(set(value)) == 1:
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
    if len(value) != 14 or not value.isdigit() or len(set(value)) == 1:
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


def _valid_tax_id(value: str, party_type: str) -> bool:
    if party_type == "F":
        return value.startswith("000") and _cpf_is_valid(value[3:])
    if party_type == "J":
        return _cnpj_is_valid(value)
    return False


def _local_timestamp(date: str, time: str) -> datetime:
    try:
        naive = datetime.strptime(date + time, "%Y%m%d%H%M%S")
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    zone = ZoneInfo("America/Sao_Paulo")
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) == naive:
            candidates.append(candidate)
    if not candidates:
        raise ValueError("INVALID_TIMESTAMP")
    return candidates[0]


def _right_tilde_unpad(record: str, start: int, end: int) -> str:
    value = record[start:end]
    stripped = value.rstrip("~")
    if "~" in stripped or value != stripped + "~" * (
        end - start - len(stripped)
    ):
        raise ValueError("INVALID_PADDING")
    return stripped


def _safe_text(value: str, pattern: str) -> str:
    if not value or re.fullmatch(pattern, value) is None:
        raise ValueError("INVALID_IDENTIFIER")
    return value


def _records(raw: bytes) -> list[str]:
    if len(raw) > 2_570_142:
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
    if not 3 <= len(physical) <= 20_002 or b"" in physical:
        raise ValueError("INVALID_RECORD_SEQUENCE")
    expected_lengths = {b"H": 56, b"D": 162, b"R": 91, b"T": 82}
    for record in physical:
        expected = expected_lengths.get(record[:1])
        if expected is None:
            raise ValueError("INVALID_RECORD_SEQUENCE")
        if len(record) != expected:
            raise ValueError("INVALID_RECORD_LENGTH")
    return [record.decode("ascii") for record in physical]


def _parse_header(record: str) -> tuple[str, str]:
    if record[0] != "H":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    file_date = record[1:9]
    batch_id = record[9:25]
    _local_timestamp(file_date, "120000")
    if (
        not re.fullmatch(r"B[0-9]{15}", batch_id)
        or record[25:37] != "TED_SETTLE04"
        or record[37:40] != "001"
        or record[40:48] != file_date
        or not re.fullmatch(r"[0-9]{8}", record[48:56])
    ):
        raise ValueError("INVALID_FIELD")
    return file_date, batch_id


def _parse_transfer(
    record: str,
    *,
    record_number: int,
    file_date: str,
) -> dict[str, object]:
    transfer_id = record[1:17]
    timestamp = _local_timestamp(record[35:43], record[43:49])
    purpose = _right_tilde_unpad(record, 127, 137)
    name = _right_tilde_unpad(record, 139, 162)
    if (
        record[17] != "+"
        or record[32:35] != "BRL"
        or not re.fullmatch(r"[0-9]{8}", record[49:57])
        or not re.fullmatch(r"[0-9]{4}", record[57:61])
        or not re.fullmatch(r"[0-9]{12}", record[61:73])
        or not re.fullmatch(r"[0-9]{8}", record[88:96])
        or not re.fullmatch(r"[0-9]{4}", record[96:100])
        or not re.fullmatch(r"[0-9]{12}", record[100:112])
        or record[87] not in {"F", "J"}
        or record[126] not in {"F", "J"}
        or record[137:139] not in {"OK", "RT"}
    ):
        raise ValueError("INVALID_FIELD")
    amount = _money(record[18:32])
    if amount <= 0:
        raise ValueError("INVALID_FIELD")
    if record[35:43] != file_date:
        raise ValueError("INVALID_TIMESTAMP")
    payer_tax_id = record[73:87]
    beneficiary_tax_id = record[112:126]
    _digits(payer_tax_id)
    _digits(beneficiary_tax_id)
    if not _valid_tax_id(payer_tax_id, record[87]):
        raise ValueError("INVALID_DOCUMENT")
    if not _valid_tax_id(beneficiary_tax_id, record[126]):
        raise ValueError("INVALID_DOCUMENT")
    if not SAFE_ID.fullmatch(transfer_id):
        raise ValueError("INVALID_IDENTIFIER")
    _safe_text(purpose, r"[A-Z][A-Z0-9_]{1,9}")
    _safe_text(name, r"[A-Z][A-Z0-9 .&/-]{0,22}")
    return {
        "record_number": record_number,
        "transfer_id": transfer_id,
        "amount": amount,
        "timestamp": timestamp,
        "payer_ispb": record[49:57],
        "payer_branch": record[57:61],
        "payer_account": record[61:73],
        "payer_tax_id": payer_tax_id,
        "payer_party_type": record[87],
        "beneficiary_ispb": record[88:96],
        "beneficiary_branch": record[96:100],
        "beneficiary_account": record[100:112],
        "beneficiary_tax_id": beneficiary_tax_id,
        "beneficiary_party_type": record[126],
        "purpose_code": purpose,
        "status_code": record[137:139],
        "beneficiary_name": name,
    }


def _parse_return(
    record: str,
    *,
    record_number: int,
) -> ReturnRecord:
    return_id = record[1:17]
    original_id = record[17:33]
    timestamp = _local_timestamp(record[48:56], record[56:62])
    reason_text = _right_tilde_unpad(record, 67, 91)
    if record[33] != "-":
        raise ValueError("INVALID_FIELD")
    amount = _money(record[34:48])
    if amount <= 0:
        raise ValueError("INVALID_FIELD")
    if (
        not SAFE_ID.fullmatch(return_id)
        or not SAFE_ID.fullmatch(original_id)
        or not re.fullmatch(r"[A-Z][A-Z0-9]{4}", record[62:67])
    ):
        raise ValueError("INVALID_IDENTIFIER")
    _safe_text(reason_text, r"[A-Z][A-Z0-9 .&/-]{0,23}")
    return ReturnRecord(
        source_record_number=record_number,
        return_id=return_id,
        original_transfer_id=original_id,
        amount=amount,
        timestamp=timestamp,
        reason_code=record[62:67],
        reason_text=reason_text,
    )


def _parse_trailer(
    record: str,
    *,
    file_date: str,
    batch_id: str,
) -> dict[str, object]:
    if record[0] != "T":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    for value in (
        record[9:15],
        record[15:21],
        record[22:36],
        record[37:51],
        record[52:66],
    ):
        _digits(value)
    if (
        record[1:9] != file_date
        or record[21] != "+"
        or record[36] not in {"+", "-"}
        or record[51] != "+"
        or record[66:82] != batch_id
    ):
        raise ValueError("INVALID_FIELD")
    transfer_count = int(record[9:15])
    return_count = int(record[15:21])
    gross = _money(record[22:36])
    returned_magnitude = _money(record[37:51])
    net = _money(record[52:66])
    if (
        not 1 <= transfer_count <= 10_000
        or not 0 <= return_count <= transfer_count
        or gross <= 0
        or (return_count == 0 and (record[36] != "+" or returned_magnitude != 0))
        or (return_count > 0 and (record[36] != "-" or returned_magnitude <= 0))
    ):
        raise ValueError("INVALID_FIELD")
    returned = -returned_magnitude if return_count else Decimal("0.00")
    return {
        "transfer_count": transfer_count,
        "return_count": return_count,
        "gross": gross,
        "returned": returned,
        "net": net,
    }


def _validate_conditional_record_grammar(physical: list[str]) -> None:
    """Validate the status-selected D or D-R branches before field parsing."""
    if physical[0][0] != "H" or physical[-1][0] != "T":
        raise ValueError("INVALID_RECORD_SEQUENCE")
    index = 1
    while index < len(physical) - 1:
        if physical[index][0] != "D":
            raise ValueError("INVALID_RECORD_SEQUENCE")
        raw_status = physical[index][137:139]
        has_following_return = (
            index + 1 < len(physical) - 1
            and physical[index + 1][0] == "R"
        )
        has_second_return = (
            has_following_return
            and index + 2 < len(physical) - 1
            and physical[index + 2][0] == "R"
        )
        if raw_status == "RT":
            if not has_following_return or has_second_return:
                raise ValueError("RETURN_LINK_MISMATCH")
            index += 2
        elif raw_status == "OK":
            if has_following_return:
                raise ValueError("RETURN_LINK_MISMATCH")
            index += 1
        else:
            index += 2 if has_following_return else 1


def _parse_source(
    raw: bytes,
    *,
    enforce_controls: bool = True,
) -> ParsedBatch:
    physical = _records(raw)
    _validate_conditional_record_grammar(physical)
    file_date, batch_id = _parse_header(physical[0])
    index = 1
    transfers: list[Transfer] = []
    movement_ids: set[str] = set()
    while index < len(physical) - 1:
        parsed = _parse_transfer(
            physical[index],
            record_number=index + 1,
            file_date=file_date,
        )
        status = str(parsed["status_code"])
        return_record: ReturnRecord | None = None
        if status == "RT":
            return_record = _parse_return(
                physical[index + 1],
                record_number=index + 2,
            )
            if (
                return_record.original_transfer_id
                != parsed["transfer_id"]
                or return_record.amount != parsed["amount"]
            ):
                raise ValueError("RETURN_LINK_MISMATCH")
            if return_record.timestamp <= parsed["timestamp"]:
                raise ValueError("INVALID_TIMESTAMP")

        transfer_id = str(parsed["transfer_id"])
        if (
            return_record is not None
            and return_record.return_id == transfer_id
        ):
            raise ValueError("DUPLICATE_IDENTIFIER")
        ids = {transfer_id}
        if return_record is not None:
            ids.add(return_record.return_id)
        if movement_ids.intersection(ids):
            raise ValueError("DUPLICATE_IDENTIFIER")
        movement_ids.update(ids)
        transfers.append(
            Transfer(
                source_record_number=int(parsed["record_number"]),
                transfer_id=str(parsed["transfer_id"]),
                amount=Decimal(parsed["amount"]),
                timestamp=parsed["timestamp"],
                payer_ispb=str(parsed["payer_ispb"]),
                payer_branch=str(parsed["payer_branch"]),
                payer_account=str(parsed["payer_account"]),
                payer_tax_id=str(parsed["payer_tax_id"]),
                payer_party_type=str(parsed["payer_party_type"]),
                beneficiary_ispb=str(parsed["beneficiary_ispb"]),
                beneficiary_branch=str(parsed["beneficiary_branch"]),
                beneficiary_account=str(parsed["beneficiary_account"]),
                beneficiary_tax_id=str(parsed["beneficiary_tax_id"]),
                beneficiary_party_type=str(parsed["beneficiary_party_type"]),
                purpose_code=str(parsed["purpose_code"]),
                status_code=status,
                beneficiary_name=str(parsed["beneficiary_name"]),
                return_record=return_record,
            )
        )
        if len(transfers) > 10_000:
            raise ValueError("INVALID_SOURCE_SIZE")
        index += 2 if return_record is not None else 1

    trailer = _parse_trailer(
        physical[-1],
        file_date=file_date,
        batch_id=batch_id,
    )
    computed_transfer_count = len(transfers)
    computed_return_count = sum(
        transfer.return_record is not None for transfer in transfers
    )
    computed_gross = sum(
        (transfer.amount for transfer in transfers),
        Decimal("0.00"),
    )
    computed_return = -sum(
        (
            transfer.return_record.amount
            for transfer in transfers
            if transfer.return_record is not None
        ),
        Decimal("0.00"),
    )
    computed_net = computed_gross + computed_return
    if enforce_controls:
        if trailer["transfer_count"] != computed_transfer_count:
            raise ValueError("SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH")
        if trailer["return_count"] != computed_return_count:
            raise ValueError("SOURCE_CONTROL_RETURN_COUNT_MISMATCH")
        if trailer["gross"] != computed_gross:
            raise ValueError("SOURCE_CONTROL_GROSS_MISMATCH")
        if trailer["returned"] != computed_return:
            raise ValueError("SOURCE_CONTROL_RETURNED_MISMATCH")
        if trailer["net"] != computed_net:
            raise ValueError("SOURCE_CONTROL_NET_MISMATCH")
    return ParsedBatch(
        file_date=file_date,
        batch_id=batch_id,
        transfers=tuple(transfers),
        declared_transfer_count=int(trailer["transfer_count"]),
        computed_transfer_count=computed_transfer_count,
        declared_return_count=int(trailer["return_count"]),
        computed_return_count=computed_return_count,
        declared_gross_amount=Decimal(trailer["gross"]),
        computed_gross_amount=computed_gross,
        declared_return_amount=Decimal(trailer["returned"]),
        computed_return_amount=computed_return,
        declared_net_amount=Decimal(trailer["net"]),
        computed_net_amount=computed_net,
    )


def _token(value: str) -> str:
    digest = hmac.new(
        ACCOUNT_KEY,
        value.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"tedacct_{digest[:24]}"


def _mask(value: str, party_type: str) -> str:
    document = value[3:] if party_type == "F" else value
    prefix = "*" * (7 if party_type == "F" else 10)
    return f"{prefix}{document[-4:]}"


def _render_csv(batch: ParsedBatch) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for transfer in batch.transfers:
        context = (
            _token(transfer.payer_account_input),
            _mask(transfer.payer_tax_id, transfer.payer_party_type),
            _token(transfer.beneficiary_account_input),
            _mask(
                transfer.beneficiary_tax_id,
                transfer.beneficiary_party_type,
            ),
            transfer.beneficiary_ispb,
            transfer.purpose_code,
            transfer.status_code,
        )
        writer.writerow(
            (
                batch.batch_id,
                batch.source_filename,
                transfer.source_record_number,
                transfer.transfer_id,
                "",
                "TRANSFER",
                transfer.timestamp.isoformat(),
                format(transfer.amount, ".2f"),
                *context,
                "",
            )
        )
        if transfer.return_record is not None:
            returned = transfer.return_record
            writer.writerow(
                (
                    batch.batch_id,
                    batch.source_filename,
                    returned.source_record_number,
                    returned.return_id,
                    returned.original_transfer_id,
                    "RETURN",
                    returned.timestamp.isoformat(),
                    format(-returned.amount, ".2f"),
                    *context,
                    returned.reason_code,
                )
            )
    rendered = output.getvalue().encode("utf-8")
    for transfer in batch.transfers:
        prohibited = {
            transfer.payer_account,
            transfer.beneficiary_account,
            transfer.payer_tax_id,
            (
                transfer.payer_tax_id[3:]
                if transfer.payer_party_type == "F"
                else transfer.payer_tax_id
            ),
            transfer.beneficiary_tax_id,
            (
                transfer.beneficiary_tax_id[3:]
                if transfer.beneficiary_party_type == "F"
                else transfer.beneficiary_tax_id
            ),
            transfer.beneficiary_name,
        }
        if transfer.return_record is not None:
            prohibited.add(transfer.return_record.reason_text)
        for clear_value in prohibited:
            if clear_value.encode("ascii") in rendered:
                raise AssertionError(
                    f"Restricted value leaked from transfer "
                    f"{transfer.source_record_number}"
                )
    return rendered


def _expected_reconciliation(batch: ParsedBatch) -> dict[str, object]:
    transfer_count = batch.computed_transfer_count
    return_count = batch.computed_return_count
    gross = format(batch.computed_gross_amount, ".2f")
    returned = format(batch.computed_return_amount, ".2f")
    net = format(batch.computed_net_amount, ".2f")
    return {
        "batch_id": batch.batch_id,
        "currency": "BRL",
        "source_transfer_count": transfer_count,
        "staged_transfer_count": transfer_count,
        "applied_transfer_count": transfer_count,
        "source_return_count": return_count,
        "staged_return_count": return_count,
        "applied_return_count": return_count,
        "source_gross_amount": gross,
        "staged_gross_amount": gross,
        "applied_gross_amount": gross,
        "source_return_amount": returned,
        "staged_return_amount": returned,
        "applied_return_amount": returned,
        "source_net_amount": net,
        "staged_net_amount": net,
        "applied_net_amount": net,
        "transfer_count_delta": 0,
        "return_count_delta": 0,
        "gross_amount_delta": "0.00",
        "return_amount_delta": "0.00",
        "net_amount_delta": "0.00",
        "reject_count": 0,
        "status": "MATCHED",
    }


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _scenario_batch(scenario: str) -> tuple[str, str]:
    values = {
        "valid-minimal": ("20260723", "B202607230000301"),
        "valid-boundary": ("20000229", "B200002290000302"),
        "malformed": ("20260723", "B202607230000303"),
        "all-returned-zero-net": ("20260723", "B202607230000304"),
        "DF-SOURCE-004": ("20260723", "B202607230000305"),
    }
    return values[scenario]


def _controls_for(scenario: str) -> dict[str, object]:
    if scenario == "valid-boundary":
        return {
            "transfer_count": 1,
            "return_count": 0,
            "gross": "999999999999.99",
            "returned": "0.00",
            "declared_net": "999999999999.99",
            "computed_net": "999999999999.99",
        }
    if scenario == "all-returned-zero-net":
        return {
            "transfer_count": 2,
            "return_count": 2,
            "gross": "1250.00",
            "returned": "-1250.00",
            "declared_net": "0.00",
            "computed_net": "0.00",
        }
    return {
        "transfer_count": 2,
        "return_count": 1,
        "gross": "1250.00",
        "returned": "-250.00",
        "declared_net": (
            "999.99" if scenario == "DF-SOURCE-004" else "1000.00"
        ),
        "computed_net": "1000.00",
    }


def _source_artifact(scenario: str) -> dict[str, object]:
    file_date, batch_id = _scenario_batch(scenario)
    controls = _controls_for(scenario)
    filename = f"NW_TED_SETTLEMENT_{file_date}_{batch_id}.dat"
    raw_name = {
        "valid-minimal": "valid-minimal.dat",
        "valid-boundary": "valid-boundary.dat",
        "malformed": "malformed.dat",
        "all-returned-zero-net": "all-returned-zero-net.dat",
        "DF-SOURCE-004": "df-source-004.dat",
    }[scenario]
    raw = (MAIN / raw_name).read_bytes()
    return {
        "batch_id": batch_id,
        "file_type": {
            "code": "TED_SETTLE04",
            "contract_version": 1,
            "layout_version": "001",
            "number": "04",
        },
        "schema_version": 1,
        "source_controls": {
            "currency": "BRL",
            "gross_amount": controls["gross"],
            "net_amount": controls["declared_net"],
            "return_amount": controls["returned"],
            "return_count": controls["return_count"],
            "transfer_count": controls["transfer_count"],
        },
        "source_file": {
            "encoding": "US-ASCII",
            "final_newline": "required",
            "line_ending": "CRLF",
            "name": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
    }


def _receipt(scenario: str) -> dict[str, object]:
    file_date, batch_id = _scenario_batch(scenario)
    values = _controls_for(scenario)
    filename = f"NW_TED_SETTLEMENT_{file_date}_{batch_id}.dat"
    expected: dict[str, object] = {
        "status": "ACCEPTED",
        "violation": None,
    }
    fault: dict[str, object] | None = None
    if scenario == "malformed":
        expected = {"status": "REJECTED", "violation": "INVALID_TRANSPORT"}
        fault = {
            "code": "INVALID_TRANSPORT",
            "expected_stage": "java-validation",
            "injected": True,
        }
    elif scenario == "DF-SOURCE-004":
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
            "checksum_file": f"{filename}.sha256",
            "data_file": filename,
            "data_sha256": "a" * 64,
            "source_manifest": "source-manifest.json",
            "source_manifest_sha256": "b" * 64,
        },
        "batch_id": batch_id,
        "contract": {
            "layout_sha256": "c" * 64,
            "layout_version": "001",
            "registry_sha256": "d" * 64,
            "type_number": "04",
            "version": 1,
        },
        "controls": {
            "computed_gross_amount": values["gross"],
            "computed_net_amount": values["computed_net"],
            "computed_return_amount": values["returned"],
            "computed_return_count": values["return_count"],
            "computed_transfer_count": values["transfer_count"],
            "declared_gross_amount": values["gross"],
            "declared_net_amount": values["declared_net"],
            "declared_return_amount": values["returned"],
            "declared_return_count": values["return_count"],
            "declared_transfer_count": values["transfer_count"],
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


def _sanitized_artifact(scenario: str) -> dict[str, object]:
    file_date, batch_id = _scenario_batch(scenario)
    values = _controls_for(scenario)
    row_count = int(values["transfer_count"]) + int(values["return_count"])
    return {
        "batch_id": batch_id,
        "csv_file": {
            "encoding": "UTF-8",
            "name": f"NW_TED_SETTLEMENT_{file_date}_{batch_id}.csv",
            "row_count": row_count,
            "sha256": "e" * 64,
            "size_bytes": 1,
        },
        "file_type": {
            "code": "TED_SETTLE04",
            "contract_version": 1,
            "layout_version": "001",
            "number": "04",
        },
        "schema_version": 1,
        "source_lineage": {
            "manifest_sha256": "f" * 64,
            "raw_file": f"NW_TED_SETTLEMENT_{file_date}_{batch_id}.dat",
            "raw_sha256": "a" * 64,
        },
        "stage_controls": {
            "currency": "BRL",
            "gross_amount": values["gross"],
            "net_amount": values["computed_net"],
            "return_amount": values["returned"],
            "return_count": values["return_count"],
            "row_count": row_count,
            "transfer_count": values["transfer_count"],
        },
    }


class Type04ContractTest(unittest.TestCase):
    def test_contract_declares_closed_transport_privacy_and_time(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        privacy = _load_yaml(TYPE_ROOT / "privacy.yaml")
        csv_contract = _load_yaml(TYPE_ROOT / "csv.yaml")
        reconciliation = _load_yaml(TYPE_ROOT / "reconciliation.yaml")
        file_type = layout["file_type"]
        self.assertEqual(file_type["number"], "04")
        self.assertEqual(file_type["decoding"], "strict")
        self.assertEqual(file_type["line_ending"], "CRLF")
        self.assertEqual(file_type["max_transfers"], 10_000)
        self.assertEqual(file_type["max_source_file_bytes"], 2_570_142)
        self.assertEqual(
            layout["timestamp_semantics"]["source_zone"],
            "America/Sao_Paulo",
        )
        self.assertEqual(
            layout["record_sequence"]["branch_rule"],
            "D.status_code=OK selects D; D.status_code=RT selects D R",
        )
        self.assertEqual(
            privacy["account_transformation"]["missing_key_behavior"],
            "fail_closed",
        )
        self.assertEqual(
            privacy["whole_output_validation"]["failure_behavior"],
            "reject_entire_batch_without_publishing_csv",
        )
        self.assertEqual(csv_contract["format"]["max_rows"], 20_000)
        self.assertEqual(
            reconciliation["semantics"]["global_movement_id"],
            "unique_across_accepted_batches",
        )

    def test_three_success_truth_sets_are_independently_reproduced(self) -> None:
        all_movement_ids: set[str] = set()
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
                ids = {
                    transfer.transfer_id
                    for transfer in batch.transfers
                } | {
                    transfer.return_record.return_id
                    for transfer in batch.transfers
                    if transfer.return_record is not None
                }
                self.assertTrue(all_movement_ids.isdisjoint(ids))
                all_movement_ids.update(ids)
                self.assertEqual(
                    batch.declared_transfer_count,
                    batch.computed_transfer_count,
                )
                self.assertEqual(
                    batch.declared_return_count,
                    batch.computed_return_count,
                )
                self.assertEqual(
                    batch.declared_gross_amount,
                    batch.computed_gross_amount,
                )
                self.assertEqual(
                    batch.declared_return_amount,
                    batch.computed_return_amount,
                )
                self.assertEqual(
                    batch.declared_net_amount,
                    batch.computed_net_amount,
                )
        zero = _parse_source((MAIN / "all-returned-zero-net.dat").read_bytes())
        self.assertEqual(zero.declared_net_amount, Decimal("0.00"))
        self.assertEqual(zero.declared_return_amount, Decimal("-1250.00"))

    def test_five_raw_fixture_hashes_are_frozen(self) -> None:
        self.assertEqual(
            set(RAW_FIXTURES),
            {
                "valid-minimal",
                "valid-boundary",
                "malformed",
                "all-returned-zero-net",
                "DF-SOURCE-004",
            },
        )
        for scenario, (filename, expected_hash) in RAW_FIXTURES.items():
            with self.subTest(scenario=scenario):
                raw = (MAIN / filename).read_bytes()
                self.assertEqual(
                    hashlib.sha256(raw).hexdigest(),
                    expected_hash,
                )

    def test_all_five_batches_are_unique_and_documents_are_valid(self) -> None:
        seen: set[str] = set()
        for scenario in (
            "valid-minimal",
            "valid-boundary",
            "malformed",
            "all-returned-zero-net",
            "DF-SOURCE-004",
        ):
            source = _source_artifact(scenario)
            batch_id = str(source["batch_id"])
            self.assertNotIn(batch_id, seen)
            seen.add(batch_id)
        self.assertEqual(
            seen,
            {
                "B202607230000301",
                "B200002290000302",
                "B202607230000303",
                "B202607230000304",
                "B202607230000305",
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
            for batch_id in seen:
                self.assertNotIn(batch_id.encode("ascii"), payload, path)

    def test_malformed_has_only_one_bare_lf_transport_defect(self) -> None:
        raw = (MAIN / "malformed.dat").read_bytes()
        self.assertEqual(raw.count(b"\n") - raw.count(b"\r\n"), 1)
        with self.assertRaisesRegex(ValueError, "INVALID_TRANSPORT"):
            _parse_source(raw)
        corrected = raw.replace(b"\n", b"\r\n", 1)
        batch = _parse_source(corrected)
        self.assertEqual(batch.computed_transfer_count, 2)
        self.assertEqual(batch.computed_return_count, 1)
        self.assertEqual(batch.computed_net_amount, Decimal("1000.00"))
        expected = _load_yaml(MAIN / "expected-malformed-rejection.yaml")
        self.assertEqual(expected["expected_code"], "INVALID_TRANSPORT")
        self.assertFalse(expected["csv_produced"])
        self.assertFalse(expected["postgres_business_mutation"])
        self.assertNotIn("movement_id", expected)

    def test_dark_factory_has_only_the_trailer_net_defect(self) -> None:
        raw = (MAIN / "df-source-004.dat").read_bytes()
        batch = _parse_source(raw, enforce_controls=False)
        self.assertEqual(
            batch.declared_transfer_count,
            batch.computed_transfer_count,
        )
        self.assertEqual(
            batch.declared_return_count,
            batch.computed_return_count,
        )
        self.assertEqual(
            batch.declared_gross_amount,
            batch.computed_gross_amount,
        )
        self.assertEqual(
            batch.declared_return_amount,
            batch.computed_return_amount,
        )
        self.assertEqual(batch.declared_net_amount, Decimal("999.99"))
        self.assertEqual(batch.computed_net_amount, Decimal("1000.00"))
        with self.assertRaisesRegex(
            ValueError,
            "SOURCE_CONTROL_NET_MISMATCH",
        ):
            _parse_source(raw)

        records = raw[:-2].split(b"\r\n")
        trailer = bytearray(records[-1])
        trailer[52:66] = b"00000000100000"
        corrected = b"\r\n".join(
            records[:-1] + [bytes(trailer)]
        ) + b"\r\n"
        _parse_source(corrected)

        finding = _load_yaml(MAIN / "expected-df-source-004-finding.yaml")
        self.assertEqual(
            finding["expected_code"],
            "SOURCE_CONTROL_NET_MISMATCH",
        )
        self.assertEqual(finding["source_system_role"], "system_of_record")
        self.assertEqual(finding["declared_net_amount"], "999.99")
        self.assertEqual(finding["computed_net_amount"], "1000.00")
        self.assertFalse(finding["csv_produced"])
        self.assertFalse(finding["postgres_business_mutation"])

    def test_branch_grammar_precedes_transfer_field_validation(self) -> None:
        raw = (MAIN / "valid-minimal.dat").read_bytes()
        records = raw[:-2].split(b"\r\n")

        def poison_transfer(record: bytes) -> bytes:
            poisoned = bytearray(record)
            poisoned[112:126] = b"99999999999999"
            poisoned[126] = ord("J")
            poisoned[161] = ord("A")
            return bytes(poisoned)

        rt_missing_return = (
            b"\r\n".join(
                records[:2]
                + [poison_transfer(records[2])]
                + records[4:]
            )
            + b"\r\n"
        )
        ok_extra_return = (
            b"\r\n".join(
                [records[0], poison_transfer(records[1]), records[3]]
                + records[2:]
            )
            + b"\r\n"
        )

        for scenario, mutated in {
            "rt_missing_return_with_bad_document_and_padding": (
                rt_missing_return
            ),
            "ok_extra_return_with_bad_document_and_padding": (
                ok_extra_return
            ),
        }.items():
            with self.subTest(scenario=scenario):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(mutated)
                self.assertEqual(
                    str(raised.exception),
                    "RETURN_LINK_MISMATCH",
                )

    def test_required_return_field_and_linkage_precedence_is_stable(
        self,
    ) -> None:
        raw = (MAIN / "valid-minimal.dat").read_bytes()
        records = raw[:-2].split(b"\r\n")

        bad_identifier_and_link = list(records)
        returned = bytearray(bad_identifier_and_link[3])
        returned[1] = ord("1")
        returned[17:33] = records[1][1:17]
        bad_identifier_and_link[3] = bytes(returned)

        bad_link_and_time = list(records)
        returned = bytearray(bad_link_and_time[3])
        returned[17:33] = records[1][1:17]
        returned[48:62] = b"20260723090000"
        bad_link_and_time[3] = bytes(returned)

        cases = {
            "bad_return_identifier_and_link": (
                bad_identifier_and_link,
                "INVALID_IDENTIFIER",
            ),
            "bad_link_and_nonlater_timestamp": (
                bad_link_and_time,
                "RETURN_LINK_MISMATCH",
            ),
        }
        for scenario, (mutated_records, expected_code) in cases.items():
            with self.subTest(scenario=scenario):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        b"\r\n".join(mutated_records) + b"\r\n"
                    )
                self.assertEqual(
                    str(raised.exception),
                    expected_code,
                )

    def test_return_id_cannot_equal_its_preceding_transfer_id(self) -> None:
        raw = (MAIN / "valid-minimal.dat").read_bytes()
        records = raw[:-2].split(b"\r\n")
        self.assertEqual(records[2][:1], b"D")
        self.assertEqual(records[3][:1], b"R")

        returned = bytearray(records[3])
        returned[1:17] = records[2][1:17]
        mutated = b"\r\n".join(
            records[:3] + [bytes(returned)] + records[4:]
        ) + b"\r\n"

        with self.assertRaises(ValueError) as raised:
            _parse_source(mutated)
        self.assertEqual(
            str(raised.exception),
            "DUPLICATE_IDENTIFIER",
        )

    def test_every_declared_rejection_phase_has_oracle_coverage(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        self.assertEqual(
            layout["validation_order"],
            [
                "source_size_and_ascii",
                "exact_crlf_transport_and_final_crlf",
                "discriminator_and_exact_variant_length",
                "conditional_record_grammar",
                "literals_dates_times_and_visible_padding",
                "field_lexical_and_numeric_rules",
                "CPF_CNPJ_Mod11",
                "safe_identifier_and_text_rules",
                "conditional_return_linkage",
                "uniqueness_and_timestamp_rules",
                "source_count_controls",
                "source_gross_control",
                "source_returned_control",
                "source_net_control",
            ],
        )
        raw = (MAIN / "valid-minimal.dat").read_bytes()
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
        first_transfer_id = records[1][1:17]
        second_transfer = bytearray(duplicate_records[2])
        second_transfer[1:17] = first_transfer_id
        duplicate_records[2] = bytes(second_transfer)
        returned = bytearray(duplicate_records[3])
        returned[17:33] = first_transfer_id
        duplicate_records[3] = bytes(returned)

        invalid_ascii = bytearray(raw)
        invalid_ascii[55] = 0xFF
        cases = {
            "INVALID_SOURCE_SIZE": b"A" * 2_570_143,
            "INVALID_ASCII": bytes(invalid_ascii),
            "INVALID_TRANSPORT": raw.replace(b"\r\n", b"\n", 1),
            "INVALID_RECORD_LENGTH": mutate(1, 161, 162, b""),
            "INVALID_RECORD_SEQUENCE": mutate(1, 0, 1, b"X"),
            "INVALID_PADDING": mutate(2, 136, 137, b"A"),
            "INVALID_FIELD": mutate(1, 17, 18, b"-"),
            "INVALID_DOCUMENT": mutate(
                1,
                73,
                87,
                b"99999999999999",
            ),
            "INVALID_IDENTIFIER": mutate(1, 1, 2, b"1"),
            "RETURN_LINK_MISMATCH": (
                b"\r\n".join(records[:3] + records[4:]) + b"\r\n"
            ),
            "INVALID_TIMESTAMP": (
                mutate(3, 48, 62, b"20260723090000")
            ),
            "DUPLICATE_IDENTIFIER": (
                b"\r\n".join(duplicate_records) + b"\r\n"
            ),
            "SOURCE_CONTROL_TRANSFER_COUNT_MISMATCH": mutate(
                4,
                9,
                15,
                b"000003",
            ),
            "SOURCE_CONTROL_RETURN_COUNT_MISMATCH": mutate(
                4,
                15,
                21,
                b"000002",
            ),
            "SOURCE_CONTROL_GROSS_MISMATCH": mutate(
                4,
                22,
                36,
                b"00000000125001",
            ),
            "SOURCE_CONTROL_RETURNED_MISMATCH": mutate(
                4,
                37,
                51,
                b"00000000025001",
            ),
            "SOURCE_CONTROL_NET_MISMATCH": mutate(
                4,
                52,
                66,
                b"00000000100001",
            ),
        }
        self.assertEqual(
            set(cases),
            set(layout["canonical_rejection_codes"].values()),
        )
        for expected_code, mutated in cases.items():
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(mutated)
                self.assertEqual(str(raised.exception), expected_code)

        document_then_identifier = list(records)
        transfer = bytearray(document_then_identifier[1])
        transfer[1] = ord("1")
        transfer[73:87] = b"99999999999999"
        document_then_identifier[1] = bytes(transfer)
        with self.assertRaises(ValueError) as raised:
            _parse_source(b"\r\n".join(document_then_identifier) + b"\r\n")
        self.assertEqual(str(raised.exception), "INVALID_DOCUMENT")

        padding_then_field = list(records)
        transfer = bytearray(padding_then_field[2])
        transfer[17] = ord("-")
        transfer[136] = ord("A")
        padding_then_field[2] = bytes(transfer)
        with self.assertRaises(ValueError) as raised:
            _parse_source(b"\r\n".join(padding_then_field) + b"\r\n")
        self.assertEqual(str(raised.exception), "INVALID_PADDING")

    def test_five_source_manifests_and_receipts_are_schema_valid(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        sanitized_validator = _validator("sanitized-manifest.schema.json")
        scenarios = (
            "valid-minimal",
            "valid-boundary",
            "malformed",
            "all-returned-zero-net",
            "DF-SOURCE-004",
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                source_validator.validate(_source_artifact(scenario))
                receipt_validator.validate(_receipt(scenario))
        for scenario in SUCCESS_SCENARIOS:
            sanitized_validator.validate(_sanitized_artifact(scenario))

        cross_source = _source_artifact("valid-minimal")
        cross_source["source_controls"] = {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "logical_count": 2,
            "lot_count": 1,
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "physical_record_count": 8,
        }
        self.assertTrue(list(source_validator.iter_errors(cross_source)))

        positive_return = _source_artifact("valid-minimal")
        positive_return["source_controls"]["return_amount"] = "250.00"
        self.assertTrue(list(source_validator.iter_errors(positive_return)))
        negative_zero = _source_artifact("valid-boundary")
        negative_zero["source_controls"]["return_amount"] = "-0.00"
        self.assertTrue(list(source_validator.iter_errors(negative_zero)))
        oversized = _source_artifact("valid-minimal")
        oversized["source_file"]["size_bytes"] = 2_570_143
        self.assertTrue(list(source_validator.iter_errors(oversized)))

        contradictory = _receipt("valid-minimal")
        contradictory["fault"] = {
            "code": "INVALID_TRANSPORT",
            "expected_stage": "java-validation",
            "injected": True,
        }
        self.assertTrue(list(receipt_validator.iter_errors(contradictory)))
        cross_receipt = _receipt("valid-minimal")
        cross_receipt["artifacts"]["data_file"] = (
            "NW_PAYMENT_SLIP_20260723_B202607230000301.rem"
        )
        self.assertTrue(list(receipt_validator.iter_errors(cross_receipt)))

        cross_lineage = _sanitized_artifact("valid-minimal")
        cross_lineage["source_lineage"]["raw_file"] = (
            "NW_INSTANT_PAYMENT_20260723_B202607230000301.txt"
        )
        self.assertTrue(
            list(sanitized_validator.iter_errors(cross_lineage))
        )
        oversized_rows = _sanitized_artifact("valid-minimal")
        oversized_rows["csv_file"]["row_count"] = 20_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_rows))
        )

    def test_artifact_links_and_control_cardinality_are_mandatory(self) -> None:
        for scenario in (
            "valid-minimal",
            "valid-boundary",
            "malformed",
            "all-returned-zero-net",
            "DF-SOURCE-004",
        ):
            source = _source_artifact(scenario)
            match = re.fullmatch(
                r"NW_TED_SETTLEMENT_([0-9]{8})_(B[0-9]{15})\.dat",
                source["source_file"]["name"],
            )
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual(match.group(2), source["batch_id"])
            self.assertLessEqual(
                source["source_controls"]["return_count"],
                source["source_controls"]["transfer_count"],
            )
        for scenario in SUCCESS_SCENARIOS:
            sanitized = _sanitized_artifact(scenario)
            controls = sanitized["stage_controls"]
            self.assertEqual(
                sanitized["csv_file"]["row_count"],
                controls["transfer_count"] + controls["return_count"],
            )
            raw_match = re.fullmatch(
                r"NW_TED_SETTLEMENT_([0-9]{8})_(B[0-9]{15})\.dat",
                sanitized["source_lineage"]["raw_file"],
            )
            csv_match = re.fullmatch(
                r"NW_TED_SETTLEMENT_([0-9]{8})_(B[0-9]{15})\.csv",
                sanitized["csv_file"]["name"],
            )
            self.assertIsNotNone(raw_match)
            self.assertIsNotNone(csv_match)
            assert raw_match is not None and csv_match is not None
            self.assertEqual(raw_match.groups(), csv_match.groups())
            self.assertEqual(raw_match.group(2), sanitized["batch_id"])


if __name__ == "__main__":
    unittest.main()
