from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import unittest
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
TYPE_ROOT = ROOT / "contracts" / "types" / "02-instant-payment-events"
MAIN = TYPE_ROOT / "main"
COMMON = ROOT / "contracts" / "common"
DOCUMENT_KEY = b"northwind-pay-edp-fixture-document-key-v1"
CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "end_to_end_id",
    "transaction_id",
    "payer_document_token",
    "payer_document_masked",
    "payee_document_token",
    "payee_document_masked",
    "event_timestamp",
    "amount_brl",
    "direction",
    "status",
    "return_code",
    "description",
)
SUCCESS_SCENARIOS = {
    "valid-minimal": (
        "valid-minimal.txt",
        "expected-sanitized.csv",
        "expected-reconciliation.yaml",
    ),
    "valid-boundary": (
        "valid-boundary.txt",
        "expected-valid-boundary-sanitized.csv",
        "expected-valid-boundary-reconciliation.yaml",
    ),
    "escaped-content": (
        "escaped-content.txt",
        "expected-escaped-content-sanitized.csv",
        "expected-escaped-content-reconciliation.yaml",
    ),
}
EXPECTED_RAW_SHA256 = {
    "valid-minimal": "a5c2ec1c586aaa2fd79c95555cc02a9d2596e473805c48c506201c18c6f7d5a9",
    "valid-boundary": "93c084cf65d48797eaaef4468d491ffb33403a750c9e691098bb6aa91e91e471",
    "malformed": "f5a54cf908a9a2d256b1c98d991f5695fa829eccaf482ea555e3a1032692fd0b",
    "escaped-content": "1f2dac2f89f54893f44e9a8aea148971446429e6f621b6734c8632d6d64a0345",
    "DF-SOURCE-002": "685c2617e7f07951181eaf646f349f6dd798638a7d14e4d268ef8f9d87d0d87d",
}
MONEY_PATTERN = re.compile(r"^(0|[1-9][0-9]{0,15})\.[0-9]{2}$")
SIGNED_MONEY_PATTERN = re.compile(
    r"^-?(0|[1-9][0-9]{0,15})\.[0-9]{2}$"
)
TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
BIDI_CONTROL_CODE_POINTS = frozenset(
    {
        0x061C,
        0x200E,
        0x200F,
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
    }
)


@dataclass(frozen=True, slots=True)
class ParsedEvent:
    source_record_number: int
    end_to_end_id: str
    transaction_id: str
    payer_document_type: str
    payer_document: str
    payee_document_type: str
    payee_document: str
    event_timestamp: str
    amount: Decimal
    direction: str
    status: str
    return_code: str
    description: str


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    file_date: str
    batch_id: str
    events: tuple[ParsedEvent, ...]
    declared_count: int
    declared_credit: Decimal
    declared_debit: Decimal
    declared_net: Decimal

    @property
    def source_filename(self) -> str:
        return f"NW_INSTANT_PAYMENT_{self.file_date}_{self.batch_id}.txt"

    @property
    def computed_credit(self) -> Decimal:
        return sum(
            (event.amount for event in self.events if event.direction == "C"),
            start=Decimal("0.00"),
        )

    @property
    def computed_debit(self) -> Decimal:
        return sum(
            (event.amount for event in self.events if event.direction == "D"),
            start=Decimal("0.00"),
        )

    @property
    def computed_net(self) -> Decimal:
        return self.computed_credit - self.computed_debit

    @property
    def returned_count(self) -> int:
        return sum(event.status == "RETURNED" for event in self.events)


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"Expected a mapping in {path.name}")
    return loaded


