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
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator

from generation import generate


ROOT = Path(__file__).resolve().parents[2]
TYPE_ROOT = ROOT / "contracts" / "types" / "01-card-settlement"
MAIN = TYPE_ROOT / "main"
COMMON = ROOT / "contracts" / "common"
CONTRACTS_ROOT = ROOT / "contracts" / "types"
FIXTURE_KEY = b"northwind-pay-edp-fixture-key-v1"
POSITIVE_OVERPUNCH = "{ABCDEFGHI"
NEGATIVE_OVERPUNCH = "}JKLMNOPQR"
CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "transaction_id",
    "merchant_id",
    "card_token",
    "card_last4",
    "cpf_masked",
    "transaction_ts",
    "amount_brl",
    "movement_code",
    "authorization_code",
    "nsu",
    "terminal_id",
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
    "negative-overpunch": (
        "negative-overpunch.dat",
        "expected-negative-overpunch-sanitized.csv",
        "expected-negative-overpunch-reconciliation.yaml",
    ),
}
RAW_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.dat",
        "66c2d02217d133e88ec28486f170a90fc134ff7a70e63e8096b8be37dacbd82f",
    ),
    "valid-boundary": (
        "valid-boundary.dat",
        "b1bcb59bcc8e0163c1cdc853f8354c881630ffbd1091385a2a368eea09b4f23d",
    ),
    "negative-overpunch": (
        "negative-overpunch.dat",
        "0c773790558e429aeaaf9beeb9e8ed8def45061b0804c9a4cb3e84825cac1de2",
    ),
    "malformed": (
        "malformed.dat",
        "c4b7815f3ae95d3259064a7a9afe52d0f30b6a289d456e09b896351294308934",
    ),
    "DF-SOURCE-001": (
        "df-source-001.dat",
        "4b72707c859c755fe9aeba6ec67996fb7b084ab0992231c8d60358bdfdd13980",
    ),
}
GENERATED_EXPECTATIONS = {
    "valid-minimal": {
        "batch_id": "B202607230000001",
        "date": "20260723",
        "declared_count": 2,
        "computed_count": 2,
        "declared_net": "173.45",
        "computed_net": "173.45",
        "status": "ACCEPTED",
        "violation": None,
    },
    "valid-boundary": {
        "batch_id": "B202402290000001",
        "date": "20240229",
        "declared_count": 1,
        "computed_count": 1,
        "declared_net": "9999999999.99",
        "computed_net": "9999999999.99",
        "status": "ACCEPTED",
        "violation": None,
    },
    "negative-overpunch": {
        "batch_id": "B202607230000002",
        "date": "20260723",
        "declared_count": 1,
        "computed_count": 1,
        "declared_net": "-12.34",
        "computed_net": "-12.34",
        "status": "ACCEPTED",
        "violation": None,
    },
    "malformed": {
        "batch_id": "B202607230000003",
        "date": "20260723",
        "declared_count": 1,
        "computed_count": 1,
        "declared_net": "-12.34",
        "computed_net": None,
        "status": "REJECTED",
        "violation": "INVALID_OVERPUNCH",
    },
    "DF-SOURCE-001": {
        "batch_id": "B202607230000004",
        "date": "20260723",
        "declared_count": 2,
        "computed_count": 2,
        "declared_net": "173.44",
        "computed_net": "173.45",
        "status": "REJECTED",
        "violation": "SOURCE_CONTROL_TOTAL_MISMATCH",
    },
}


@dataclass(frozen=True, slots=True)
class Detail:
    source_record_number: int
    transaction_id: str
    merchant_id: str
    pan: str
    cpf: str
    transaction_date: str
    transaction_time: str
    amount: Decimal
    movement_code: str
    authorization_code: str
    nsu: str
    terminal_id: str


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    file_date: str
    batch_id: str
    details: tuple[Detail, ...]
    declared_count: int
    declared_net: Decimal

    @property
    def source_filename(self) -> str:
        return (
            f"NW_CARD_SETTLEMENT_{self.file_date}_{self.batch_id}.dat"
        )

    @property
    def computed_count(self) -> int:
        return len(self.details)

    @property
    def computed_net(self) -> Decimal:
        return sum(
            (detail.amount for detail in self.details),
            start=Decimal("0.00"),
        )


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"Expected a mapping in {path.name}")
    return loaded


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _parse_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("INVALID_FIELD") from exc


