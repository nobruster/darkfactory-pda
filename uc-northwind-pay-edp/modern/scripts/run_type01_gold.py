#!/usr/bin/env python3
"""Rebuild Type 01 Gold from landing: emit → dlt register → dbt Bronze/Silver/Gold."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SRC = REPO_ROOT / "modern" / "ingestion" / "src"
DLT_DIR = REPO_ROOT / "modern" / "lakehouse" / "dlt"
DBT_DIR = REPO_ROOT / "modern" / "dbt"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

sys.path.insert(0, str(INGEST_SRC))
sys.path.insert(0, str(DLT_DIR))

os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
os.environ["NWP_MODERN_DUCKDB"] = str(DATABASE)


def _write_outcome(outcome: dict[str, object]) -> None:
    batch_id = str(outcome["batch_id"])
    directory = EVIDENCE / batch_id
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    (directory / "parser-run.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (directory / "final-status.json").write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "code": outcome.get("code"),
                "record_count": outcome.get("record_count"),
                "status": outcome.get("status"),
                "type_number": "01",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    from northwind_pay.emit import emit_all
    from registration import register

    outcomes = emit_all(LANDING)
    for outcome in outcomes.values():
        _write_outcome(outcome)

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = register("01", landing_root=LANDING, database=DATABASE)
    (EVIDENCE / "B202607230000001").mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "B202607230000001" / "dlt-load.json").write_text(
        json.dumps(
            {
                "load_id": result.load_id,
                "parquet_files": list(result.parquet_files),
                "row_count": result.row_count,
                "table": result.table,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(DBT_DIR)
    env["NWP_MODERN_DUCKDB"] = str(DATABASE)
    dbt = Path(sys.executable).parent / "dbt"
    dbt_bin = str(dbt if dbt.exists() else "dbt")
    subprocess.check_call(
        [dbt_bin, "run", "--project-dir", str(DBT_DIR), "--select", "tag:type_01"],
        cwd=REPO_ROOT,
        env=env,
    )
    subprocess.check_call(
        [dbt_bin, "test", "--project-dir", str(DBT_DIR), "--select", "tag:type_01"],
        cwd=REPO_ROOT,
        env=env,
    )
    print(json.dumps({"dlt": result.row_count, "emit": list(outcomes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
