#!/bin/bash
# run-tests.sh — table-driven regression for new-plan.sh (Pass 3, dir-per-swimlane
# model). Every row: the command, the exit code it MUST produce, a pattern the
# output MUST contain (the intended reason — a run failing for the wrong reason is
# a broken test), and a pattern it MUST NOT contain. Exit 0 iff every row holds.
# bash 3.2 safe.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/new-plan.sh"
FIX="$HERE/fixtures"
TOTAL=0
FAILED=0

report() { # <name> <rc> <want_rc> <out> <must> <must_not>
  NAME="$1"; RC="$2"; WANT_RC="$3"; OUT="$4"; MUST="$5"; MUST_NOT="$6"; ROW_OK=1; REASON=""
  [ "$RC" -ne "$WANT_RC" ] && { ROW_OK=0; REASON="exit $RC, wanted $WANT_RC"; }
  if [ -n "$MUST" ] && ! printf '%s\n' "$OUT" | grep -qE "$MUST"; then ROW_OK=0; REASON="$REASON; missing: $MUST"; fi
  if [ -n "$MUST_NOT" ] && printf '%s\n' "$OUT" | grep -qE "$MUST_NOT"; then ROW_OK=0; REASON="$REASON; forbidden: $MUST_NOT"; fi
  if [ "$ROW_OK" -eq 1 ]; then printf 'ok    %-32s (exit %s)\n' "$NAME" "$RC"
  else printf 'FAIL  %-32s %s\n' "$NAME" "$REASON"; printf '%s\n' "$OUT" | sed 's/^/      | /'; FAILED=$((FAILED + 1)); fi
}

run_case() { # <name> <args...> -- <expected_exit> <must> <must_not>
  NAME="$1"; shift; CMD_ARGS=()
  while [ "$1" != "--" ]; do CMD_ARGS+=("$1"); shift; done; shift
  TOTAL=$((TOTAL + 1)); OUT="$(bash "$SCRIPT" "${CMD_ARGS[@]}" 2>&1)"; RC=$?
  report "$NAME" "$RC" "$1" "$OUT" "$2" "$3"
}

assert_file() { # <name> <file> <must> <must_not>
  NAME="$1"; FILE="$2"; TOTAL=$((TOTAL + 1))
  if [ -f "$FILE" ]; then report "$NAME" 0 0 "$(cat "$FILE")" "$3" "$4"
  else printf 'FAIL  %-32s file missing: %s\n' "$NAME" "$FILE"; FAILED=$((FAILED + 1)); fi
}

echo "== --check on dir-per-swimlane fixtures =="
run_case good           --check --dir "$FIX/good"          -- 0 '^CHECK: OK'            ''
# Both LAYOUTS must gate green:
#   good      LEGACY  swimlane-<seam>/swimlane-<seam>.plan.md + swimlane-<seam>-leg-NN-*.md
#   good-lane CANON   <seam>/_lane.md + leg-NN-*.md   (nothing repeats the folder)
# Keeping both is the back-compat contract: a workspace written before the
# rename must never read as EMPTY, which is how a gate silently drops a pass.
# The canonical fixture also proves a lane is found by CONTENT (it holds a lane
# PRD), not by its directory name — the folder no longer says "swimlane" at all.
run_case good-lane      --check --dir "$FIX/good-lane"     -- 0 '^CHECK: OK'            ''
# F-009: prose may name Converge's own noun; only a real task ID or eval leaks.
# The fork declaration the Pass 4 gate DEMANDS reads "…become Task-Specs at Pass 5",
# and that used to fail the altitude guard.
S="$(mktemp -d -t p3-noun.XXXXXX)"; cp -R "$FIX/good-lane/." "$S/"
printf '\n> Fork: B — task-driven. The plans become Task-Specs at Pass 5.\n' >> "$S/checkout/_lane.md"
run_case prose-names-taskspec --check --dir "$S" -- 0 'CHECK_PLAN=OK' 'DRIFT'
printf '\nTask 4: wire the handler\n' >> "$S/checkout/_lane.md"
run_case real-task-id-still-drifts --check --dir "$S" -- 1 'atomic task' '^CHECK_PLAN=OK'
rm -rf "$S"
run_case lane-token-ok  --check --dir "$FIX/good-lane"     -- 0 'CHECK_PLAN=OK'          ''
assert_file lane-keeps-id  "$FIX/good-lane/checkout/leg-01-fastapi.md" '^leg: swimlane-checkout-leg-01' ''
run_case no-thread      --check --dir "$FIX/no-thread"     -- 1 'THREAD.*steel-thread'  '^CHECK: OK'
run_case no-mermaid     --check --dir "$FIX/no-mermaid"    -- 1 'VISUAL.*mermaid'       '^CHECK: OK'
run_case no-lanemeta    --check --dir "$FIX/no-lanemeta"   -- 1 "no 'lane-meta:'"       '^CHECK: OK'
run_case no-nongoals    --check --dir "$FIX/no-nongoals"   -- 1 'section matching /Non' '^CHECK: OK'
run_case leg-no-proves  --check --dir "$FIX/leg-no-proves" -- 1 'no Proves'             '^CHECK: OK'
run_case drift-sql      --check --dir "$FIX/drift-sql"     -- 1 'DRIFT.*SQL'            '^CHECK: OK'
run_case no-legs        --check --dir "$FIX/no-legs"       -- 1 'no leg files'          '^CHECK: OK'
run_case leg-gap        --check --dir "$FIX/leg-gap"       -- 1 'LEGS.*no gap'          '^CHECK: OK'
run_case orphan-leg     --check --dir "$FIX/orphan-leg"    -- 1 'orphan leg'            '^CHECK: OK'
run_case empty-dir      --check --dir "$FIX/empty"         -- 2 'no swimlanes found'    ''

