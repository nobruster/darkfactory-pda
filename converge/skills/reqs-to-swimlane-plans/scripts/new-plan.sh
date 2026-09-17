#!/usr/bin/env bash
# new-plan.sh — Converge Pass 3 (DECOMPOSE): scaffold a swimlane as a directory —
# one lean PRD index (_lane.md) plus one file per leg
# (leg-NN-<tech>.md) — or --check the swimlanes/ tree for altitude
# drift and structural completeness.
#
# The swimlane PRD is a lean INDEX: it names the seam, shows the architecture, and
# LINKS to its legs — it never embeds leg detail (so it never bloats). Each leg is
# its own atomic, independently-evolvable file. That split + the plan-altitude
# boundary (no SQL, no handler body, no atomic task with an eval — those are Pass 5)
# are the invariants --check guards.
#
# Usage:
#   new-plan.sh "capture"                          Scaffold swimlanes/capture/_lane.md
#   new-plan.sh --component "A · Capture" "capture" Set the identity line's component
#   new-plan.sh --consumes <seam> "serve"          Mark a DOWNSTREAM swimlane + its consumed seam
#   new-plan.sh --lane capture --leg 01-dlt         Scaffold swimlanes/capture/leg-01-dlt.md
#   new-plan.sh --dir path/to/sketch ...            Override the sketch directory
#   new-plan.sh --check                            Lint the swimlanes/ tree
#   new-plan.sh --help
#
# Layout (dir-per-swimlane — the folder names the seam ONCE, nothing repeats it):
#   swimlanes/
#     <seam>/
#       _lane.md                           the PRD (lean index; sorts above the legs)
#       leg-NN-<tech>.md                   one file per leg (full detail)
#
#   Legacy, still gated: swimlane-<seam>/swimlane-<seam>.plan.md (+ either leg shape).
#   A swimlane dir is recognized by CONTAINING a lane PRD, never by its name —
#   that is what lets the folder drop the prefix without the gate losing the lane.
#
# WHY NOTHING REPEATS THE FOLDER. The workspace adopted one naming rule — a folder
#   per artifact type, the slug on the file (cvg/docs/brd/<slug>.md). swimlanes/ was
#   the last place that still restated its own directory in every filename
#   (swimlane-models/swimlane-models-leg-01-staging.md), so one tree taught two
#   contradictory conventions. The folder names the seam once; the PRD is _lane.md
#   (no seam in it at all) and a leg is leg-NN-<tech>.md.
#
# THE ID DID NOT CHANGE. The stable reference key is still the fully-qualified
#   swimlane-<seam>-leg-NN (2-digit zero-pad) — it lives in each leg's `leg:`
#   frontmatter, is what --check verifies, and is what a Pass 5B task-spec cites.
#   Only the filename dropped the redundancy. <tech> stays a swappable display
#   label, NEVER part of the key. Legs are contiguous leg-01..leg-0N. Each leg
#   yields 1:N task-specs at Pass 5B. See references/legs.md.
#
# --check accepts BOTH filename shapes (new first, legacy second), because the
#   gate is the discovery key: a rename that the gate did not already understand
#   would report CHECK_PLAN=EMPTY and silently drop a workspace's Pass 3 evidence
#   mid-migration. Same additive rule the typed docs/ folders shipped under.
#
# Internal structure (field-grounded — Spec Kit / arc42 / Amazon PR-FAQ / INVEST /
#   Gherkin / Shape Up / ADR): PRD = lane-meta / identity+why / Seam / Architecture
#   (mermaid LR + steps) / Non-Goals / Legs index / Dependencies / Build order /
#   Open questions / Spec traceability. Leg = frontmatter (stable id, parent,
#   status, spec_ref) / Responsibility / Proves (Given/When/Then, 1-3, no evals) /
#   Independence / Consumes-Produces / Appetite / Yields / Re-verify when.
#
# Agent contract: every --check / usage surface ends in a stable machine token —
#   CHECK_PLAN=OK | FAIL | EMPTY | USAGE_ERROR. Pass 3's cvg subcommand gates on it.
# Exit:     0 = ok; 1 = drift/usage error; 2 = nothing to check
#
# bash 3.2-safe (runs on macOS system /bin/bash). No associative arrays, no mapfile.

set -euo pipefail

