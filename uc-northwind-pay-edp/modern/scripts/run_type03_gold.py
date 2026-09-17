#!/usr/bin/env python3
"""Rebuild Type 03 Gold from landing: emit -> dlt register -> Bronze/Silver/Gold.

Type 01's registration/dbt project only knows the ``card_settlement`` grain,
and this leaf's write scope is exactly this file plus
``modern/validation/attach_type03.py`` -- so the dlt register step and the
Bronze/Silver/Gold build for Type 03 are self-contained here rather than
extending shared registration or dbt project files that are out of scope.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SRC = REPO_ROOT / "modern" / "ingestion" / "src"
PKG_DIR = INGEST_SRC / "northwind_pay" / "types" / "03-payment-slip-settlement"
MAIN_FIXTURES = REPO_ROOT / "contracts" / "types" / "03-payment-slip-settlement" / "main"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

sys.path.insert(0, str(INGEST_SRC))
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

LANDING_TABLE = "payment_slip_settlement"
LANDING_PREFIX = "NW_PAYMENT_SLIP"

# valid-minimal registers a live Gold row; df-source-003 is the source lie and
# must reach landing with zero Parquet, per the ingest leaf it depends on.
SCENARIOS = {
    "valid-minimal": MAIN_FIXTURES / "valid-minimal.rem",
    "df-source-003": MAIN_FIXTURES / "df-source-003.rem",
}


def _load_handler() -> ModuleType:
    path = PKG_DIR / "handler.py"
    spec = importlib.util.spec_from_file_location("nwp_t03_handler", path)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t03_handler"] = module
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
                "type_number": "03",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _emit_all(handler: ModuleType) -> dict[str, dict[str, object]]:
    outcomes: dict[str, dict[str, object]] = {}
    for name, raw_path in SCENARIOS.items():
        outcome = handler.process(raw_path, landing_root=LANDING)
        outcomes[name] = outcome.as_dict()
    return outcomes


def _landing_files() -> list[Path]:
    return sorted(
        path
        for path in LANDING.rglob("*.parquet")
        if path.name.startswith(LANDING_PREFIX)
        and not any(part.startswith(".") for part in path.relative_to(LANDING).parts)
    )


def _register_landing() -> int:
    import dlt
    import pyarrow.parquet as pq

    files = _landing_files()
    if not files:
        return 0

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ.setdefault("DLT_DATA_DIR", str(REPO_ROOT / ".runtime" / "dlt"))
    pipeline = dlt.pipeline(
        pipeline_name="northwind_modern_type03",
        destination=dlt.destinations.duckdb(str(DATABASE)),
        dataset_name="landing",
        progress=None,
    )

    def _batches():
        for path in files:
            yield pq.read_table(path)

    def _controls():
        for path in files:
            manifest_path = path.parent / "parquet-manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            yield {
                "batch_id": str(manifest["batch_id"]),
                "computed_logical_count": int(manifest["computed_logical_count"]),
                "computed_net_amount": str(manifest["computed_net_amount"]),
                "contract_code": str(manifest["contract_code"]),
                "currency": str(manifest.get("currency", "BRL")),
                "declared_logical_count": int(manifest["declared_logical_count"]),
                "declared_net_amount": str(manifest["declared_net_amount"]),
                "parquet_sha256": str(manifest["parquet_sha256"]),
                "raw_sha256": str(manifest["raw_sha256"]),
                "record_count": int(manifest["record_count"]),
                "source_file": str(manifest["source_file"]),
                "type_number": "03",
            }

    pipeline.run(_batches(), table_name=LANDING_TABLE, write_disposition="replace")
    pipeline.run(
        _controls(), table_name=f"{LANDING_TABLE}_control", write_disposition="replace"
    )
    return sum(pq.read_metadata(path).num_rows for path in files)


def _build_lakehouse() -> None:
    con = duckdb.connect(str(DATABASE))
    try:
        con.execute("create schema if not exists bronze")
        con.execute("create schema if not exists silver")
        con.execute("create schema if not exists gold")

        # Bronze: typed and source-aligned. Grain is (batch_id, source_record_number_a).
        con.execute(
            """
            create or replace table bronze.bronze_payment_slip_settlement as
            select
                batch_id,
                source_file,
                cast(source_record_number_a as integer) as source_record_number_a,
                cast(source_record_number_b as integer) as source_record_number_b,
                lot_number,
                sequence,
                settlement_id,
                payment_reference_token,
                payment_reference_last4,
                beneficiary_token,
                beneficiary_tax_id_type,
                beneficiary_tax_id_masked,
                bank_account_token,
                bank_account_last4,
                due_date,
                payment_date,
                cast(face_amount_brl as decimal(18, 2)) as face_amount_brl,
                cast(discount_brl as decimal(18, 2))    as discount_brl,
                cast(fee_brl as decimal(18, 2))          as fee_brl,
                cast(net_amount_brl as decimal(18, 2))   as net_amount_brl,
                status,
                bank_reference,
                client_reference
            from landing.payment_slip_settlement
            """
        )
        con.execute(
            """
            create or replace table bronze.bronze_payment_slip_settlement_control as
            select * from landing.payment_slip_settlement_control
            """
        )

        # Silver: conformed entity at the same grain as Bronze. Changes no money.
        con.execute(
            """
            create or replace table silver.silver_payment_slip_settlement as
            select * from bronze.bronze_payment_slip_settlement
            """
        )

        # Gold: governed reconciliation, one row per batch. source_* is the
        # declaration, staged_* is Bronze, applied_* is Silver. Legacy state is
        # never an input here -- attach_type03.py brings that in as observation.
        con.execute(
            """
            create or replace table gold.gold_payment_slip_settlement_reconciliation as
            with control as (
                select * from bronze.bronze_payment_slip_settlement_control
            ),
            staged as (
                select
                    batch_id,
                    count(*)                            as staged_count,
                    coalesce(sum(net_amount_brl), 0.00) as staged_net_amount
                from bronze.bronze_payment_slip_settlement
                group by batch_id
            ),
            applied as (
                select
                    batch_id,
                    count(*)                            as applied_count,
                    coalesce(sum(net_amount_brl), 0.00) as applied_net_amount
                from silver.silver_payment_slip_settlement
                group by batch_id
            )
            select
                control.batch_id,
                control.currency,
                control.declared_logical_count                                as source_count,
                staged.staged_count,
                applied.applied_count,
                cast(control.declared_net_amount as decimal(18, 2))           as source_net_amount,
                cast(staged.staged_net_amount as decimal(18, 2))              as staged_net_amount,
                cast(applied.applied_net_amount as decimal(18, 2))           as applied_net_amount,
                applied.applied_count - control.declared_logical_count        as count_delta,
                cast(
                    applied.applied_net_amount
                    - cast(control.declared_net_amount as decimal(18, 2))
                    as decimal(18, 2)
                )                                                            as amount_delta,
                0                                                             as reject_count,
                case
                    when applied.applied_count = control.declared_logical_count
                     and applied.applied_net_amount = cast(control.declared_net_amount as decimal(18, 2))
                     and staged.staged_count = control.declared_logical_count
                     and staged.staged_net_amount = cast(control.declared_net_amount as decimal(18, 2))
                    then 'MATCHED'
                    else 'MISMATCHED'
                end                                                          as status
            from control
            join staged  on staged.batch_id  = control.batch_id
            join applied on applied.batch_id = control.batch_id
            """
        )
    finally:
        con.close()


def main() -> int:
    handler = _load_handler()
    outcomes = _emit_all(handler)
    for outcome in outcomes.values():
        _write_outcome(outcome)

    row_count = _register_landing()
    _build_lakehouse()
    print(json.dumps({"dlt_rows": row_count, "emit": list(outcomes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
