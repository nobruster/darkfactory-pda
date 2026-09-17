#!/bin/bash
# run-tests.sh — table-driven regression suite for the Pass 0 gate
# (check-brd.sh). Every row: fixture + mode, the exit code it MUST produce,
# a pattern the output MUST contain (the *intended reason* — a fixture
# failing for the wrong reason is a broken test, not a pass), and a pattern
# the output MUST NOT contain (the handoff verdict guarding rule: only a
# canonical brief may be handed to Pass 1).
#
# Exit 0 iff every row holds. bash 3.2 safe.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="$HERE/../scripts/check-brd.sh"
FIX="$HERE/fixtures"

TOTAL=0
FAILED=0

# run_case <name> <args...> -- <expected_exit> <must_match> <must_not_match>
run_case() {
  NAME="$1"; shift
  ARGS=""
  while [ "$1" != "--" ]; do ARGS="$ARGS $1"; shift; done
  shift
  WANT_RC="$1"; MUST="$2"; MUST_NOT="$3"

  TOTAL=$((TOTAL + 1))
  # shellcheck disable=SC2086  # ARGS is a deliberate word-split flag list
  OUT="$(bash "$CHECK" $ARGS 2>&1)"
  RC=$?

  ROW_OK=1
  REASON=""
  if [ "$RC" -ne "$WANT_RC" ]; then
    ROW_OK=0; REASON="exit $RC, wanted $WANT_RC"
  fi
  if [ -n "$MUST" ] && ! printf '%s\n' "$OUT" | grep -qE "$MUST"; then
    ROW_OK=0; REASON="$REASON; missing required pattern: $MUST"
  fi
  if [ -n "$MUST_NOT" ] && printf '%s\n' "$OUT" | grep -qE "$MUST_NOT"; then
    ROW_OK=0; REASON="$REASON; forbidden pattern present: $MUST_NOT"
  fi

  if [ "$ROW_OK" -eq 1 ]; then
    printf 'ok    %-38s (exit %s)\n' "$NAME" "$RC"
  else
    printf 'FAIL  %-38s %s\n' "$NAME" "$REASON"
    printf '%s\n' "$OUT" | sed 's/^/      | /'
    FAILED=$((FAILED + 1))
  fi
}

# --- canonical briefs must pass, in more than one domain (universality) ----
run_case canonical-data          "$FIX/brd-canonical.md"        -- 0 '^CHECK_BRD=PASS$' ''
run_case canonical-devops        "$FIX/brd-canonical-devops.md" -- 0 '^CHECK_BRD=PASS$' ''

# --- the exit contract: a draft can NEVER reach Pass 1 ---------------------
run_case pending-signoff-blocks  "$FIX/brd-pending-signoff.md"  -- 1 "FAIL  Sign-off: owner verdict 'canonical' missing" 'hand off to Pass 1'
run_case pending-signoff-draftok --draft "$FIX/brd-pending-signoff.md" -- 0 '^CHECK_BRD=DRAFT_OK$' 'hand off to Pass 1'
run_case draft-never-authorizes  --draft "$FIX/brd-canonical.md" -- 0 '^CHECK_BRD=DRAFT_OK$' 'hand off to Pass 1'

# --- each negative fails for its INTENDED reason ---------------------------
run_case empty-scope             "$FIX/brd-empty-scope.md"      -- 1 'FAIL  Scope: In has no entries' ''
run_case blank-owner             "$FIX/brd-blank-owner.md"      -- 1 'FAIL  Open questions: .*owner'  ''
run_case no-provenance           "$FIX/brd-no-provenance.md"    -- 1 'FAIL  numbers in Problem/Goals carry no provenance tag' ''
run_case no-provenance-draft     --draft "$FIX/brd-no-provenance.md" -- 0 'WARN  numbers in Problem/Goals carry no provenance tag' 'hand off to Pass 1'
run_case guessed-without-oq      "$FIX/brd-guessed-no-oq.md"    -- 1 'FAIL  \(guessed\) number\(s\) with no open question' ''

# --- second-eyes hardening (v0.3.1): the gate survives its own template ----
run_case template-copy-blocked   "$FIX/brd-template-copy.md"    -- 1 "FAIL  Sign-off: owner verdict 'canonical' missing" 'hand off to Pass 1'
run_case codefence-evasion       "$FIX/brd-codefence-evasion.md" -- 1 "FAIL  Sign-off: owner verdict 'canonical' missing" 'hand off to Pass 1'
run_case oq-shape-fails-closed   "$FIX/brd-oq-evasion.md"       -- 1 'record shape' 'hand off to Pass 1'
run_case oq-shape-draft-warns    --draft "$FIX/brd-oq-evasion.md" -- 0 'record shape.*draft: advisory' 'hand off to Pass 1'
run_case invalid-date-blocked    "$FIX/brd-bad-date.md"         -- 1 'FAIL  Sign-off: no valid ISO date' 'hand off to Pass 1'

