#!/bin/bash
# run-tests.sh — regression suite for the Pass 2 gate (scaffold-adr.sh).
#
# WHY THIS EXISTS
# Pass 2 was the ONLY pass in the chain with no suite at all. `CHECK_ADR` was
# declared closed on a real proving-ground run (7 ADRs canonical) and nothing
# anywhere proved the gate could still refuse a bad set. A gate that has never been
# shown to FAIL is a claim, not a check.
#
# (Deliberately no fixture path named above: the shipped product must not reference
# the proving ground, and CI enforces that with a blunt grep that cannot tell a
# comment from an import — which is exactly what makes it ungameable.)
#
# WHAT PASS 2 ACTUALLY GUARDS
# A grounding ADR records a FACT or CONSTRAINT about the terrain — what IS, or what
# MUST hold — with evidence. It must NOT contain design ("build X"). That boundary
# is the pass's one invariant, and `--check` is its deterministic guard. So the
# suite's centre of gravity is the two drift guards plus the set-level contract
# (context record, glossary, lifecycle, bidirectional supersede links).
#
# WHY FIXTURES ARE BUILT, NOT STORED
# This gate reasons over a DIRECTORY (the whole ADR set) and over cross-file
# supersede links, not over one document. Committing ~15 near-identical trees would
# obscure exactly what each case mutates; building each set from one known-good
# generator makes the mutation the point of the test. Every case is one deliberate
# deviation from a set that is proven green in row 1.
#
# Exit 0 iff every row holds. Last line is a machine token:
#   CHECK_ADR_TESTS=PASS | CHECK_ADR_TESTS=FAIL
# bash 3.2 safe (stock macOS). Deps: awk, grep, sed.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
SCAFFOLD="$HERE/../scripts/scaffold-adr.sh"
WORK="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/adr-tests.$$")"
mkdir -p "$WORK"
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

TOTAL=0
FAILED=0

# ---------------------------------------------------------------------------
# Fixture generators
# ---------------------------------------------------------------------------

# new_set <dir> — a MINIMAL VALID set: filled context record + glossary.
# Deliberately contains no HTML comments: `--check` treats a surviving
# `<!-- -->` as an unfilled scaffold, which is the whole point of row "unfilled".
new_set() {
  d="$1"
  mkdir -p "$d/docs/adrs"
  cat > "$d/docs/CONTEXT.md" <<'EOF'
# CONTEXT — pinned vocabulary

- **capture**: moving source rows into the analytical lane, unchanged.
- **gold**: the modelled layer a consumer is allowed to read.
EOF
  cat > "$d/docs/adrs/0000-context.md" <<'EOF'
---
adr: "0000"
status: accepted
date: 2026-07-29
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "owner"
---

# 0000 — Context: the ground we stand on

## Terrain

Brownfield: an operational Postgres already serves the application.

## Given surface

Postgres 16 with customers, products, orders and payments.

## Build surface

The analytical lane: capture, transform, serve.

## Spec

docs/tech-spec-analytics.md, signed off 2026-07-19.
EOF
}

