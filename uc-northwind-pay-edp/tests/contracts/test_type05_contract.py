from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import unittest
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
TYPE_ROOT = ROOT / "contracts" / "types" / "05-merchant-fee-assessment"
MAIN = TYPE_ROOT / "main"
COMMON = ROOT / "contracts" / "common"
HEADER = (
    "assessment_id;batch_id;merchant_id;merchant_tax_id;fee_code;"
    "description;gross_amount_brl;rate_percent;assessed_fee_brl;"
    "assessment_date"
)
CSV_COLUMNS = (
    "batch_id",
    "source_file",
    "source_record_number",
    "assessment_id",
    "merchant_id",
    "merchant_tax_id_masked",
    "fee_code",
    "description",
    "gross_amount_brl",
    "rate_percent",
    "assessed_fee_brl",
    "calculated_fee_brl",
    "assessment_date",
    "rounding_mode",
)
SUCCESS_SCENARIOS = {
    "valid-minimal": (
        "valid-minimal.csv",
        "expected-sanitized.csv",
        "expected-reconciliation.yaml",
    ),
    "valid-boundary": (
        "valid-boundary.csv",
        "expected-valid-boundary-sanitized.csv",
        "expected-valid-boundary-reconciliation.yaml",
    ),
    "rounding-half-up": (
        "rounding-half-up.csv",
        "expected-rounding-half-up-sanitized.csv",
        "expected-rounding-half-up-reconciliation.yaml",
    ),
}
RAW_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.csv",
        "457e1737d6540850e9543766c3ffdfd608141d06c9f1cc484d67458753f5df53",
    ),
    "valid-boundary": (
        "valid-boundary.csv",
        "fd3cc536e1d61fca14e397a50d194d3f0037680756df69350f0f03a140ca594b",
    ),
    "malformed": (
        "malformed.csv",
        "f9b1478fa6407aff4f45a04ec3261dac264a0254f7bfec356c1380906c0929cb",
    ),
    "rounding-half-up": (
        "rounding-half-up.csv",
        "7964eb84cb89816e814ef790c4feb4add90350f3a8d3aca31875427241e474a5",
    ),
    "DF-SOURCE-005": (
        "df-source-005.csv",
        "f6e018b1b3bec55d6b56c4ae46ea65079053176644502c51d384acb9498ef145",
    ),
}
MONEY_SOURCE = re.compile(r"^(0|[1-9][0-9]{0,11}),[0-9]{2}$")
RATE_SOURCE = re.compile(r"^(0|[1-9][0-9]{0,2}),[0-9]{3}$")
BIDI_CONTROLS = {
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


@dataclass(frozen=True, slots=True)
class LexedRow:
    record_number: int
    fields: tuple[str, ...]
    quoted: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class Assessment:
    source_record_number: int
    assessment_id: str
    batch_id: str
    merchant_id: str
    merchant_tax_id: str
    fee_code: str
    description: str
    gross_amount: Decimal
    rate_percent: Decimal
    assessed_fee: Decimal
    calculated_fee: Decimal
    assessment_date: str


@dataclass(frozen=True, slots=True)
class ParsedBatch:
    file_date: str
    batch_id: str
    assessments: tuple[Assessment, ...]
    declared_row_count: int
    computed_row_count: int
    declared_gross_amount: Decimal
    computed_gross_amount: Decimal
    declared_assessed_fee: Decimal
    computed_assessed_fee: Decimal
    declared_calculated_fee: Decimal
    computed_calculated_fee: Decimal

    @property
    def source_filename(self) -> str:
        return (
            f"NW_MERCHANT_FEES_{self.file_date}_{self.batch_id}.csv"
        )


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"Expected a mapping in {path.name}")
    return loaded


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


def _source_decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))


