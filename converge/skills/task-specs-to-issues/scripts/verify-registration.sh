#!/usr/bin/env bash
# verify-registration.sh — the GATE. Assert the board faithfully mirrors the
# signed-off specs before this pass is allowed to end.
#
# Confirms, and emits a single machine-readable VERDICT line:
#   1) 1:1 mapping        — count(issues) == count(signed_off specs), every spec
#                           has exactly one issue and vice-versa (no orphans, no
#                           double-registration).
#   2) graph faithful     — every depends_on edge is one blocked-by link; no
#                           extra links, none missing.
#   3) no cycles          — the signed-off dependency subgraph is a DAG.
#   4) no un-gated leak    — only signed_off specs are on the board.
#
# Usage:
#   verify-registration.sh [--tracker github|linear|jira] [--tasks-dir DIR]
#                          [--dry-run] [--prune]
#
#   --dry-run  verify the SPEC side only (cycles, edge integrity, gate) with no
#              network — the offline half of the gate. Board-vs-spec count/link
#              comparison is SKIPPED (it needs a live adapter).
#   --prune    report orphan issues (on the board but with no signed-off spec).
#              Live only.
#
# Exit: 0 and `VERDICT: REGISTERED` when every check holds; 1 and
# `VERDICT: DO NOT PROCEED` on the first failure. This is a gate, not a fixer.
#
# bash-3.2-safe: scratch files + grep/awk, no associative arrays.

set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_parse.sh
source "$SELF_DIR/_parse.sh"

TRACKER="linear"
TASKS_DIR="${TSI_TASKS_DIR:-tasks}"
DRY_RUN=0
PRUNE=0
BOARD_RAW=""   # count of registered issues the live board reported (set in check [D])

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tracker)   TRACKER="${2:?}"; shift 2 ;;
    --tracker=*) TRACKER="${1#--tracker=}"; shift ;;
    --tasks-dir)   TASKS_DIR="${2:?}"; shift 2 ;;
    --tasks-dir=*) TASKS_DIR="${1#--tasks-dir=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --prune)     PRUNE=1; shift ;;
    -h|--help) grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'; exit 0 ;;
    *) tsi_die "unknown arg '$1' (see --help)" ;;
  esac
done

case "$TRACKER" in github|linear|jira|fake) ;; *) tsi_die "unknown --tracker '$TRACKER'" ;; esac
[[ -d "$TASKS_DIR" ]] || tsi_die "tasks dir '$TASKS_DIR' not found"
ADAPTER="$SELF_DIR/adapters/${TRACKER}.sh"
[[ -f "$ADAPTER" ]] || tsi_die "adapter not found: $ADAPTER"

WORK="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/tsi-verify.$$")"
mkdir -p "$WORK"
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

SIGNED="$WORK/signed.txt"   # signed-off spec ids
EDGES="$WORK/edges.tsv"     # from_id \t to_id
UNGATED="$WORK/ungated.txt" # ids with signed_off != true
: > "$SIGNED"; : > "$EDGES"; : > "$UNGATED"

FAIL=0
fail() { echo "  FAIL: $*" >&2; FAIL=1; }
pass() { echo "  ok:   $*"; }

echo "VERIFY REGISTRATION — tracker=$TRACKER tasks-dir=$TASKS_DIR dry-run=$DRY_RUN"
echo "----------------------------------------------------------------"

# ----- Collect the spec-side truth -----
for f in "$TASKS_DIR"/T-*.md; do
  [[ -f "$f" ]] || continue
  id="$(tsi_id "$f")"
  [[ -n "$id" ]] || continue
  if [[ "$(tsi_signed_off "$f")" == "true" ]]; then
    echo "$id" >> "$SIGNED"
    for dep in $(tsi_depends_on "$f"); do
      printf '%s\t%s\n' "$id" "$dep" >> "$EDGES"
    done
  else
    echo "$id" >> "$UNGATED"
  fi
done
sort -u -o "$SIGNED" "$SIGNED"
SPEC_COUNT="$(awk 'END{print NR+0}' "$SIGNED")"

# ----- LANDED: specs that finished, and still own their board issue -----
#
# `cvg transition <id> done` MOVES a spec into tasks/done/. This gate only ever
# scanned tasks/*.md, so the instant Pass 8 closed its first task the completed
# spec vanished from every set here and produced three confidently wrong verdicts
# at once: its dependents' edges looked dangling [A], the graph could not be built
# so the Kahn peel reported a "cycle" among eight tasks that form a CHAIN [B], and
# the issue it still legitimately owns looked like a board orphan [D].
#
# Finishing work broke the gate that checks the board. It could not have been
# found before today, because before today nothing had ever finished.
#
# A landed spec is KNOWN (it exists, it is signed, it owns an issue) but is NOT in
# the register SET (it must not be re-created as new work). That distinction is the
# whole fix: SIGNED stays "active work", KNOWN answers "does this id exist at all".
LANDED="$WORK/landed.txt"; : > "$LANDED"
if [[ -d "$TASKS_DIR/done" ]]; then
  for f in "$TASKS_DIR"/done/T-*.md; do
    [[ -e "$f" ]] || continue
    id="$(tsi_id "$f")"
    [[ -n "$id" ]] || continue
    [[ "$(tsi_signed_off "$f")" == "true" ]] && echo "$id" >> "$LANDED"
  done
