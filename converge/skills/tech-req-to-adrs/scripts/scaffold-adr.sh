#!/usr/bin/env bash
# scaffold-adr.sh — Converge Pass 2 (Structure): scaffold a numbered grounding ADR,
# scaffold the 0000 context record, supersede an ADR, or check the set.
#
# Grounding ADRs record a FACT or CONSTRAINT about the terrain (what IS / what MUST
# hold) with its evidence — never a "build X" instruction. That boundary is the one
# invariant this pass enforces; --check is its deterministic guard.
#
# Lifecycle (v0.4.0): proposed → accepted → deprecated | superseded.
# Accepted ADRs are immutable — when a recorded fact stops being true, scaffold a
# replacement with --supersede NNNN (links are stamped bidirectionally).
#
# Usage:
#   scaffold-adr.sh "orders join events on user_id"  Create docs/adrs/NNNN-<slug>.md
#   scaffold-adr.sh --context                        Create docs/adrs/0000-context.md
#   scaffold-adr.sh --supersede NNNN "new title"     Replace ADR NNNN (bidirectional links)
#   scaffold-adr.sh --ground greenfield "title"      Set the ground type (default: brownfield)
#   scaffold-adr.sh --status proposed "title"        proposed|accepted (default: proposed)
#   scaffold-adr.sh --dir path/to/adrs "title"       Override the ADR directory
#   scaffold-adr.sh --check [--final]                Lint the set; --final also requires
#                                                    every status accepted (pass close)
#   scaffold-adr.sh --help
#
# Agent contract: --check's LAST line is a stable machine token —
#   CHECK_ADR=OK | FAIL | EMPTY | USAGE_ERROR
#
# Exit: 0 = ok; 1 = check failed / usage error; 2 = nothing to check
# bash 3.2-safe (runs on macOS system /bin/bash). No associative arrays.

set -euo pipefail

ADR_DIR="docs/adrs"
GROUND="brownfield"
STATUS="proposed"
STATUS_ENUM='proposed|accepted|deprecated|superseded'

usage() { sed -n '2,27p' "$0"; }

usage_error() {
  echo "ERROR: $*" >&2
  usage >&2
  echo "CHECK_ADR=USAGE_ERROR"
  exit 1
}

# ── Build-verb drift guards ───────────────────────────────────────────────────
# 1) Line-head imperative: a Decision line that STARTS with a build-verb.
DRIFT_RE='^[[:space:]]*[-*>]?[[:space:]]*(Build|Create|Implement|Add|Introduce|Design|Refactor|Migrate|Scaffold|Wire up|Set up)[[:space:]]'
# 2) Mid-sentence modal design, scoped to the Decision section only (v0.4.0):
#    "the pipeline must therefore build a fct table" is Pass 3, not terrain.
DRIFT_MODAL_RE='\b(we|pass 3|the (pipeline|system|engine|team|backbone|service))[[:space:]]+(will|should|must)([[:space:]]+(therefore|then|also))?[[:space:]]+(build|create|add|implement|introduce|migrate|wire|scaffold|design|refactor)\b'

slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

