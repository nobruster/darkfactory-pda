#!/usr/bin/env python3
"""Attach golden-match to Type 02 modern observations. Does not edit the referee."""

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

CONTRACT = REPO_ROOT / "contracts" / "types" / "02-instant-payment-events" / "main"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

HAPPY_BATCH = "B202607230000101"
LIE_BATCH = "B202607230000105"
MALFORMED_BATCH = "B202607230000103"


def _money_fields(row: dict[str, Any]) -> dict[str, Any]:
    converted = dict(row)
    for key in (
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
    ):
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
            amount = row["amount_brl"]
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount))
            records.append({**row, "amount_brl": amount})
    return records


def _gold_row(batch_id: str) -> dict[str, Any] | None:
    if not DATABASE.is_file():
        return None
    con = duckdb.connect(str(DATABASE), read_only=True)
    try:
        result = con.execute(
            "select * from gold.gold_instant_payment_reconciliation where batch_id = ?",
            [batch_id],
        )
        columns = [item[0] for item in result.description]
        row = result.fetchone()
    except duckdb.Error:
        return None
    finally:
        con.close()
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
    comparison = golden_match.Comparison(HAPPY_BATCH, "02", "accepted")
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


def attach_rejection(
    batch_id: str,
    contract_file: str,
    outcome_class: str,
) -> golden_match.Comparison:
    modern = _parser_run(batch_id)
    contract = _load_yaml(CONTRACT / contract_file)
    comparison = golden_match.Comparison(batch_id, "02", outcome_class)
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
        batch_id=batch_id,
    )
    comparison.differences.extend(differences)
    comparison.checks.update(checks)
    comparison.checks["gold_absent"] = _gold_row(batch_id) is None
    landing_files = (
        list((LANDING / batch_id).glob("*.parquet")) if (LANDING / batch_id).exists() else []
    )
    comparison.checks["modern_produced_no_parquet"] = not landing_files and modern.get(
        "parquet_sha256"
    ) in (None, "")
    return comparison


def main() -> int:
    happy = attach_happy()
    lie = attach_rejection(
        LIE_BATCH, "expected-df-source-002-finding.yaml", "source-defect"
    )
    malformed = attach_rejection(
        MALFORMED_BATCH, "expected-malformed-rejection.yaml", "rejected"
    )
    _write(HAPPY_BATCH, "golden-match.json", happy.as_dict())
    _write(LIE_BATCH, "golden-match.json", lie.as_dict())
    _write(MALFORMED_BATCH, "golden-match.json", malformed.as_dict())
    _write(
        HAPPY_BATCH,
        "difference-adjudication.json",
        {
            "happy_resolved": happy.resolved,
            "lie_unexplained": len(lie.unexplained),
            "malformed_unexplained": len(malformed.unexplained),
        },
    )
    print(
        json.dumps(
            {
                "valid-minimal": happy.as_dict(),
                "df-source-002": lie.as_dict(),
                "malformed": malformed.as_dict(),
            },
            indent=2,
        )
    )
    if not happy.resolved:
        return 1
    if lie.unexplained or malformed.unexplained:
        return 1
    if "CONFIRMED_SOURCE_DEFECT" not in {
        item.classification for item in lie.differences
    }:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