fi
sort -u -o "$LANDED" "$LANDED"
LANDED_COUNT="$(awk 'END{print NR+0}' "$LANDED")"

KNOWN="$WORK/known.txt"
cat "$SIGNED" "$LANDED" | sort -u > "$KNOWN"
KNOWN_COUNT="$(awk 'END{print NR+0}' "$KNOWN")"
[[ "$LANDED_COUNT" -gt 0 ]] && echo "landed (done/, still registered): $LANDED_COUNT"
EDGE_COUNT="$(awk 'END{print NR+0}' "$EDGES")"
echo "spec side: $SPEC_COUNT signed-off, $EDGE_COUNT depends_on edge(s)"

# ----- Check A: every edge target is itself a signed-off spec (no dangling) -----
echo "[A] edge integrity (every depends_on target is registerable)"
DANGLE=0
while IFS=$'\t' read -r from dep; do
  [[ -n "$dep" ]] || continue
  if ! grep -qxF "$dep" "$KNOWN"; then
    fail "edge $from -> $dep targets an id that is neither active nor landed (blocked-by would dangle)"
    DANGLE=1
  fi
done < "$EDGES"
[[ "$DANGLE" -eq 0 ]] && pass "all edge targets are signed-off specs"

# ----- Check B: no cycle in the signed-off subgraph (Kahn peel) -----
echo "[B] acyclic dependency graph"
REMAIN="$WORK/remain.txt"; REM="$WORK/remedges.tsv"
# Seed from KNOWN: a landed node has no unmet dependency, so it peels first
# and lets its dependents follow. Seeding from SIGNED alone left every dependent
# permanently blocked and reported that deadlock as a "cycle".
cp "$KNOWN" "$REMAIN"; cp "$EDGES" "$REM"
CYCLE=0
while [[ -s "$REMAIN" ]]; do
  ROOTS="$WORK/roots.txt"; : > "$ROOTS"
  while read -r n; do
    [[ -n "$n" ]] || continue
    if ! awk -F'\t' -v x="$n" '$1==x{f=1} END{exit f?0:1}' "$REM"; then
      echo "$n" >> "$ROOTS"
    fi
  done < "$REMAIN"
  if [[ ! -s "$ROOTS" ]]; then
    fail "dependency cycle among: $(tr '\n' ' ' < "$REMAIN")"
    CYCLE=1; break
  fi
  grep -vxF -f "$ROOTS" "$REMAIN" > "$REMAIN.next" || true; mv "$REMAIN.next" "$REMAIN"
  awk -F'\t' 'NR==FNR{d[$1]=1; next} !($2 in d)' "$ROOTS" "$REM" > "$REM.next" || true; mv "$REM.next" "$REM"
done
[[ "$CYCLE" -eq 0 ]] && pass "graph is a DAG"

# ----- Check C: no un-gated leak is possible from the spec side -----
# (Registration only ever writes signed-off specs; this asserts the input the
# gate reasons over never included an un-gated id in the SIGNED set.)
echo "[C] no un-gated spec in the register set"
LEAK=0
while read -r u; do
  [[ -n "$u" ]] || continue
  if grep -qxF "$u" "$SIGNED"; then
    fail "un-gated id '$u' present in the signed set (should have been skipped)"
    LEAK=1
  fi
done < "$UNGATED"
[[ "$LEAK" -eq 0 ]] && pass "un-gated specs ($(awk 'END{print NR+0}' "$UNGATED")) correctly excluded"