# --- usage errors exit 2 AND still end in the machine token (v0.3.1) -------
run_case flags-conflict          --draft --no-go "$FIX/nogo-valid.md" -- 2 '^CHECK_BRD=USAGE_ERROR$' 'CHECK_BRD=NOGO'
run_case unknown-flag            -draft "$FIX/brd-canonical.md" -- 2 '^CHECK_BRD=USAGE_ERROR$' 'CHECK_BRD=PASS'
run_case two-files-refused       "$FIX/brd-pending-signoff.md" "$FIX/brd-canonical.md" -- 2 '^CHECK_BRD=USAGE_ERROR$' 'CHECK_BRD=PASS'
run_case missing-file-token      "$FIX/does-not-exist.md"       -- 2 '^CHECK_BRD=USAGE_ERROR$' ''

# --- semantic judgment stays human: altitude only WARNS --------------------
run_case altitude-warns-only     "$FIX/brd-altitude-warn.md"    -- 0 'WARN  possible solution-shape leak' ''
run_case altitude-still-passes   "$FIX/brd-altitude-warn.md"    -- 0 '^CHECK_BRD=PASS$' ''

# --- the no-go exit has a validator too ------------------------------------
run_case nogo-valid              --no-go "$FIX/nogo-valid.md"   -- 0 '^CHECK_BRD=NOGO_OK$' ''
run_case nogo-invalid            --no-go "$FIX/nogo-invalid.md" -- 1 'reopen' ''
run_case nogo-invalid-token      --no-go "$FIX/nogo-invalid.md" -- 1 '^CHECK_BRD=NOGO_INVALID$' ''

# --- v0.4.0: exact headings, real scope entries, calendar-real dates --------
run_case section-prefix-evasion  "$FIX/brd-section-evasion.md" -- 1 'FAIL  section missing: Problem' 'hand off to Pass 1'
run_case scope-contentfree-in    "$FIX/brd-scope-none.md"      -- 1 'FAIL  Scope: In has no entries' ''
run_case calendar-date-blocked   "$FIX/brd-bad-date2.md"       -- 1 'FAIL  Sign-off: no valid ISO date' 'hand off to Pass 1'

# --- v0.4.0: per-line provenance — one tag no longer launders the rest ------
run_case provenance-perline-evasion "$FIX/brd-provenance-evasion.md" -- 1 'FAIL  Problem: .*no provenance tag on the line' 'carry no provenance tag'
run_case provenance-perline-draft --draft "$FIX/brd-provenance-evasion.md" -- 0 'WARN  Problem: .*no provenance tag on the line' 'hand off to Pass 1'
run_case provenance-perline-pass "$FIX/brd-provenance-pass.md" -- 0 '^CHECK_BRD=PASS$' ''

# --- v0.4.0: hygiene WARNs surface but stay advisory (never fail) -----------
run_case warn-donothing-evidence "$FIX/brd-canonical.md"       -- 0 'WARN  no do-nothing-test evidence' ''
run_case warn-exec-summary-long  "$FIX/brd-provenance-pass.md" -- 0 'WARN  Executive summary runs' ''
run_case warn-no-decider         "$FIX/brd-provenance-pass.md" -- 0 'WARN  no decider named' ''

# --- v0.4.0: the no-go gate fails closed per structural element -------------
run_case nogo-template-shape     --no-go "$FIX/nogo-template-shape.md" -- 0 '^CHECK_BRD=NOGO_OK$' ''
run_case nogo-bad-date           --no-go "$FIX/nogo-bad-date.md" -- 1 'FAIL  no-go: no valid ISO date' 'CHECK_BRD=NOGO_OK'
run_case nogo-missing-owner      --no-go "$FIX/nogo-missing-owner.md" -- 1 'FAIL  no-go: no named owner' ''

# --- PDF policy: text in, or no gate verdict at all -------------------------
PDF_TMP="${TMPDIR:-/tmp}/check-brd-test-$$.pdf"
: > "$PDF_TMP"
run_case pdf-refused             "$PDF_TMP"                     -- 2 '[Cc]onvert' 'CHECK_BRD=(PASS|FAIL|DRAFT|NOGO)'
run_case pdf-refused-token       "$PDF_TMP"                     -- 2 '^CHECK_BRD=USAGE_ERROR$' ''
rm -f "$PDF_TMP"

# --- the true positive: a real signed BRD stays green ----------------------
# The fixture is OWNED here, not borrowed from a use case. A skill that reaches
# outside itself for a golden is a skill that breaks when the use case moves.
run_case golden-signed-brd       "$FIX/golden-signed-brd.md"    -- 0 '^CHECK_BRD=PASS$' ''

echo "────────────────────────────────────────────"
echo "rows: $TOTAL  failed: $FAILED"
[ "$FAILED" -eq 0 ]
