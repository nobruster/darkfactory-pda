"""Independent Type 05 fixture and reconciliation oracle.

Canonical merchant-fee batches are scored against committed normalized CSV
and reconciliation artifacts. Unseen batches must prove internally consistent
gross, assessed, calculated, and count controls without oracle normalization.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import yaml

from canonical import canonical_money as _money


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_MAIN = (
    ROOT
    / "contracts"
    / "types"
    / "05-merchant-fee-assessment"
    / "main"
)
SUCCESS_CONTRACT_FILES = MappingProxyType(
    {
        "valid-minimal": (
            "expected-sanitized.csv",
            "expected-reconciliation.yaml",
        ),
        "valid-boundary": (
            "expected-valid-boundary-sanitized.csv",
            "expected-valid-boundary-reconciliation.yaml",
        ),
        "rounding-half-up": (
            "expected-rounding-half-up-sanitized.csv",
            "expected-rounding-half-up-reconciliation.yaml",
        ),
    }
)
REJECTION_CONTRACT_FILES = MappingProxyType(
    {
        "malformed": "expected-malformed-rejection.yaml",
        "DF-SOURCE-005": "expected-df-source-005-finding.yaml",
    }
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
MONEY_NAMES = ("gross_amount", "assessed_fee", "calculated_fee")
MONEY_FIELDS = frozenset(
    f"{boundary}_{name}"
    for boundary in ("source", "staged", "applied")
    for name in MONEY_NAMES
) | frozenset(
    {
        "gross_amount_delta",
        "assessed_fee_delta",
        "calculated_fee_delta",
        "assessment_calculation_delta",
    }
)
ORACLE_MATCHED = "oracle_matched"
INTERNALLY_RECONCILED_UNSCORED = "internally_reconciled_unscored"
REJECTED_UNSCORED = "rejected_unscored"


class Type05OracleMismatchError(Exception):
    """Observed Type 05 behavior differs from its approved oracle."""


class Type05OracleContractError(Type05OracleMismatchError):
    """Approved Type 05 oracle artifacts are unavailable or inconsistent."""


@dataclass(frozen=True, slots=True)
class OracleResult:
    """One immutable comparison suitable for privacy-safe evidence."""

    matches: bool | None
    expected: dict[str, object] | None
    actual: dict[str, object]
    oracle_status: str

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible comparison mapping."""

        return {
            "actual": self.actual,
            "expected": self.expected,
            "matches": self.matches,
            "oracle_status": self.oracle_status,
        }


@dataclass(frozen=True, slots=True)
class _SuccessContract:
    batch_id: str
    csv_sha256: str
    controls: dict[str, int | str]
    reconciliation: dict[str, object]


def _read_yaml(filename: str) -> dict[str, object]:
    try:
        value = yaml.safe_load(
            (CONTRACT_MAIN / filename).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise Type05OracleContractError(
            f"Type 05 oracle artifact cannot be loaded: {filename}"
        ) from exc
    if not isinstance(value, dict):
        raise Type05OracleContractError(
            f"Type 05 oracle artifact is not a mapping: {filename}"
        )
    return value


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, int) and str(parsed) != str(value):
        return None
    return parsed