def _lex_record(line: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(line):
        character = line[index]
        if character == "\\":
            if index + 1 >= len(line) or line[index + 1] not in {"\\", "|"}:
                raise ValueError("INVALID_ESCAPE_SEQUENCE")
            current.append(line[index + 1])
            index += 2
            continue
        if character == "|":
            fields.append("".join(current))
            current = []
            index += 1
            continue
        current.append(character)
        index += 1
    fields.append("".join(current))
    return fields


def _cpf_is_valid(value: str) -> bool:
    if len(value) != 11 or not value.isascii() or not value.isdigit():
        return False
    if len(set(value)) == 1:
        return False
    digits = [int(character) for character in value]
    first_sum = sum(digit * weight for digit, weight in zip(digits[:9], range(10, 1, -1)))
    first_remainder = first_sum % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_sum = sum(
        digit * weight
        for digit, weight in zip(digits[:9] + [first], range(11, 1, -1))
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
        digit * weight for digit, weight in zip(digits[:12], first_weights)
    ) % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_remainder = sum(
        digit * weight
        for digit, weight in zip(digits[:12] + [first], second_weights)
    ) % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return digits[-2:] == [first, second]


def _document_is_valid(document_type: str, value: str) -> bool:
    if document_type == "CPF":
        return _cpf_is_valid(value)
    if document_type == "CNPJ":
        return _cnpj_is_valid(value)
    return False


def _validate_description(value: str) -> None:
    if not 1 <= len(value) <= 80:
        raise ValueError("INVALID_DESCRIPTION")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("INVALID_DESCRIPTION")
    if value[0] in "=+-@":
        raise ValueError("INVALID_DESCRIPTION")
    if re.search(r"[0-9]{11,19}", value):
        raise ValueError("INVALID_DESCRIPTION")
    for character in value:
        category = unicodedata.category(character)
        if (
            category == "Cc"
            or ord(character) in BIDI_CONTROL_CODE_POINTS
        ):
            raise ValueError("INVALID_DESCRIPTION")


def _parse_source(raw: bytes, *, enforce_controls: bool = True) -> ParsedBatch:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("INVALID_TRANSPORT")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n") or b"\r" in raw:
        raise ValueError("INVALID_TRANSPORT")
    text = raw.decode("utf-8", errors="strict")
    lines = text[:-1].split("\n")
    if "" in lines:
        raise ValueError("INVALID_TRANSPORT")
    parsed = [_lex_record(line) for line in lines]
    if len(parsed[0]) != 5 or parsed[0][:3] != ["H", "PIX_EVENTS01", "001"]:
        raise ValueError("INVALID_RECORD_SEQUENCE")
    if len(parsed[-1]) != 5 or parsed[-1][0] != "T":
        raise ValueError("INVALID_RECORD_SEQUENCE")

    file_date = parsed[0][3]
    batch_id = parsed[0][4]
    events: list[ParsedEvent] = []
    for physical_record_number, fields in enumerate(parsed[1:-1], start=2):
        if len(fields) != 13:
            raise ValueError(
                f"INVALID_FIELD_COUNT:{physical_record_number}:{len(fields)}"
            )
        if fields[0] != "D":
            raise ValueError("INVALID_RECORD_SEQUENCE")
        if not _document_is_valid(fields[3], fields[4]):
            raise ValueError("INVALID_DOCUMENT")
        if not _document_is_valid(fields[5], fields[6]):
            raise ValueError("INVALID_DOCUMENT")
        timestamp = fields[7]
        if not TIMESTAMP_PATTERN.fullmatch(timestamp):
            raise ValueError("INVALID_TIMESTAMP")
        if timestamp.endswith(("+00:00", "-00:00")):
            raise ValueError("INVALID_TIMESTAMP")
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        local_date = parsed_timestamp.astimezone(
            ZoneInfo("America/Sao_Paulo")
        ).strftime("%Y%m%d")
        if local_date != file_date:
            raise ValueError("INVALID_TIMESTAMP")
        if not MONEY_PATTERN.fullmatch(fields[8]) or Decimal(fields[8]) <= 0:
            raise ValueError("INVALID_AMOUNT")
        if fields[9] not in {"C", "D"}:
            raise ValueError("INVALID_AMOUNT")
        if fields[10] == "SETTLED" and fields[11] != "":
            raise ValueError("INVALID_STATUS_RETURN_CODE")
        if fields[10] == "RETURNED" and not re.fullmatch(
            r"[A-Z0-9]{1,4}", fields[11]
        ):
            raise ValueError("INVALID_STATUS_RETURN_CODE")
        if fields[10] not in {"SETTLED", "RETURNED"}:
            raise ValueError("INVALID_STATUS_RETURN_CODE")
        _validate_description(fields[12])
        if fields[4] in fields[12] or fields[6] in fields[12]:
            raise ValueError("INVALID_DESCRIPTION")
        events.append(
            ParsedEvent(
                source_record_number=physical_record_number,
                end_to_end_id=fields[1],
                transaction_id=fields[2],
                payer_document_type=fields[3],
                payer_document=fields[4],
                payee_document_type=fields[5],
                payee_document=fields[6],
                event_timestamp=timestamp,
                amount=Decimal(fields[8]),
                direction=fields[9],
                status=fields[10],
                return_code=fields[11],
                description=fields[12],
            )
        )

    trailer = parsed[-1]
    if not MONEY_PATTERN.fullmatch(trailer[2]):
        raise ValueError("INVALID_AMOUNT")
    if not MONEY_PATTERN.fullmatch(trailer[3]):
        raise ValueError("INVALID_AMOUNT")
    if not SIGNED_MONEY_PATTERN.fullmatch(trailer[4]) or trailer[4] == "-0.00":
        raise ValueError("INVALID_AMOUNT")
    batch = ParsedBatch(
        file_date=file_date,
        batch_id=batch_id,
        events=tuple(events),
        declared_count=int(trailer[1]),
        declared_credit=Decimal(trailer[2]),
        declared_debit=Decimal(trailer[3]),
        declared_net=Decimal(trailer[4]),
    )
    if len({event.end_to_end_id for event in events}) != len(events):
        raise ValueError("DUPLICATE_IDENTIFIER")
    if len({event.transaction_id for event in events}) != len(events):
        raise ValueError("DUPLICATE_IDENTIFIER")
    if enforce_controls:
        if batch.declared_count != len(events):
            raise ValueError("SOURCE_CONTROL_COUNT_MISMATCH")
        if batch.declared_credit != batch.computed_credit:
            raise ValueError("SOURCE_CONTROL_CREDIT_MISMATCH")
        if batch.declared_debit != batch.computed_debit:
            raise ValueError("SOURCE_CONTROL_DEBIT_MISMATCH")
        if batch.declared_net != batch.computed_net:
            raise ValueError("SOURCE_CONTROL_NET_MISMATCH")
    return batch


def _token(value: str) -> str:
    digest = hmac.new(
        DOCUMENT_KEY,
        value.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"doc_{digest[:24]}"


def _mask(document_type: str, value: str) -> str:
    prefix = "*" * (7 if document_type == "CPF" else 10)
    return f"{prefix}{value[-4:]}"


def _render_csv(batch: ParsedBatch) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(
        output,
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(CSV_COLUMNS)
    for event in batch.events:
        signed_amount = (
            event.amount if event.direction == "C" else -event.amount
        )
        writer.writerow(
            (
                batch.batch_id,
                batch.source_filename,
                event.source_record_number,
                event.end_to_end_id,
                event.transaction_id,
                _token(event.payer_document),
                _mask(event.payer_document_type, event.payer_document),
                _token(event.payee_document),
                _mask(event.payee_document_type, event.payee_document),
                event.event_timestamp,
                format(signed_amount, ".2f"),
                event.direction,
                event.status,
                event.return_code,
                event.description,
            )
        )
    rendered = output.getvalue().encode("utf-8")
    for event in batch.events:
        if event.payer_document.encode("ascii") in rendered:
            raise AssertionError("Payer document leaked into CSV")
        if event.payee_document.encode("ascii") in rendered:
            raise AssertionError("Payee document leaked into CSV")
    return rendered


def _expected_reconciliation(batch: ParsedBatch) -> dict[str, object]:
    credit = format(batch.computed_credit, ".2f")
    debit = format(batch.computed_debit, ".2f")
    net = format(batch.computed_net, ".2f")
    count = len(batch.events)
    returned = batch.returned_count
    return {
        "batch_id": batch.batch_id,
        "currency": "BRL",
        "source_count": count,
        "staged_count": count,
        "applied_count": count,
        "source_credit_amount": credit,
        "staged_credit_amount": credit,
        "applied_credit_amount": credit,
        "source_debit_amount": debit,
        "staged_debit_amount": debit,
        "applied_debit_amount": debit,
        "source_net_amount": net,
        "staged_net_amount": net,
        "applied_net_amount": net,
        "source_returned_count": returned,
        "staged_returned_count": returned,
        "applied_returned_count": returned,
        "count_delta": 0,
        "credit_amount_delta": "0.00",
        "debit_amount_delta": "0.00",
        "net_amount_delta": "0.00",
        "returned_count_delta": 0,
        "reject_count": 0,
        "status": "MATCHED",
    }


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_type02_artifact_links(
    *,
    batch_id: str,
    raw_filename: str,
    checksum_filename: str | None = None,
    csv_filename: str | None = None,
) -> None:
    raw_match = re.fullmatch(
        r"NW_INSTANT_PAYMENT_([0-9]{8})_(B[0-9]{15})\.txt",
        raw_filename,
    )
    if raw_match is None or raw_match.group(2) != batch_id:
        raise ValueError("MANIFEST_BATCH_LINK_MISMATCH")
    date = raw_match.group(1)
    if checksum_filename is not None and checksum_filename != f"{raw_filename}.sha256":
        raise ValueError("MANIFEST_CHECKSUM_LINK_MISMATCH")
    if csv_filename is not None:
        expected_csv = f"NW_INSTANT_PAYMENT_{date}_{batch_id}.csv"
        if csv_filename != expected_csv:
            raise ValueError("MANIFEST_CSV_LINK_MISMATCH")


def _validate_type02_sanitized_control_links(
    *,
    row_count: int,
    returned_count: int,
) -> None:
    if returned_count > row_count:
        raise ValueError("MANIFEST_RETURNED_COUNT_LINK_MISMATCH")


class Type02ContractTest(unittest.TestCase):
    def test_description_accepts_zwj_and_rejects_declared_controls(self) -> None:
        _validate_description("Pagamento 👩‍💻")

        for code_point in sorted(BIDI_CONTROL_CODE_POINTS):
            with self.subTest(kind="bidi", code_point=f"U+{code_point:04X}"):
                with self.assertRaisesRegex(
                    ValueError,
                    "^INVALID_DESCRIPTION$",
                ):
                    _validate_description(f"safe{chr(code_point)}text")

        control_code_points = (
            *range(0x0000, 0x0020),
            *range(0x007F, 0x00A0),
        )
        for code_point in control_code_points:
            with self.subTest(
                kind="unicode-control",
                code_point=f"U+{code_point:04X}",
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "^INVALID_DESCRIPTION$",
                ):
                    _validate_description(f"safe{chr(code_point)}text")

    def test_contract_yaml_is_parseable_and_declares_closed_transport(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        privacy = _load_yaml(TYPE_ROOT / "privacy.yaml")
        csv_contract = _load_yaml(TYPE_ROOT / "csv.yaml")
        reconciliation = _load_yaml(TYPE_ROOT / "reconciliation.yaml")

        file_type = layout["file_type"]
        grammar = layout["grammar"]
        self.assertEqual(file_type["number"], "02")
        self.assertEqual(file_type["encoding"], "UTF-8")
        self.assertEqual(file_type["utf8_decoding"], "strict")
        self.assertEqual(file_type["bom"], "forbidden")
        self.assertEqual(file_type["line_ending"], "LF")
        self.assertEqual(file_type["final_newline"], "required")
        self.assertEqual(file_type["max_record_bytes"], 512)
        self.assertEqual(file_type["max_source_file_bytes"], 5_200_000)
        self.assertEqual(grammar["parser"], "single_pass_escape_aware_lexer")
        self.assertEqual(grammar["escape_decoding"], "exactly_once")
        self.assertEqual(
            privacy["document_transformation"]["token"]["missing_key_behavior"],
            "fail_closed",
        )
        self.assertEqual(csv_contract["format"]["final_newline"], "required")
        self.assertEqual(csv_contract["format"]["max_rows"], 10_000)
        self.assertEqual(csv_contract["format"]["max_file_bytes"], 6_000_000)
        self.assertEqual(
            reconciliation["semantics"]["global_end_to_end_id"],
            "unique_across_accepted_batches",
        )

    def test_three_success_oracles_are_independently_reproduced(self) -> None:
        for scenario, filenames in SUCCESS_SCENARIOS.items():
            with self.subTest(scenario=scenario):
                raw_name, csv_name, reconciliation_name = filenames
                raw = (MAIN / raw_name).read_bytes()
                batch = _parse_source(raw)
                self.assertEqual(
                    _render_csv(batch),
                    (MAIN / csv_name).read_bytes(),
                )
                self.assertEqual(
                    _expected_reconciliation(batch),
                    _load_yaml(MAIN / reconciliation_name),
                )
                for event in batch.events:
                    self.assertNotIn(
                        event.payer_document,
                        (MAIN / csv_name).read_text(encoding="utf-8"),
                    )
                    self.assertNotIn(
                        event.payee_document,
                        (MAIN / csv_name).read_text(encoding="utf-8"),
                    )

    def test_existing_raw_fixture_hashes_remain_stable(self) -> None:
        raw_names = {
            "valid-minimal": "valid-minimal.txt",
            "valid-boundary": "valid-boundary.txt",
            "malformed": "malformed.txt",
            "escaped-content": "escaped-content.txt",
            "DF-SOURCE-002": "df-source-002.txt",
        }
        for scenario, expected_hash in EXPECTED_RAW_SHA256.items():
            with self.subTest(scenario=scenario):
                actual = hashlib.sha256(
                    (MAIN / raw_names[scenario]).read_bytes()
                ).hexdigest()
                self.assertEqual(actual, expected_hash)

    def test_malformed_is_only_an_unescaped_delimiter_failure(self) -> None:
        raw = (MAIN / "malformed.txt").read_bytes()
        with self.assertRaisesRegex(ValueError, r"INVALID_FIELD_COUNT:2:14"):
            _parse_source(raw)
        expected = _load_yaml(MAIN / "expected-malformed-rejection.yaml")
        self.assertEqual(expected["expected_code"], "INVALID_FIELD_COUNT")
        self.assertFalse(expected["csv_produced"])
        self.assertFalse(expected["postgres_business_mutation"])
        self.assertNotIn("end_to_end_id", expected)
        self.assertNotIn("transaction_id", expected)

    def test_dark_factory_fixture_is_only_a_source_net_control_defect(self) -> None:
        raw = (MAIN / "df-source-002.txt").read_bytes()
        batch = _parse_source(raw, enforce_controls=False)
        self.assertEqual(batch.declared_count, len(batch.events))
        self.assertEqual(batch.declared_credit, batch.computed_credit)
        self.assertEqual(batch.declared_debit, batch.computed_debit)
        self.assertEqual(batch.declared_net, Decimal("173.44"))
        self.assertEqual(batch.computed_net, Decimal("173.45"))
        with self.assertRaisesRegex(ValueError, "SOURCE_CONTROL_NET_MISMATCH"):
            _parse_source(raw)

        finding = _load_yaml(MAIN / "expected-df-source-002-finding.yaml")
        self.assertEqual(
            finding["expected_code"],
            "SOURCE_CONTROL_NET_MISMATCH",
        )
        self.assertEqual(finding["source_system_role"], "system_of_record")
        self.assertEqual(finding["declared_net_amount"], "173.44")
        self.assertEqual(finding["computed_net_amount"], "173.45")
        self.assertFalse(finding["postgres_business_mutation"])

    def test_type02_common_schema_branches_are_closed(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        sanitized_validator = _validator("sanitized-manifest.schema.json")

        type02_source = {
            "batch_id": "B202607230000101",
            "file_type": {
                "code": "PIX_EVENTS01",
                "contract_version": 1,
                "layout_version": "001",
                "number": "02",
            },
            "schema_version": 1,
            "source_controls": {
                "credit_amount": "200.00",
                "currency": "BRL",
                "debit_amount": "26.55",
                "event_count": 2,
                "net_amount": "173.45",
            },
            "source_file": {
                "encoding": "UTF-8",
                "final_newline": "required",
                "line_ending": "LF",
                "name": (
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.txt"
                ),
                "sha256": "a" * 64,
                "size_bytes": 1,
            },
        }
        source_validator.validate(type02_source)

        cross_paired = json.loads(json.dumps(type02_source))
        cross_paired["source_controls"] = {
            "currency": "BRL",
            "detail_count": 2,
            "net_amount": "173.45",
        }
        self.assertTrue(list(source_validator.iter_errors(cross_paired)))

        negative_zero_source = json.loads(json.dumps(type02_source))
        negative_zero_source["source_controls"]["net_amount"] = "-0.00"
        self.assertTrue(
            list(source_validator.iter_errors(negative_zero_source))
        )

        oversized_source = json.loads(json.dumps(type02_source))
        oversized_source["source_file"]["size_bytes"] = 5_200_001
        self.assertTrue(list(source_validator.iter_errors(oversized_source)))

        type02_receipt = {
            "artifacts": {
                "checksum_file": (
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.txt.sha256"
                ),
                "data_file": (
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.txt"
                ),
                "data_sha256": "a" * 64,
                "source_manifest": "source-manifest.json",
                "source_manifest_sha256": "b" * 64,
            },
            "batch_id": "B202607230000101",
            "contract": {
                "layout_sha256": "c" * 64,
                "layout_version": "001",
                "registry_sha256": "d" * 64,
                "type_number": "02",
                "version": 1,
            },
            "controls": {
                "computed_credit_amount": "200.00",
                "computed_debit_amount": "26.55",
                "computed_event_count": 2,
                "computed_net_amount": "173.45",
                "declared_credit_amount": "200.00",
                "declared_debit_amount": "26.55",
                "declared_event_count": 2,
                "declared_net_amount": "173.45",
            },
            "expected_contract_result": {
                "status": "ACCEPTED",
                "violation": None,
            },
            "fault": None,
            "generator": {
                "name": "northwind-pay-datagen",
                "version": "0.1.0",
            },
            "scenario": "valid-minimal",
            "schema_version": 1,
            "status": "generated",
        }
        receipt_validator.validate(type02_receipt)

        wrong_type_receipt = json.loads(json.dumps(type02_receipt))
        wrong_type_receipt["artifacts"]["data_file"] = "wrong.dat"
        wrong_type_receipt["artifacts"]["checksum_file"] = "wrong.dat.sha256"
        self.assertTrue(
            list(receipt_validator.iter_errors(wrong_type_receipt))
        )

        negative_zero_receipt = json.loads(json.dumps(type02_receipt))
        negative_zero_receipt["controls"]["computed_net_amount"] = "-0.00"
        self.assertTrue(
            list(receipt_validator.iter_errors(negative_zero_receipt))
        )

        contradictory_receipt = json.loads(json.dumps(type02_receipt))
        contradictory_receipt["fault"] = {
            "code": "INVALID_FIELD_COUNT",
            "expected_stage": "java-validation",
            "injected": True,
        }
        self.assertTrue(
            list(receipt_validator.iter_errors(contradictory_receipt))
        )

        for count_field in (
            "computed_event_count",
            "declared_event_count",
        ):
            oversized_receipt = json.loads(json.dumps(type02_receipt))
            oversized_receipt["controls"][count_field] = 10_001
            self.assertTrue(
                list(receipt_validator.iter_errors(oversized_receipt)),
                count_field,
            )

        type02_sanitized = {
            "batch_id": "B202607230000101",
            "csv_file": {
                "encoding": "UTF-8",
                "name": (
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.csv"
                ),
                "row_count": 2,
                "sha256": "e" * 64,
                "size_bytes": 1,
            },
            "file_type": {
                "code": "PIX_EVENTS01",
                "contract_version": 1,
                "layout_version": "001",
                "number": "02",
            },
            "schema_version": 1,
            "source_lineage": {
                "manifest_sha256": "f" * 64,
                "raw_file": (
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.txt"
                ),
                "raw_sha256": "a" * 64,
            },
            "stage_controls": {
                "credit_amount": "200.00",
                "currency": "BRL",
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
                "row_count": 2,
            },
        }
        sanitized_validator.validate(type02_sanitized)

        wrong_type_lineage = json.loads(json.dumps(type02_sanitized))
        wrong_type_lineage["source_lineage"]["raw_file"] = (
            "NW_CARD_SETTLEMENT_20260723_B202607230000101.dat"
        )
        self.assertTrue(
            list(sanitized_validator.iter_errors(wrong_type_lineage))
        )

        negative_zero_sanitized = json.loads(json.dumps(type02_sanitized))
        negative_zero_sanitized["stage_controls"]["net_amount"] = "-0.00"
        self.assertTrue(
            list(sanitized_validator.iter_errors(negative_zero_sanitized))
        )

        oversized_csv_rows = json.loads(json.dumps(type02_sanitized))
        oversized_csv_rows["csv_file"]["row_count"] = 10_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_csv_rows))
        )

        oversized_stage_rows = json.loads(json.dumps(type02_sanitized))
        oversized_stage_rows["stage_controls"]["row_count"] = 10_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_stage_rows))
        )

        oversized_returned = json.loads(json.dumps(type02_sanitized))
        oversized_returned["stage_controls"]["returned_count"] = 10_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_returned))
        )

    def test_type02_artifact_date_and_batch_links_are_mandatory(self) -> None:
        raw_filename = (
            "NW_INSTANT_PAYMENT_20260723_B202607230000101.txt"
        )
        _validate_type02_artifact_links(
            batch_id="B202607230000101",
            raw_filename=raw_filename,
            checksum_filename=f"{raw_filename}.sha256",
            csv_filename=(
                "NW_INSTANT_PAYMENT_20260723_B202607230000101.csv"
            ),
        )

        with self.assertRaisesRegex(
            ValueError,
            "MANIFEST_BATCH_LINK_MISMATCH",
        ):
            _validate_type02_artifact_links(
                batch_id="B202607230000101",
                raw_filename=(
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000102.txt"
                ),
            )

        _validate_type02_sanitized_control_links(
            row_count=2,
            returned_count=1,
        )
        with self.assertRaisesRegex(
            ValueError,
            "MANIFEST_RETURNED_COUNT_LINK_MISMATCH",
        ):
            _validate_type02_sanitized_control_links(
                row_count=2,
                returned_count=3,
            )

        with self.assertRaisesRegex(
            ValueError,
            "MANIFEST_CHECKSUM_LINK_MISMATCH",
        ):
            _validate_type02_artifact_links(
                batch_id="B202607230000101",
                raw_filename=raw_filename,
                checksum_filename="unrelated.txt.sha256",
            )

        with self.assertRaisesRegex(
            ValueError,
            "MANIFEST_CSV_LINK_MISMATCH",
        ):
            _validate_type02_artifact_links(
                batch_id="B202607230000101",
                raw_filename=raw_filename,
                csv_filename=(
                    "NW_INSTANT_PAYMENT_20260724_"
                    "B202607230000101.csv"
                ),
            )


if __name__ == "__main__":
    unittest.main()
