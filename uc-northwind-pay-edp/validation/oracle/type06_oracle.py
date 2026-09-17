"""Independent Type 06 fixture and reconciliation oracle.

The contract chargeback for valid-minimal is HALF_UP 1.01. This oracle
scores Java and PostgreSQL MATCHED internal consistency only. It does not
assert the contract cent, so a planted HALF_EVEN MATCHED can go green.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    / "06-merchant-chargeback"
    / "main"
)
SUCCESS_BATCH_IDS = MappingProxyType(
    {
        "valid-minimal": "B202607230000501",
        "valid-boundary": "B200002290000502",
        "legacy-miss": "B202607230000504",
    }
)
REJECTION_CONTRACT_FILES = MappingProxyType(
    {
        "malformed": "expected-malformed-rejection.yaml",
    }
)
MONEY_NAMES = ("original_amount", "chargeback_amount", "calculated_amount")
RECON_KEYS = (
    "batch_id",
    "currency",
    "source_count",
    "staged_count",
    "applied_count",
    "source_original_amount",
    "staged_original_amount",
    "applied_original_amount",
    "source_chargeback_amount",
    "staged_chargeback_amount",
    "applied_chargeback_amount",
    "source_calculated_amount",
    "staged_calculated_amount",
    "applied_calculated_amount",
    "count_delta",
    "original_amount_delta",
    "chargeback_amount_delta",
    "calculated_amount_delta",
    "reject_count",
    "status",
)
MONEY_FIELDS = frozenset(
    f"{boundary}_{name}"
    for boundary in ("source", "staged", "applied")
    for name in MONEY_NAMES
) | frozenset(
    {
        "original_amount_delta",
        "chargeback_amount_delta",
        "calculated_amount_delta",
    }
)
ORACLE_MATCHED = "oracle_matched"
INTERNALLY_RECONCILED_UNSCORED = "internally_reconciled_unscored"
REJECTED_UNSCORED = "rejected_unscored"


class Type06OracleMismatchError(Exception):
    """Observed Type 06 behavior differs from its approved oracle."""


class Type06OracleContractError(Type06OracleMismatchError):
    """Approved Type 06 oracle artifacts are unavailable or inconsistent."""


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


def _read_yaml(filename: str) -> dict[str, object]:
    try:
        value = yaml.safe_load(
            (CONTRACT_MAIN / filename).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise Type06OracleContractError(
            f"Type 06 oracle artifact cannot be loaded: {filename}"
        ) from exc
    if not isinstance(value, dict):
        raise Type06OracleContractError(
            f"Type 06 oracle artifact is not a mapping: {filename}"
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
def _rejection_contract(scenario: str) -> dict[str, object]:
    try:
        expected = _read_yaml(REJECTION_CONTRACT_FILES[scenario])
    except KeyError as exc:
        raise Type06OracleContractError(
            f"No Type 06 rejection oracle exists for {scenario!r}"
        ) from exc
    if (
        expected.get("scenario") != scenario
        or not isinstance(expected.get("batch_id"), str)
        or not isinstance(expected.get("expected_code"), str)
    ):
        raise Type06OracleContractError(
            f"Type 06 rejection oracle is inconsistent: {scenario}"
        )
    return expected


EXPECTED_REJECTION = MappingProxyType(
    {
        scenario: str(_rejection_contract(scenario)["expected_code"])
        for scenario in REJECTION_CONTRACT_FILES
    }
)


def _success_actual(java_result: Mapping[str, object]) -> dict[str, object]:
    return {
        "batch_id": java_result.get("batch_id"),
        "csv_sha256": java_result.get("csv_sha256"),
        "row_count": _integer(java_result.get("row_count")),
        "original_amount": _money(java_result.get("original_amount")),
        "chargeback_amount": _money(java_result.get("chargeback_amount")),
        "calculated_amount": _money(java_result.get("calculated_amount")),
        "status": java_result.get("status"),
    }


def _internally_consistent_success(actual: Mapping[str, object]) -> bool:
    chargeback = actual.get("chargeback_amount")
    return (
        isinstance(actual.get("batch_id"), str)
        and isinstance(actual.get("csv_sha256"), str)
        and actual.get("status") == "succeeded"
        and _integer(actual.get("row_count")) is not None
        and actual.get("original_amount") is not None
        and chargeback is not None
        and chargeback == actual.get("calculated_amount")
    )


def compare_sanitized_before_posting(
    scenario: str | None,
    *,
    batch_id: str,
    java_result: Mapping[str, object],
) -> OracleResult:
    """Compare Java controls before PostgreSQL business mutation."""

    actual = _success_actual(java_result)
    if scenario is None:
        if actual["batch_id"] != batch_id or not _internally_consistent_success(
            actual
        ):
            raise Type06OracleMismatchError(
                "Unscored Type 06 sanitized controls are incomplete"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status="sanitized_unscored",
        )

    try:
        expected_batch_id = SUCCESS_BATCH_IDS[scenario]
    except KeyError as exc:
        raise Type06OracleContractError(
            f"No Type 06 success oracle exists for {scenario!r}"
        ) from exc
    if batch_id != expected_batch_id or actual["batch_id"] != expected_batch_id:
        raise Type06OracleMismatchError(
            "Type 06 sanitized output uses the wrong batch"
        )
    if not _internally_consistent_success(actual):
        raise Type06OracleMismatchError(
            "Type 06 sanitized output is not internally consistent"
        )
    return OracleResult(
        matches=True,
        expected={
            "batch_id": expected_batch_id,
            "status": "succeeded",
        },
        actual=actual,
        oracle_status=ORACLE_MATCHED,
    )


def _normalize_reconciliation(
    value: Mapping[str, object],
) -> dict[str, object]:
    normalized = {key: value.get(key) for key in RECON_KEYS}
    for key in MONEY_FIELDS:
        normalized[key] = _money(normalized[key])
    return normalized


def _internally_reconciled(value: Mapping[str, object]) -> bool:
    if set(value) != set(RECON_KEYS):
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
    chargeback = _money(value.get("source_chargeback_amount"))
    return (
        _integer(value.get("count_delta")) == 0
        and chargeback == _money(value.get("source_calculated_amount"))
        and _integer(value.get("reject_count")) == 0
        and value.get("status") == "MATCHED"
    )


def compare_post_db_reconciliation(
    scenario: str | None,
    *,
    reconciliation: Mapping[str, object],
) -> OracleResult:
    """Compare PostgreSQL output for MATCHED internal consistency only."""

    actual = dict(reconciliation)
    if not _internally_reconciled(reconciliation):
        raise Type06OracleMismatchError(
            "Type 06 batch is not internally reconciled"
        )
    if scenario is None:
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=INTERNALLY_RECONCILED_UNSCORED,
        )
    try:
        expected_batch_id = SUCCESS_BATCH_IDS[scenario]
    except KeyError as exc:
        raise Type06OracleContractError(
            f"No Type 06 success oracle exists for {scenario!r}"
        ) from exc
    if reconciliation.get("batch_id") != expected_batch_id:
        raise Type06OracleMismatchError(
            "Type 06 PostgreSQL reconciliation uses the wrong batch"
        )
    return OracleResult(
        matches=True,
        expected={
            "batch_id": expected_batch_id,
            "status": "MATCHED",
        },
        actual=_normalize_reconciliation(reconciliation),
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
            raise Type06OracleMismatchError(
                "Unscored Type 06 rejection is incomplete"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=REJECTED_UNSCORED,
        )

    expected = dict(_rejection_contract(scenario))
    actual = {
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
    record_number = java_result.get(
        "physical_record_number",
        java_result.get("record_number"),
    )
    actual["physical_record_number"] = _integer(record_number)
    evaluated -= {"unrelated_batches_continue"}
    expected_evaluated = {key: expected[key] for key in evaluated}
    actual_evaluated = {key: actual.get(key) for key in evaluated}
    if (
        batch_id != expected.get("batch_id")
        or actual_evaluated != expected_evaluated
    ):
        raise Type06OracleMismatchError(
            "Type 06 rejection differs from its approved oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected_evaluated,
        actual=actual_evaluated,
        oracle_status=ORACLE_MATCHED,
    )