echo "== machine token (agents-first) =="
run_case token-ok           --check --dir "$FIX/good"        -- 0 'CHECK_PLAN=OK'          ''
run_case token-fail         --check --dir "$FIX/no-thread"   -- 1 'CHECK_PLAN=FAIL'        ''
run_case token-empty        --check --dir "$FIX/empty"       -- 2 'CHECK_PLAN=EMPTY'       ''
run_case token-usage-error  --check --bogus --dir "$FIX/good" -- 1 'CHECK_PLAN=USAGE_ERROR' ''

echo "== scaffold =="
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

run_case scaffold-prd     --dir "$TMP/sketch" "capture"                 -- 0 '^Created ' ''
assert_file prd-seam      "$TMP/sketch/capture/_lane.md" '^## Seam'      ''
assert_file prd-nongoals  "$TMP/sketch/capture/_lane.md" '^## Non-Goals' ''
assert_file prd-mermaid   "$TMP/sketch/capture/_lane.md" '```mermaid'    ''
assert_file prd-lanemeta  "$TMP/sketch/capture/_lane.md" '^lane-meta: thread=' ''

run_case scaffold-leg     --dir "$TMP/sketch" --lane capture --leg 01-dlt -- 0 '^Created ' ''
assert_file leg-resp      "$TMP/sketch/capture/leg-01-dlt.md" '^## Responsibility' ''
assert_file leg-proves    "$TMP/sketch/capture/leg-01-dlt.md" '^## Proves'         ''
# The filename is short (leg-01-dlt.md) but the STABLE KEY inside it stays
# fully-qualified (swimlane-capture-leg-01) — that separation is the change.
assert_file leg-key       "$TMP/sketch/capture/leg-01-dlt.md" '^leg: swimlane-capture-leg-01' ''

run_case scaffold-leg-badfmt  --dir "$TMP/sketch" --lane capture --leg 1-dlt -- 1 'must be NN-<tech>' ''
run_case scaffold-no-clobber  --dir "$TMP/sketch" "capture"                  -- 1 'already exists'    ''
run_case scaffold-no-title    --dir "$TMP/sketch2"                           -- 1 'title required'    ''

# an unfilled PRD scaffold MUST fail --check (placeholders + no legs) — teeth.
TOTAL=$((TOTAL + 1))
bash "$SCRIPT" --dir "$TMP/s3" "alpha" >/dev/null 2>&1
OUT="$(bash "$SCRIPT" --check --dir "$TMP/s3" 2>&1)"; RC=$?
report scaffold-unfilled-fails "$RC" 1 "$OUT" 'META|WEAK|THREAD' '^CHECK: OK'

echo
if [ "$FAILED" -eq 0 ]; then echo "PASS — all $TOTAL rows green."; exit 0
else echo "FAIL — $FAILED of $TOTAL rows red." >&2; exit 1; fi
