#!/usr/bin/env bash
# test-cvg-tasks-dod.sh — the Definition of Done checklist must not weaken a criterion.
#
# WHY THIS EXISTS
# `cvg tasks dod` renders the matrix a human ticks off to declare a task done, and
# it shipped with ZERO suites — the only verb in the Task-Spec engine with a machine
# token and no test. It cost exactly what an untested gate costs: the checklist was
# reading `description:` with a character class that excluded `,`, so every block-style
# prose description was cut at its first comma. English puts the DEMANDING clause
# after that comma, so:
#
#   written:   the entry point exists, is executable, takes no arguments and fetches nothing
#   rendered:  the entry point exists                      <- satisfied by `touch`
#
# Eight of eight descriptions in the uc-01 backlog were silently halved this way, and
# the checkbox still read as the whole criterion. So the load-bearing rows here are
# [1] and [2] together: prose keeps its commas, AND the inline flow form the old
# pattern existed to protect still stops at one. A fix that breaks the case the bug
# was guarding is not a fix.
#
# Also pinned: announced truncation (a cut that says it is a cut), the traceability
# matrix both ways, the GAPS token and its exit code, and read-onlyness.
#
# Hermetic: throwaway spec files. No engine, no network, no credentials.
# Token: TASKS_DOD_TESTS=PASS | TASKS_DOD_TESTS=FAIL
# bash 3.2 safe. Deps: python3.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
CVG="$REPO/bin/cvg"
TASKSPEC_ENGINE="${CVG_TASKSPEC_BIN:-${TASKSPEC_BIN:-taskspec}}"
command -v "$TASKSPEC_ENGINE" >/dev/null 2>&1 || {
  echo "TASKS_DOD_TESTS=UNRUNNABLE missing compatible Task-Spec engine" >&2
  exit 3
}

rows=0; failed=0
ok()  { printf '  ok   — %s\n' "$1"; rows=$((rows+1)); }
bad() { printf '  FAIL — %s\n' "$1"; rows=$((rows+1)); failed=$((failed+1)); }

echo "=================================================================="
echo "test-cvg-tasks-dod.sh — the checklist must not weaken a criterion"
echo "=================================================================="

