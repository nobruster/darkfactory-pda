#!/bin/bash
# check-lesson.sh — Converge teaching-companion gate checker. v0.3.0
# Verifies a lesson produced by pass-to-lesson is structurally gate-ready:
#   1. all required sections present (exact template names, case-insensitive,
#      trailing punctuation tolerated — substring decoys do NOT count)
#   2. every '### <component>' walkthrough block carries 'what breaks downstream'
#   3. the Decisions table has at least one row (header + separator + >=1 row);
#      whether each row names a REAL rejected alternative stays a human check
#   4. Check yourself carries 3-5 numbered questions
#   5. declared emitter modes (adept/review/map) are present and well-formed:
#      adept → all five labels per '### <component>' block; review → >=3 'Q:'
#      cards AND every one of the day 1/3/7/21 checkpoints; map → edge lines
#   6. with --immutable <path>...: every taught artifact is unmodified
#      ('git status --porcelain' clean; modified or untracked-but-referenced
#      fails; outside a git repo it warns and skips, never crashes)
# Exit codes are contracts: 0 pass · 1 fail · 2 usage error. The LAST stdout
# line is always exactly one machine token:
#   CHECK_LESSON=PASS | CHECK_LESSON=FAIL | CHECK_LESSON=USAGE_ERROR
# Warns (never fails) where judgment stays human (coverage vs. the pass's
# real inventory can only be checked against git, not the file alone).
# bash 3.2 safe (macOS system bash). Deps: awk, grep, sed; git only for --immutable.

set -euo pipefail

usage() {
  echo "usage: check-lesson.sh <lesson-file> [--immutable <taught-artifact-path>...]" >&2
  echo "CHECK_LESSON=USAGE_ERROR"
  exit 2
}

FILE="${1:-}"
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  usage
fi

# --immutable consumes every argument after it:
#   check-lesson.sh lesson.md --immutable docs/brd-x.md docs/adrs/
IMMUTABLE=()
N_IMMUTABLE=0
if [ $# -ge 2 ]; then
  if [ "${2:-}" = "--immutable" ]; then
    shift 2
    if [ $# -eq 0 ]; then usage; fi
    IMMUTABLE=("$@")
    N_IMMUTABLE=$#
  else
    usage
  fi
fi

FAIL=0
pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=1; }
warn() { printf 'WARN  %s\n' "$1"; }

# --- section helpers: exact template-name matching --------------------------
# A heading matches a section only when its FULL text equals the template name
# (case-insensitive, trailing punctuation tolerated). "## Notes on why this
# pass exists" no longer satisfies "## Why this pass exists".
AWK_NORM='
function norm(s) {
  s = tolower(s)
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", s)
  gsub(/[.:;!?]+$/, "", s)
  gsub(/[[:space:]]+$/, "", s)
  return s
}
'

has_section() { # <exact-template-name> → rc 0 when a "## <name>" heading exists
  awk -v want="$1" "$AWK_NORM"'
    /^##[^#]/ {
      line = $0
      sub(/^##+[[:space:]]*/, "", line)
      if (norm(line) == tolower(want)) { found = 1; exit }
    }
    END { exit(found ? 0 : 1) }
  ' "$FILE"
}

# --- extract a section body: lines after "## <name>" until the next "## " ---
section() {
  awk -v want="$1" "$AWK_NORM"'
    /^##[^#]/ {
      line = $0
      sub(/^##+[[:space:]]*/, "", line)
      inside = (norm(line) == tolower(want)) ? 1 : 0
      next
    }
    inside { print }
  ' "$FILE"
}

# 1 — required sections (exact template names; an honestly-empty section still
# needs its heading — silence is indistinguishable from an oversight)
for SEC in "TL;DR" "Why this pass exists" "The artifact, component by component" "Decisions and roads not taken" "Vocabulary" "What to watch" "Check yourself"; do
  if has_section "$SEC"; then
    pass "section present: $SEC"
  else
    fail "section missing: $SEC"
  fi
done

# 2 — every '### <component>' block in the walkthrough carries the fourth part
# of the treatment ('what breaks downstream') — section-wide counts would let
# one component's line cross-satisfy another's absence
CW_BODY="$(section "The artifact, component by component")"
CW_STATS="$(printf '%s\n' "$CW_BODY" | awk '
  /^### / {
    if (inblock && !hit) { bad++; names = names "\n" cname }
    cname = $0; sub(/^###[[:space:]]*/, "", cname)
    n++; hit = 0; inblock = 1; next
  }
  tolower($0) ~ /breaks downstream/ { hit = 1 }
  END {
    if (inblock && !hit) { bad++; names = names "\n" cname }
    printf "%d %d%s\n", n, bad, names
  }
')"
C_LINE="${CW_STATS%%$'\n'*}"
C_COUNT="${C_LINE%% *}"
B_BAD="${C_LINE##* }"
case "$CW_STATS" in
  *$'\n'*) B_NAMES="${CW_STATS#*$'\n'}" ;;
  *)       B_NAMES="" ;;
