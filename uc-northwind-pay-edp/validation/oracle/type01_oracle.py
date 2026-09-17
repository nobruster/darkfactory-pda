from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

import yaml

from canonical import canonical_money as _money

if TYPE_CHECKING:
    from loader_common import LoadResult
    from raw_publisher import PublishedRaw


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_MAIN = (
    ROOT / "contracts" / "types" / "01-card-settlement" / "main"
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
        "negative-overpunch": (
            "expected-negative-overpunch-sanitized.csv",
            "expected-negative-overpunch-reconciliation.yaml",
        ),
    }
)
REJECTION_CONTRACT_FILES = MappingProxyType(
    {
        "malformed": "expected-malformed-rejection.yaml",
        "DF-SOURCE-001": "expected-df-source-001-finding.yaml",
    }
)

ORACLE_MATCHED = "oracle_matched"
INTERNALLY_RECONCILED_UNSCORED = "internally_reconciled_unscored"
REJECTED_UNSCORED = "rejected_unscored"


class Type01OracleMismatchError(Exception):
    """Observed legacy behavior differs from the approved Type 01 oracle."""


class Type01OracleContractError(Type01OracleMismatchError):
    """The approved Type 01 oracle artifacts are missing or inconsistent."""


@dataclass(frozen=True, slots=True)
class OracleResult:
    matches: bool | None
    expected: dict[str, object] | None
    actual: dict[str, object]
    oracle_status: str

    def as_dict(self) -> dict[str, object]:
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
    row_count: int
    net_amount: str
    reconciliation: dict[str, object]


def _read_yaml(filename: str) -> dict[str, object]:
    path = CONTRACT_MAIN / filename
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise Type01OracleContractError(
            f"Type 01 oracle artifact cannot be loaded: {filename}"
        ) from exc
    if not isinstance(loaded, dict):
        raise Type01OracleContractError(
            f"Type 01 oracle artifact is not a mapping: {filename}"
        )
    return loaded


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None
    if str(integer) != str(value) and not isinstance(value, int):
        return None
    return integer


@lru_cache(maxsize=None)
def _success_contract(scenario: str) -> _SuccessContract:
    try:
        csv_filename, reconciliation_filename = SUCCESS_CONTRACT_FILES[
            scenario
        ]
    except KeyError as exc:
        raise Type01OracleContractError(
            f"No approved Type 01 success oracle exists for {scenario!r}"
        ) from exc

    reconciliation = _read_yaml(reconciliation_filename)
    expected_keys = {
        "batch_id",
        "currency",
        "source_count",
        "staged_count",
        "applied_count",
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "count_delta",
        "amount_delta",
        "reject_count",
        "status",
    }
    if set(reconciliation) != expected_keys:
        raise Type01OracleContractError(
            f"Type 01 reconciliation oracle has unexpected fields: "
            f"{reconciliation_filename}"
        )

    csv_path = CONTRACT_MAIN / csv_filename
    try:
        csv_bytes = csv_path.read_bytes()
        csv_text = csv_bytes.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise Type01OracleContractError(
            f"Type 01 sanitized oracle cannot be loaded: {csv_filename}"
        ) from exc
    if not csv_text.endswith("\n") or "\r" in csv_text:
        raise Type01OracleContractError(
            f"Type 01 sanitized oracle has invalid transport: {csv_filename}"
        )

    rows = list(csv.DictReader(io.StringIO(csv_text, newline="")))
    if not rows:
        raise Type01OracleContractError(
            f"Type 01 sanitized oracle contains no rows: {csv_filename}"
        )
    batch_id = reconciliation.get("batch_id")
    if not isinstance(batch_id, str) or any(
        row.get("batch_id") != batch_id for row in rows
    ):
        raise Type01OracleContractError(
            f"Type 01 sanitized and reconciliation oracles disagree: "
            f"{scenario}"
        )
    try:
        csv_net_amount = sum(
            (Decimal(row["amount_brl"]) for row in rows),
            start=Decimal("0.00"),
        )
    except (InvalidOperation, KeyError) as exc:
        raise Type01OracleContractError(
            f"Type 01 sanitized oracle has invalid amounts: {csv_filename}"
        ) from exc

    row_count = len(rows)
    net_amount = format(csv_net_amount, ".2f")
    if (
        reconciliation.get("source_count") != row_count
        or reconciliation.get("staged_count") != row_count
        or reconciliation.get("applied_count") != row_count
        or _money(reconciliation.get("source_net_amount")) != net_amount
        or _money(reconciliation.get("staged_net_amount")) != net_amount
        or _money(reconciliation.get("applied_net_amount")) != net_amount
        or reconciliation.get("status") != "MATCHED"
    ):
        raise Type01OracleContractError(
            f"Type 01 sanitized and reconciliation controls disagree: "
            f"{scenario}"
        )

    return _SuccessContract(
        batch_id=batch_id,
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        row_count=row_count,
        net_amount=net_amount,
        reconciliation=dict(reconciliation),
    )