next_number() {
  # Highest existing NNNN in ADR_DIR, plus one, zero-padded to 4.
  local max=0 n f
  if [ -d "$ADR_DIR" ]; then
    for f in "$ADR_DIR"/[0-9][0-9][0-9][0-9]-*.md; do
      [ -e "$f" ] || continue
      n=$(basename "$f" | cut -c1-4)
      n=$((10#$n))
      [ "$n" -gt "$max" ] && max="$n"
    done
  fi
  printf '%04d' "$((max + 1))"
}

# fm_get <file> <key> — first frontmatter value for key (empty if absent).
fm_get() {
  awk -v key="$2" '
    NR == 1 && $0 != "---" { exit }
    NR > 1 && $0 == "---"  { exit }
    $0 ~ "^" key ":" {
      sub("^" key ":[[:space:]]*", ""); gsub(/^"|"$/, ""); print; exit
    }
  ' "$1"
}

# section_body <file> <name> — lines of "## <name>" section, HTML comments and
# blanks stripped (comments may span lines).
section_body() {
  awk -v want="$2" '
    /^##[^#]/ { inside = (tolower($0) ~ tolower(want)) ? 1 : 0; next }
    inside    { print }
  ' "$1" | awk '
    /<!--/ { incmt = 1 }
    incmt  { if (/-->/) incmt = 0; next }
    /[^[:space:]]/ { print }
  '
}

check_set() {
  local final="$1" rc=0 hits f st num sup back ctx
  if [ ! -d "$ADR_DIR" ] || ! ls "$ADR_DIR"/[0-9][0-9][0-9][0-9]-*.md >/dev/null 2>&1; then
    echo "CHECK: no ADRs found in $ADR_DIR/ — run Step 3 first." >&2
    echo "CHECK_ADR=EMPTY"
    return 2
  fi

  # H9 — the context record and the glossary are part of the set's contract.
  if [ ! -f "$ADR_DIR/0000-context.md" ]; then
    echo "MISSING $ADR_DIR/0000-context.md — name the ground first (scaffold-adr.sh --context)."
    rc=1
  fi
  ctx="$(dirname "$ADR_DIR")/CONTEXT.md"
  if [ ! -s "$ctx" ]; then
    echo "MISSING $ctx — the glossary is a gate artifact; pin terms as they crystallize."
    rc=1
  fi

  for f in "$ADR_DIR"/[0-9][0-9][0-9][0-9]-*.md; do
    [ -e "$f" ] || continue
    num="$(basename "$f" | cut -c1-4)"

    # H3 — an unfilled scaffold is not a record.
    if grep -q '<!--' "$f"; then
      echo "UNFILLED $f — template comment(s) still present; fill or delete every <!-- --> block."
      rc=1
    fi

    # H4/H2 — frontmatter status must exist and sit in the lifecycle enum.
    st="$(fm_get "$f" status)"
    if [ -z "$st" ]; then
      echo "META   $f — no 'status:' in YAML frontmatter (proposed|accepted|deprecated|superseded)."
      rc=1
    elif ! printf '%s' "$st" | grep -qE "^($STATUS_ENUM)$"; then
      echo "META   $f — status '$st' not in lifecycle enum ($STATUS_ENUM)."
      rc=1
    fi
    if [ "$final" = true ] && [ "$st" = "proposed" ]; then
      echo "OPEN   $f — still 'proposed'; the pass cannot close until every ADR is accepted (or superseded/deprecated)."
      rc=1
    fi

    # H2 — supersede links must be bidirectional.
    sup="$(fm_get "$f" supersedes)"
    if [ -n "$sup" ]; then
      supf=""
      for g in "$ADR_DIR/$sup"-*.md; do
        [ -e "$g" ] && supf="$g"
      done
      if [ -z "$supf" ]; then
        echo "LINK   $f — supersedes $sup but no $sup-*.md exists."
        rc=1
      else
        back="$(fm_get "$supf" superseded_by)"
        if [ "$back" != "$num" ]; then
          echo "LINK   $f — supersedes $sup but $sup does not point back (superseded_by: '$back')."
          rc=1
        fi
      fi
    fi

    # 0000 is the context record; the checks below are for numbered facts.
    [ "$num" = "0000" ] && continue

    # H3 — required sections must carry real content once comments are gone.
    for sec in Context Decision Evidence Consequences; do
      if [ -z "$(section_body "$f" "$sec")" ]; then
        echo "EMPTY  $f — section '$sec' has no content."
        rc=1
      fi
    done

    # Drift guard 1: line-head imperative anywhere in the record.
    hits=$(grep -nEi "$DRIFT_RE" "$f" || true)
    if [ -n "$hits" ]; then
      echo "DRIFT  $f — build-verb at line head (this is Pass 3 design, not Pass 2 grounding):"
      printf '%s\n' "$hits" | sed 's/^/         /'
      rc=1
    fi
    # Drift guard 2 (H7): mid-sentence modal design, Decision section only.
    hits=$(section_body "$f" Decision | grep -nEi "$DRIFT_MODAL_RE" || true)
    if [ -n "$hits" ]; then
      echo "DRIFT  $f — modal design language in Decision ('…must build…' is Pass 3):"
      printf '%s\n' "$hits" | sed 's/^/         /'
      rc=1
    fi

    # An ADR with no Evidence header is unfalsifiable grounding.
    if ! grep -qiE '^\#+[[:space:]]*Evidence' "$f"; then
      echo "WEAK   $f — no Evidence section; a grounding fact must cite its source."
      rc=1
    fi

    # H1 — advisory: the worthiness test says it could have been otherwise;
    # record the otherwise. H5 — advisory: trace the spec requirement.
    if ! grep -qiE '^\#+[[:space:]]*Rejected reading' "$f"; then
      echo "NOTE   $f — no 'Rejected reading' section; if a genuine ambiguity was resolved, record the losing reading."
    fi
    if [ -z "$(fm_get "$f" spec_ref)" ]; then
      echo "NOTE   $f — spec_ref is empty; cite the requirement ID(s) this fact grounds (e.g. R-1)."
    fi
    # H6 — advisory: evidence should carry the runnable command, not just output.
    if ! section_body "$f" Evidence | grep -q '```'; then
      echo "NOTE   $f — Evidence has no fenced command block; record the command that re-proves the fact."
    fi
  done

  if [ "$rc" -eq 0 ]; then
    echo "CHECK: OK — every ADR reads as terrain (fact/constraint) with evidence, no design-drift."
    echo "CHECK_ADR=OK"
  else
    echo "CHECK: FAIL — fix the flagged records; the fact stays here, the design goes to Pass 3." >&2
    echo "CHECK_ADR=FAIL"
  fi
  return "$rc"
}

# ── Parse args ────────────────────────────────────────────────────────────────
TITLE=""
DO_CHECK=false
DO_FINAL=false
DO_CONTEXT=false
SUPERSEDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h)   usage; exit 0 ;;
    --check)     DO_CHECK=true; shift ;;
    --final)     DO_FINAL=true; shift ;;
    --context)   DO_CONTEXT=true; shift ;;
    --supersede) SUPERSEDE="${2:?--supersede needs an ADR number (NNNN)}"; shift 2 ;;
    --dir)       ADR_DIR="${2:?--dir needs a path}"; shift 2 ;;
    --ground)    GROUND="${2:?--ground needs greenfield|brownfield}"; shift 2 ;;
    --status)    STATUS="${2:?--status needs proposed|accepted}"; shift 2 ;;
    --)          shift; TITLE="${1:-}"; break ;;
    -*)          usage_error "unknown option: $1" ;;
    *)           TITLE="$1"; shift ;;
  esac
