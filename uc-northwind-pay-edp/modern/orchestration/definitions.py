"""Dagster assets for the modern plant — lineage, not a parser (ADR 0012).

Every asset shells out to the code that already owns the step, through
``modern/.venv`` (pyarrow 25 — the interpreter that wrote landing). Dagster
holds no layout, no money rule and no classification: it records what ran, in
what order, and what the referee said. Nothing here may be imported by the
ingestion package.
"""

import json
import subprocess
from pathlib import Path

import duckdb
from dagster import (
    AssetExecutionContext,
    Definitions,
    MaterializeResult,
    MetadataValue,
    asset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANT_PYTHON = REPO_ROOT / "modern" / ".venv" / "bin" / "python"
DATABASE = REPO_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
BATCH = "B202607230000001"


STEPS = REPO_ROOT / "modern" / "scripts" / "plant_steps.py"


def _step(name: str) -> dict:
    """Call one plant step out-of-process. The plant computes; Dagster records."""
    done = subprocess.run(
        [str(PLANT_PYTHON), str(STEPS), name], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip()[-800:] or f"step {name} failed")
    return json.loads(done.stdout)


@asset(group_name="ingest_landing", description="Legacy observation for the batch — the referee's input, never modified.")
def legacy_ground_truth(context: AssetExecutionContext) -> MaterializeResult:
    packet = REPO_ROOT / "evidence" / BATCH / "reconciliation.json"
    if not packet.is_file():
        raise RuntimeError(f"no legacy observation at {packet.relative_to(REPO_ROOT)}")
    data = json.loads(packet.read_text(encoding="utf-8"))
    context.log.info(f"legacy {data['status']} · applied_net {data['applied_net_amount']}")
    return MaterializeResult(metadata={
        "status": data["status"],
        "applied_net_amount": data["applied_net_amount"],
        "packet": MetadataValue.path(str(packet)),
    })


@asset(group_name="ingest_landing", description="Landing Parquet published by the five-file package. Dagster does not parse.")
def landing_parquet(context: AssetExecutionContext) -> MaterializeResult:
    emitted = _step("emit")
    context.log.info(f"emit scenarios: {', '.join(emitted['scenarios'])}")
    manifest = REPO_ROOT / "modern" / "landing" / BATCH / "parquet-manifest.json"
    if not manifest.is_file():
        raise RuntimeError("landing Parquet absent after emit")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    context.log.info(f"landing sha {data['parquet_sha256'][:12]}… · {data['record_count']} records")
    return MaterializeResult(metadata={
        "parquet_sha256": data["parquet_sha256"],
        "record_count": data["record_count"],
        "declared_net_amount": data["declared_net_amount"],
        "computed_net_amount": data["computed_net_amount"],
    })


@asset(deps=[landing_parquet], group_name="dlt_gold", description="dlt registers landing Parquet. Register only — it never reshapes money.")
def lakehouse_registered(context: AssetExecutionContext) -> MaterializeResult:
    loaded = _step("register")
    con = duckdb.connect(str(DATABASE), read_only=True)
    rows = con.execute("select count(*) from landing.card_settlement").fetchone()[0]
    context.log.info(f"dlt load {loaded['load_id']} · landing.card_settlement rows={rows}")
    return MaterializeResult(metadata={
        "landing_rows": rows,
        "dlt_load_id": loaded["load_id"],
        "parquet_files": MetadataValue.json(loaded["parquet_files"]),
        "database": MetadataValue.path(str(DATABASE)),
    })


@asset(deps=[lakehouse_registered], group_name="dlt_gold", description="dbt Bronze/Silver/Gold at the documented grains.")
def gold_reconciliation(context: AssetExecutionContext) -> MaterializeResult:
    _step("build")
    con = duckdb.connect(str(DATABASE), read_only=True)
    row = con.execute(
        "select applied_net_amount, status, amount_delta from gold.gold_card_settlement_reconciliation where batch_id = ?",
        [BATCH],
    ).fetchone()
    if row is None:
        raise RuntimeError("Gold holds no row for this batch")
    context.log.info(f"gold applied_net {row[0]} · {row[1]}")
    return MaterializeResult(metadata={
        "applied_net_amount": str(row[0]),
        "status": str(row[1]),
        "amount_delta": str(row[2]),
    })


@asset(deps=[gold_reconciliation, legacy_ground_truth], group_name="orchestrate_serve", description="Golden-match verdict. Two questions, never netted. Dagster records it; it does not decide it.")
def golden_match_verdict(context: AssetExecutionContext) -> MaterializeResult:
    verdict = REPO_ROOT / "evidence" / "modern" / BATCH / "golden-match.json"
    if not verdict.is_file():
        raise RuntimeError("no golden-match verdict on disk")
    data = json.loads(verdict.read_text(encoding="utf-8"))
    for name, value in sorted(data["checks"].items()):
        context.log.info(f"  {name}: {value}")
    if not data["resolved"]:
        raise RuntimeError(f"unresolved differences: {data['unexplained_count']}")
    return MaterializeResult(metadata={
        "outcome_class": data["outcome_class"],
        "resolved": data["resolved"],
        "unexplained_count": data["unexplained_count"],
        "checks": MetadataValue.json(data["checks"]),
    })


@asset(deps=[golden_match_verdict], group_name="orchestrate_serve", description="Gold hash — the determinism record the loop packet skips when Dagster is down.")
def gold_hash(context: AssetExecutionContext) -> MaterializeResult:
    manifest = json.loads((REPO_ROOT / "modern" / "landing" / BATCH / "parquet-manifest.json").read_text(encoding="utf-8"))
    context.log.info(f"gold hash recorded from landing sha {manifest['parquet_sha256'][:12]}…")
    return MaterializeResult(metadata={"parquet_sha256": manifest["parquet_sha256"], "skipped": False})


defs = Definitions(
    assets=[
        legacy_ground_truth,
        landing_parquet,
        lakehouse_registered,
        gold_reconciliation,
        golden_match_verdict,
        gold_hash,
    ]
)