@lru_cache(maxsize=None)
def _success_contract(scenario: str) -> _SuccessContract:
    try:
        csv_filename, reconciliation_filename = SUCCESS_CONTRACT_FILES[
            scenario
        ]
    except KeyError as exc:
        raise Type05OracleContractError(
            f"No Type 05 success oracle exists for {scenario!r}"
        ) from exc

    try:
        csv_bytes = (CONTRACT_MAIN / csv_filename).read_bytes()
        text = csv_bytes.decode("utf-8")
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise Type05OracleContractError(
            f"Type 05 CSV oracle cannot be loaded: {csv_filename}"
        ) from exc
    if (
        not rows
        or tuple(reader.fieldnames or ()) != CSV_COLUMNS
        or not text.endswith("\n")
        or "\r" in text
    ):
        raise Type05OracleContractError(
            f"Type 05 CSV oracle transport is invalid: {csv_filename}"
        )

    reconciliation = _read_yaml(reconciliation_filename)
    batch_id = reconciliation.get("batch_id")
    if not isinstance(batch_id, str) or any(
        row.get("batch_id") != batch_id for row in rows
    ):
        raise Type05OracleContractError(
            f"Type 05 CSV and reconciliation disagree: {scenario}"
        )
    try:
        controls: dict[str, int | str] = {
            "row_count": len(rows),
            "gross_amount": format(
                sum(
                    (Decimal(row["gross_amount_brl"]) for row in rows),
                    Decimal("0.00"),
                ),
                ".2f",
            ),
            "assessed_fee": format(
                sum(
                    (Decimal(row["assessed_fee_brl"]) for row in rows),
                    Decimal("0.00"),
                ),
                ".2f",
            ),
            "calculated_fee": format(
                sum(
                    (Decimal(row["calculated_fee_brl"]) for row in rows),
                    Decimal("0.00"),
                ),
                ".2f",
            ),
        }
    except (InvalidOperation, KeyError) as exc:
        raise Type05OracleContractError(
            f"Type 05 CSV oracle controls are invalid: {csv_filename}"
        ) from exc
    if (
        reconciliation.get("source_count") != controls["row_count"]
        or any(
            _money(reconciliation.get(f"source_{name}"))
            != controls[name]
            for name in MONEY_NAMES
        )
        or reconciliation.get("status") != "MATCHED"
    ):
        raise Type05OracleContractError(
            f"Type 05 oracle controls disagree: {scenario}"
        )
    return _SuccessContract(
        batch_id=batch_id,
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        controls=controls,
        reconciliation=dict(reconciliation),
    )


@lru_cache(maxsize=None)
def _rejection_contract(scenario: str) -> dict[str, object]:
    try:
        expected = _read_yaml(REJECTION_CONTRACT_FILES[scenario])
    except KeyError as exc:
        raise Type05OracleContractError(
            f"No Type 05 rejection oracle exists for {scenario!r}"
        ) from exc
    if (
        expected.get("scenario") != scenario
        or not isinstance(expected.get("batch_id"), str)
        or not isinstance(expected.get("expected_code"), str)
    ):
        raise Type05OracleContractError(
            f"Type 05 rejection oracle is inconsistent: {scenario}"
        )
    return expected


EXPECTED_REJECTION = MappingProxyType(
    {
        scenario: str(_rejection_contract(scenario)["expected_code"])
        for scenario in REJECTION_CONTRACT_FILES
    }
)


def compare_sanitized_before_posting(
    scenario: str | None,
    *,
    batch_id: str,
    java_result: Mapping[str, object],
) -> OracleResult:
    """Compare Java controls before PostgreSQL business mutation."""

    actual: dict[str, object] = {
        "batch_id": java_result.get("batch_id"),
        "csv_sha256": java_result.get("csv_sha256"),
        "row_count": _integer(java_result.get("row_count")),
        "gross_amount": _money(java_result.get("gross_amount")),
        "assessed_fee": _money(java_result.get("assessed_fee")),
        "calculated_fee": _money(java_result.get("calculated_fee")),
        "status": java_result.get("status"),
    }
    if scenario is None:
        if (
            actual["batch_id"] != batch_id
            or actual["status"] != "succeeded"
            or any(value is None for value in actual.values())
        ):
            raise Type05OracleMismatchError(
                "Unscored Type 05 sanitized controls are incomplete"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status="sanitized_unscored",
        )

    contract = _success_contract(scenario)
    expected: dict[str, object] = {
        "batch_id": contract.batch_id,
        "csv_sha256": contract.csv_sha256,
        **contract.controls,
        "status": "succeeded",
    }
    if batch_id != contract.batch_id or actual != expected:
        raise Type05OracleMismatchError(
            "Type 05 sanitized output differs from its oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected,
        actual=actual,
        oracle_status=ORACLE_MATCHED,
    )


def _normalize_reconciliation(
    value: Mapping[str, object],
    *,
    keys: set[str],
) -> dict[str, object]:
    normalized = {key: value.get(key) for key in keys}
    for key in MONEY_FIELDS & keys:
        normalized[key] = _money(normalized[key])
    return normalized


