#!/usr/bin/env python3
"""Attach golden-match to Type 05 modern observations. Does not edit the referee."""

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

CONTRACT = REPO_ROOT / "contracts" / "types" / "05-merchant-fee-assessment" / "main"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

HAPPY_BATCH = "B202607230000401"
DF_SOURCE_005_BATCH = "B202607230000405"

MONEY_FIELDS = (
    "source_gross_amount",
    "staged_gross_amount",
    "applied_gross_amount",
    "source_assessed_fee",
    "staged_assessed_fee",
    "applied_assessed_fee",
    "source_calculated_fee",
    "staged_calculated_fee",
    "applied_calculated_fee",
    "gross_amount_delta",
    "assessed_fee_delta",
    "calculated_fee_delta",
    "assessment_calculation_delta",
)


def _money_fields(row: dict[str, Any]) -> dict[str, Any]:
    converted = dict(row)
    for key in MONEY_FIELDS:
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


def _landing_records(batch_id: str) -> list[dict[str, Any]]:
    files = sorted((LANDING / batch_id).glob("*.parquet")) if (LANDING / batch_id).exists() else []
    records: list[dict[str, Any]] = []
    for path in files:
        table = pq.read_table(path)
        for row in table.to_pylist():
            converted = dict(row)
            for key in ("gross_amount_brl", "rate_percent", "assessed_fee_brl", "calculated_fee_brl"):
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
            "select * from gold.gold_merchant_fee_assessment_reconciliation "
            "where batch_id = ?",
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


def attach_happy() -> golden_match.Comparison:
    contract = _load_yaml(CONTRACT / "expected-reconciliation.yaml")
    gold = _gold_row(HAPPY_BATCH)
    records = _landing_records(HAPPY_BATCH)
    comparison = golden_match.Comparison(HAPPY_BATCH, "05", "accepted")
    comparison.differences.extend(
        golden_match.compare_records(
            records,
            CONTRACT / "expected-sanitized.csv",
            batch_id=HAPPY_BATCH,
            reference_name="contract",
        )
    )
    comparison.differences.extend(
        golden_match.compare_reconciliation(
            gold, contract, batch_id=HAPPY_BATCH, reference_name="contract"
        )
    )
    comparison.checks["gold_present"] = gold is not None
    comparison.checks["contract_reconciliation"] = not any(
        item.reference_name == "contract" and item.scope == "reconciliation"
        for item in comparison.differences
    )
    comparison.checks["records_match_contract"] = not any(
        item.scope == "record" for item in comparison.differences
    )
    return comparison


def attach_df_source_005() -> golden_match.Comparison:
    modern = _parser_run(DF_SOURCE_005_BATCH)
    contract = _load_yaml(CONTRACT / "expected-df-source-005-finding.yaml")
    comparison = golden_match.Comparison(DF_SOURCE_005_BATCH, "05", "source-defect")
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
        batch_id=DF_SOURCE_005_BATCH,
    )
    comparison.differences.extend(differences)
    comparison.checks.update(checks)
    comparison.checks["gold_absent"] = _gold_row(DF_SOURCE_005_BATCH) is None
    landing_dir = LANDING / DF_SOURCE_005_BATCH
    landing_files = list(landing_dir.glob("*.parquet")) if landing_dir.exists() else []
    comparison.checks["modern_produced_no_parquet"] = (
        not landing_files and modern.get("parquet_sha256") in (None, "")
    )
    return comparison


def main() -> int:
    happy = attach_happy()
    lie = attach_df_source_005()
    _write(HAPPY_BATCH, "golden-match.json", happy.as_dict())
    _write(DF_SOURCE_005_BATCH, "golden-match.json", lie.as_dict())
    _write(
        HAPPY_BATCH,
        "difference-adjudication.json",
        {
            "happy_resolved": happy.resolved,
            "df_source_005_unexplained": len(lie.unexplained),
        },
    )
    print(
        json.dumps(
            {"valid-minimal": happy.as_dict(), "df-source-005": lie.as_dict()},
            indent=2,
        )
    )
    if not happy.resolved:
        return 1
    if lie.unexplained:
        return 1
    if golden_match.CONFIRMED_SOURCE_DEFECT not in {
        item.classification for item in lie.differences
    }:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