def _parse_time(value: str) -> None:
    try:
        datetime.strptime(value, "%H%M%S")
    except ValueError as exc:
        raise ValueError("INVALID_FIELD") from exc


def _decode_overpunch(value: str) -> Decimal:
    if len(value) < 2 or not value[:-1].isascii() or not value[:-1].isdigit():
        raise ValueError("INVALID_OVERPUNCH")
    final = value[-1]
    if final in POSITIVE_OVERPUNCH:
        sign = 1
        digit = POSITIVE_OVERPUNCH.index(final)
    elif final in NEGATIVE_OVERPUNCH:
        sign = -1
        digit = NEGATIVE_OVERPUNCH.index(final)
    else:
        raise ValueError("INVALID_OVERPUNCH")
    minor_units = int(f"{value[:-1]}{digit}") * sign
    return Decimal(minor_units) / 100


def _encode_overpunch(value: Decimal, *, width: int) -> str:
    minor_units = int(value * 100)
    digits = str(abs(minor_units)).zfill(width)
    mapping = NEGATIVE_OVERPUNCH if minor_units < 0 else POSITIVE_OVERPUNCH
    return f"{digits[:-1]}{mapping[int(digits[-1])]}"


def _require_pattern(value: str, pattern: str) -> None:
    if re.fullmatch(pattern, value) is None:
        raise ValueError("INVALID_FIELD")


def _parse_source(
    raw: bytes,
    *,
    enforce_controls: bool = True,
) -> ParsedBatch:
    if (
        not raw.endswith(b"\n")
        or raw.endswith(b"\n\n")
        or b"\r" in raw
        or b"\n\n" in raw
    ):
        raise ValueError("INVALID_TRANSPORT")
    records = raw[:-1].split(b"\n")
    try:
        decoded = [
            record.decode("ISO-8859-1", errors="strict")
            for record in records
        ]
    except UnicodeDecodeError as exc:
        raise ValueError("INVALID_ENCODING") from exc
    if (
        len(decoded) < 3
        or len(decoded[0].encode("ISO-8859-1")) != 40
        or len(decoded[-1].encode("ISO-8859-1")) != 46
        or any(
            len(record.encode("ISO-8859-1")) != 124
            for record in decoded[1:-1]
        )
    ):
        raise ValueError("INVALID_RECORD_LENGTH")
    if (
        decoded[0][0] != "H"
        or decoded[-1][0] != "T"
        or any(record[0] != "D" for record in decoded[1:-1])
    ):
        raise ValueError("INVALID_RECORD_SEQUENCE")

    header = decoded[0]
    file_date = header[1:9]
    batch_id = header[9:25]
    _parse_date(file_date)
    _require_pattern(batch_id, r"B[0-9]{15}")
    if (
        header[25:37] != "CRD_SETTLE01"
        or header[37:40] != "001"
        or batch_id[1:9] != file_date
    ):
        raise ValueError("INVALID_FIELD")

    details: list[Detail] = []
    for source_record_number, record in enumerate(decoded[1:-1], start=2):
        transaction_id = record[1:17]
        merchant_id = record[17:33]
        pan = record[33:49]
        cpf = record[49:60]
        transaction_date = record[60:68]
        transaction_time = record[68:74]
        amount = _decode_overpunch(record[74:86])
        currency = record[86:89]
        movement_code = record[89]
        authorization_code = record[90:96]
        nsu = record[96:108]
        terminal_id = record[108:124]

        _require_pattern(transaction_id, r"[A-Z0-9]{16}")
        _require_pattern(merchant_id, r"[A-Z0-9]{16}")
        _require_pattern(pan, r"[0-9]{16}")
        _require_pattern(cpf, r"[0-9]{11}")
        _parse_date(transaction_date)
        _parse_time(transaction_time)
        _require_pattern(authorization_code, r"[A-Z0-9]{6}")
        _require_pattern(nsu, r"[0-9]{12}")
        _require_pattern(terminal_id, r"[A-Z0-9]{16}")
        if currency != "BRL" or transaction_date != file_date:
            raise ValueError("INVALID_FIELD")
        if (
            movement_code == "P"
            and amount <= Decimal("0.00")
            or movement_code == "R"
            and amount >= Decimal("0.00")
            or movement_code not in {"P", "R"}
        ):
            raise ValueError("INVALID_MOVEMENT_AMOUNT")
        details.append(
            Detail(
                source_record_number=source_record_number,
                transaction_id=transaction_id,
                merchant_id=merchant_id,
                pan=pan,
                cpf=cpf,
                transaction_date=transaction_date,
                transaction_time=transaction_time,
                amount=amount,
                movement_code=movement_code,
                authorization_code=authorization_code,
                nsu=nsu,
                terminal_id=terminal_id,
            )
        )

    if len({detail.transaction_id for detail in details}) != len(details):
        raise ValueError("DUPLICATE_TRANSACTION_ID")

    trailer = decoded[-1]
    trailer_date = trailer[1:9]
    declared_count_text = trailer[9:15]
    declared_net = _decode_overpunch(trailer[15:30])
    trailer_batch_id = trailer[30:46]
    if not declared_count_text.isascii() or not declared_count_text.isdigit():
        raise ValueError("INVALID_FIELD")
    if trailer_date != file_date or trailer_batch_id != batch_id:
        raise ValueError("SOURCE_LINK_MISMATCH")
    declared_count = int(declared_count_text)
    batch = ParsedBatch(
        file_date=file_date,
        batch_id=batch_id,
        details=tuple(details),
        declared_count=declared_count,
        declared_net=declared_net,
    )
    if enforce_controls and (
        batch.declared_count != batch.computed_count
        or batch.declared_net != batch.computed_net
    ):
        raise ValueError("SOURCE_CONTROL_TOTAL_MISMATCH")
    return batch


