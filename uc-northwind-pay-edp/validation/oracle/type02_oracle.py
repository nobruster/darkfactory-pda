"""Independent Type 02 fixture and reconciliation oracle.

Known canonical batches are scored against committed contract artifacts.
Previously unseen valid batches are not fixture-scored, but they must still
prove zero-delta internal PostgreSQL reconciliation.
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
    / "02-instant-payment-events"
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
        "escaped-content": (
            "expected-escaped-content-sanitized.csv",
            "expected-escaped-content-reconciliation.yaml",
        ),
    }
)
REJECTION_CONTRACT_FILES = MappingProxyType(
    {
        "malformed": "expected-malformed-rejection.yaml",
        "DF-SOURCE-002": "expected-df-source-002-finding.yaml",
    }
)
MONEY_FIELDS = frozenset(
    {
        "source_credit_amount",
        "staged_credit_amount",
        "applied_credit_amount",
        "source_debit_amount",
        "staged_debit_amount",
        "applied_debit_amount",
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "credit_amount_delta",
        "debit_amount_delta",
        "net_amount_delta",
    }
)
ORACLE_MATCHED = "oracle_matched"
INTERNALLY_RECONCILED_UNSCORED = "internally_reconciled_unscored"
REJECTED_UNSCORED = "rejected_unscored"


class Type02OracleMismatchError(Exception):
    """Observed Type 02 behavior differs from its approved oracle."""


class Type02OracleContractError(Type02OracleMismatchError):
    """Approved Type 02 oracle artifacts are missing or inconsistent."""


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
        raise Type02OracleContractError(
            f"Type 02 oracle artifact cannot be loaded: {filename}"
        ) from exc
    if not isinstance(value, dict):
        raise Type02OracleContractError(
            f"Type 02 oracle artifact is not a mapping: {filename}"
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
        raise Type02OracleContractError(
            f"No Type 02 success oracle exists for {scenario!r}"
        ) from exc

    try:
        csv_bytes = (CONTRACT_MAIN / csv_filename).read_bytes()
        text = csv_bytes.decode("utf-8")
        rows = list(
            csv.DictReader(
                io.StringIO(text, newline=""),
                strict=True,
            )
        )
    except (OSError, UnicodeError, csv.Error) as exc:
        raise Type02OracleContractError(
            f"Type 02 CSV oracle cannot be loaded: {csv_filename}"
        ) from exc
    if not rows or not text.endswith("\n") or "\r" in text:
        raise Type02OracleContractError(
            f"Type 02 CSV oracle transport is invalid: {csv_filename}"
        )

    reconciliation = _read_yaml(reconciliation_filename)
    batch_id = reconciliation.get("batch_id")
    if not isinstance(batch_id, str) or any(
        row.get("batch_id") != batch_id for row in rows
    ):
        raise Type02OracleContractError(
            f"Type 02 CSV and reconciliation disagree: {scenario}"
        )
    try:
        credit = sum(
            (
                Decimal(row["amount_brl"])
                for row in rows
                if row["direction"] == "C"
            ),
            start=Decimal("0.00"),
        )
        debit = sum(
            (
                abs(Decimal(row["amount_brl"]))
                for row in rows
                if row["direction"] == "D"
            ),
            start=Decimal("0.00"),
        )
    except (InvalidOperation, KeyError) as exc:
        raise Type02OracleContractError(
            f"Type 02 CSV oracle controls are invalid: {csv_filename}"
        ) from exc
    controls: dict[str, int | str] = {
        "row_count": len(rows),
        "credit_amount": format(credit, ".2f"),
        "debit_amount": format(debit, ".2f"),
        "net_amount": format(credit - debit, ".2f"),
        "returned_count": sum(
            row.get("status") == "RETURNED" for row in rows
        ),
    }
    if (
        reconciliation.get("source_count") != controls["row_count"]
        or _money(reconciliation.get("source_credit_amount"))
        != controls["credit_amount"]
        or _money(reconciliation.get("source_debit_amount"))
        != controls["debit_amount"]
        or _money(reconciliation.get("source_net_amount"))
        != controls["net_amount"]
        or reconciliation.get("source_returned_count")
        != controls["returned_count"]
        or reconciliation.get("status") != "MATCHED"
    ):
        raise Type02OracleContractError(
            f"Type 02 oracle controls disagree: {scenario}"
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
        raise Type02OracleContractError(
            f"No Type 02 rejection oracle exists for {scenario!r}"
        ) from exc
    if (
        expected.get("scenario") != scenario
        or not isinstance(expected.get("batch_id"), str)
        or not isinstance(expected.get("expected_code"), str)
    ):
        raise Type02OracleContractError(
            f"Type 02 rejection oracle is inconsistent: {scenario}"
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
        "credit_amount": _money(java_result.get("credit_amount")),
        "debit_amount": _money(java_result.get("debit_amount")),
        "net_amount": _money(java_result.get("net_amount")),
        "returned_count": _integer(java_result.get("returned_count")),
        "status": java_result.get("status"),
    }
    if scenario is None:
        if (
            actual["batch_id"] != batch_id
            or actual["status"] != "succeeded"
            or any(value is None for value in actual.values())
        ):
            raise Type02OracleMismatchError(
                "Unscored Type 02 sanitized controls are incomplete"
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
        raise Type02OracleMismatchError(
            "Type 02 sanitized output differs from its oracle"
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
    credit = _money(value.get("source_credit_amount"))
    debit = _money(value.get("source_debit_amount"))
    net = _money(value.get("source_net_amount"))
    returned = _integer(value.get("source_returned_count"))
    return (
        isinstance(value.get("batch_id"), str)
        and value.get("currency") == "BRL"
        and count is not None
        and count
        == _integer(value.get("staged_count"))
        == _integer(value.get("applied_count"))
        and credit is not None
        and credit
        == _money(value.get("staged_credit_amount"))
        == _money(value.get("applied_credit_amount"))
        and debit is not None
        and debit
        == _money(value.get("staged_debit_amount"))
        == _money(value.get("applied_debit_amount"))
        and net is not None
        and net
        == _money(value.get("staged_net_amount"))
        == _money(value.get("applied_net_amount"))
        and returned is not None
        and returned
        == _integer(value.get("staged_returned_count"))
        == _integer(value.get("applied_returned_count"))
        and _integer(value.get("count_delta")) == 0
        and _money(value.get("credit_amount_delta")) == "0.00"
        and _money(value.get("debit_amount_delta")) == "0.00"
        and _money(value.get("net_amount_delta")) == "0.00"
        and _integer(value.get("returned_count_delta")) == 0
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
            raise Type02OracleMismatchError(
                "Unscored Type 02 batch is not internally reconciled"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=INTERNALLY_RECONCILED_UNSCORED,
        )

    expected = dict(_success_contract(scenario).reconciliation)
    if set(reconciliation) != set(expected):
        raise Type02OracleMismatchError(
            "Type 02 PostgreSQL reconciliation has an unexpected shape"
        )
    actual = _normalize_reconciliation(
        reconciliation,
        keys=set(expected),
    )
    if actual != expected:
        raise Type02OracleMismatchError(
            "Type 02 PostgreSQL output differs from its oracle"
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
    """Compare a safe Java rejection with its canonical outcome."""

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
            raise Type02OracleMismatchError(
                "Unscored Type 02 rejection is incomplete"
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
        actual["source_record_number"] = _integer(
            java_result.get("record_number")
        )
    else:
        actual.update(
            {
                "declared_event_count": _integer(
                    java_result.get("declared_event_count")
                ),
                "computed_event_count": _integer(
                    java_result.get("computed_event_count")
                ),
                "declared_credit_amount": _money(
                    java_result.get("declared_credit_amount")
                ),
                "computed_credit_amount": _money(
                    java_result.get("computed_credit_amount")
                ),
                "declared_debit_amount": _money(
                    java_result.get("declared_debit_amount")
                ),
                "computed_debit_amount": _money(
                    java_result.get("computed_debit_amount")
                ),
                "declared_net_amount": _money(
                    java_result.get("declared_net_amount")
                ),
                "computed_net_amount": _money(
                    java_result.get("computed_net_amount")
                ),
            }
        )
        evaluated -= {"source_system_role", "unrelated_batches_continue"}

    expected_evaluated = {key: expected[key] for key in evaluated}
    actual_evaluated = {key: actual.get(key) for key in evaluated}
    if (
        batch_id != expected.get("batch_id")
        or actual_evaluated != expected_evaluated
    ):
        raise Type02OracleMismatchError(
            "Type 02 rejection differs from its approved oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected_evaluated,
        actual=actual_evaluated,
        oracle_status=ORACLE_MATCHED,
    )
