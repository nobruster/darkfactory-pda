#!/usr/bin/env python3
"""One callable step per plant stage, so the CLI and Dagster share one implementation.

The plant owns the logic. Dagster calls these steps; it never imports the parser.
Run with modern/.venv (pyarrow 25 — the interpreter that wrote landing).
"""

from __future__ import annotations

import argparse
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


def step_emit() -> dict:
    from northwind_pay.emit import emit_all

    outcomes = emit_all(LANDING)
    for outcome in outcomes.values():
        batch = str(outcome["batch_id"])
        directory = EVIDENCE / batch
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        (directory / "parser-run.json").write_text(
            json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (directory / "final-status.json").write_text(
            json.dumps(
                {
                    "batch_id": batch,
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
    return {"scenarios": sorted(outcomes), "published": [
        str(o["batch_id"]) for o in outcomes.values() if o.get("stage") == "published"
    ]}


def step_register() -> dict:
    from registration import register

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = register("01", landing_root=LANDING, database=DATABASE)
    directory = EVIDENCE / "B202607230000001"
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "load_id": result.load_id,
        "parquet_files": list(result.parquet_files),
        "row_count": result.row_count,
        "table": result.table,
    }
    (directory / "dlt-load.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def step_build() -> dict:
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(DBT_DIR)
    env["NWP_MODERN_DUCKDB"] = str(DATABASE)
    dbt = Path(sys.executable).parent / "dbt"
    dbt_bin = str(dbt if dbt.exists() else "dbt")
    for command in ("run", "test"):
        # dbt logs go to stderr so stdout stays a clean JSON contract for callers.
        subprocess.run(
            [dbt_bin, command, "--project-dir", str(DBT_DIR), "--select", "tag:type_01"],
            cwd=REPO_ROOT,
            env=env,
            stdout=sys.stderr,
            check=True,
        )
    return {"dbt": ["run", "test"], "select": "tag:type_01"}


STEPS = {"emit": step_emit, "register": step_register, "build": step_build}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one plant step.")
    ap.add_argument("step", choices=sorted(STEPS))
    args = ap.parse_args()
    print(json.dumps(STEPS[args.step](), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