def _calculated_fee(gross: Decimal, rate: Decimal) -> Decimal:
    return (gross * rate / Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _physical_lines(raw: bytes) -> list[str]:
    if len(raw) > 5_130_138:
        raise ValueError("INVALID_SOURCE_SIZE")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("INVALID_UTF8")
    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("INVALID_UTF8") from exc
    if unicodedata.normalize("NFC", decoded) != decoded:
        raise ValueError("INVALID_UNICODE_NORMALIZATION")
    if (
        not raw.endswith(b"\n")
        or raw.endswith(b"\n\n")
        or b"\r" in raw
    ):
        raise ValueError("INVALID_TRANSPORT")
    encoded_lines = raw[:-1].split(b"\n")
    if (
        len(encoded_lines) < 2
        or len(encoded_lines) > 10_001
        or b"" in encoded_lines
    ):
        raise ValueError("INVALID_SOURCE_SIZE")
    if any(len(line) > 512 for line in encoded_lines):
        raise ValueError("INVALID_RECORD_LENGTH")
    lines = decoded[:-1].split("\n")
    if lines[0] != HEADER:
        raise ValueError("INVALID_HEADER")
    return lines


def _lex_row(line: str, record_number: int) -> LexedRow:
    fields: list[str] = []
    quoted_flags: list[bool] = []
    index = 0
    while True:
        if index < len(line) and line[index] == '"':
            quoted = True
            index += 1
            characters: list[str] = []
            closed = False
            while index < len(line):
                character = line[index]
                if character != '"':
                    characters.append(character)
                    index += 1
                    continue
                if index + 1 < len(line) and line[index + 1] == '"':
                    characters.append('"')
                    index += 2
                    continue
                index += 1
                closed = True
                break
            if not closed:
                raise ValueError("INVALID_CSV_QUOTING")
            if index < len(line) and line[index] != ";":
                raise ValueError("INVALID_CSV_QUOTING")
            value = "".join(characters)
        else:
            quoted = False
            start = index
            while index < len(line) and line[index] != ";":
                if line[index] == '"':
                    raise ValueError("INVALID_CSV_QUOTING")
                index += 1
            value = line[start:index]
        fields.append(value)
        quoted_flags.append(quoted)
        if index == len(line):
            break
        index += 1
        if index == len(line):
            fields.append("")
            quoted_flags.append(False)
            break
    return LexedRow(
        record_number=record_number,
        fields=tuple(fields),
        quoted=tuple(quoted_flags),
    )


def _description_is_safe(
    value: str,
    raw_tax_ids: set[str],
) -> bool:
    if not 1 <= len(value) <= 80:
        return False
    if value[0] in {"=", "+", "-", "@"}:
        return False
    if re.search(r"[0-9]{11,}", value):
        return False
    if any(
        unicodedata.category(character) == "Cc"
        or character in BIDI_CONTROLS
        for character in value
    ):
        return False
    return not any(tax_id in value for tax_id in raw_tax_ids)


def _parse_source(
    raw: bytes,
    *,
    source_filename: str,
    declared_controls: dict[str, object],
    enforce_controls: bool = True,
) -> ParsedBatch:
    lines = _physical_lines(raw)
    lexed = tuple(
        _lex_row(line, record_number)
        for record_number, line in enumerate(lines[1:], start=2)
    )

    if any(
        (len(row.quoted) >= 6 and not row.quoted[5])
        or any(
            quoted
            for position, quoted in enumerate(row.quoted)
            if position != 5
        )
        for row in lexed
    ):
        raise ValueError("INVALID_CSV_QUOTING")
    if any(len(row.fields) != 10 for row in lexed):
        raise ValueError("INVALID_FIELD_COUNT")

    parsed_values: list[dict[str, object]] = []
    for row in lexed:
        fields = row.fields
        if (
            not fields[3].isascii()
            or not re.fullmatch(r"[0-9]{14}", fields[3])
            or MONEY_SOURCE.fullmatch(fields[6]) is None
            or RATE_SOURCE.fullmatch(fields[7]) is None
            or MONEY_SOURCE.fullmatch(fields[8]) is None
        ):
            raise ValueError("INVALID_FIELD")
        gross = _source_decimal(fields[6])
        rate = _source_decimal(fields[7])
        assessed = _source_decimal(fields[8])
        if (
            gross <= 0
            or rate <= 0
            or rate > Decimal("100.000")
            or assessed < 0
        ):
            raise ValueError("INVALID_FIELD")
        parsed_values.append(
            {
                "row": row,
                "gross": gross,
                "rate": rate,
                "assessed": assessed,
            }
        )

    for values in parsed_values:
        row = values["row"]
        assert isinstance(row, LexedRow)
        if not _cnpj_is_valid(row.fields[3]):
            raise ValueError("INVALID_DOCUMENT")

    raw_tax_ids = {
        row.fields[3]
        for row in lexed
    }
    for row in lexed:
        if (
            re.fullmatch(r"FEE[0-9]{13}", row.fields[0]) is None
            or re.fullmatch(r"B[0-9]{15}", row.fields[1]) is None
            or re.fullmatch(r"MER[0-9]{13}", row.fields[2]) is None
            or re.fullmatch(r"[A-Z][A-Z0-9_]{1,9}", row.fields[4])
            is None
        ):
            raise ValueError("INVALID_IDENTIFIER")
        if not _description_is_safe(row.fields[5], raw_tax_ids):
            raise ValueError("INVALID_DESCRIPTION")

    filename_match = re.fullmatch(
        r"NW_MERCHANT_FEES_([0-9]{8})_(B[0-9]{15})\.csv",
        source_filename,
    )
    if filename_match is None:
        raise ValueError("INVALID_BUSINESS_DATE")
    file_date, batch_id = filename_match.groups()
    for row in lexed:
        try:
            assessment_date = datetime.strptime(
                row.fields[9],
                "%d/%m/%Y",
            )
        except ValueError as exc:
            raise ValueError("INVALID_BUSINESS_DATE") from exc
        canonical_source_date = assessment_date.strftime("%d/%m/%Y")
        canonical_filename_date = assessment_date.strftime("%Y%m%d")
        if (
            row.fields[9] != canonical_source_date
            or canonical_filename_date != file_date
            or row.fields[1] != batch_id
        ):
            raise ValueError("INVALID_BUSINESS_DATE")

    assessment_ids = [row.fields[0] for row in lexed]
    if len(set(assessment_ids)) != len(assessment_ids):
        raise ValueError("DUPLICATE_IDENTIFIER")

    assessments: list[Assessment] = []
    for values in parsed_values:
        row = values["row"]
        assert isinstance(row, LexedRow)
        gross = Decimal(values["gross"])
        rate = Decimal(values["rate"])
        assessed = Decimal(values["assessed"])
        calculated = _calculated_fee(gross, rate)
        if assessed != calculated:
            raise ValueError("FEE_CALCULATION_MISMATCH")
        source_date = datetime.strptime(
            row.fields[9],
            "%d/%m/%Y",
        ).strftime("%Y%m%d")
        assessments.append(
            Assessment(
                source_record_number=row.record_number,
                assessment_id=row.fields[0],
                batch_id=row.fields[1],
                merchant_id=row.fields[2],
                merchant_tax_id=row.fields[3],
                fee_code=row.fields[4],
                description=row.fields[5],
                gross_amount=gross,
                rate_percent=rate,
                assessed_fee=assessed,
                calculated_fee=calculated,
                assessment_date=source_date,
            )
        )

    computed_row_count = len(assessments)
    computed_gross = sum(
        (assessment.gross_amount for assessment in assessments),
        Decimal("0.00"),
    )
    computed_assessed = sum(
        (assessment.assessed_fee for assessment in assessments),
        Decimal("0.00"),
    )
    computed_calculated = sum(
        (assessment.calculated_fee for assessment in assessments),
        Decimal("0.00"),
    )
    declared_row_count = int(declared_controls["row_count"])
    declared_gross = Decimal(str(declared_controls["gross_amount"]))
    declared_assessed = Decimal(str(declared_controls["assessed_fee"]))
    declared_calculated = Decimal(
        str(declared_controls["calculated_fee"])
    )
    if enforce_controls:
        if declared_row_count != computed_row_count:
            raise ValueError("SOURCE_CONTROL_COUNT_MISMATCH")
        if declared_gross != computed_gross:
            raise ValueError("SOURCE_CONTROL_GROSS_MISMATCH")
        if declared_assessed != computed_assessed:
            raise ValueError("SOURCE_CONTROL_ASSESSED_FEE_MISMATCH")
        if declared_calculated != computed_calculated:
            raise ValueError("SOURCE_CONTROL_CALCULATED_FEE_MISMATCH")

    return ParsedBatch(
        file_date=file_date,
        batch_id=batch_id,
        assessments=tuple(assessments),
        declared_row_count=declared_row_count,
        computed_row_count=computed_row_count,
        declared_gross_amount=declared_gross,
        computed_gross_amount=computed_gross,
        declared_assessed_fee=declared_assessed,
        computed_assessed_fee=computed_assessed,
        declared_calculated_fee=declared_calculated,
        computed_calculated_fee=computed_calculated,
    )


def _validate_output_privacy(rendered: bytes, batch: ParsedBatch) -> None:
    for assessment in batch.assessments:
        if assessment.merchant_tax_id.encode("ascii") in rendered:
            raise ValueError("PRIVACY_OUTPUT_VIOLATION")


def _render_csv(batch: ParsedBatch) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(
        output,
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    writer.writerow(CSV_COLUMNS)
    for assessment in batch.assessments:
        writer.writerow(
            (
                batch.batch_id,
                batch.source_filename,
                assessment.source_record_number,
                assessment.assessment_id,
                assessment.merchant_id,
                f"**********{assessment.merchant_tax_id[-4:]}",
                assessment.fee_code,
                assessment.description,
                format(assessment.gross_amount, ".2f"),
                format(assessment.rate_percent, ".3f"),
                format(assessment.assessed_fee, ".2f"),
                format(assessment.calculated_fee, ".2f"),
                (
                    f"{assessment.assessment_date[:4]}-"
                    f"{assessment.assessment_date[4:6]}-"
                    f"{assessment.assessment_date[6:]}"
                ),
                "HALF_UP",
            )
        )
    rendered = output.getvalue().encode("utf-8")
    _validate_output_privacy(rendered, batch)
    return rendered


def _expected_reconciliation(batch: ParsedBatch) -> dict[str, object]:
    count = batch.computed_row_count
    gross = format(batch.computed_gross_amount, ".2f")
    assessed = format(batch.computed_assessed_fee, ".2f")
    calculated = format(batch.computed_calculated_fee, ".2f")
    return {
        "batch_id": batch.batch_id,
        "currency": "BRL",
        "source_count": count,
        "staged_count": count,
        "applied_count": count,
        "source_gross_amount": gross,
        "staged_gross_amount": gross,
        "applied_gross_amount": gross,
        "source_assessed_fee": assessed,
        "staged_assessed_fee": assessed,
        "applied_assessed_fee": assessed,
        "source_calculated_fee": calculated,
        "staged_calculated_fee": calculated,
        "applied_calculated_fee": calculated,
        "count_delta": 0,
        "gross_amount_delta": "0.00",
        "assessed_fee_delta": "0.00",
        "calculated_fee_delta": "0.00",
        "assessment_calculation_delta": "0.00",
        "reject_count": 0,
        "status": "MATCHED",
    }


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _scenario_values(scenario: str) -> dict[str, object]:
    values = {
        "valid-minimal": {
            "file_date": "20260723",
            "batch_id": "B202607230000401",
            "raw_name": "valid-minimal.csv",
            "row_count": 2,
            "gross": "1001.00",
            "declared_assessed": "12.36",
            "computed_assessed": "12.36",
            "calculated": "12.36",
        },
        "valid-boundary": {
            "file_date": "20000229",
            "batch_id": "B200002290000402",
            "raw_name": "valid-boundary.csv",
            "row_count": 1,
            "gross": "999999999999.99",
            "declared_assessed": "999999999999.99",
            "computed_assessed": "999999999999.99",
            "calculated": "999999999999.99",
        },
        "malformed": {
            "file_date": "20260723",
            "batch_id": "B202607230000403",
            "raw_name": "malformed.csv",
            "row_count": 1,
            "gross": "10.00",
            "declared_assessed": "0.10",
            "computed_assessed": "0.10",
            "calculated": "0.10",
        },
        "rounding-half-up": {
            "file_date": "20260723",
            "batch_id": "B202607230000404",
            "raw_name": "rounding-half-up.csv",
            "row_count": 2,
            "gross": "3.50",
            "declared_assessed": "0.04",
            "computed_assessed": "0.04",
            "calculated": "0.04",
        },
        "DF-SOURCE-005": {
            "file_date": "20260723",
            "batch_id": "B202607230000405",
            "raw_name": "df-source-005.csv",
            "row_count": 1,
            "gross": "100.00",
            "declared_assessed": "0.99",
            "computed_assessed": "1.00",
            "calculated": "1.00",
        },
    }
    return values[scenario]


def _filename_for(scenario: str) -> str:
    values = _scenario_values(scenario)
    return (
        f"NW_MERCHANT_FEES_{values['file_date']}_"
        f"{values['batch_id']}.csv"
    )


def _declared_controls(scenario: str) -> dict[str, object]:
    values = _scenario_values(scenario)
    return {
        "row_count": values["row_count"],
        "gross_amount": values["gross"],
        "assessed_fee": values["declared_assessed"],
        "calculated_fee": values["calculated"],
    }


def _source_artifact(scenario: str) -> dict[str, object]:
    values = _scenario_values(scenario)
    raw = (MAIN / str(values["raw_name"])).read_bytes()
    return {
        "batch_id": values["batch_id"],
        "file_type": {
            "code": "MER_FEESET05",
            "contract_version": 1,
            "layout_version": "001",
            "number": "05",
        },
        "schema_version": 1,
        "source_controls": {
            "assessed_fee": values["declared_assessed"],
            "calculated_fee": values["calculated"],
            "currency": "BRL",
            "gross_amount": values["gross"],
            "row_count": values["row_count"],
        },
        "source_file": {
            "encoding": "UTF-8",
            "final_newline": "required",
            "line_ending": "LF",
            "name": _filename_for(scenario),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "unicode_normalization": "NFC",
        },
    }


def _receipt(scenario: str) -> dict[str, object]:
    values = _scenario_values(scenario)
    filename = _filename_for(scenario)
    expected: dict[str, object] = {
        "status": "ACCEPTED",
        "violation": None,
    }
    fault: dict[str, object] | None = None
    if scenario == "malformed":
        expected = {
            "status": "REJECTED",
            "violation": "INVALID_CSV_QUOTING",
        }
        fault = {
            "code": "INVALID_CSV_QUOTING",
            "expected_stage": "java-validation",
            "injected": True,
        }
    elif scenario == "DF-SOURCE-005":
        expected = {
            "status": "REJECTED",
            "violation": "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
        }
        fault = {
            "code": "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
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
        "batch_id": values["batch_id"],
        "contract": {
            "layout_sha256": "c" * 64,
            "layout_version": "001",
            "registry_sha256": "d" * 64,
            "type_number": "05",
            "version": 1,
        },
        "controls": {
            "computed_assessed_fee": values["computed_assessed"],
            "computed_calculated_fee": values["calculated"],
            "computed_gross_amount": values["gross"],
            "computed_row_count": values["row_count"],
            "declared_assessed_fee": values["declared_assessed"],
            "declared_calculated_fee": values["calculated"],
            "declared_gross_amount": values["gross"],
            "declared_row_count": values["row_count"],
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
    values = _scenario_values(scenario)
    raw_filename = _filename_for(scenario)
    sanitized_filename = raw_filename[:-4] + "_SANITIZED.csv"
    return {
        "batch_id": values["batch_id"],
        "csv_file": {
            "encoding": "UTF-8",
            "name": sanitized_filename,
            "row_count": values["row_count"],
            "sha256": "e" * 64,
            "size_bytes": 1,
            "unicode_normalization": "NFC",
        },
        "file_type": {
            "code": "MER_FEESET05",
            "contract_version": 1,
            "layout_version": "001",
            "number": "05",
        },
        "schema_version": 1,
        "source_lineage": {
            "manifest_sha256": "f" * 64,
            "raw_file": raw_filename,
            "raw_sha256": "a" * 64,
        },
        "stage_controls": {
            "assessed_fee": values["computed_assessed"],
            "calculated_fee": values["calculated"],
            "currency": "BRL",
            "gross_amount": values["gross"],
            "row_count": values["row_count"],
        },
    }


class Type05ContractTest(unittest.TestCase):
    def test_contract_declares_closed_locale_privacy_and_rounding(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        privacy = _load_yaml(TYPE_ROOT / "privacy.yaml")
        csv_contract = _load_yaml(TYPE_ROOT / "csv.yaml")
        reconciliation = _load_yaml(TYPE_ROOT / "reconciliation.yaml")

        file_type = layout["file_type"]
        self.assertEqual(file_type["number"], "05")
        self.assertEqual(file_type["decoding"], "strict")
        self.assertEqual(file_type["unicode_normalization"], "NFC_required_on_input")
        self.assertEqual(file_type["line_ending"], "LF")
        self.assertEqual(file_type["max_detail_rows"], 10_000)
        self.assertEqual(file_type["max_physical_record_bytes"], 512)
        self.assertEqual(file_type["max_source_file_bytes"], 5_130_138)
        self.assertEqual(
            layout["grammar"]["parser"],
            "single_pass_quote_aware_lexer",
        )
        self.assertTrue(layout["grammar"]["description_must_be_quoted"])
        self.assertEqual(layout["calculation"]["rounding_mode"], "HALF_UP")
        self.assertTrue(layout["calculation"]["binary_floating_point"] == "forbidden")
        self.assertEqual(
            privacy["whole_output_validation"]["failure_code"],
            "PRIVACY_OUTPUT_VIOLATION",
        )
        self.assertEqual(csv_contract["format"]["max_rows"], 10_000)
        self.assertEqual(
            reconciliation["semantics"]["global_assessment_id"],
            "unique_across_accepted_batches",
        )

    def test_three_success_truth_sets_are_independently_reproduced(self) -> None:
        all_assessment_ids: set[str] = set()
        for scenario, filenames in SUCCESS_SCENARIOS.items():
            with self.subTest(scenario=scenario):
                raw_name, csv_name, reconciliation_name = filenames
                batch = _parse_source(
                    (MAIN / raw_name).read_bytes(),
                    source_filename=_filename_for(scenario),
                    declared_controls=_declared_controls(scenario),
                )
                self.assertEqual(
                    _render_csv(batch),
                    (MAIN / csv_name).read_bytes(),
                )
                self.assertEqual(
                    _expected_reconciliation(batch),
                    _load_yaml(MAIN / reconciliation_name),
                )
                ids = {
                    assessment.assessment_id
                    for assessment in batch.assessments
                }
                self.assertTrue(all_assessment_ids.isdisjoint(ids))
                all_assessment_ids.update(ids)
                self.assertEqual(
                    batch.declared_row_count,
                    batch.computed_row_count,
                )
                self.assertEqual(
                    batch.declared_gross_amount,
                    batch.computed_gross_amount,
                )
                self.assertEqual(
                    batch.declared_assessed_fee,
                    batch.computed_assessed_fee,
                )
                self.assertEqual(
                    batch.declared_calculated_fee,
                    batch.computed_calculated_fee,
                )

        rounding = _parse_source(
            (MAIN / "rounding-half-up.csv").read_bytes(),
            source_filename=_filename_for("rounding-half-up"),
            declared_controls=_declared_controls("rounding-half-up"),
        )
        self.assertEqual(
            [item.calculated_fee for item in rounding.assessments],
            [Decimal("0.01"), Decimal("0.03")],
        )

    def test_five_raw_fixtures_have_frozen_bytes_and_unique_batches(self) -> None:
        seen_batches: set[str] = set()
        for scenario, (raw_name, expected_hash) in RAW_FIXTURES.items():
            with self.subTest(scenario=scenario):
                raw = (MAIN / raw_name).read_bytes()
                self.assertEqual(
                    hashlib.sha256(raw).hexdigest(),
                    expected_hash,
                )
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))
                self.assertNotIn(b"\r", raw)
                self.assertEqual(
                    unicodedata.normalize("NFC", raw.decode("utf-8")),
                    raw.decode("utf-8"),
                )
                batch_id = str(_scenario_values(scenario)["batch_id"])
                self.assertNotIn(batch_id, seen_batches)
                seen_batches.add(batch_id)
        self.assertEqual(
            seen_batches,
            {
                "B202607230000401",
                "B200002290000402",
                "B202607230000403",
                "B202607230000404",
                "B202607230000405",
            },
        )
        boundary_line = (
            MAIN / "valid-boundary.csv"
        ).read_text(encoding="utf-8").splitlines()[1]
        boundary_description = _lex_row(boundary_line, 2).fields[5]
        self.assertEqual(len(boundary_description), 80)
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

    def test_malformed_has_only_the_description_quoting_defect(self) -> None:
        raw = (MAIN / "malformed.csv").read_bytes()
        with self.assertRaises(ValueError) as raised:
            _parse_source(
                raw,
                source_filename=_filename_for("malformed"),
                declared_controls=_declared_controls("malformed"),
            )
        self.assertEqual(str(raised.exception), "INVALID_CSV_QUOTING")

        repaired = raw.replace(
            b";Tarifa sem aspas;",
            b';"Tarifa sem aspas";',
            1,
        )
        batch = _parse_source(
            repaired,
            source_filename=_filename_for("malformed"),
            declared_controls=_declared_controls("malformed"),
        )
        self.assertEqual(batch.computed_row_count, 1)
        self.assertEqual(batch.computed_assessed_fee, Decimal("0.10"))

        expected = _load_yaml(MAIN / "expected-malformed-rejection.yaml")
        self.assertEqual(expected["expected_code"], "INVALID_CSV_QUOTING")
        self.assertEqual(expected["physical_record_number"], 2)
        self.assertFalse(expected["csv_produced"])
        self.assertFalse(expected["postgres_business_mutation"])

    def test_transport_csv_lexer_and_locale_decimals_fail_closed(self) -> None:
        scenario = "valid-minimal"
        raw = (MAIN / "valid-minimal.csv").read_bytes()
        controls = _declared_controls(scenario)
        filename = _filename_for(scenario)
        transport_mutations = {
            "missing_final_lf": raw[:-1],
            "extra_final_lf": raw + b"\n",
            "crlf": raw.replace(b"\n", b"\r\n", 1),
            "bare_cr": raw.replace(b"\n", b"\r", 1),
        }
        for mutation_name, mutated in transport_mutations.items():
            with self.subTest(transport=mutation_name):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        mutated,
                        source_filename=filename,
                        declared_controls=controls,
                    )
                self.assertEqual(str(raised.exception), "INVALID_TRANSPORT")

        text = raw.decode("utf-8")
        lines = text[:-1].split("\n")
        first = lines[1]
        lexed = _lex_row(first, 2)
        self.assertEqual(
            lexed.fields[5],
            'Tarifa "VIP"; julho, lote A',
        )
        self.assertTrue(lexed.quoted[5])
        self.assertFalse(any(lexed.quoted[:5] + lexed.quoted[6:]))

        def replace_first(value: str) -> bytes:
            mutated = list(lines)
            mutated[1] = value
            return ("\n".join(mutated) + "\n").encode("utf-8")

        quoted_identifier = replace_first(
            first.replace(
                "FEE2026072304001;",
                '"FEE2026072304001";',
                1,
            )
        )
        with self.assertRaises(ValueError) as raised:
            _parse_source(
                quoted_identifier,
                source_filename=filename,
                declared_controls=controls,
            )
        self.assertEqual(str(raised.exception), "INVALID_CSV_QUOTING")

        decimal_mutations = {
            "period_separator": (";1000,00;", ";1000.00;"),
            "explicit_sign": (";1000,00;", ";+1000,00;"),
            "digit_grouping": (";1000,00;", ";1.000,00;"),
            "scientific_notation": (";1000,00;", ";1E3,00;"),
            "missing_fraction_digit": (";1000,00;", ";1000,0;"),
            "leading_zero": (";1000,00;", ";01000,00;"),
            "zero_rate": (";1,235;", ";0,000;"),
            "rate_above_100": (";1,235;", ";100,001;"),
            "negative_assessed": (";12,35;", ";-12,35;"),
        }
        for mutation_name, (old, new) in decimal_mutations.items():
            with self.subTest(decimal=mutation_name):
                mutated = replace_first(first.replace(old, new, 1))
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        mutated,
                        source_filename=filename,
                        declared_controls=controls,
                    )
                self.assertEqual(str(raised.exception), "INVALID_FIELD")

    def test_document_identifier_and_business_date_codes_are_specific(
        self,
    ) -> None:
        scenario = "valid-minimal"
        raw = (MAIN / "valid-minimal.csv").read_bytes()
        lines = raw.decode("utf-8")[:-1].split("\n")
        first = lines[1]
        controls = _declared_controls(scenario)
        filename = _filename_for(scenario)

        def mutate_first(old: str, new: str) -> bytes:
            mutated = list(lines)
            mutated[1] = first.replace(old, new, 1)
            return ("\n".join(mutated) + "\n").encode("utf-8")

        cases = {
            "non_digit_document": (
                "12345678000195",
                "1234567800019X",
                "INVALID_FIELD",
            ),
            "repeated_document": (
                "12345678000195",
                "11111111111111",
                "INVALID_DOCUMENT",
            ),
            "bad_check_digit": (
                "12345678000195",
                "12345678000196",
                "INVALID_DOCUMENT",
            ),
            "assessment_identifier": (
                "FEE2026072304001",
                "1EE2026072304001",
                "INVALID_IDENTIFIER",
            ),
            "batch_identifier": (
                "B202607230000401",
                "X202607230000401",
                "INVALID_IDENTIFIER",
            ),
            "merchant_identifier": (
                "MER0000000000001",
                "1ER0000000000001",
                "INVALID_IDENTIFIER",
            ),
            "fee_identifier": (
                ";MDR;",
                ";1DR;",
                "INVALID_IDENTIFIER",
            ),
            "invalid_calendar_date": (
                "23/07/2026",
                "31/02/2026",
                "INVALID_BUSINESS_DATE",
            ),
            "wrong_business_date": (
                "23/07/2026",
                "22/07/2026",
                "INVALID_BUSINESS_DATE",
            ),
        }
        for mutation_name, (old, new, expected_code) in cases.items():
            with self.subTest(mutation=mutation_name):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        mutate_first(old, new),
                        source_filename=filename,
                        declared_controls=controls,
                    )
                self.assertEqual(str(raised.exception), expected_code)

    def test_dark_factory_is_only_the_source_assessed_control(self) -> None:
        scenario = "DF-SOURCE-005"
        raw = (MAIN / "df-source-005.csv").read_bytes()
        batch = _parse_source(
            raw,
            source_filename=_filename_for(scenario),
            declared_controls=_declared_controls(scenario),
            enforce_controls=False,
        )
        self.assertEqual(
            batch.declared_row_count,
            batch.computed_row_count,
        )
        self.assertEqual(
            batch.declared_gross_amount,
            batch.computed_gross_amount,
        )
        self.assertEqual(batch.declared_assessed_fee, Decimal("0.99"))
        self.assertEqual(batch.computed_assessed_fee, Decimal("1.00"))
        self.assertEqual(
            batch.declared_calculated_fee,
            batch.computed_calculated_fee,
        )
        with self.assertRaises(ValueError) as raised:
            _parse_source(
                raw,
                source_filename=_filename_for(scenario),
                declared_controls=_declared_controls(scenario),
            )
        self.assertEqual(
            str(raised.exception),
            "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
        )

        repaired_controls = _declared_controls(scenario)
        repaired_controls["assessed_fee"] = "1.00"
        _parse_source(
            raw,
            source_filename=_filename_for(scenario),
            declared_controls=repaired_controls,
        )

        finding = _load_yaml(MAIN / "expected-df-source-005-finding.yaml")
        self.assertEqual(
            finding["expected_code"],
            "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
        )
        self.assertEqual(finding["source_system_role"], "system_of_record")
        self.assertEqual(finding["declared_assessed_fee"], "0.99")
        self.assertEqual(finding["computed_assessed_fee"], "1.00")
        self.assertFalse(finding["csv_produced"])
        self.assertFalse(finding["postgres_business_mutation"])

    def test_every_declared_rejection_phase_has_oracle_coverage(self) -> None:
        layout = _load_yaml(TYPE_ROOT / "layout.yaml")
        self.assertEqual(
            layout["validation_order"],
            [
                "source_size",
                "strict_UTF8_without_BOM",
                "NFC_normalization",
                "exact_LF_transport_and_record_byte_bounds",
                "exact_header",
                "CSV_quoting",
                "field_count",
                "field_lexical_and_decimal_rules",
                "CNPJ_Mod11",
                "identifier_and_description_rules",
                "filename_batch_and_business_date_rules",
                "assessment_id_uniqueness",
                "HALF_UP_fee_calculation",
                "source_count_control",
                "source_gross_control",
                "source_assessed_fee_control",
                "source_calculated_fee_control",
                "whole_output_privacy_scan",
            ],
        )
        scenario = "valid-minimal"
        raw = (MAIN / "valid-minimal.csv").read_bytes()
        text = raw.decode("utf-8")
        lines = text[:-1].split("\n")

        def replace_line(index: int, value: str) -> bytes:
            mutated = list(lines)
            mutated[index] = value
            return ("\n".join(mutated) + "\n").encode("utf-8")

        first = lines[1]
        second = lines[2]
        first_fields = _lex_row(first, 2).fields
        second_fields = _lex_row(second, 3).fields

        def source_row(fields: tuple[str, ...], description: str) -> str:
            values = list(fields)
            escaped = description.replace('"', '""')
            values[5] = f'"{escaped}"'
            return ";".join(values)

        duplicate_fields = list(second_fields)
        duplicate_fields[0] = first_fields[0]
        duplicate_row = source_row(
            tuple(duplicate_fields),
            second_fields[5],
        )
        decomposed = text.replace("mínimo", "mi\u0301nimo").encode("utf-8")
        bad_utf8 = bytearray(raw)
        bad_utf8[0] = 0xFF
        source_cases = {
            "INVALID_SOURCE_SIZE": b"A" * 5_130_139,
            "INVALID_UTF8": bytes(bad_utf8),
            "INVALID_UNICODE_NORMALIZATION": decomposed,
            "INVALID_TRANSPORT": raw.replace(b"\n", b"\r\n", 1),
            "INVALID_RECORD_LENGTH": (
                (HEADER + "\n" + "X" * 513 + "\n").encode("utf-8")
            ),
            "INVALID_HEADER": raw.replace(
                b"assessment_id;",
                b"assessment_ix;",
                1,
            ),
            "INVALID_CSV_QUOTING": (
                MAIN / "malformed.csv"
            ).read_bytes(),
            "INVALID_FIELD_COUNT": replace_line(1, first + ";EXTRA"),
            "INVALID_FIELD": replace_line(
                1,
                first.replace(";1000,00;", ";1000.00;", 1),
            ),
            "INVALID_DOCUMENT": replace_line(
                1,
                first.replace("12345678000195", "11111111111111", 1),
            ),
            "INVALID_IDENTIFIER": replace_line(
                1,
                first.replace("FEE2026072304001", "1EE2026072304001", 1),
            ),
            "INVALID_DESCRIPTION": replace_line(
                1,
                source_row(first_fields, "=FORMULA"),
            ),
            "INVALID_BUSINESS_DATE": replace_line(
                1,
                first.replace("23/07/2026", "22/07/2026", 1),
            ),
            "DUPLICATE_IDENTIFIER": replace_line(2, duplicate_row),
            "FEE_CALCULATION_MISMATCH": replace_line(
                1,
                first.replace(";12,35;", ";12,34;", 1),
            ),
        }
        covered_codes: set[str] = set()
        for expected_code, mutated in source_cases.items():
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        mutated,
                        source_filename=_filename_for(scenario),
                        declared_controls=_declared_controls(scenario),
                    )
                self.assertEqual(str(raised.exception), expected_code)
                covered_codes.add(expected_code)

        control_mutations = {
            "SOURCE_CONTROL_COUNT_MISMATCH": ("row_count", 3),
            "SOURCE_CONTROL_GROSS_MISMATCH": (
                "gross_amount",
                "1001.01",
            ),
            "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH": (
                "assessed_fee",
                "12.35",
            ),
            "SOURCE_CONTROL_CALCULATED_FEE_MISMATCH": (
                "calculated_fee",
                "12.35",
            ),
        }
        for expected_code, (field, value) in control_mutations.items():
            with self.subTest(expected_code=expected_code):
                controls = _declared_controls(scenario)
                controls[field] = value
                with self.assertRaises(ValueError) as raised:
                    _parse_source(
                        raw,
                        source_filename=_filename_for(scenario),
                        declared_controls=controls,
                    )
                self.assertEqual(str(raised.exception), expected_code)
                covered_codes.add(expected_code)

        batch = _parse_source(
            raw,
            source_filename=_filename_for(scenario),
            declared_controls=_declared_controls(scenario),
        )
        leaked_output = (
            _render_csv(batch)
            + batch.assessments[0].merchant_tax_id.encode("ascii")
        )
        with self.assertRaises(ValueError) as raised:
            _validate_output_privacy(leaked_output, batch)
        self.assertEqual(str(raised.exception), "PRIVACY_OUTPUT_VIOLATION")
        covered_codes.add("PRIVACY_OUTPUT_VIOLATION")

        declared_codes = set(layout["canonical_rejection_codes"].values())
        self.assertEqual(covered_codes, declared_codes)

        quote_and_count = replace_line(
            2,
            second.replace(
                ';"Arredondamento mínimo";',
                ";Arredondamento mínimo;",
            )
            + ";EXTRA",
        )
        with self.assertRaises(ValueError) as raised:
            _parse_source(
                quote_and_count,
                source_filename=_filename_for(scenario),
                declared_controls=_declared_controls(scenario),
            )
        self.assertEqual(str(raised.exception), "INVALID_CSV_QUOTING")

    def test_type05_common_schema_branches_are_closed(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        sanitized_validator = _validator("sanitized-manifest.schema.json")
        scenarios = (
            "valid-minimal",
            "valid-boundary",
            "malformed",
            "rounding-half-up",
            "DF-SOURCE-005",
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
            "gross_amount": "1250.00",
            "net_amount": "1000.00",
            "return_amount": "-250.00",
            "return_count": 1,
            "transfer_count": 2,
        }
        self.assertTrue(list(source_validator.iter_errors(cross_source)))
        missing_nfc = _source_artifact("valid-minimal")
        del missing_nfc["source_file"]["unicode_normalization"]
        self.assertTrue(list(source_validator.iter_errors(missing_nfc)))
        oversized = _source_artifact("valid-minimal")
        oversized["source_file"]["size_bytes"] = 5_130_139
        self.assertTrue(list(source_validator.iter_errors(oversized)))

        contradictory = _receipt("valid-minimal")
        contradictory["fault"] = {
            "code": "INVALID_CSV_QUOTING",
            "expected_stage": "java-validation",
            "injected": True,
        }
        self.assertTrue(list(receipt_validator.iter_errors(contradictory)))
        cross_receipt = _receipt("valid-minimal")
        cross_receipt["artifacts"]["data_file"] = (
            "NW_TED_SETTLEMENT_20260723_B202607230000401.dat"
        )
        self.assertTrue(list(receipt_validator.iter_errors(cross_receipt)))

        cross_lineage = _sanitized_artifact("valid-minimal")
        cross_lineage["source_lineage"]["raw_file"] = (
            "NW_PAYMENT_SLIP_20260723_B202607230000401.rem"
        )
        self.assertTrue(
            list(sanitized_validator.iter_errors(cross_lineage))
        )
        oversized_rows = _sanitized_artifact("valid-minimal")
        oversized_rows["csv_file"]["row_count"] = 10_001
        self.assertTrue(
            list(sanitized_validator.iter_errors(oversized_rows))
        )

    def test_artifact_links_and_control_cardinality_are_mandatory(self) -> None:
        for scenario in (
            "valid-minimal",
            "valid-boundary",
            "malformed",
            "rounding-half-up",
            "DF-SOURCE-005",
        ):
            source = _source_artifact(scenario)
            match = re.fullmatch(
                r"NW_MERCHANT_FEES_([0-9]{8})_(B[0-9]{15})\.csv",
                source["source_file"]["name"],
            )
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual(match.group(2), source["batch_id"])
            self.assertEqual(
                match.group(1),
                str(_scenario_values(scenario)["file_date"]),
            )
        for scenario in SUCCESS_SCENARIOS:
            sanitized = _sanitized_artifact(scenario)
            raw_match = re.fullmatch(
                r"NW_MERCHANT_FEES_([0-9]{8})_(B[0-9]{15})\.csv",
                sanitized["source_lineage"]["raw_file"],
            )
            csv_match = re.fullmatch(
                (
                    r"NW_MERCHANT_FEES_([0-9]{8})_"
                    r"(B[0-9]{15})_SANITIZED\.csv"
                ),
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
