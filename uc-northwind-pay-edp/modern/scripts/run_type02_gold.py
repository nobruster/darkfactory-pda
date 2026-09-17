#!/usr/bin/env python3
"""Rebuild Type 02 Gold from landing: emit → dlt register → Bronze/Silver/Gold.

Same lane as Type 01 (`run_type01_gold.py`): dlt registers the landing
Parquet the ingest leaf already published, Bronze/Silver/Gold are built at
the documented grain (``contracts/types/02-instant-payment-events/reconciliation.yaml``),
and the referee is attached separately (``validation/attach_type02.py``). No
new grain is invented here — ADR 0009 stays Type 01 only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SRC = REPO_ROOT / "modern" / "ingestion" / "src"
HANDLER_PATH = (
    INGEST_SRC / "northwind_pay" / "types" / "02-instant-payment-events" / "handler.py"
)
CONTRACT_MAIN = REPO_ROOT / "contracts" / "types" / "02-instant-payment-events" / "main"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

SCENARIOS = {
    "valid-minimal": CONTRACT_MAIN / "valid-minimal.txt",
    "df-source-002": CONTRACT_MAIN / "df-source-002.txt",
    "malformed": CONTRACT_MAIN / "malformed.txt",
}

sys.path.insert(0, str(INGEST_SRC))

os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
os.environ["NWP_MODERN_DUCKDB"] = str(DATABASE)


def _load_handler():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("nwp_t02_handler", HANDLER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t02_handler"] = module
    spec.loader.exec_module(module)
    return module


def _emit_all() -> dict[str, dict[str, object]]:
    handler = _load_handler()
    outcomes: dict[str, dict[str, object]] = {}
    for name, raw_path in SCENARIOS.items():
        outcome = handler.process(raw_path, landing_root=LANDING)
        outcomes[name] = outcome.as_dict()
    return outcomes


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
                "type_number": "02",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _landing_parquet_files() -> list[Path]:
    return sorted(
        path
        for path in LANDING.rglob("NW_INSTANT_PAYMENT_*.parquet")
        if not any(part.startswith(".") for part in path.relative_to(LANDING).parts)
    )


def _batch_controls(files: list[Path]) -> list[dict[str, object]]:
    controls: list[dict[str, object]] = []
    for path in files:
        manifest_path = path.parent / "parquet-manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        controls.append(
            {
                "batch_id": str(manifest["batch_id"]),
                "computed_credit_amount": str(manifest["computed_credit_amount"]),
                "computed_debit_amount": str(manifest["computed_debit_amount"]),
                "computed_event_count": int(manifest["computed_event_count"]),
                "computed_net_amount": str(manifest["computed_net_amount"]),
                "contract_code": str(manifest["contract_code"]),
                "currency": str(manifest.get("currency", "BRL")),
                "declared_credit_amount": str(manifest["declared_credit_amount"]),
                "declared_debit_amount": str(manifest["declared_debit_amount"]),
                "declared_event_count": int(manifest["declared_event_count"]),
                "declared_net_amount": str(manifest["declared_net_amount"]),
                "parquet_sha256": str(manifest["parquet_sha256"]),
                "raw_sha256": str(manifest["raw_sha256"]),
                "record_count": int(manifest["record_count"]),
                "source_file": str(manifest["source_file"]),
                "type_number": "02",
            }
        )
    return controls


def _register(files: list[Path]) -> dict[str, object]:
    """dlt boundary: register published landing Parquet. Never re-parse raw."""

    import dlt
    import pyarrow.parquet as pq

    table = "instant_payment_event"
    if not files:
        return {"load_id": "", "row_count": 0, "table": table, "parquet_files": []}

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ.setdefault("DLT_DATA_DIR", str(REPO_ROOT / ".runtime" / "dlt"))
    pipeline = dlt.pipeline(
        pipeline_name="northwind_modern_type02",
        destination=dlt.destinations.duckdb(str(DATABASE)),
        dataset_name="landing",
        progress=None,
    )
    info = pipeline.run(
        (pq.read_table(path) for path in files),
        table_name=table,
        write_disposition="replace",
    )
    pipeline.run(
        _batch_controls(files),
        table_name=f"{table}_control",
        write_disposition="replace",
    )
    load_ids = getattr(info, "loads_ids", None) or [""]
    row_count = sum(pq.read_metadata(path).num_rows for path in files)
    return {
        "load_id": str(load_ids[-1]),
        "row_count": row_count,
        "table": table,
        "parquet_files": [path.name for path in files],
    }


def _build_bronze_silver_gold() -> None:
    """Bronze → Silver → Gold at the documented grain. No new Type 02 dimension."""

    import duckdb

    con = duckdb.connect(str(DATABASE))
    try:
        con.execute("create schema if not exists bronze")
        con.execute("create schema if not exists silver")
        con.execute("create schema if not exists gold")

        con.execute(
            """
            create or replace table bronze.bronze_instant_payment_event as
            select
                batch_id,
                source_file,
                cast(source_record_number as integer) as source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                cast(amount_brl as decimal(18, 2)) as amount_brl,
                direction,
                status,
                return_code,
                description
            from landing.instant_payment_event
            """
        )
        con.execute(
            """
            create or replace table bronze.bronze_instant_payment_event_control as
            select * from landing.instant_payment_event_control
            """
        )

        con.execute(
            """
            create or replace table silver.silver_instant_payment_event as
            select
                batch_id,
                source_record_number,
                end_to_end_id,
                transaction_id,
                payer_document_token,
                payer_document_masked,
                payee_document_token,
                payee_document_masked,
                event_timestamp,
                amount_brl,
                direction,
                case direction
                    when 'C' then 'CREDIT'
                    when 'D' then 'DEBIT'
                end as direction_label,
                status,
                return_code,
                description,
                source_file
            from bronze.bronze_instant_payment_event
            """
        )

        con.execute(
            """
            create or replace table gold.gold_instant_payment_reconciliation as
            with control as (
                select * from bronze.bronze_instant_payment_event_control
            ),
            staged as (
                select
                    batch_id,
                    count(*) as staged_count,
                    coalesce(sum(amount_brl) filter (where direction = 'C'), 0.00) as staged_credit_amount,
                    coalesce(sum(abs(amount_brl)) filter (where direction = 'D'), 0.00) as staged_debit_amount,
                    coalesce(sum(amount_brl), 0.00) as staged_net_amount,
                    count(*) filter (where status = 'RETURNED') as staged_returned_count
                from bronze.bronze_instant_payment_event
                group by batch_id
            ),
            applied as (
                select
                    batch_id,
                    count(*) as applied_count,
                    coalesce(sum(amount_brl) filter (where direction = 'C'), 0.00) as applied_credit_amount,
                    coalesce(sum(abs(amount_brl)) filter (where direction = 'D'), 0.00) as applied_debit_amount,
                    coalesce(sum(amount_brl), 0.00) as applied_net_amount,
                    count(*) filter (where status = 'RETURNED') as applied_returned_count
                from silver.silver_instant_payment_event
                group by batch_id
            )
            select
                control.batch_id,
                control.currency,
                control.declared_event_count as source_count,
                staged.staged_count,
                applied.applied_count,
                cast(control.declared_credit_amount as decimal(18, 2)) as source_credit_amount,
                cast(staged.staged_credit_amount as decimal(18, 2)) as staged_credit_amount,
                cast(applied.applied_credit_amount as decimal(18, 2)) as applied_credit_amount,
                cast(control.declared_debit_amount as decimal(18, 2)) as source_debit_amount,
                cast(staged.staged_debit_amount as decimal(18, 2)) as staged_debit_amount,
                cast(applied.applied_debit_amount as decimal(18, 2)) as applied_debit_amount,
                cast(control.declared_net_amount as decimal(18, 2)) as source_net_amount,
                cast(staged.staged_net_amount as decimal(18, 2)) as staged_net_amount,
                cast(applied.applied_net_amount as decimal(18, 2)) as applied_net_amount,
                staged.staged_returned_count as source_returned_count,
                staged.staged_returned_count,
                applied.applied_returned_count,
                applied.applied_count - control.declared_event_count as count_delta,
                cast(
                    applied.applied_credit_amount - cast(control.declared_credit_amount as decimal(18, 2))
                    as decimal(18, 2)
                ) as credit_amount_delta,
                cast(
                    applied.applied_debit_amount - cast(control.declared_debit_amount as decimal(18, 2))
                    as decimal(18, 2)
                ) as debit_amount_delta,
                cast(
                    applied.applied_net_amount - cast(control.declared_net_amount as decimal(18, 2))
                    as decimal(18, 2)
                ) as net_amount_delta,
                applied.applied_returned_count - staged.staged_returned_count as returned_count_delta,
                0 as reject_count,
                case
                    when applied.applied_count = control.declared_event_count
                     and applied.applied_credit_amount = cast(control.declared_credit_amount as decimal(18, 2))
                     and applied.applied_debit_amount = cast(control.declared_debit_amount as decimal(18, 2))
                     and applied.applied_net_amount = cast(control.declared_net_amount as decimal(18, 2))
                     and staged.staged_count = control.declared_event_count
                     and staged.staged_credit_amount = cast(control.declared_credit_amount as decimal(18, 2))
                     and staged.staged_debit_amount = cast(control.declared_debit_amount as decimal(18, 2))
                     and staged.staged_net_amount = cast(control.declared_net_amount as decimal(18, 2))
                    then 'MATCHED'
                    else 'MISMATCHED'
                end as status
            from control
            join staged on staged.batch_id = control.batch_id
            join applied on applied.batch_id = control.batch_id
            """
        )
    finally:
        con.close()


def main() -> int:
    outcomes = _emit_all()
    for outcome in outcomes.values():
        _write_outcome(outcome)

    files = _landing_parquet_files()
    registration = _register(files)

    happy_batch = outcomes["valid-minimal"]["batch_id"]
    (EVIDENCE / str(happy_batch)).mkdir(mode=0o700, parents=True, exist_ok=True)
    (EVIDENCE / str(happy_batch) / "dlt-load.json").write_text(
        json.dumps(registration, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _build_bronze_silver_gold()

    print(json.dumps({"dlt": registration["row_count"], "emit": list(outcomes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
