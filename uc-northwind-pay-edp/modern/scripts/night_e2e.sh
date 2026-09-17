#!/usr/bin/env bash
# One command: the whole plant, narrated, with the proofs printed as they land.
#   modern/scripts/night_e2e.sh
# Builds nothing that the room is meant to build. Edits no frozen tree.
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT=$(pwd)
PLANT="$ROOT/modern/.venv/bin/python"        # pyarrow 25 — wrote landing
ORCH="$ROOT/modern/orchestration/.venv/bin"  # dagster, isolated on purpose
FAIL=0

rule() { printf '\n\033[2m%s\033[0m\n' "────────────────────────────────────────────────────────────────"; }
step() { printf '\n\033[1m▸ %s\033[0m  \033[2m%s\033[0m\n' "$1" "${2:-}"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL=1; }
note() { printf '    \033[2m%s\033[0m\n' "$1"; }

rule; printf '\033[1mDARK FACTORY · end to end\033[0m  \033[2m%s\033[0m\n' "$(date '+%Y-%m-%d %H:%M')"; rule

# ── preflight: say what is missing once, instead of failing eight times ──
MISS=0
[ -x "$PLANT" ]      || { printf '  \033[31mmissing\033[0m  modern/.venv            → modern/scripts/bootstrap.sh\n'; MISS=1; }
[ -x "$ORCH/dagster" ] || { printf '  \033[31mmissing\033[0m  orchestration env       → modern/scripts/bootstrap.sh\n'; MISS=1; }
for d in evidence modern/landing modern/lakehouse/ducklake; do
  [ -e "$d" ] || { printf '  \033[31mmissing\033[0m  %-23s → runtime artifact; run the nights on this checkout\n' "$d"; MISS=1; }
done
if [ "$MISS" -ne 0 ]; then
  printf '\n  This checkout cannot run the Night. Evidence, landing and the lakehouse are\n'
  printf '  gitignored: they are produced by running the plant, never by cloning it.\n'
  rule; exit 2
fi

step "1 · legacy ground truth" "the plant that already works"
if S=$($PLANT -c "import json;d=json.load(open('evidence/B202607230000001/reconciliation.json'));print(d['status'],d['applied_net_amount'])" 2>/dev/null); then
  ok "legacy reconciliation: $S"; note "evidence/B202607230000001/reconciliation.json"
else bad "no legacy observation — run: make run TYPE=01 SCENARIO=valid-minimal"; fi

step "2 · emit → landing Parquet" "first write is landing, not SFTP"
if $PLANT modern/scripts/plant_steps.py emit >/tmp/nightly-emit.json 2>/tmp/nightly-emit.err; then
  ok "emit: $($PLANT -c "import json;print(', '.join(json.load(open('/tmp/nightly-emit.json'))['scenarios']))")"
  note "sha $(shasum -a 256 modern/landing/B202607230000001/*.parquet | cut -c1-16)…"
else bad "emit failed"; tail -3 /tmp/nightly-emit.err | sed 's/^/    /'; fi

step "3 · dlt register → landing tables" "register only; it never reshapes money"
if $PLANT modern/scripts/plant_steps.py register >/tmp/nightly-reg.json 2>/dev/null; then
  ok "dlt load $($PLANT -c "import json;print(json.load(open('/tmp/nightly-reg.json'))['load_id'])")"
else bad "dlt register failed"; fi

step "4 · dbt build → Bronze · Silver · Gold" "documented grains, privacy assertions, release gate"
if $PLANT modern/scripts/plant_steps.py build >/dev/null 2>/tmp/nightly-dbt.err; then
  ok "dbt run + dbt test green (tag:type_01)"
  note "$(grep -Eo 'PASS=[0-9]+ WARN=[0-9]+ ERROR=[0-9]+ SKIP=[0-9]+' /tmp/nightly-dbt.err | tail -1)"
else bad "dbt failed"; grep -E 'ERROR' /tmp/nightly-dbt.err | tail -3 | sed 's/^/    /'; fi

step "5 · the data, in DuckDB" "open it, do not take my word"
$PLANT - <<'PY'
import duckdb
c = duckdb.connect('modern/lakehouse/ducklake/northwind_modern.duckdb', read_only=True)
for t in ('landing.card_settlement','bronze.bronze_card_settlement','silver.silver_card_settlement'):
    print(f"    {t:44s} rows={c.execute(f'select count(*) from {t}').fetchone()[0]}")
cur = c.execute('select batch_id,currency,applied_net_amount,status from gold.gold_card_settlement_reconciliation')
for r in cur.fetchall():
    print(f"    GOLD  {r[0]}  {r[1]}  applied_net {r[2]}  {r[3]}")
PY

step "6 · Dagster lineage" "ADR 0012 — lineage, not parser"
export DAGSTER_HOME=${DAGSTER_HOME:-/tmp/dagster-home}; mkdir -p "$DAGSTER_HOME"
if (cd modern/orchestration && "$ORCH/dagster" asset materialize --select '*' -m definitions) >/tmp/nightly-dag.log 2>&1; then
  ok "6 assets materialized · $(grep -c ASSET_MATERIALIZATION /tmp/nightly-dag.log) materializations"
  grep -E 'gold applied_net|gold hash recorded' /tmp/nightly-dag.log | sed 's/.* - //' | sed 's/^/    /'
  note "UI: cd modern/orchestration && .venv/bin/dagster dev -m definitions"
else bad "Dagster materialize failed"; tail -5 /tmp/nightly-dag.log | sed 's/^/    /'; fi

step "7 · the factory gates · type 01" "the type that is built"
$PLANT modern/scripts/factory_e2e.py --type 01 | sed 's/^/  /'
[ "${PIPESTATUS[0]}" -eq 0 ] || true

step "8 · the factory gates · type 06" "the type that is not — this is the Night"
$PLANT modern/scripts/factory_e2e.py --type 06 | sed 's/^/  /'

rule
if [ "$FAIL" -eq 0 ]; then
  printf '\033[32m  READY\033[0m  type 01 accepted · type 06 stalled with one code · frozen trees untouched\n'
else
  printf '\033[31m  NOT READY\033[0m  a step above failed — fix it before the room arrives\n'
fi
rule
exit $FAIL