def _render_csv(batch: ParsedBatch) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(
        stream,
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(CSV_COLUMNS)
    timezone = ZoneInfo("America/Sao_Paulo")
    for detail in batch.details:
        token = hmac.new(
            FIXTURE_KEY,
            detail.pan.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()[:24]
        transaction_timestamp = datetime.strptime(
            f"{detail.transaction_date}{detail.transaction_time}",
            "%Y%m%d%H%M%S",
        ).replace(tzinfo=timezone)
        writer.writerow(
            (
                batch.batch_id,
                batch.source_filename,
                detail.source_record_number,
                detail.transaction_id,
                detail.merchant_id,
                f"tok_{token}",
                detail.pan[-4:],
                f"*******{detail.cpf[-4:]}",
                transaction_timestamp.isoformat(timespec="seconds"),
                format(detail.amount, ".2f"),
                detail.movement_code,
                detail.authorization_code,
                detail.nsu,
                detail.terminal_id,
            )
        )
    rendered = stream.getvalue().encode("utf-8")
    for detail in batch.details:
        if detail.pan.encode("ascii") in rendered:
            raise AssertionError("Clear PAN leaked into sanitized output")
        if detail.cpf.encode("ascii") in rendered:
            raise AssertionError("Clear CPF leaked into sanitized output")
    return rendered


def _expected_reconciliation(batch: ParsedBatch) -> dict[str, object]:
    count = batch.computed_count
    net = format(batch.computed_net, ".2f")
    return {
        "batch_id": batch.batch_id,
        "currency": "BRL",
        "source_count": count,
        "staged_count": count,
        "applied_count": count,
        "source_net_amount": net,
        "staged_net_amount": net,
        "applied_net_amount": net,
        "count_delta": 0,
        "amount_delta": "0.00",
        "reject_count": 0,
        "status": "MATCHED",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Type01ContractTest(unittest.TestCase):
    def test_contract_yaml_is_closed_and_declares_transport_privacy(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        privacy = _load_yaml(TYPE_ROOT / "privacy.yaml")
        csv_contract = _load_yaml(TYPE_ROOT / "csv.yaml")
        reconciliation = _load_yaml(TYPE_ROOT / "reconciliation.yaml")

        self.assertEqual(
            set(layout),
            {
                "version",
                "file_type",
                "record_sequence",
                "overpunch",
                "records",
                "cross_record_rules",
                "canonical_rejection_codes",
            },
        )
        self.assertEqual(
            set(layout["file_type"]),
            {
                "number",
                "name",
                "code",
                "layout_version",
                "filename_regex",
                "encoding",
                "line_ending",
                "final_newline",
                "blank_lines",
            },
        )
        self.assertEqual(layout["version"], 1)
        self.assertEqual(layout["file_type"]["number"], "01")
        self.assertEqual(layout["file_type"]["code"], "CRD_SETTLE01")
        self.assertEqual(layout["file_type"]["encoding"], "ISO-8859-1")
        self.assertEqual(layout["file_type"]["line_ending"], "LF")
        self.assertEqual(layout["file_type"]["final_newline"], "required")
        self.assertEqual(layout["file_type"]["blank_lines"], "forbidden")
        self.assertEqual(
            layout["record_sequence"],
            [
                {
                    "record": "header",
                    "cardinality": "exactly_one",
                    "position": "first",
                },
                {"record": "detail", "cardinality": "one_or_more"},
                {
                    "record": "trailer",
                    "cardinality": "exactly_one",
                    "position": "last",
                },
            ],
        )
        self.assertEqual(
            layout["overpunch"]["positive_characters"],
            POSITIVE_OVERPUNCH,
        )
        self.assertEqual(
            layout["overpunch"]["negative_characters"],
            NEGATIVE_OVERPUNCH,
        )
        self.assertEqual(layout["overpunch"]["decimal_scale"], 2)
        rejection_codes = layout["canonical_rejection_codes"]
        self.assertEqual(
            rejection_codes["invalid_overpunch"],
            "INVALID_OVERPUNCH",
        )
        self.assertEqual(
            rejection_codes["source_control_total_mismatch"],
            "SOURCE_CONTROL_TOTAL_MISMATCH",
        )
        self.assertEqual(len(rejection_codes), len(set(rejection_codes.values())))

        expected_record_lengths = {
            "header": 40,
            "detail": 124,
            "trailer": 46,
        }
        expected_field_names = {
            "header": (
                "record_type",
                "file_date",
                "batch_id",
                "file_type_code",
                "layout_version",
            ),
            "detail": (
                "record_type",
                "transaction_id",
                "merchant_id",
                "pan",
                "cpf",
                "transaction_date",
                "transaction_time",
                "amount_brl",
                "currency",
                "movement_code",
                "authorization_code",
                "nsu",
                "terminal_id",
            ),
            "trailer": (
                "record_type",
                "file_date",
                "detail_count",
                "net_amount_brl",
                "batch_id",
            ),
        }
        self.assertEqual(set(layout["records"]), set(expected_record_lengths))
        for record_name, expected_length in expected_record_lengths.items():
            record = layout["records"][record_name]
            self.assertEqual(
                set(record),
                {"discriminator", "length_bytes", "fields"},
            )
            self.assertEqual(record["length_bytes"], expected_length)
            fields = record["fields"]
            self.assertEqual(
                tuple(field["name"] for field in fields),
                expected_field_names[record_name],
            )
            self.assertEqual(fields[0]["start"], 1)
            self.assertEqual(fields[-1]["end"], expected_length)
            for previous, current in zip(fields, fields[1:]):
                self.assertEqual(previous["end"] + 1, current["start"])
            for field in fields:
                self.assertEqual(
                    field["end"] - field["start"] + 1,
                    field["length"],
                )

        self.assertEqual(
            set(privacy),
            {
                "version",
                "type_number",
                "raw_data_classification",
                "fields",
                "fixture_tokenization",
                "handling",
            },
        )
        self.assertEqual(privacy["type_number"], "01")
        self.assertEqual(set(privacy["fields"]), {"pan", "cpf"})
        pan = privacy["fields"]["pan"]
        cpf = privacy["fields"]["cpf"]
        self.assertEqual(
            pan["transformations"]["token"]["algorithm"],
            "HMAC-SHA-256",
        )
        self.assertEqual(
            pan["transformations"]["token"]["missing_key_behavior"],
            "fail_closed",
        )
        self.assertEqual(
            pan["transformations"]["last4"]["output_format"],
            "last_4_digits",
        )
        self.assertEqual(
            cpf["transformation"]["output_format"],
            "*******<last4>",
        )
        for field in (pan, cpf):
            self.assertEqual(
                set(field["prohibited_outputs"]),
                {
                    "sanitized_csv",
                    "application_logs",
                    "error_messages",
                    "batch_evidence",
                    "database_staging",
                    "database_operational",
                },
            )
        self.assertFalse(
            privacy["fixture_tokenization"]["may_be_used_outside_tests"]
        )
        self.assertFalse(
            privacy["handling"]["raw_sftp_zones"]["content_may_be_logged"]
        )
        self.assertFalse(
            privacy["handling"]["evidence"]["store_raw_content"]
        )
        self.assertTrue(
            privacy["handling"]["evidence"]["store_raw_sha256"]
        )

        self.assertEqual(
            set(csv_contract),
            {
                "version",
                "type_number",
                "format",
                "publication",
                "columns",
                "database_target",
                "validation",
            },
        )
        self.assertEqual(csv_contract["type_number"], "01")
        self.assertEqual(csv_contract["format"]["encoding"], "UTF-8")
        self.assertEqual(csv_contract["format"]["line_ending"], "LF")
        self.assertEqual(csv_contract["format"]["final_newline"], "required")
        self.assertEqual(
            tuple(column["name"] for column in csv_contract["columns"]),
            CSV_COLUMNS,
        )
        self.assertEqual(
            tuple(column["position"] for column in csv_contract["columns"]),
            tuple(range(1, len(CSV_COLUMNS) + 1)),
        )
        self.assertEqual(
            csv_contract["publication"]["readiness_rule"],
            "manifest_renamed_last",
        )

        self.assertEqual(
            set(reconciliation),
            {
                "version",
                "type_number",
                "grain",
                "source_controls",
                "stage_controls",
                "operational_controls",
                "procedure_order",
                "report",
                "tolerances",
                "semantics",
                "success",
                "approved_example",
            },
        )
        self.assertEqual(reconciliation["type_number"], "01")
        self.assertEqual(
            reconciliation["tolerances"],
            {"count_delta": 0, "amount_delta": "0.00"},
        )
        self.assertEqual(
            [
                entry["procedure"]
                for entry in reconciliation["procedure_order"]
            ],
            [
                "legacy.apply_card_settlement_batch",
                "reporting.refresh_card_settlement_reconciliation",
            ],
        )

    def test_three_success_truth_sets_are_independently_reproduced(self) -> None:
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
                self.assertEqual(
                    batch.declared_count,
                    batch.computed_count,
                )
                self.assertEqual(
                    batch.declared_net,
                    batch.computed_net,
                )

    def test_five_raw_fixture_hashes_and_transport_are_frozen(self) -> None:
        seen_batches: set[str] = set()
        for scenario, (filename, expected_hash) in RAW_FIXTURES.items():
            with self.subTest(scenario=scenario):
                raw = (MAIN / filename).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected_hash)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))
                self.assertNotIn(b"\r", raw)
                records = raw[:-1].split(b"\n")
                self.assertEqual(len(records[0]), 40)
                self.assertEqual(len(records[-1]), 46)
                self.assertTrue(
                    all(len(record) == 124 for record in records[1:-1])
                )
                batch_id = records[0][9:25].decode("ascii")
                self.assertNotIn(batch_id, seen_batches)
                seen_batches.add(batch_id)
        self.assertEqual(
            seen_batches,
            {
                "B202607230000001",
                "B202402290000001",
                "B202607230000002",
                "B202607230000003",
                "B202607230000004",
            },
        )

    def test_malformed_rejects_only_as_invalid_overpunch(self) -> None:
        raw = (MAIN / "malformed.dat").read_bytes()
        records = raw[:-1].split(b"\n")
        malformed_amount = records[1][74:86].decode("ascii")
        self.assertEqual(malformed_amount, "00000000123Z")
        self.assertNotIn(malformed_amount[-1], POSITIVE_OVERPUNCH)
        self.assertNotIn(malformed_amount[-1], NEGATIVE_OVERPUNCH)
        with self.assertRaises(ValueError) as raised:
            _parse_source(raw)
        self.assertEqual(str(raised.exception), "INVALID_OVERPUNCH")

        expected = _load_yaml(MAIN / "expected-malformed-rejection.yaml")
        self.assertEqual(
            set(expected),
            {
                "batch_id",
                "scenario",
                "expected_stage",
                "expected_status",
                "expected_code",
                "source_record_number",
                "transaction_id",
                "csv_produced",
                "postgres_business_mutation",
                "quarantine_scope",
            },
        )
        self.assertEqual(expected["scenario"], "malformed")
        self.assertEqual(expected["expected_code"], "INVALID_OVERPUNCH")
        self.assertEqual(expected["expected_stage"], "java-validation")
        self.assertEqual(expected["expected_status"], "quarantined")
        self.assertFalse(expected["csv_produced"])
        self.assertFalse(expected["postgres_business_mutation"])
        self.assertEqual(expected["quarantine_scope"], "batch")

    def test_dark_factory_is_only_the_declared_source_total_defect(self) -> None:
        raw = (MAIN / "df-source-001.dat").read_bytes()
        batch = _parse_source(raw, enforce_controls=False)
        self.assertEqual(batch.declared_count, batch.computed_count)
        self.assertEqual(batch.declared_net, Decimal("173.44"))
        self.assertEqual(batch.computed_net, Decimal("173.45"))
        with self.assertRaises(ValueError) as raised:
            _parse_source(raw)
        self.assertEqual(
            str(raised.exception),
            "SOURCE_CONTROL_TOTAL_MISMATCH",
        )

        records = raw[:-1].split(b"\n")
        corrected_trailer = bytearray(records[-1])
        corrected_trailer[15:30] = _encode_overpunch(
            Decimal("173.45"),
            width=15,
        ).encode("ascii")
        corrected = b"\n".join(
            [*records[:-1], bytes(corrected_trailer)]
        ) + b"\n"
        corrected_batch = _parse_source(corrected)
        self.assertEqual(corrected_batch.computed_net, Decimal("173.45"))

        finding = _load_yaml(MAIN / "expected-df-source-001-finding.yaml")
        self.assertEqual(
            set(finding),
            {
                "batch_id",
                "scenario",
                "source_system_role",
                "expected_stage",
                "expected_status",
                "expected_code",
                "declared_detail_count",
                "computed_detail_count",
                "declared_net_amount",
                "computed_net_amount",
                "csv_produced",
                "postgres_business_mutation",
                "quarantine_scope",
                "unrelated_batches_continue",
            },
        )
        self.assertEqual(finding["source_system_role"], "system_of_record")
        self.assertEqual(
            finding["expected_code"],
            "SOURCE_CONTROL_TOTAL_MISMATCH",
        )
        self.assertEqual(finding["declared_net_amount"], "173.44")
        self.assertEqual(finding["computed_net_amount"], "173.45")
        self.assertFalse(finding["csv_produced"])
        self.assertFalse(finding["postgres_business_mutation"])
        self.assertTrue(finding["unrelated_batches_continue"])

    def test_all_generated_manifests_receipts_and_links_are_exact(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        layout_sha256 = _sha256(TYPE_ROOT / "layout.yaml")
        registry_sha256 = _sha256(CONTRACTS_ROOT / "registry.yaml")

        with tempfile.TemporaryDirectory() as output:
            for scenario, values in GENERATED_EXPECTATIONS.items():
                with self.subTest(scenario=scenario):
                    bundle = generate(
                        type_number="01",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS_ROOT,
                    )
                    manifest_bytes = bundle.manifest_file.read_bytes()
                    manifest = json.loads(manifest_bytes)
                    receipt = json.loads(bundle.receipt_file.read_bytes())
                    source_validator.validate(manifest)
                    receipt_validator.validate(receipt)

                    fixture_name, expected_raw_sha256 = RAW_FIXTURES[scenario]
                    fixture_bytes = (MAIN / fixture_name).read_bytes()
                    self.assertEqual(bundle.raw_file.read_bytes(), fixture_bytes)
                    self.assertEqual(bundle.raw_sha256, expected_raw_sha256)

                    batch_id = values["batch_id"]
                    file_date = values["date"]
                    raw_filename = (
                        f"NW_CARD_SETTLEMENT_{file_date}_{batch_id}.dat"
                    )
                    self.assertEqual(batch_id[1:9], file_date)
                    self.assertEqual(bundle.batch_id, batch_id)
                    self.assertEqual(bundle.raw_file.name, raw_filename)
                    self.assertEqual(
                        bundle.checksum_file.name,
                        f"{raw_filename}.sha256",
                    )
                    self.assertEqual(
                        bundle.checksum_file.read_text(encoding="ascii"),
                        f"{expected_raw_sha256}  {raw_filename}\n",
                    )

                    self.assertEqual(manifest["batch_id"], batch_id)
                    self.assertEqual(
                        manifest["file_type"],
                        {
                            "code": "CRD_SETTLE01",
                            "contract_version": 1,
                            "layout_version": "001",
                            "number": "01",
                        },
                    )
                    self.assertEqual(
                        manifest["source_controls"],
                        {
                            "currency": "BRL",
                            "detail_count": values["declared_count"],
                            "net_amount": values["declared_net"],
                        },
                    )
                    self.assertEqual(
                        manifest["source_file"],
                        {
                            "encoding": "ISO-8859-1",
                            "final_newline": "required",
                            "line_ending": "LF",
                            "name": raw_filename,
                            "sha256": expected_raw_sha256,
                            "size_bytes": len(fixture_bytes),
                        },
                    )

                    self.assertEqual(receipt["batch_id"], batch_id)
                    self.assertEqual(receipt["scenario"], scenario)
                    self.assertEqual(
                        receipt["contract"],
                        {
                            "layout_sha256": layout_sha256,
                            "layout_version": "001",
                            "registry_sha256": registry_sha256,
                            "type_number": "01",
                            "version": 1,
                        },
                    )
                    self.assertEqual(
                        receipt["controls"],
                        {
                            "computed_detail_count": values["computed_count"],
                            "computed_net_amount": values["computed_net"],
                            "declared_detail_count": values["declared_count"],
                            "declared_net_amount": values["declared_net"],
                        },
                    )
                    self.assertEqual(
                        receipt["expected_contract_result"],
                        {
                            "status": values["status"],
                            "violation": values["violation"],
                        },
                    )
                    expected_fault = None
                    if values["violation"] is not None:
                        expected_fault = {
                            "code": values["violation"],
                            "expected_stage": "java-validation",
                            "injected": True,
                        }
                    self.assertEqual(receipt["fault"], expected_fault)
                    self.assertEqual(
                        receipt["artifacts"],
                        {
                            "checksum_file": f"{raw_filename}.sha256",
                            "data_file": raw_filename,
                            "data_sha256": expected_raw_sha256,
                            "source_manifest": "source-manifest.json",
                            "source_manifest_sha256": hashlib.sha256(
                                manifest_bytes
                            ).hexdigest(),
                        },
                    )

    def test_rejection_oracles_cover_every_declared_rejected_scenario(
        self,
    ) -> None:
        receipt_schema = json.loads(
            (COMMON / "generation-receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        type01_branch = receipt_schema["allOf"][0]["then"]
        declared_scenarios = set(
            type01_branch["properties"]["scenario"]["enum"]
        )
        self.assertEqual(declared_scenarios, set(GENERATED_EXPECTATIONS))

        schema_rejections: dict[str, str] = {}
        for rule in type01_branch["allOf"]:
            scenario_rule = rule["if"]["properties"]["scenario"]
            if "const" not in scenario_rule:
                continue
            expected_result = rule["then"]["properties"][
                "expected_contract_result"
            ]["const"]
            if expected_result["status"] == "REJECTED":
                schema_rejections[scenario_rule["const"]] = expected_result[
                    "violation"
                ]

        oracle_files = {
            "malformed": "expected-malformed-rejection.yaml",
            "DF-SOURCE-001": "expected-df-source-001-finding.yaml",
        }
        oracle_rejections = {
            scenario: _load_yaml(MAIN / filename)["expected_code"]
            for scenario, filename in oracle_files.items()
        }
        self.assertEqual(schema_rejections, oracle_rejections)
        self.assertEqual(
            {
                scenario
                for scenario, values in GENERATED_EXPECTATIONS.items()
                if values["status"] == "REJECTED"
            },
            set(oracle_rejections),
        )


if __name__ == "__main__":
    unittest.main()
