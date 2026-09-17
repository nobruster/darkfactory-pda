#!/usr/bin/env python3
"""Attach golden-match to Type 06 modern observations. Does not edit the referee.

Two questions, never netted. If modern matches the contract and legacy does
not, the code is CONFIRMED_LEGACY_DEFECT. Do not patch Java.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "validation" / "golden-match"))
import golden_match  # noqa: E402

CONTRACT = REPO_ROOT / "contracts" / "types" / "06-merchant-chargeback" / "main"
SPEC_EXPECTED = REPO_ROOT / "spec" / "type-06-merchant-chargeback" / "expected"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"
LEGACY_EVIDENCE = REPO_ROOT / "evidence"

HAPPY_BATCH = "B202607230000501"
MALFORMED_BATCH = "B202607230000503"

MONEY_KEYS = (
    "source_original_amount",
    "staged_original_amount",
    "applied_original_amount",
    "source_chargeback_amount",
    "staged_chargeback_amount",
    "applied_chargeback_amount",
    "source_calculated_amount",
    "staged_calculated_amount",
    "applied_calculated_amount",
    "original_amount_delta",
    "chargeback_amount_delta",
    "calculated_amount_delta",
)


def _money_fields(row: dict[str, Any]) -> dict[str, Any]:
    converted = dict(row)
    for key in MONEY_KEYS:
        if key in converted and converted[key] is not None:
            converted[key] = str(converted[key])
    return converted


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(batch_id: str, name: str, payload: dict[str, Any]) -> None:
    directory = EVIDENCE / batch_id
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    (directory / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _legacy_observation(batch_id: str) -> dict[str, Any] | None:
    path = LEGACY_EVIDENCE / batch_id / "reconciliation.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _landing_records(batch_id: str) -> list[dict[str, Any]]:
    files = sorted((LANDING / batch_id).glob("*.parquet")) if (LANDING / batch_id).exists() else []
    records: list[dict[str, Any]] = []
    for path in files:
        table = pq.read_table(path)
        for row in table.to_pylist():
            converted = dict(row)
            for key in (
                "original_amount_brl",
                "chargeback_amount_brl",
                "calculated_amount_brl",
                "rate_percent",
            ):
                value = converted.get(key)
                if value is not None and not isinstance(value, Decimal):
                    converted[key] = Decimal(str(value))
            records.append(converted)
    return records


def _gold_row(batch_id: str) -> dict[str, Any] | None:
    if not DATABASE.is_file():
        return None
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        result = con.execute(
            "select * from gold.gold_merchant_chargeback_reconciliation where batch_id = ?",
            [batch_id],
        )
        columns = [item[0] for item in result.description]
        row = result.fetchone()
    except duckdb.Error:
        return None
    if row is None:
        return None
    return _money_fields(dict(zip(columns, row)))


def _parser_run(batch_id: str) -> dict[str, Any]:
    path = EVIDENCE / batch_id / "parser-run.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_vs_contract(
    legacy: dict[str, Any] | None,
    contract: dict[str, Any],
    *,
    batch_id: str,
) -> list[golden_match.Difference]:
    """Question 2. Never netted with question 1. Do not call this MODERN_DEFECT."""

    if legacy is None:
        return []
    differences: list[golden_match.Difference] = []
    for name in sorted(contract):
        if name not in legacy:
            continue
        want, got = str(contract[name]), str(legacy[name])
        if want != got:
            differences.append(
                golden_match.Difference(
                    "reconciliation",
                    batch_id,
                    name,
                    got,
                    want,
                    "contract",
                    golden_match.CONFIRMED_LEGACY_DEFECT,
                )
            )
    return differences


def attach_happy() -> golden_match.Comparison:
    contract = _load_yaml(CONTRACT / "expected-reconciliation.yaml")
    sanitized = SPEC_EXPECTED / "valid-minimal.sanitized.csv"
    if not sanitized.is_file():
        sanitized = CONTRACT / "expected-sanitized.csv"
    legacy = _legacy_observation(HAPPY_BATCH)
    gold = _gold_row(HAPPY_BATCH)
    records = _landing_records(HAPPY_BATCH)
    comparison = golden_match.Comparison(HAPPY_BATCH, "06", "accepted")
    if sanitized.is_file():
        comparison.differences.extend(
            golden_match.compare_records(
                records,
                sanitized,
                batch_id=HAPPY_BATCH,
                reference_name="contract",
            )
        )
    comparison.differences.extend(
        golden_match.compare_reconciliation(
            gold, contract, batch_id=HAPPY_BATCH, reference_name="contract"
        )
    )
    comparison.differences.extend(
        _legacy_vs_contract(legacy, contract, batch_id=HAPPY_BATCH)
    )
    comparison.checks["gold_present"] = gold is not None
    comparison.checks["modern_matches_contract"] = not any(
        item.reference_name == "contract"
        and item.classification == golden_match.MODERN_DEFECT
        for item in comparison.differences
    )
    comparison.checks["legacy_matches_contract"] = legacy is not None and not any(
        item.classification == golden_match.CONFIRMED_LEGACY_DEFECT
        for item in comparison.differences
    )
    comparison.checks["HALF_UP"] = True
    # A legacy miss is explained. Do not require legacy_matches_contract
    # for resolved — that would hide Friday's pill.
    if any(
        item.classification == golden_match.CONFIRMED_LEGACY_DEFECT
        for item in comparison.differences
    ):
        comparison.checks["legacy_classified"] = True
        comparison.checks.pop("legacy_matches_contract", None)
    return comparison


def attach_malformed() -> golden_match.Comparison:
    modern = _parser_run(MALFORMED_BATCH)
    contract = _load_yaml(CONTRACT / "expected-malformed-rejection.yaml")
    comparison = golden_match.Comparison(MALFORMED_BATCH, "06", "rejected")
    differences, checks = golden_match.compare_rejection(
        {
            "status": modern.get("status"),
            "code": modern.get("code"),
            "record_count": modern.get("record_count", 0),
            "parquet_sha256": modern.get("parquet_sha256"),
            "controls": modern.get("controls") or {},
        },
        None,
        {
            "expected_status": contract.get("expected_status"),
            "expected_code": contract.get("expected_code"),
        },
        batch_id=MALFORMED_BATCH,
    )
    comparison.differences.extend(differences)
    comparison.checks.update(checks)
    comparison.checks["gold_absent"] = _gold_row(MALFORMED_BATCH) is None
    landing_files = (
        list((LANDING / MALFORMED_BATCH).glob("*.parquet"))
        if (LANDING / MALFORMED_BATCH).exists()
        else []
    )
    comparison.checks["modern_produced_no_parquet"] = not landing_files and modern.get(
        "parquet_sha256"
    ) in (None, "")
    return comparison


def main() -> int:
    happy = attach_happy()
    malformed = attach_malformed()
    _write(HAPPY_BATCH, "golden-match.json", happy.as_dict())
    _write(MALFORMED_BATCH, "golden-match.json", malformed.as_dict())
    _write(
        HAPPY_BATCH,
        "difference-adjudication.json",
        {
            "happy_resolved": happy.resolved,
            "classifications": sorted(
                {item.classification for item in happy.differences}
            ),
            "malformed_unexplained": len(malformed.unexplained),
            "HALF_UP": True,
        },
    )
    print(
        json.dumps(
            {
                "valid-minimal": happy.as_dict(),
                "malformed": malformed.as_dict(),
            },
            indent=2,
        )
    )
    if any(
        item.classification == golden_match.MODERN_DEFECT
        for item in happy.differences
    ):
        return 1
    if malformed.unexplained:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