# The swimlane tree: canonical cvg/swimlanes/, legacy cvg/sketch/ (or a bare
# sketch/). Preference is by CONTENT, not existence — `cvg init` may have created
# an empty swimlanes/ beside a populated legacy sketch/, and picking the empty one
# would answer EMPTY and drop this workspace's Pass 3 evidence.
# NOTE: the literal "sketch" below is deliberate back-compat. A bulk rename already
# rewrote this comment once into naming the canonical path twice — leave it alone.
_lane_tree() {
  local c
  for c in swimlanes sketch; do
    if [ -d "$c" ] && [ -n "$(find "$c" -mindepth 2 -type f -name '*.md' -print 2>/dev/null | head -1)" ]; then
      printf '%s' "$c"; return 0
    fi
  done
  for c in swimlanes sketch; do
    if [ -d "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  printf 'swimlanes'
}
SKETCH_DIR="$(_lane_tree)"
COMPONENT=""
CONSUMES=""
LANE=""
LEG=""

usage() { sed -n '11,20p' "$0"; }

# ── Altitude-drift guards ─────────────────────────────────────────────────────
# SQL_RE — a SQL statement opening a line (the SELECT/handler-body leak).
SQL_RE='^[[:space:]]*(SELECT|INSERT[[:space:]]+INTO|UPDATE|DELETE[[:space:]]+FROM|CREATE[[:space:]]+(TABLE|VIEW|OR[[:space:]]+REPLACE)|WITH[[:space:]]+[A-Za-z_].*[[:space:]]+AS[[:space:]]*\(|MERGE[[:space:]]+INTO)[[:space:]]'
# TASK_RE — an atomic task id or an eval block; tasks live at tasks/T-*.md (Pass 5).
# The bare word "Task" used to be enough to trip this, which false-positived on
# Converge's OWN noun: the fork declaration the Pass 4 gate demands reads most
# naturally as "the plans become Task-Specs at Pass 5", and a line opening with
# that phrase was reported as an atomic-task leak. A real leak carries an ID or a
# label, so require one: a number/hash after "Task", or the T-NNNNNN id shape.
# Prose may now say Task-Spec; it still may not smuggle in "Task 4:" or "T-20260803-x".
TASK_RE='(^[[:space:]]*[-*>]?[[:space:]]*(Task[[:space:]]*[#0-9]|T-[0-9]{6,})[-: ]?|^[[:space:]]*(eval|acceptance[_-]?eval|bash[_-]?eval)[[:space:]]*:)'

# PRD sections that must be present (newline-delimited; spaces inside a pattern).
REQUIRED_PRD='Seam
Architecture
Non-?Goals|Out of scope
Legs
Dependenc(y|ies)
Build[ -]order
Open +question'

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

# altitude_drift <file> — echo DRIFT lines for SQL/task leaks; return 1 if any.
altitude_drift() {
  local f="$1" hits arc=0
  hits=$(grep -nEi "$SQL_RE" "$f" || true)
  if [ -n "$hits" ]; then
    echo "DRIFT  $f — SQL at a line head (that is Pass 5 / task-spec, not a plan):"
    printf '%s\n' "$hits" | sed 's/^/         /'; arc=1
  fi
  hits=$(grep -nEi "$TASK_RE" "$f" || true)
  if [ -n "$hits" ]; then
    echo "DRIFT  $f — atomic task / eval block (that is Pass 5 / task-spec, not a plan):"
    printf '%s\n' "$hits" | sed 's/^/         /'; arc=1
  fi
  return "$arc"
}

check_tree() {
  local rc=0 thread_seen=0 found=0 d prd lf n
  if [ ! -d "$SKETCH_DIR" ]; then
    echo "CHECK: no sketch dir $SKETCH_DIR/ — scaffold a swimlane first." >&2
    echo "CHECK_PLAN=EMPTY"; return 2
  fi

  for d in "$SKETCH_DIR"/*/; do
    [ -d "$d" ] || continue
    # A swimlane directory is identified by CONTAINING a lane PRD, not by its
    # name. That is what lets the folder drop the redundant "swimlane-" prefix
    # without the gate losing the ability to find a lane at all.
    #   _lane.md            canonical (sorts above the legs, names no seam twice)
    #   <anything>.plan.md  legacy (swimlane-<seam>.plan.md)
    prd=""
    [ -e "${d}_lane.md" ] && prd="${d}_lane.md"
    if [ -z "$prd" ]; then
      for p in "$d"*.plan.md; do [ -e "$p" ] && prd="$p"; done
    fi
    [ -n "$prd" ] || continue
    found=1

    # PRD altitude + mermaid + lane-meta + required sections + seam-evolution
    altitude_drift "$prd" || rc=1
    grep -qi '```mermaid' "$prd" || { echo "VISUAL $prd — no mermaid diagram; add the ## Architecture block (flowchart LR + numbered steps)."; rc=1; }

    if ! grep -qiE 'lane-meta:' "$prd"; then
      echo "WEAK   $prd — no 'lane-meta:' line (thread=<yes|no> · risk=<low|med|high> · owner=<stream>)."; rc=1
    else
      grep -qiE 'thread=(yes|no)' "$prd" || { echo "META   $prd — lane-meta missing a real thread=yes|no (H1)."; rc=1; }
      grep -qiE 'risk=(low|med|high)' "$prd" || { echo "META   $prd — lane-meta missing a real risk=low|med|high (H2)."; rc=1; }
      grep -qiE 'owner=[^[:space:]<]' "$prd" || { echo "META   $prd — lane-meta missing a real owner=<stream> (H3)."; rc=1; }
    fi
    if grep -qiE 'thread=yes' "$prd"; then thread_seen=1; fi

    local sec oldifs="$IFS"
    IFS='
'
    for sec in $REQUIRED_PRD; do
      IFS="$oldifs"
      grep -qiE "^#+ +.*($sec)" "$prd" || { echo "WEAK   $prd — no section matching /$sec/ (PRD needs Seam, Architecture, Non-Goals, Legs, Dependencies, Build order, Open questions)."; rc=1; }
      IFS='
'
    done
    IFS="$oldifs"

    if grep -qiE 'interface this lane consumes|consumes the seam|consumed seam' "$prd"; then
      grep -qiE 'seam evolution|additive|breaking' "$prd" || { echo "SEAM   $prd — downstream lane names a consumed seam but no evolution rule (H4)."; rc=1; }
    fi

    # Leg files in this swimlane dir. Two accepted shapes, canonical first:
    #   leg-NN-<tech>.md                  the folder carries the type, the file the slug
    #   swimlane-<seam>-leg-NN-<tech>.md  legacy — the filename repeated its directory
    # The two globs are mutually exclusive (a name starting with "leg-" has nothing
    # before "-leg-"), so no leg is counted twice into the contiguity check.
    local has_leg=0 leg_nums=""
    for lf in "$d"leg-*.md "$d"*-leg-*.md; do
      [ -e "$lf" ] || continue
      has_leg=1
      altitude_drift "$lf" || rc=1
      grep -qiE '^#+ +Responsibilit' "$lf" || { echo "LEG    $lf — no Responsibility section."; rc=1; }
      grep -qiE '^#+ +Proves' "$lf" || { echo "LEG    $lf — no Proves section (Given/When/Then acceptance criteria, 1-3, no evals)."; rc=1; }
      grep -qiE '^leg:[[:space:]]+swimlane-.*-leg-[0-9]{2}' "$lf" || { echo "LEG    $lf — frontmatter missing the stable key 'leg: swimlane-<seam>-leg-NN'."; rc=1; }
      grep -qiE '^status:' "$lf" || { echo "LEG    $lf — frontmatter missing 'status:'."; rc=1; }
      grep -qiE '^(parent|swimlane):' "$lf" || { echo "LEG    $lf — frontmatter missing a parent/swimlane pointer."; rc=1; }
      grep -qF "$(basename "$lf")" "$prd" || { echo "LINK   $prd — Legs index does not reference $(basename "$lf") (orphan leg)."; rc=1; }
      n="$(basename "$lf" | grep -oE 'leg-[0-9]{2}' | head -1)"
      leg_nums="$leg_nums$n
"
    done

    if [ "$has_leg" -eq 0 ]; then
      echo "WEAK   $d — no leg files (leg-NN-<tech>.md, or the legacy swimlane-<seam>-leg-NN-<tech>.md); a swimlane is its PRD + its legs."; rc=1
    else
      local leg_sorted leg_cnt leg_first leg_last leg_expect
      leg_sorted="$(printf '%s\n' "$leg_nums" | grep -v '^$' | sort -u)"
      leg_cnt="$(printf '%s\n' "$leg_sorted" | grep -c .)"
      leg_first="$(printf '%s\n' "$leg_sorted" | head -1)"
      leg_last="$(printf '%s\n' "$leg_sorted" | tail -1)"
      leg_expect="$(printf 'leg-%02d' "$leg_cnt")"
      if [ "$leg_first" != "leg-01" ] || [ "$leg_last" != "$leg_expect" ]; then
        # shellcheck disable=SC2086  # deliberate word-split of the id list for display
        echo "LEGS   $d — leg files must run leg-01..$leg_expect with no gap (found: $(printf '%s ' $leg_sorted)); a gap is a dropped or misnamed leg."; rc=1
      fi
    fi
  done

  if [ "$found" -eq 0 ]; then
    echo "CHECK: no swimlanes found in $SKETCH_DIR/ (expected $SKETCH_DIR/<seam>/_lane.md, or the legacy $SKETCH_DIR/swimlane-<seam>/swimlane-<seam>.plan.md)." >&2
    echo "CHECK_PLAN=EMPTY"; return 2
  fi
  if [ "$thread_seen" -eq 0 ]; then
    echo "THREAD $SKETCH_DIR/ — no steel-thread swimlane (none carries thread=yes); one lane must exercise every seam end-to-end first (H1)."; rc=1
  fi

  if [ "$rc" -eq 0 ]; then
    echo "CHECK: OK — every swimlane is a lean PRD + linked leg files; plan altitude held (no SQL/tasks); seam economics + architecture + contiguous legs present."
    echo "CHECK_PLAN=OK"
  else
    echo "CHECK: FAIL — fix the flagged swimlanes; keep the PRD an index, push detail to legs, hold plan altitude, and complete the structure." >&2
    echo "CHECK_PLAN=FAIL"
  fi
  return "$rc"
}

usage_error() { echo "Error: $*" >&2; usage >&2; echo "CHECK_PLAN=USAGE_ERROR"; exit 1; }

# ── Parse args ────────────────────────────────────────────────────────────────
TITLE=""
DO_CHECK=false
while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h)   usage; exit 0 ;;
    --check)     DO_CHECK=true; shift ;;
    --dir)       SKETCH_DIR="${2:?--dir needs a path}"; shift 2 ;;
    --component) COMPONENT="${2:?--component needs a label}"; shift 2 ;;
    --consumes)  CONSUMES="${2:?--consumes needs an upstream seam}"; shift 2 ;;
    --lane)      LANE="${2:?--lane needs a seam name}"; shift 2 ;;
    --leg)       LEG="${2:?--leg needs NN-<tech>, e.g. 01-dlt}"; shift 2 ;;
    --)          shift; TITLE="${1:-}"; break ;;
    -*)          usage_error "unknown option: $1" ;;
    *)           TITLE="$1"; shift ;;
  esac
done

if [ "$DO_CHECK" = true ]; then
  check_tree
  exit $?
fi

# ── Leg scaffold ──────────────────────────────────────────────────────────────
if [ -n "$LEG" ]; then
  [ -n "$LANE" ] || usage_error "--leg needs --lane <seam>"
  SEAM="$(slugify "$LANE")"
  printf '%s' "$LEG" | grep -qE '^[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*$' \
    || usage_error "--leg must be NN-<tech>, 2-digit zero-pad + lowercase-kebab tech (e.g. 01-dlt, 04-dbt-bronze)"
  LEG_NN="${LEG%%-*}"
  DIR="$SKETCH_DIR/$SEAM"
  [ -d "$DIR" ] || DIR="$SKETCH_DIR/swimlane-$SEAM"   # legacy lane dir keeps working
  mkdir -p "$DIR"
  OUT="$DIR/leg-$LEG.md"
  [ -e "$OUT" ] && usage_error "$OUT already exists — edit it, don't re-scaffold"
  cat > "$OUT" <<EOF
---
leg: swimlane-$SEAM-leg-$LEG_NN
tech: ${LEG#*-}
swimlane: swimlane-$SEAM
parent: swimlane-$SEAM.plan.md
status: proposed
spec_ref: []
depends_on: []
type: leg
---

# swimlane-$SEAM-leg-$LEG — <one-line responsibility>

> Part of swimlane **$SEAM** ([swimlane-$SEAM.plan.md](swimlane-$SEAM.plan.md)).
> Plan altitude only — responsibility + acceptance criteria; the runnable eval binds at Pass 5B.

## Responsibility

<!-- ONE job, in prose (INVEST-Valuable). Optionally: "so that <benefit>". Never
     the SQL / handler body — that is the task-spec this leg yields at 5B. -->

## Proves (acceptance criteria — Given/When/Then; 1-3; NO evals)

<!-- Declarative behaviour/outcome, technology-agnostic. 4+ criteria = the leg is
     too big; split it. The runnable eval is generated FROM these at Pass 5B. -->

- Given <state>, when <event>, then <observable outcome>.

## Independence

<!-- Why this leg is buildable + provable with no later leg existing (INVEST-Independent). -->

## Consumes / produces

- Consumes: <this leg's inputs>.
- Produces: <this leg's outputs — toward the lane's output contract>.

## Appetite

<!-- One token bounding size (Shape Up): small | medium — one build-order step,
     one context window. Bigger is two legs. -->

## Yields at Pass 5B (named units, not specified here)

- <the 1:N task-specs this leg becomes — named in prose, no evals>.

## Re-verify when

<!-- The event that invalidates this leg (an ADR supersede, a contract change). -->
EOF
  echo "Created $OUT"
  exit 0
fi

# ── Swimlane PRD scaffold ─────────────────────────────────────────────────────
[ -n "$TITLE" ] || usage_error "swimlane title required (e.g. \"capture\")"
SEAM="$(slugify "$TITLE")"
[ -n "$SEAM" ] || usage_error "title slugified to empty"
DIR="$SKETCH_DIR/$SEAM"
mkdir -p "$DIR"
OUT="$DIR/_lane.md"
[ -e "$OUT" ] && usage_error "$OUT already exists — edit it, don't re-scaffold"

if [ -n "$COMPONENT" ]; then
  IDENTITY="Component **$COMPONENT**"
else
  IDENTITY="Component **<A · Capture | B · Serve>**"
fi

CONSUMED_BLOCK=""
if [ -n "$CONSUMES" ]; then
  CONSUMED_BLOCK="## The interface this lane consumes (the seam — hard boundary)

This lane reads **only the \`$CONSUMES\` contract**, never below it. Name the exact
upstream fields each leg consumes. A missing field is a new upstream-contract
request, never a deeper read.

| upstream unit | fields consumed | read by (leg) |
|---|---|---|
| \`$CONSUMES\` <unit> | <field, …> | swimlane-$SEAM-leg-01 |

**Seam evolution:** additive changes (a new column/field/endpoint) are non-breaking;
renames, removals, and newly-required fields are BREAKING and need a coexistence
window. <State how this lane learns of a change — e.g. a consumer-driven contract test.>

---

"
fi

cat > "$OUT" <<EOF
# Swimlane · $SEAM

lane-meta: thread=<yes|no> · risk=<low|med|high> · owner=<owning stream/team>

$IDENTITY — its purpose in one line (the problem this slice solves).
Input contract: \`<upstream>.*\`. Output contract: \`<downstream>.*\` (the seam the next lane consumes).

> **This is the swimlane PRD — a lean INDEX over the legs.** Each leg's full detail
> lives in its own file (\`leg-NN-<tech>.md\`, keyed \`swimlane-$SEAM-leg-NN\`). Keep this at black-box
> altitude: interfaces, the seam, the DAG, links — never leg detail, never SQL, never evals.

## Seam

<!-- Where this lane cuts: the nameable one-way interface. What is given/frozen
     upstream, what is published downstream, and why the dependency is one-way. -->

## Architecture

<!-- Dual-coding: a diagram + adjacent numbered steps. Black-box altitude only. -->

\`\`\`mermaid
flowchart LR
  SRC[(<source / upstream seam>)] --> A["<this lane> · leg-01-<tech>"]
  A --> OUT["<downstream seam> · <next lane>"]
\`\`\`

Step-by-step:

1. <source> changes land where this lane's leg-01 reads them.
2. <leg-01> shapes them toward the lane's output contract.
3. <downstream> consumes only the published contract — never below the seam.

## Non-Goals

<!-- Explicit out-of-scope — the #1 anti-bloat device. What this swimlane will NOT do. -->

- <not this>.

## Legs — index (full detail in each file)

| Leg | Responsibility (one line) | File |
|---|---|---|
| **leg-01-<tech>** | <one line> | [leg-01-<tech>.md](leg-01-<tech>.md) |
| **leg-02-<tech>** | <one line> | [leg-02-<tech>.md](leg-02-<tech>.md) |

Stable keys: \`swimlane-$SEAM-leg-01/02\` — the \`<tech>\` suffix is a swappable label.

${CONSUMED_BLOCK}## Dependencies

<!-- A small DAG across the legs + the inbound seam. One direction. -->

\`\`\`
<upstream seam>  ->  leg-01  ->  leg-02
\`\`\`

## Build order

<!-- A sane sequence of legs; call out the GATING input. -->

1. **leg-01** — <why it unblocks the rest>.
2. **leg-02** — <next>.

## Open questions

<!-- Anything the ADRs do NOT cover: owner + blocks-build flag. Do not invent answers.
     CYCLE NOTE (H5): a genuine two-way dependency is broken here (dependency
     inversion / async boundary / shared kernel) and flagged blocks-build. -->

| # | Item | Owner | Blocks build? |
|---|---|---|---|
| Q1 | <question the ADRs don't settle> | <owner> | <Yes/No> |

## Spec traceability

<!-- Every leg traces to an ADR / requirement; the leg files carry the leg-level trace. -->

- **<ADR / R-n>** — <how this lane honors it>.
EOF

echo "Created $OUT"
echo "Next: add legs with  new-plan.sh --lane $SEAM --leg 01-<tech>"