done

if [ "$DO_CHECK" = true ]; then
  check_set "$DO_FINAL"
  exit $?
fi

printf '%s' "$STATUS" | grep -qE '^(proposed|accepted)$' \
  || usage_error "--status must be proposed|accepted at scaffold time (deprecated/superseded are set by lifecycle, not by birth)"

TODAY="$(date +%Y-%m-%d)"

# ── --context: the 0000 record (H8) ──────────────────────────────────────────
if [ "$DO_CONTEXT" = true ]; then
  mkdir -p "$ADR_DIR"
  OUT="$ADR_DIR/0000-context.md"
  [ -e "$OUT" ] && usage_error "$OUT already exists — the context record is written once, then superseded like any ADR"
  cat > "$OUT" <<EOF
---
adr: "0000"
status: $STATUS
date: $TODAY
ground: $GROUND
converge_pass: 2
spec_ref: ""
supersedes: ""
superseded_by: ""
deciders: ""
---

# 0000 — Context: the ground we stand on

## Terrain

<!-- greenfield (nothing exists; ADRs record the constraints the spec imposes)
     or brownfield (a working base exists; ADRs record what is already true) —
     and the one-sentence why. -->

## Given surface

<!-- What runs TODAY: sources, stores, build steps, serving components.
     One line each, verified — not assumed. -->

## Build surface

<!-- What the spec still asks later passes to build. One line each. -->

## Spec

<!-- The canonical tech-spec this grounding consumes (path + sign-off date). -->
EOF
  echo "Created $OUT"
  exit 0
fi

# ── Scaffold a numbered ADR ───────────────────────────────────────────────────
if [ -z "$TITLE" ]; then
  usage_error "ADR title required"
fi

SLUG="$(slugify "$TITLE")"
[ -n "$SLUG" ] || usage_error "title slugified to empty"

mkdir -p "$ADR_DIR"
NUM="$(next_number)"
OUT="$ADR_DIR/$NUM-$SLUG.md"
[ -e "$OUT" ] && usage_error "$OUT already exists"

# H2 — supersede mechanics: validate the target, stamp both directions.
OLD_FILE=""
if [ -n "$SUPERSEDE" ]; then
  for f in "$ADR_DIR/$SUPERSEDE"-*.md; do
    [ -e "$f" ] && OLD_FILE="$f"
  done
  [ -n "$OLD_FILE" ] || usage_error "--supersede $SUPERSEDE: no $ADR_DIR/$SUPERSEDE-*.md found"
fi

cat > "$OUT" <<EOF
---
adr: "$NUM"
status: $STATUS
date: $TODAY
ground: $GROUND
converge_pass: 2
spec_ref: ""
supersedes: "$SUPERSEDE"
superseded_by: ""
deciders: ""
---

# $NUM — $TITLE

## Context

<!-- What part of the terrain does this record pin down? State the question a
     Pass 3 planner would otherwise get wrong. Put the requirement ID(s) this
     grounds in spec_ref above (e.g. "R-1, R-4"). -->

## Decision

<!-- A FACT or CONSTRAINT about the terrain — what IS, or what MUST hold.
     NOT a build instruction. If this says Build/Create/Implement/Add — or
     "the pipeline must therefore build…" — it belongs in Pass 3, not here. -->

## Rejected reading

<!-- The plausible alternative interpretation, and the evidence that killed it.
     The worthiness test says this fact could have been otherwise — record the
     otherwise so no later agent re-litigates it. -->

## Evidence

<!-- The exact source line / row count / command output that makes this true —
     AND the runnable command that re-proves it:

\`\`\`sh
# command used (re-runnable)
\`\`\`

     observed output: … -->

## Consequences

<!-- What downstream passes must respect. e.g. "Pass 3 plans must join
     A↔B on <key> only; no other key exists."
     Re-verify when: <the event that would invalidate this fact>. -->
EOF

if [ -n "$OLD_FILE" ]; then
  TMP="$OLD_FILE.tmp.$$"
  awk -v newnum="$NUM" '
    NR == 1 && $0 == "---" { infm = 1; print; next }
    infm && $0 == "---"    { infm = 0; print; next }
    infm && /^status:/        { print "status: superseded"; next }
    infm && /^superseded_by:/ { print "superseded_by: \"" newnum "\""; next }
    { print }
  ' "$OLD_FILE" > "$TMP" && mv "$TMP" "$OLD_FILE"
  echo "Superseded $OLD_FILE (status: superseded, superseded_by: $NUM)"
fi

echo "Created $OUT"