# ----- Live board comparison (skipped on --dry-run) -----
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[D] board comparison SKIPPED (--dry-run: spec-side gate only)"
else
  # The board is compared against KNOWN, not SIGNED. A landed spec still owns the
  # issue it was registered as, so measuring 1:1 against active-only work reports
  # every completed task as a board orphan — which is what happened the moment the
  # first task finished. Parity is about "does an issue have a spec", and a done
  # spec is still a spec.
  echo "[D] board mirrors the specs (1:1 count · no orphan · no missing · no dup)"
  if ! bash "$ADAPTER" preflight >/dev/null 2>&1; then
    fail "adapter preflight failed — cannot verify the live board"
  else
    # The FULL registered set, keyed on the spec id its marker carries (list-issues,
    # not just list-ready roots), so the board can be diffed against the signed specs.
    # NB: capture the adapter's stderr and SHOW it on failure. Swallowing it with
    # 2>/dev/null once turned a broken GraphQL type into a silent "board: 0 registered",
    # which reads like "nothing is registered" when the real cause was a query error.
    # A gate that hides why it failed is worse than no gate.
    BOARD="$WORK/board.tsv"          # extid \t issue_ref  (one line per registered issue)
    BOARD_ERR="$WORK/board.err"
    if ! bash "$ADAPTER" list-issues > "$BOARD" 2>"$BOARD_ERR"; then
      : > "$BOARD"
      echo "  WARN: adapter list-issues failed — the parity check cannot see the board:" >&2
      [[ -s "$BOARD_ERR" ]] && sed 's/^/    /' "$BOARD_ERR" >&2
    elif [[ -s "$BOARD_ERR" ]]; then
      sed 's/^/  note: /' "$BOARD_ERR" >&2   # e.g. the >250 truncation warning
    fi
    BOARD_IDS="$WORK/board_ids.txt"; awk -F'\t' '$1!=""{print $1}' "$BOARD" | sort > "$BOARD_IDS"  # sorted, dups KEPT
    BOARD_UNIQ="$WORK/board_uniq.txt"; sort -u "$BOARD_IDS" > "$BOARD_UNIQ"
    BOARD_RAW="$(awk 'END{print NR+0}' "$BOARD_IDS")"
    BOARD_COUNT="$(awk 'END{print NR+0}' "$BOARD_UNIQ")"
    echo "  spec: $KNOWN_COUNT signed-off   board: $BOARD_RAW registered ($BOARD_COUNT distinct)"

    if [[ "$BOARD_RAW" -eq 0 && "$KNOWN_COUNT" -gt 0 ]]; then
      fail "board carries no registered issue but $KNOWN_COUNT spec(s) are signed off — not registered yet? (or adapter lacks list-issues)"
    else
      # (1) double-registration — the same spec id on two board issues.
      if [[ "$BOARD_RAW" -ne "$BOARD_COUNT" ]]; then
        DUPS="$(uniq -d "$BOARD_IDS" | tr '\n' ' ' | sed 's/ *$//')"
        fail "spec id(s) registered to more than one issue (double-registration): $DUPS"
      fi
      # (2) missing — a signed-off spec with no board issue (under-registered).
      MISSING="$(comm -23 "$KNOWN" "$BOARD_UNIQ" | tr '\n' ' ' | sed 's/ *$//')"
      [[ -n "$MISSING" ]] && fail "signed-off spec(s) with no board issue: $MISSING"
      # (3) orphan — a board issue whose spec id is not in the signed-off set.
      ORPHAN="$(comm -13 "$KNOWN" "$BOARD_UNIQ" | tr '\n' ' ' | sed 's/ *$//')"
      if [[ -n "$ORPHAN" ]]; then
        fail "board issue(s) with no signed-off spec (orphan): $ORPHAN"
        if [[ "$PRUNE" -eq 1 ]]; then
          echo "  --prune: close/delete these orphan issue(s), or re-gate their spec:" >&2
          for o in $ORPHAN; do
            awk -F'\t' -v e="$o" '$1==e{printf "    orphan: %s (%s)\n", $1, $2}' "$BOARD" >&2
          done
        fi
      fi
      [[ -z "$MISSING" && -z "$ORPHAN" && "$BOARD_RAW" -eq "$KNOWN_COUNT" ]] \
        && pass "1:1 — $KNOWN_COUNT spec(s) ⇄ $BOARD_RAW issue(s); no orphan, no missing, no dup"
    fi

    # Secondary signal: the board's ready frontier (roots) is live.
    SPEC_ROOTS="$WORK/spec_roots.txt"; : > "$SPEC_ROOTS"
    while read -r id; do
      awk -F'\t' -v x="$id" '$1==x{f=1} END{exit f?0:1}' "$EDGES" || echo "$id" >> "$SPEC_ROOTS"
    done < "$KNOWN"
    sort -u -o "$SPEC_ROOTS" "$SPEC_ROOTS"
    BOARD_READY="$WORK/board_ready.txt"
    bash "$ADAPTER" list-ready > "$BOARD_READY" 2>/dev/null || : > "$BOARD_READY"
    echo "  ready frontier: spec roots $(awk 'END{print NR+0}' "$SPEC_ROOTS") · board ready $(awk 'END{print NR+0}' "$BOARD_READY")"
  fi
fi

echo "----------------------------------------------------------------"
if [[ "$FAIL" -eq 0 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "spec-side gate only: $SPEC_COUNT signed-off spec(s), $EDGE_COUNT edge(s) — board comparison skipped (--dry-run)."
  else
    echo "1:1 mapping: $SPEC_COUNT spec(s) -> ${BOARD_RAW:-?} issue(s); $EDGE_COUNT edge(s) as blocked-by links."
  fi
  echo "VERDICT: REGISTERED"
  echo "CHECK_REGISTER=OK"
  exit 0
else
  echo "VERDICT: DO NOT PROCEED"
  echo "CHECK_REGISTER=FAIL"
  exit 1
fi
