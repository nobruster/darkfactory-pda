#!/usr/bin/env python3
"""Rebuild Type 04 Gold from landing: emit -> dlt register -> Bronze/Silver/Gold.

Type 01's registration/dbt project only knows the ``card_settlement`` grain,
and this leaf's write scope is exactly this file plus
``modern/validation/attach_type04.py`` -- so the dlt register step and the
Bronze/Silver/Gold build for Type 04 are self-contained here rather than
extending shared registration or dbt project files that are out of scope.

Type 04's landing manifest (published by the out-of-scope ``handler.py``)
only carries ``transfer_count``/``net_amount`` controls, not the full
transfer/return/gross/net split the reconciliation grain needs. That split
is read from the in-process ``BatchOutcome.controls`` this script's own
``_emit_all`` call produces, rather than re-parsed from the narrower
manifest on disk.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_SRC = REPO_ROOT / "modern" / "ingestion" / "src"
PKG_DIR = INGEST_SRC / "northwind_pay" / "types" / "04-ted-transfer-settlement"
MAIN_FIXTURES = REPO_ROOT / "contracts" / "types" / "04-ted-transfer-settlement" / "main"
LANDING = REPO_ROOT / "modern" / "landing"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
EVIDENCE = REPO_ROOT / "evidence" / "modern"

sys.path.insert(0, str(INGEST_SRC))
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
os.environ.setdefault(
    "NWP_TED_ACCOUNT_TOKEN_KEY", "northwind-pay-edp-fixture-ted-account-key-v1"
)

LANDING_TABLE = "ted_transfer_movement"
LANDING_PREFIX = "NW_TED_SETTLEMENT"

# valid-minimal registers a live Gold row; df-source-004 is the source lie and
# must reach landing with zero Parquet, per the ingest leaf it depends on.
SCENARIOS = {
    "valid-minimal": MAIN_FIXTURES / "valid-minimal.dat",
    "df-source-004": MAIN_FIXTURES / "df-source-004.dat",
}


def _load_handler() -> ModuleType:
    path = PKG_DIR / "handler.py"
    spec = importlib.util.spec_from_file_location("nwp_t04_handler", path)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t04_handler"] = module
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
                "type_number": "04",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _emit_all(handler: ModuleType) -> dict[str, dict[str, Any]]:
    outcomes: dict[str, dict[str, Any]] = {}
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


def _register_landing(outcomes: dict[str, dict[str, Any]]) -> int:
    import dlt
    import pyarrow.parquet as pq

    files = _landing_files()
    if not files:
        return 0

    DATABASE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ.setdefault("DLT_DATA_DIR", str(REPO_ROOT / ".runtime" / "dlt"))
    pipeline = dlt.pipeline(
        pipeline_name="northwind_modern_type04",
        destination=dlt.destinations.duckdb(str(DATABASE)),
        dataset_name="landing",
        progress=None,
    )

    def _batches():
        for path in files:
            yield pq.read_table(path)

    succeeded = {
        outcome["batch_id"]: outcome["controls"]
        for outcome in outcomes.values()
        if outcome.get("status") == "succeeded"
    }

    def _controls():
        for batch_id, controls in succeeded.items():
            yield {
                "batch_id": batch_id,
                "currency": "BRL",
                "declared_transfer_count": int(controls["declared_transfer_count"]),
                "computed_transfer_count": int(controls["computed_transfer_count"]),
                "declared_return_count": int(controls["declared_return_count"]),
                "computed_return_count": int(controls["computed_return_count"]),
                "declared_gross_amount": str(controls["declared_gross_amount"]),
                "computed_gross_amount": str(controls["computed_gross_amount"]),
                "declared_returned_amount": str(controls["declared_returned_amount"]),
                "computed_returned_amount": str(controls["computed_returned_amount"]),
                "declared_net_amount": str(controls["declared_net_amount"]),
                "computed_net_amount": str(controls["computed_net_amount"]),
                "type_number": "04",
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

        # Bronze: typed and source-aligned. Grain is (batch_id, source_record_number).
        con.execute(
            """
            create or replace table bronze.bronze_ted_transfer_movement as
            select
                batch_id,
                source_file,
                cast(source_record_number as integer) as source_record_number,
                movement_id,
                original_transfer_id,
                movement_kind,
                movement_ts,
                cast(amount_brl as decimal(18, 2)) as amount_brl,
                payer_account_token,
                payer_tax_id_masked,
                beneficiary_account_token,
                beneficiary_tax_id_masked,
                beneficiary_ispb,
                purpose_code,
                status_code,
                return_reason_code
            from landing.ted_transfer_movement
            """
        )
        con.execute(
            """
            create or replace table bronze.bronze_ted_transfer_movement_control as
            select * from landing.ted_transfer_movement_control
            """
        )

        # Silver: conformed entity at the same grain as Bronze. Changes no money.
        con.execute(
            """
            create or replace table silver.silver_ted_transfer_movement as
            select * from bronze.bronze_ted_transfer_movement
            """
        )

        # Gold: governed reconciliation, one row per batch, transfer/return
        # split. source_* is the declaration, staged_* is Bronze, applied_* is
        # Silver. Legacy state is never an input here -- attach_type04.py
        # brings that in as observation.
        con.execute(
            """
            create or replace table gold.gold_ted_transfer_settlement_reconciliation as
            with control as (
                select * from bronze.bronze_ted_transfer_movement_control
            ),
            staged as (
                select
                    batch_id,
                    sum(case when movement_kind = 'TRANSFER' then 1 else 0 end)          as staged_transfer_count,
                    sum(case when movement_kind = 'RETURN' then 1 else 0 end)            as staged_return_count,
                    coalesce(sum(case when movement_kind = 'TRANSFER' then amount_brl end), 0.00) as staged_gross_amount,
                    coalesce(sum(case when movement_kind = 'RETURN' then amount_brl end), 0.00)   as staged_return_amount
                from bronze.bronze_ted_transfer_movement
                group by batch_id
            ),
            applied as (
                select
                    batch_id,
                    sum(case when movement_kind = 'TRANSFER' then 1 else 0 end)          as applied_transfer_count,
                    sum(case when movement_kind = 'RETURN' then 1 else 0 end)            as applied_return_count,
                    coalesce(sum(case when movement_kind = 'TRANSFER' then amount_brl end), 0.00) as applied_gross_amount,
                    coalesce(sum(case when movement_kind = 'RETURN' then amount_brl end), 0.00)   as applied_return_amount
                from silver.silver_ted_transfer_movement
                group by batch_id
            )
            select
                control.batch_id,
                control.currency,
                control.declared_transfer_count                                        as source_transfer_count,
                staged.staged_transfer_count,
                applied.applied_transfer_count,
                control.declared_return_count                                          as source_return_count,
                staged.staged_return_count,
                applied.applied_return_count,
                cast(control.declared_gross_amount as decimal(18, 2))                  as source_gross_amount,
                cast(staged.staged_gross_amount as decimal(18, 2))                     as staged_gross_amount,
                cast(applied.applied_gross_amount as decimal(18, 2))                   as applied_gross_amount,
                cast(control.declared_returned_amount as decimal(18, 2))               as source_return_amount,
                cast(staged.staged_return_amount as decimal(18, 2))                    as staged_return_amount,
                cast(applied.applied_return_amount as decimal(18, 2))                  as applied_return_amount,
                cast(control.declared_net_amount as decimal(18, 2))                    as source_net_amount,
                cast(staged.staged_gross_amount + staged.staged_return_amount as decimal(18, 2))   as staged_net_amount,
                cast(applied.applied_gross_amount + applied.applied_return_amount as decimal(18, 2)) as applied_net_amount,
                applied.applied_transfer_count - control.declared_transfer_count       as transfer_count_delta,
                applied.applied_return_count - control.declared_return_count           as return_count_delta,
                cast(
                    applied.applied_gross_amount
                    - cast(control.declared_gross_amount as decimal(18, 2))
                    as decimal(18, 2)
                )                                                                      as gross_amount_delta,
                cast(
                    applied.applied_return_amount
                    - cast(control.declared_returned_amount as decimal(18, 2))
                    as decimal(18, 2)
                )                                                                      as return_amount_delta,
                cast(
                    (applied.applied_gross_amount + applied.applied_return_amount)
                    - cast(control.declared_net_amount as decimal(18, 2))
                    as decimal(18, 2)
                )                                                                      as net_amount_delta,
                0                                                                       as reject_count,
                case
                    when applied.applied_transfer_count = control.declared_transfer_count
                     and applied.applied_return_count = control.declared_return_count
                     and applied.applied_gross_amount = cast(control.declared_gross_amount as decimal(18, 2))
                     and applied.applied_return_amount = cast(control.declared_returned_amount as decimal(18, 2))
                     and staged.staged_transfer_count = control.declared_transfer_count
                     and staged.staged_return_count = control.declared_return_count
                     and staged.staged_gross_amount = cast(control.declared_gross_amount as decimal(18, 2))
                     and staged.staged_return_amount = cast(control.declared_returned_amount as decimal(18, 2))
                    then 'MATCHED'
                    else 'MISMATCHED'
                end                                                                    as status
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

    row_count = _register_landing(outcomes)
    _build_lakehouse()
    print(json.dumps({"dlt_rows": row_count, "emit": list(outcomes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
