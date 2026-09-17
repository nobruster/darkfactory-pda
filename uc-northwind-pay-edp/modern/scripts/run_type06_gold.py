#!/usr/bin/env python3
"""Rebuild Type 06 Gold from spec samples: emit → dlt register → dbt Bronze/Silver/Gold."""

from __future__ import annotations

import importlib.util
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
SAMPLES = REPO_ROOT / "spec" / "type-06-merchant-chargeback" / "samples"
HANDLER = (
    REPO_ROOT
    / "modern"
    / "ingestion"
    / "src"
    / "northwind_pay"
    / "types"
    / "06-merchant-chargeback"
    / "handler.py"
)

sys.path.insert(0, str(INGEST_SRC))
sys.path.insert(0, str(DLT_DIR))
os.environ["NWP_MODERN_DUCKDB"] = str(DATABASE)

SCENARIOS = ("valid-minimal", "valid-boundary", "malformed")


def _load_handler():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("nwp_t06_handler_run", HANDLER)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t06_handler_run"] = module
    spec.loader.exec_module(module)
    return module


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
                "type_number": "06",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    from registration import register

    handler = _load_handler()
    outcomes: dict[str, dict[str, object]] = {}
    for scenario in SCENARIOS:
        raw = SAMPLES / f"{scenario}.csv"
        outcome = handler.process(raw, landing_root=LANDING).as_dict()
        outcomes[scenario] = outcome
        _write_outcome(outcome)

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    result = register("06", landing_root=LANDING, database=DATABASE)
    happy = outcomes["valid-minimal"]["batch_id"]
    (EVIDENCE / str(happy)).mkdir(parents=True, exist_ok=True)
    (EVIDENCE / str(happy) / "dlt-load.json").write_text(
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
        [dbt_bin, "run", "--project-dir", str(DBT_DIR), "--select", "tag:type_06"],
        cwd=REPO_ROOT,
        env=env,
    )
    subprocess.check_call(
        [dbt_bin, "test", "--project-dir", str(DBT_DIR), "--select", "tag:type_06"],
        cwd=REPO_ROOT,
        env=env,
    )
    print(json.dumps({"dlt": result.row_count, "emit": list(outcomes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