esac
if [ "$C_COUNT" -eq 0 ]; then
  fail "walkthrough has no components (need at least one '### <component>' block)"
elif [ "$B_BAD" -gt 0 ]; then
  fail "walkthrough: $B_BAD of $C_COUNT component(s) lack 'what breaks downstream' — the fourth part is the test of understanding"
  printf '%s\n' "$B_NAMES" | sed 's/^/      missing: /'
else
  pass "walkthrough: $C_COUNT component(s), each with 'what breaks downstream'"
fi

# 3 — decisions table non-empty (each row naming a REAL rejected alternative
# and why it lost stays a human criterion — the script counts rows, not sense)
D_BODY="$(section "Decisions and roads not taken")"
D_ROWS=$(printf '%s\n' "$D_BODY" | grep -cE '^\|' || true)
if [ "$D_ROWS" -ge 3 ]; then   # header + separator + >=1 row
  pass "decisions table has at least one row (decision + rejected alternative)"
else
  fail "decisions table empty — every locked decision needs a rejected alternative and why it lost"
fi

# 4 — check-yourself question count
Q_COUNT=$(section "Check yourself" | grep -cE '^[0-9]+\.' || true)
if [ "$Q_COUNT" -ge 3 ] && [ "$Q_COUNT" -le 5 ]; then
  pass "Check yourself: $Q_COUNT question(s) (3-5 required)"
else
  fail "Check yourself: $Q_COUNT question(s) — need 3-5 numbered questions"
fi

# 5 — advisory: unresolved rationale markers
if grep -qiE 'alternative unrecorded' "$FILE"; then
  warn "'alternative unrecorded' marker(s) present — confirm each is flagged under What to watch"
fi

