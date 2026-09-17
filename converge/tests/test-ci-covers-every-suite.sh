#!/usr/bin/env bash
# test-ci-covers-every-suite.sh — a suite that exists but never runs is worse
# than a missing one.
#
# WHY THIS EXISTS
# On 2026-07-29 an audit found NINE working test suites the workflow never
# invoked: Pass 3 (reqs-to-swimlane-plans), Pass 4 (sketch-plans-adversarial-
# review — THE BARRIER, the last human sign-off in the whole method), the
# teaching companion, the legacy safety contracts, skill-creator, and four of
# task-spec's own suites. All nine passed when finally run by hand, so nothing was
# broken — but nothing was PROVING they weren't, and the repo read as if they were
# covered. That is the failure mode: coverage on the tin, not in the pipeline.
#
# The list in ci.yml cannot police itself, so this does. Add a suite and forget to
# wire it, and this fails with the exact path to add.
#
# WHAT COUNTS AS A SUITE
# An executable *.sh under tests/ or skills/*/tests/ whose name starts with
# `test-` or is exactly `run-tests.sh`. Helpers, generators and fixtures are not
# suites; EXEMPT below is the recorded, reasoned list of non-suites — every entry
# needs a why, because an exemption is how a real gap gets hidden.
#
# Token: CI_COVERAGE=PASS | CI_COVERAGE=FAIL
# bash 3.2 safe. Deps: grep, sed, find.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
cd "$REPO" || { echo "cannot enter repo"; echo "CI_COVERAGE=FAIL"; exit 1; }

WORKFLOW=".github/workflows/ci.yml"
if [ ! -f "$WORKFLOW" ]; then
  echo "  FAIL — no $WORKFLOW to check against"
  echo "CI_COVERAGE=FAIL"; exit 1
fi

# EXEMPT — non-suites, each with its reason. Keep this list SHORT and justified.
#   this file itself          : it IS the coverage gate; CI invokes it by name
#   task-spec/tests/conformance/*: adapter fixtures driven BY the suites, not suites
is_exempt() {
  case "$1" in
    tests/test-ci-covers-every-suite.sh) return 0 ;;
    */tests/conformance/*)               return 0 ;;
    *) return 1 ;;
  esac
}

echo "=================================================================="
echo "test-ci-covers-every-suite.sh — every suite is wired into CI"
echo "=================================================================="

MISSING=""
TOTAL=0
COVERED=0

# Collect candidate suites, portably (no mapfile, no process substitution).
LIST="$(find tests skills -type f -name '*.sh' 2>/dev/null \
        | grep -E '(^|/)tests/' \
        | grep -E '/(test-[^/]+|run-tests)\.sh$' \
        | sort)"

for f in $LIST; do
  is_exempt "$f" && continue
  TOTAL=$((TOTAL + 1))
  if grep -qF -- "$f" "$WORKFLOW"; then
    COVERED=$((COVERED + 1))
  else
    MISSING="${MISSING}${MISSING:+ }$f"
  fi
done

echo
echo "suites found: $TOTAL   wired into CI: $COVERED"

if [ -n "$MISSING" ]; then
  echo
  echo "  FAIL — these suites exist and CI never runs them:"
  for m in $MISSING; do echo "      $m"; done
  echo
  echo "  Add each to $WORKFLOW, or add it to EXEMPT in this file WITH a reason."
  echo "CI_COVERAGE=FAIL"; exit 1
fi

echo "  ok   — every suite in the package is invoked by the workflow"

# The counter-check: a pass here must mean something. If the workflow somehow
# references no suites at all, the loop above would trivially "cover" nothing.
REFS="$(grep -cE '^[[:space:]]+bash (skills|tests)/' "$WORKFLOW" 2>/dev/null || echo 0)"
REFS="${REFS//[^0-9]/}"; REFS="${REFS:-0}"
if [ "$REFS" -lt 8 ]; then
  echo "  FAIL — the workflow only invokes $REFS suite(s); that cannot be right"
  echo "CI_COVERAGE=FAIL"; exit 1
fi
echo "  ok   — the workflow invokes $REFS suite line(s), so the check has teeth"

echo
echo "=================================================================="
echo "CI_COVERAGE=PASS"