# add_adr <dir> <num> <slug> [status] — a VALID numbered grounding fact.
add_adr() {
  d="$1"; num="$2"; slug="$3"; st="${4:-accepted}"
  cat > "$d/docs/adrs/$num-$slug.md" <<EOF
---
adr: "$num"
status: $st
date: 2026-07-29
ground: brownfield
converge_pass: 2
spec_ref: "R-1"
supersedes: ""
superseded_by: ""
deciders: "owner"
---

# $num — payments link to orders on order_id

## Context

A Pass 3 planner would otherwise guess how payments attach to products.

## Decision

\`payments.order_id\` is the only column linking payments to orders. No
\`payments.product_id\` exists in this schema.

## Rejected reading

That payments carried a product reference directly. The column is absent, so
any per-product revenue figure has to travel through orders.

## Evidence

\`\`\`sh
psql -d ecommerce -c '\\d payments'
\`\`\`

observed: columns are payment_id, order_id, amount, status, created_at.

## Consequences

Pass 3 plans route product attribution transitively through orders.
Re-verify when: the payments table gains or loses a column.
EOF
}

# ---------------------------------------------------------------------------
# expect <name> <dir> <flags...> -- <want_rc> <must_match> <must_not_match>
# ---------------------------------------------------------------------------
# A row asserts the INTENDED REASON, not merely the verdict. A set that fails for
# the wrong reason is a broken test wearing a green shirt — the same discipline the
# Pass 0 suite uses.
expect() {
  NAME="$1"; DIR="$2"; shift 2
  ARGS=""
  while [ "$1" != "--" ]; do ARGS="$ARGS $1"; shift; done
  shift
  WANT_RC="$1"; MUST="$2"; MUST_NOT="$3"

  TOTAL=$((TOTAL + 1))
  # shellcheck disable=SC2086  # ARGS is a deliberate word-split flag list
  OUT="$(cd "$DIR" && bash "$SCAFFOLD" $ARGS 2>&1)"
  RC=$?

  ROW_OK=1; REASON=""
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
    printf 'ok    %-44s (exit %s)\n' "$NAME" "$RC"
  else
    printf 'FAIL  %-44s %s\n' "$NAME" "$REASON"
    printf '%s\n' "$OUT" | sed 's/^/      | /'
    FAILED=$((FAILED + 1))
  fi
}

echo "run-tests.sh — Pass 2 gate (scaffold-adr.sh)"
echo "──────────────────────────────────────────────────────────────────"

# ===========================================================================
# A · the happy path must be green — everything below is one mutation off it
# ===========================================================================
D="$WORK/a"; new_set "$D"; add_adr "$D" 0001 payments-join
expect valid-set-passes "$D" --check -- 0 '^CHECK_ADR=OK$' 'FAIL'
expect valid-set-passes-final "$D" --check --final -- 0 '^CHECK_ADR=OK$' 'OPEN'

# ===========================================================================
# B · the set-level contract
# ===========================================================================
D="$WORK/b-empty"; mkdir -p "$D/docs/adrs"
expect no-adrs-is-empty-not-ok "$D" --check -- 2 '^CHECK_ADR=EMPTY$' 'CHECK_ADR=OK'

D="$WORK/b-noctx"; new_set "$D"; add_adr "$D" 0001 payments-join
rm "$D/docs/adrs/0000-context.md"
expect missing-context-record-fails "$D" --check -- 1 'MISSING .*0000-context.md' '^CHECK_ADR=OK$'

D="$WORK/b-noglossary"; new_set "$D"; add_adr "$D" 0001 payments-join
rm "$D/docs/CONTEXT.md"
expect missing-glossary-fails "$D" --check -- 1 'MISSING .*CONTEXT.md' '^CHECK_ADR=OK$'

D="$WORK/b-emptyglossary"; new_set "$D"; add_adr "$D" 0001 payments-join
: > "$D/docs/CONTEXT.md"
expect empty-glossary-fails "$D" --check -- 1 'MISSING .*CONTEXT.md' '^CHECK_ADR=OK$'

# ===========================================================================
# C · an unfilled scaffold is not a record
# ===========================================================================
# The strongest case available: scaffold a REAL ADR through the tool and check it
# untouched. The template is all comments, so a freshly scaffolded set must FAIL.
# If this ever passes, the gate has stopped distinguishing a form from a record.
D="$WORK/c"; new_set "$D"
( cd "$D" && bash "$SCAFFOLD" "orders carry a status column" >/dev/null 2>&1 )
expect freshly-scaffolded-adr-is-unfilled "$D" --check -- 1 'UNFILLED' '^CHECK_ADR=OK$'

# ===========================================================================
# D · lifecycle + frontmatter
# ===========================================================================
D="$WORK/d-nostatus"; new_set "$D"; add_adr "$D" 0001 payments-join
sed -i.bak '/^status:/d' "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect missing-status-fails "$D" --check -- 1 "no 'status:' in YAML frontmatter" '^CHECK_ADR=OK$'

D="$WORK/d-badstatus"; new_set "$D"; add_adr "$D" 0001 payments-join
sed -i.bak 's/^status: accepted/status: sortof/' "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect status-outside-enum-fails "$D" --check -- 1 'not in lifecycle enum' '^CHECK_ADR=OK$'

# `proposed` is legal mid-pass and MUST block the pass CLOSING. Both halves are
# asserted, because a --final that never blocks is the same as no --final.
D="$WORK/d-proposed"; new_set "$D"; add_adr "$D" 0001 payments-join proposed
expect proposed-ok-without-final "$D" --check -- 0 '^CHECK_ADR=OK$' 'OPEN'
expect proposed-blocks-final "$D" --check --final -- 1 "OPEN .*still 'proposed'" '^CHECK_ADR=OK$'

# ===========================================================================
# E · supersede links must be bidirectional
# ===========================================================================
# Driven through the tool, which is the only sanctioned way to supersede.
D="$WORK/e"; new_set "$D"; add_adr "$D" 0001 payments-join
( cd "$D" && bash "$SCAFFOLD" --supersede 0001 "payments now carry a settlement id" >/dev/null 2>&1 )
NEWF="$(ls "$D"/docs/adrs/0002-*.md 2>/dev/null | head -1)"
TOTAL=$((TOTAL + 1))
if [ -n "$NEWF" ] \
   && grep -q '^supersedes: "0001"' "$NEWF" \
   && grep -q '^status: superseded' "$D/docs/adrs/0001-payments-join.md" \
   && grep -q '^superseded_by: "0002"' "$D/docs/adrs/0001-payments-join.md"; then
  printf 'ok    %-44s (both directions stamped)\n' supersede-stamps-both-directions
else
  printf 'FAIL  %-44s links not bidirectional\n' supersede-stamps-both-directions
  FAILED=$((FAILED + 1))
fi

D="$WORK/e-dangling"; new_set "$D"; add_adr "$D" 0001 payments-join
sed -i.bak 's/^supersedes: ""/supersedes: "0009"/' "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect dangling-supersede-fails "$D" --check -- 1 'LINK .*no 0009-\*\.md exists' '^CHECK_ADR=OK$'

D="$WORK/e-oneway"; new_set "$D"; add_adr "$D" 0001 payments-join; add_adr "$D" 0002 settlement-id
sed -i.bak 's/^supersedes: ""/supersedes: "0001"/' "$D/docs/adrs/0002-settlement-id.md" && rm -f "$D"/docs/adrs/*.bak
expect one-way-supersede-fails "$D" --check -- 1 'does not point back' '^CHECK_ADR=OK$'

expect supersede-missing-target-is-usage-error "$WORK/a" --supersede 4242 "no such adr" -- 1 '^CHECK_ADR=USAGE_ERROR$' ''

# ===========================================================================
# F · THE INVARIANT — design must not survive in a grounding record
# ===========================================================================
# Guard 1: a build-verb at line head, anywhere in the record.
for verb in Build Create Implement Refactor Migrate; do
  D="$WORK/f-$verb"; new_set "$D"; add_adr "$D" 0001 payments-join
  sed -i.bak "s|^\`payments.order_id\` is the only column.*|$verb a fct_revenue table keyed on order_id.|" \
    "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
  expect "drift-line-head-$verb-fails" "$D" --check -- 1 'DRIFT .*build-verb at line head' '^CHECK_ADR=OK$'
done

# Guard 2: mid-sentence modal design, scoped to Decision. This is the subtle one —
# it reads like a fact and is a plan.
D="$WORK/f-modal"; new_set "$D"; add_adr "$D" 0001 payments-join
sed -i.bak "s|^\`payments.order_id\` is the only column.*|The pipeline must therefore build a bridge table from orders.|" \
  "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect drift-modal-in-decision-fails "$D" --check -- 1 'DRIFT .*modal design language in Decision' '^CHECK_ADR=OK$'

# ...and the counter-test that keeps guard 2 honest: the SAME sentence in
# Consequences is legitimate — telling Pass 3 what it must respect is this
# section's entire job. If this row ever fails, the guard has over-reached and
# will start rejecting correct ADRs.
D="$WORK/f-modal-ok"; new_set "$D"; add_adr "$D" 0001 payments-join
printf '\nThe pipeline must therefore build its product rollup through orders.\n' \
  >> "$D/docs/adrs/0001-payments-join.md"
expect modal-in-consequences-is-allowed "$D" --check -- 0 '^CHECK_ADR=OK$' 'DRIFT'

# ===========================================================================
# G · required sections must carry content
# ===========================================================================
for sec in Context Decision Evidence Consequences; do
  D="$WORK/g-$sec"; new_set "$D"; add_adr "$D" 0001 payments-join
  awk -v s="## $sec" '
    $0 == s { print; skip = 1; next }
    /^## / && skip { skip = 0 }
    !skip { print }
    skip && /^## /  { print }
  ' "$D/docs/adrs/0001-payments-join.md" > "$D/tmp" && mv "$D/tmp" "$D/docs/adrs/0001-payments-join.md"
  expect "empty-section-$sec-fails" "$D" --check -- 1 "EMPTY .*section '$sec'" '^CHECK_ADR=OK$'
done

# ===========================================================================
# H · advisories must NOT fail the gate
# ===========================================================================
# H1/H5/H6 are NOTEs on purpose: they are judgement calls, and a gate that
# hard-fails on judgement gets switched off wholesale instead of aimed. Asserting
# they stay advisory is what stops a future edit from quietly promoting them.
D="$WORK/h"; new_set "$D"; add_adr "$D" 0001 payments-join
awk '
  /^## Rejected reading$/ { skip = 1; next }
  /^## / && skip          { skip = 0 }
  !skip                   { print }
' "$D/docs/adrs/0001-payments-join.md" > "$D/tmp" && mv "$D/tmp" "$D/docs/adrs/0001-payments-join.md"
sed -i.bak 's/^spec_ref: "R-1"/spec_ref: ""/' "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect advisories-warn-but-do-not-block "$D" --check -- 0 '^CHECK_ADR=OK$' '^CHECK_ADR=FAIL$'
expect advisories-are-actually-reported "$D" --check -- 0 "NOTE .*no 'Rejected reading'" ''
expect advisory-spec-ref-is-reported "$D" --check -- 0 'NOTE .*spec_ref is empty' ''

# An ADR with no Evidence HEADER at all is unfalsifiable — that one does block.
D="$WORK/h-noev"; new_set "$D"; add_adr "$D" 0001 payments-join
sed -i.bak 's/^## Evidence$/## Notes/' "$D/docs/adrs/0001-payments-join.md" && rm -f "$D"/docs/adrs/*.bak
expect no-evidence-section-fails "$D" --check -- 1 'WEAK .*no Evidence section' '^CHECK_ADR=OK$'

# ===========================================================================
# I · scaffold mechanics + usage contract
# ===========================================================================
D="$WORK/i"; new_set "$D"; rm "$D/docs/adrs/0000-context.md"
expect context-record-scaffolds "$D" --context -- 0 'Created .*0000-context.md' ''
expect context-record-is-written-once "$D" --context -- 1 '^CHECK_ADR=USAGE_ERROR$' ''

D="$WORK/i2"; new_set "$D"
TOTAL=$((TOTAL + 1))
( cd "$D" && bash "$SCAFFOLD" "orders carry a status column" >/dev/null 2>&1 )
( cd "$D" && bash "$SCAFFOLD" "payments carry a captured flag" >/dev/null 2>&1 )
if [ -f "$D/docs/adrs/0001-orders-carry-a-status-column.md" ] \
   && [ -f "$D/docs/adrs/0002-payments-carry-a-captured-flag.md" ]; then
  printf 'ok    %-44s (0001 then 0002, slugified)\n' numbering-and-slug-autoincrement
else
  printf 'FAIL  %-44s numbering/slug wrong: %s\n' numbering-and-slug-autoincrement "$(ls "$D/docs/adrs")"
  FAILED=$((FAILED + 1))
fi

expect no-title-is-usage-error       "$WORK/i2" ""            -- 1 '^CHECK_ADR=USAGE_ERROR$' ''
expect unsluggable-title-rejected    "$WORK/i2" "!!! ???"     -- 1 '^CHECK_ADR=USAGE_ERROR$' ''
expect unknown-flag-is-usage-error   "$WORK/i2" --nope        -- 1 '^CHECK_ADR=USAGE_ERROR$' ''
expect birth-status-superseded-refused "$WORK/i2" --status superseded "some fact" -- 1 '^CHECK_ADR=USAGE_ERROR$' ''
expect help-exits-clean              "$WORK/i2" --help        -- 0 'scaffold-adr.sh' 'CHECK_ADR=USAGE_ERROR'

# ===========================================================================
echo "──────────────────────────────────────────────────────────────────"
printf 'rows: %s  failed: %s\n' "$TOTAL" "$FAILED"
if [ "$FAILED" -eq 0 ]; then
  echo "CHECK_ADR_TESTS=PASS"
  exit 0
else
  echo "CHECK_ADR_TESTS=FAIL"
  exit 1
fi