# 6 — teaching modes. A lesson declares its modes on a `modes:` line;
# emitter modes (adept/review/map) are gate-checkable, reshape modes are
# behavioral (advisory). No modes: line → nothing here runs (full back-compat).
MODES_LINE="$(grep -iE '^>?[[:space:]]*modes:' "$FILE" | head -1 | sed -E 's/^[^:]*://; s/^[[:space:]]*//; s/[[:space:]]*$//' || true)"
if [ -n "$MODES_LINE" ]; then
  pass "modes declared: $MODES_LINE"
  has_mode() { printf '%s' "$MODES_LINE" | grep -qiw "$1"; }

  if has_mode adept; then
    AB="$(section "ADEPT explanations")"
    if [ -z "$AB" ]; then
      fail "mode 'adept' declared but no '## ADEPT explanations' section"
    else
      # all five labels per '### <component>' block — section-wide counts
      # would let one complete block cross-satisfy an incomplete one
      ADEPT_STATS="$(printf '%s\n' "$AB" | awk '
        BEGIN { split("Analogy Diagram Example Plain-English Technical", lbl, " ") }
        function missing(  i, m) {
          m = ""
          for (i = 1; i <= 5; i++) if (!seen[i]) m = m " " lbl[i]
          return m
        }
        /^### / {
          if (inblock) { m = missing(); if (m != "") { bad++; names = names "\n" cname ":" m } }
          cname = $0; sub(/^###[[:space:]]*/, "", cname)
          n++; inblock = 1
          for (i = 1; i <= 5; i++) seen[i] = 0
          next
        }
        { for (i = 1; i <= 5; i++) if (index($0, "**" lbl[i] ":") > 0) seen[i] = 1 }
        END {
          if (inblock) { m = missing(); if (m != "") { bad++; names = names "\n" cname ":" m } }
          printf "%d %d%s\n", n, bad, names
        }
      ')"
      A_LINE="${ADEPT_STATS%%$'\n'*}"
      A_BLOCKS="${A_LINE%% *}"
      A_BAD="${A_LINE##* }"
      case "$ADEPT_STATS" in
        *$'\n'*) A_NAMES="${ADEPT_STATS#*$'\n'}" ;;
        *)       A_NAMES="" ;;
      esac
      if [ "$A_BLOCKS" -eq 0 ]; then
        fail "adept: '## ADEPT explanations' has no '### <component>' blocks (one block per load-bearing component)"
      elif [ "$A_BAD" -gt 0 ]; then
        fail "adept: $A_BAD of $A_BLOCKS ADEPT block(s) missing label(s) — every component block carries all five"
        printf '%s\n' "$A_NAMES" | sed 's/^/      missing:/'
      else
        pass "adept: $A_BLOCKS component block(s), all five ADEPT labels each"
      fi
    fi
  fi

  if has_mode review; then
    RB="$(section "Review schedule")"
    if [ -z "$RB" ]; then
      fail "mode 'review' declared but no '## Review schedule' section"
    else
      QN=$(printf '%s\n' "$RB" | grep -cE '^Q:' || true)
      miss=""
      for D in 1 3 7 21; do
        if ! printf '%s\n' "$RB" | grep -qiE "day +$D([^0-9]|\$)"; then
          miss="$miss $D"
        fi
      done
      if [ "$QN" -ge 3 ] && [ -z "$miss" ]; then
        pass "review: $QN flashcard(s) + all four checkpoints (day 1 · 3 · 7 · 21)"
      else
        fail "review: need >=3 'Q:' cards (have $QN) and every checkpoint day 1/3/7/21 (missing:${miss:- none}) — spacing is the point"
      fi
    fi
  fi

  if has_mode map; then
    MB="$(section "Concept map")"
    if [ -z "$MB" ]; then
      fail "mode 'map' declared but no '## Concept map' section"
    else
      if printf '%s\n' "$MB" | grep -v '<!--' | grep -qE -- '-->'; then
        pass "map: concept map carries edges"
      else
        fail "map: '## Concept map' has no edges (expected 'A --> B' lines below the answer marker)"
      fi
    fi
  fi

  for M in teachback socratic why mix; do
    if has_mode "$M"; then
      warn "mode '$M' is behavioral (reshapes quiz/walkthrough) — not script-verifiable; confirm it was honored"
    fi
  done
fi

# 7 — immutability of taught artifacts (--immutable). Teaching changes
# nothing: every taught artifact must sit exactly as the pass left it
# (modified or untracked-but-referenced fails). Only verifiable inside a git
# repo; outside one, WARN and skip — never crash.
if [ "$N_IMMUTABLE" -gt 0 ]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if DIRTY="$(git status --porcelain -- "${IMMUTABLE[@]}" 2>/dev/null)"; then
      if [ -z "$DIRTY" ]; then
        pass "immutable: $N_IMMUTABLE taught artifact(s) unmodified — git status clean"
      else
        N_DIRTY=$(printf '%s\n' "$DIRTY" | grep -c . || true)
        fail "immutable: $N_DIRTY taught artifact(s) modified or untracked — the lesson changes nothing in what it teaches"
        printf '%s\n' "$DIRTY" | sed 's/^/      /'
      fi
    else
      fail "immutable: 'git status --porcelain' failed — could not verify the taught artifacts (check the paths)"
    fi
  else
    warn "--immutable given but not inside a git repo — skipping the immutability check; confirm by hand that the taught artifacts are unmodified"
  fi
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "GATE: PASS — the lesson is teach-ready; walk it, then quiz (unless --quiz off)."
  echo "CHECK_LESSON=PASS"
  exit 0
else
  echo "GATE: FAIL — fix the items above; the lesson is not yet gate-ready."
  echo "CHECK_LESSON=FAIL"
  exit 1
fi