TMP="$(mktemp -d -t cvg-tasks-dod.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# A minimal but REALISTIC spec: the descriptions carry commas because real
# acceptance criteria do. A fixture whose prose has no commas cannot exhibit the
# property under test.
mk_spec() { # mk_spec <path> <criteria-block>
  local p="$1" crit="$2"
  cat > "$p" <<SPEC
---
id: T-20260101-alpha-thing
title: "Do the thing"
status: ready
format_version: 3
profile: standard
effort: S
---

# "Do the thing"

## Behavior

- **B-1** — GIVEN a clean checkout with every pinned dependency already installed and the cache warm, WHEN the entry point runs, THEN it exits 0.
- **B-2** — GIVEN the artifact, WHEN inspected, THEN it carries no credential.

## Success Criteria

\`\`\`bash
eval_1() { return 0; }
eval_2() { return 0; }
\`\`\`

## Validation Card

\`\`\`yaml
success_criteria:
$crit

retry_policy:
  max_iterations: 15
\`\`\`

## Exit Check

\`\`\`bash
eval_1 && eval_2
\`\`\`
SPEC
}

BLOCK='  - id: eval_1
    description: the entry point exists, is executable, takes no arguments and fetches nothing
    runnable: bash
    verifies: [B-1]
    terminal: true
  - id: eval_2
    description: the artifact carries no credential, no host and no port
    runnable: bash
    verifies: [B-2]
    terminal: true'

mk_spec "$TMP/block.md" "$BLOCK"

run() { # run <expected-exit> <args...>; sets OUT/RC
  local want="$1"; shift
  local rc=0
  OUT="$("$TASKSPEC_ENGINE" dod "$@" 2>&1)" || rc=$?
  RC="$rc"
  [ "$rc" = "$want" ]
}
last() { printf '%s\n' "$OUT" | tail -1; }

# ---------------------------------------------------------------------------
echo
echo "[1] THE LOAD-BEARING ROW: block prose keeps every clause after its comma"
# ---------------------------------------------------------------------------
if run 0 "$TMP/block.md" && [ "$(last)" = "DOD=COMPLETE" ]; then
  ok "a fully traced spec renders at exit 0 + DOD=COMPLETE"
else
  bad "expected exit 0 + DOD=COMPLETE (got $RC / $(last))"
fi
case "$OUT" in
  *"exists, is executable, takes no arguments and fetches nothing"*)
    ok "the whole criterion survives — commas are content, not delimiters" ;;
  *) bad "the criterion was cut at its first comma (the shipped defect)" ;;
esac
# The precise regression: the weakened form must not appear as the FULL rendering.
if printf '%s\n' "$OUT" | grep -qE 'eval_1 — the entry point exists( ⟵|$)'; then
  bad "eval_1 rendered as the weakened half-criterion"
else
  ok "no criterion renders as a strictly weaker version of itself"
fi
case "$OUT" in
  *"no credential, no host and no port"*) ok "a second comma'd description also survives" ;;
  *) bad "only the first description was fixed" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[2] THE OTHER HALF: inline flow form still ends a field at its comma"
# ---------------------------------------------------------------------------
# This is why the comma-excluding pattern existed. Keeping it working is part of
# the fix, not a separate concern.
FLOW='  - {id: eval_1, description: the entry point exists, runnable: bash, verifies: [B-1], terminal: true}
  - {id: eval_2, description: the artifact carries no credential, runnable: bash, verifies: [B-2], terminal: true}'
mk_spec "$TMP/flow.md" "$FLOW"
if run 0 "$TMP/flow.md"; then
  case "$OUT" in
    *"eval_1 — the entry point exists ⟵"*)
      ok "inline flow form stops at the comma — the field does not swallow siblings" ;;
    *) bad "flow-form description leaked its sibling fields" ;;
  esac
  case "$OUT" in
    *"runnable: bash"*) bad "the rendered description absorbed 'runnable: bash'" ;;
    *) ok "no sibling key bled into the rendered criterion" ;;
  esac
else
  bad "the inline flow form must still render (got $RC)"
fi

# ---------------------------------------------------------------------------
echo
echo "[3] a cut that has to happen ANNOUNCES itself"
# ---------------------------------------------------------------------------
LONG="  - id: eval_1
    description: $(printf 'verylongclause%.0s ' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15)
    runnable: bash
    verifies: [B-1]
    terminal: true
  - id: eval_2
    description: short one
    runnable: bash
    verifies: [B-2]
    terminal: true"
mk_spec "$TMP/long.md" "$LONG"
if run 0 "$TMP/long.md"; then
  case "$OUT" in
    *"…"*) ok "an over-long criterion is marked with an ellipsis, not silently shortened" ;;
    *) bad "a truncated criterion gave the reader no sign it was truncated" ;;
  esac
  if printf '%s\n' "$OUT" | grep -qE 'verylongclausev|verylongc …'; then
    bad "the cut landed mid-word"
  else
    ok "the cut lands on a word boundary"
  fi
  # The behavior line is long too, and had the same silent [:96] slice.
  case "$OUT" in
    *"every pinned dependency"*) ok "the behavior text is rendered, not dropped" ;;
    *) bad "the behavior text vanished" ;;
  esac
else
  bad "a long description must not break the render (got $RC)"
fi

# ---------------------------------------------------------------------------
echo
echo "[4] the matrix gates BOTH ways — an untraced behavior is a GAP"
# ---------------------------------------------------------------------------
ORPHAN_B='  - id: eval_1
    description: only B-1 is covered, and B-2 is left with nothing
    runnable: bash
    verifies: [B-1]
    terminal: true'
mk_spec "$TMP/orphan-b.md" "$ORPHAN_B"
if run 1 "$TMP/orphan-b.md" && [ "$(last)" = "DOD=GAPS" ]; then
  ok "a behavior with no verifying eval → exit 1 + DOD=GAPS"
else
  bad "expected exit 1 + DOD=GAPS for an untraced behavior (got $RC / $(last))"
fi
case "$OUT" in
  *"B-2"*"NO EVAL"*) ok "and it names the untraced behavior" ;;
  *) bad "the gap did not name which behavior was untraced" ;;
esac

ORPHAN_E='  - id: eval_1
    description: traced fine
    runnable: bash
    verifies: [B-1]
    terminal: true
  - id: eval_2
    description: this eval maps to no behavior at all
    runnable: bash
    terminal: true
  - id: eval_3
    description: covers the second behavior
    runnable: bash
    verifies: [B-2]
    terminal: true'
mk_spec "$TMP/orphan-e.md" "$ORPHAN_E"
if run 1 "$TMP/orphan-e.md" && [ "$(last)" = "DOD=GAPS" ]; then
  ok "an eval with no verifies: mapping → exit 1 + DOD=GAPS (orphan evals count too)"
else
  bad "expected exit 1 + DOD=GAPS for an orphan eval (got $RC / $(last))"
fi

mk_spec "$TMP/none.md" "  # nothing declared"
if run 1 "$TMP/none.md" && [ "$(last)" = "DOD=GAPS" ]; then
  ok "no success_criteria at all → GAPS, never COMPLETE"
else
  bad "a spec with no evals must not report COMPLETE (got $RC / $(last))"
fi

# ---------------------------------------------------------------------------
echo
echo "[5] the token is the LAST stdout line, and usage fails closed"
# ---------------------------------------------------------------------------
if OUT="$("$TASKSPEC_ENGINE" dod "$TMP/block.md" 2>/dev/null)"; then
  [ "$(printf '%s\n' "$OUT" | tail -1)" = "DOD=COMPLETE" ] \
    && ok "the machine token is the last STDOUT line (gaps go to stderr)" \
    || bad "the token is not the last stdout line"
else
  bad "the happy path must exit 0"
fi
rc=0; OUT="$("$TASKSPEC_ENGINE" dod "$TMP/nope.md" 2>&1)" || rc=$?
if [ "$rc" = 2 ] && [ "$(printf '%s\n' "$OUT" | tail -1)" = "DOD=USAGE_ERROR" ]; then
  ok "a missing spec → exit 2 + DOD=USAGE_ERROR"
else
  bad "expected exit 2 + DOD=USAGE_ERROR (got $rc / $(printf '%s\n' "$OUT" | tail -1))"
fi
rc=0; OUT="$("$TASKSPEC_ENGINE" dod 2>&1)" || rc=$?
[ "$rc" = 2 ] && ok "no argument → exit 2" || bad "no argument should be a usage error (got $rc)"

# ---------------------------------------------------------------------------
echo
echo "[6] the CLI door is byte-parity with the standalone engine, and read-only"
# ---------------------------------------------------------------------------
BEFORE="$(cd "$TMP" && find . -type f -exec cksum {} + | sort)"
DIRECT="$("$TASKSPEC_ENGINE" dod "$TMP/block.md" 2>&1)"
VIA="$(cd "$TMP" && bash "$CVG" tasks dod "block.md" 2>&1)"
if [ "$DIRECT" = "$VIA" ]; then
  ok "cvg tasks dod is byte-identical to the standalone engine"
else
  bad "the CLI door diverges from the standalone engine"
fi
AFTER="$(cd "$TMP" && find . -type f -exec cksum {} + | sort)"
if [ "$BEFORE" = "$AFTER" ]; then
  ok "rendering a DoD writes nothing — it is a read-only surface"
else
  bad "the DoD render mutated the tree"
fi

# ---------------------------------------------------------------------------
echo
echo "[7] a lite-profile spec says the evals ARE the definition of done"
# ---------------------------------------------------------------------------
LITE="$TMP/lite.md"
python3 - "$TMP/block.md" "$LITE" <<'PY'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
s = re.sub(r"## Behavior\n.*?(?=## Success Criteria)", "", s, flags=re.S)
s = re.sub(r"verifies: \[B-\d+\]\n", "", s)
open(sys.argv[2], "w", encoding="utf-8").write(s)
PY
if run 0 "$LITE"; then
  case "$OUT" in
    *"no Behavior zone"*) ok "no Behavior zone → it says so instead of reporting a phantom gap" ;;
    *) bad "a lite spec should explain why there is no matrix" ;;
  esac
else
  bad "a lite-profile spec must still render at exit 0 (got $RC)"
fi

# ---------------------------------------------------------------------------
echo
echo "=================================================================="
printf 'rows: %s   failed: %s\n' "$rows" "$failed"
if [ "$failed" -eq 0 ]; then
  echo "TASKS_DOD_TESTS=PASS"; exit 0
fi
echo "TASKS_DOD_TESTS=FAIL"; exit 1