def _internally_reconciled(value: Mapping[str, object]) -> bool:
    if set(value) != set(
        _success_contract("valid-minimal").reconciliation
    ):
        return False
    count = _integer(value.get("source_count"))
    if (
        not isinstance(value.get("batch_id"), str)
        or value.get("currency") != "BRL"
        or count is None
        or count != _integer(value.get("staged_count"))
        or count != _integer(value.get("applied_count"))
    ):
        return False
    for name in MONEY_NAMES:
        source = _money(value.get(f"source_{name}"))
        if (
            source is None
            or source != _money(value.get(f"staged_{name}"))
            or source != _money(value.get(f"applied_{name}"))
            or _money(value.get(f"{name}_delta")) != "0.00"
        ):
            return False
    return (
        _integer(value.get("count_delta")) == 0
        and _money(value.get("assessment_calculation_delta")) == "0.00"
        and _integer(value.get("reject_count")) == 0
        and value.get("status") == "MATCHED"
    )


def compare_post_db_reconciliation(
    scenario: str | None,
    *,
    reconciliation: Mapping[str, object],
) -> OracleResult:
    """Compare PostgreSQL output with the complete approved YAML."""

    if scenario is None:
        actual = dict(reconciliation)
        if not _internally_reconciled(reconciliation):
            raise Type05OracleMismatchError(
                "Unscored Type 05 batch is not internally reconciled"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=INTERNALLY_RECONCILED_UNSCORED,
        )

    expected = dict(_success_contract(scenario).reconciliation)
    if set(reconciliation) != set(expected):
        raise Type05OracleMismatchError(
            "Type 05 PostgreSQL reconciliation has an unexpected shape"
        )
    actual = _normalize_reconciliation(
        reconciliation,
        keys=set(expected),
    )
    if actual != expected:
        raise Type05OracleMismatchError(
            "Type 05 PostgreSQL output differs from its oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected,
        actual=actual,
        oracle_status=ORACLE_MATCHED,
    )


def compare_rejection(
    scenario: str | None,
    *,
    batch_id: str,
    java_result: Mapping[str, object],
) -> OracleResult:
    """Compare a privacy-safe Java rejection with its canonical outcome."""

    if scenario is None:
        actual = {
            "batch_id": java_result.get("batch_id"),
            "code": java_result.get("code"),
            "status": java_result.get("status"),
        }
        if (
            actual["batch_id"] != batch_id
            or actual["status"] != "rejected"
            or not isinstance(actual["code"], str)
        ):
            raise Type05OracleMismatchError(
                "Unscored Type 05 rejection is incomplete"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=REJECTED_UNSCORED,
        )

    expected = dict(_rejection_contract(scenario))
    actual: dict[str, object] = {
        "batch_id": java_result.get("batch_id"),
        "scenario": scenario,
        "expected_stage": "java-validation",
        "expected_status": (
            "quarantined"
            if java_result.get("status") == "rejected"
            else java_result.get("status")
        ),
        "expected_code": java_result.get("code"),
        "csv_produced": java_result.get("csv_file") is not None,
        "postgres_business_mutation": False,
        "quarantine_scope": "batch",
    }
    evaluated = set(expected)
    if scenario == "malformed":
        record_number = java_result.get(
            "physical_record_number",
            java_result.get("record_number"),
        )
        actual["physical_record_number"] = _integer(record_number)
        evaluated -= {"unrelated_batches_continue"}
    else:
        actual["declared_row_count"] = _integer(
            java_result.get("declared_row_count")
        )
        actual["computed_row_count"] = _integer(
            java_result.get("computed_row_count")
        )
        for name in MONEY_NAMES:
            actual[f"declared_{name}"] = _money(
                java_result.get(f"declared_{name}")
            )
            actual[f"computed_{name}"] = _money(
                java_result.get(f"computed_{name}")
            )
        evaluated -= {"source_system_role", "unrelated_batches_continue"}

    expected_evaluated = {key: expected[key] for key in evaluated}
    actual_evaluated = {key: actual.get(key) for key in evaluated}
    if (
        batch_id != expected.get("batch_id")
        or actual_evaluated != expected_evaluated
    ):
        raise Type05OracleMismatchError(
            "Type 05 rejection differs from its approved oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected_evaluated,
        actual=actual_evaluated,
        oracle_status=ORACLE_MATCHED,
    )