@lru_cache(maxsize=None)
def _rejection_contract(scenario: str) -> dict[str, object]:
    try:
        filename = REJECTION_CONTRACT_FILES[scenario]
    except KeyError as exc:
        raise Type01OracleContractError(
            f"No approved Type 01 rejection oracle exists for {scenario!r}"
        ) from exc
    expected = _read_yaml(filename)
    if (
        expected.get("scenario") != scenario
        or not isinstance(expected.get("batch_id"), str)
        or not isinstance(expected.get("expected_code"), str)
    ):
        raise Type01OracleContractError(
            f"Type 01 rejection oracle is inconsistent: {filename}"
        )
    return expected


# The runner uses this mapping to identify scenarios that must never reach the
# sanitized/PostgreSQL path. Values are loaded from the canonical YAML files.
EXPECTED_REJECTION = MappingProxyType(
    {
        scenario: str(_rejection_contract(scenario)["expected_code"])
        for scenario in REJECTION_CONTRACT_FILES
    }
)

# Kept for existing callers, but derived from the canonical CSV artifacts.
EXPECTED_CSV_SHA256 = MappingProxyType(
    {
        scenario: _success_contract(scenario).csv_sha256
        for scenario in SUCCESS_CONTRACT_FILES
    }
)


def compare_sanitized_before_posting(
    scenario: str | None,
    *,
    batch_id: str,
    java_result: Mapping[str, object],
) -> OracleResult:
    """Gate a known sanitized output before PostgreSQL can be mutated.

    The actual values come from the independently produced Java result. The
    expected SHA, row count, and net amount come only from committed contract
    artifacts.
    """

    actual = {
        "batch_id": java_result.get("batch_id"),
        "csv_sha256": java_result.get("csv_sha256"),
        "row_count": _integer(java_result.get("row_count")),
        "net_amount": _money(java_result.get("net_amount")),
        "status": java_result.get("status"),
    }
    if scenario is None:
        if (
            actual["batch_id"] != batch_id
            or actual["status"] != "succeeded"
            or actual["csv_sha256"] is None
            or actual["row_count"] is None
            or actual["net_amount"] is None
        ):
            raise Type01OracleMismatchError(
                "Unscored Type 01 sanitized controls are incomplete"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status="sanitized_unscored",
        )

    contract = _success_contract(scenario)
    expected = {
        "batch_id": contract.batch_id,
        "csv_sha256": contract.csv_sha256,
        "row_count": contract.row_count,
        "net_amount": contract.net_amount,
        "status": "succeeded",
    }
    matches = (
        batch_id == contract.batch_id
        and actual == expected
    )
    if not matches:
        raise Type01OracleMismatchError(
            "Type 01 sanitized output does not match its approved oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected,
        actual=actual,
        oracle_status=ORACLE_MATCHED,
    )


def _reconciliation_actual(
    reconciliation: Mapping[str, object],
    *,
    expected_keys: set[str],
) -> dict[str, object]:
    actual = {
        key: reconciliation.get(key)
        for key in expected_keys
    }
    for key in (
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "amount_delta",
    ):
        if key in actual:
            actual[key] = _money(actual[key])
    return actual


def _internally_reconciled(
    reconciliation: Mapping[str, object],
) -> bool:
    if set(reconciliation) != set(
        _success_contract("valid-minimal").reconciliation
    ):
        return False
    source_count = _integer(reconciliation.get("source_count"))
    staged_count = _integer(reconciliation.get("staged_count"))
    applied_count = _integer(reconciliation.get("applied_count"))
    source_net = _money(reconciliation.get("source_net_amount"))
    staged_net = _money(reconciliation.get("staged_net_amount"))
    applied_net = _money(reconciliation.get("applied_net_amount"))
    return (
        isinstance(reconciliation.get("batch_id"), str)
        and reconciliation.get("currency") == "BRL"
        and source_count is not None
        and source_count == staged_count == applied_count
        and source_net is not None
        and source_net == staged_net == applied_net
        and _integer(reconciliation.get("count_delta")) == 0
        and _money(reconciliation.get("amount_delta")) == "0.00"
        and _integer(reconciliation.get("reject_count")) == 0
        and reconciliation.get("status") == "MATCHED"
    )


def compare_post_db_reconciliation(
    scenario: str | None,
    *,
    reconciliation: Mapping[str, object],
) -> OracleResult:
    """Compare committed DB controls with the canonical reconciliation."""

    if scenario is None:
        actual = dict(reconciliation)
        if not _internally_reconciled(reconciliation):
            raise Type01OracleMismatchError(
                "Unscored Type 01 file is not internally reconciled"
            )
        return OracleResult(
            matches=None,
            expected=None,
            actual=actual,
            oracle_status=INTERNALLY_RECONCILED_UNSCORED,
        )

    contract = _success_contract(scenario)
    expected = dict(contract.reconciliation)
    if set(reconciliation) != set(expected):
        raise Type01OracleMismatchError(
            "Type 01 PostgreSQL reconciliation has an unexpected shape"
        )
    actual = _reconciliation_actual(
        reconciliation,
        expected_keys=set(expected),
    )
    matches = actual == expected
    if not matches:
        raise Type01OracleMismatchError(
            "Type 01 PostgreSQL reconciliation does not match its "
            "approved oracle"
        )
    return OracleResult(
        matches=True,
        expected=expected,
        actual=actual,
        oracle_status=ORACLE_MATCHED,
    )


def compare_success(
    scenario: str | None,
    *,
    raw: PublishedRaw,
    load: LoadResult,
) -> OracleResult:
    """Compatibility composition for callers that already completed loading.

    New orchestration should call ``compare_sanitized_before_posting`` before
    loading and ``compare_post_db_reconciliation`` after loading.
    """

    pre_commit = compare_sanitized_before_posting(
        scenario,
        batch_id=raw.batch_id,
        java_result={
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "row_count": load.row_count,
            "net_amount": load.net_amount,
            "status": "succeeded",
        },
    )
    post_db = compare_post_db_reconciliation(
        scenario,
        reconciliation=load.reconciliation,
    )
    return OracleResult(
        matches=post_db.matches,
        expected=(
            None
            if scenario is None
            else {
                "sanitized": pre_commit.expected,
                "reconciliation": post_db.expected,
            }
        ),
        actual={
            "sanitized": pre_commit.actual,
            "reconciliation": post_db.actual,
        },
        oracle_status=post_db.oracle_status,
    )


def compare_rejection(
    scenario: str | None,
    *,
    batch_id: str,
    java_result: Mapping[str, object],
) -> OracleResult:
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
            raise Type01OracleMismatchError(
                "Unscored Type 01 rejection is incomplete"
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

    if scenario == "malformed":
        actual.update(
            {
                "source_record_number": _integer(
                    java_result.get("record_number")
                ),
                "transaction_id": java_result.get("transaction_id"),
            }
        )
        evaluated_fields = set(expected)
    elif scenario == "DF-SOURCE-001":
        actual.update(
            {
                "declared_detail_count": _integer(
                    java_result.get("declared_detail_count")
                ),
                "declared_net_amount": _money(
                    java_result.get("declared_net_amount")
                ),
                "computed_detail_count": _integer(
                    java_result.get("computed_detail_count")
                ),
                "computed_net_amount": _money(
                    java_result.get("computed_net_amount")
                ),
            }
        )
        # These two contract assertions need evidence outside a single Java
        # invocation: source ownership comes from topology/lineage, and
        # unrelated continuation is established by the multi-batch suite.
        evaluated_fields = set(expected) - {
            "source_system_role",
            "unrelated_batches_continue",
        }
    else:
        raise Type01OracleContractError(
            f"Unsupported Type 01 rejection scenario: {scenario!r}"
        )

    matches = (
        batch_id == expected["batch_id"]
        and all(actual.get(key) == expected[key] for key in evaluated_fields)
    )
    if not matches:
        raise Type01OracleMismatchError(
            "Type 01 rejection does not match its approved oracle"
        )
    return OracleResult(
        matches=True,
        expected={
            key: expected[key]
            for key in sorted(evaluated_fields)
        },
        actual={
            key: actual[key]
            for key in sorted(evaluated_fields)
        },
        oracle_status=ORACLE_MATCHED,
    )
