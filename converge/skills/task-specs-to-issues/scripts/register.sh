#!/usr/bin/env bash
# register.sh — the REGISTER driver: project signed-off task-specs onto a tracker.
#
# Reads tasks/T-*.md, keeps only `signed_off: true` specs, refuses on a
# depends_on cycle, topologically orders the survivors, and drives the selected
# adapter's `upsert` (one issue per spec) then `link` (each depends_on edge as a
# blocked-by link) in BUILD ORDER. Idempotent by construction — the adapter keys
# on the spec id.
#
# It also reads tasks/done/T-*.md, but only to KNOW those ids: a landed spec still
# owns its issue, so it satisfies a dependent's blocked-by edge and it peels first
# in the topological order — while never being re-upserted as new work.
#
# Usage:
#   register.sh [--tracker github|linear|jira] [--tasks-dir DIR] [--dry-run]
#               [--no-stamp-refs]
#
#   --tracker        backend to register onto (default: linear)
#   --tasks-dir      where the specs live (default: tasks)
#   --dry-run        parse + validate + PRINT the plan; make NO network calls and
#                    invoke NO adapter. Fully runnable offline with no creds.
#   --no-stamp-refs  do NOT write the tracker_ref receipt back into each spec.
#                    Default is to stamp `tracker_ref: <tracker>:<issue>` into the
#                    spec frontmatter after a successful upsert (a convenience
#                    backlink; the issue-side marker stays the idempotency key).
#                    Use this for read-only / CI contexts that must not touch the
#                    repo — resolution still works by marker with an empty ref.
#
# Exit: 0 on a clean plan/registration; 1 on a cycle, a missing dependency, an
# adapter preflight failure, or a mid-run adapter error (never half-silent).
#
# bash-3.2-safe: no mapfile, no `declare -A`. The graph is held in newline-
# delimited scratch files under a temp dir and walked with grep/awk, mirroring
# the task-spec skill's portable style.

set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_parse.sh
source "$SELF_DIR/_parse.sh"

# ----- Defaults -----
TRACKER="linear"
TASKS_DIR="${TSI_TASKS_DIR:-tasks}"
DRY_RUN=0
STAMP_REFS=1

# ----- Arg parse -----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tracker)   TRACKER="${2:?--tracker needs a value}"; shift 2 ;;
    --tracker=*) TRACKER="${1#--tracker=}"; shift ;;
    --tasks-dir)   TASKS_DIR="${2:?--tasks-dir needs a value}"; shift 2 ;;
    --tasks-dir=*) TASKS_DIR="${1#--tasks-dir=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --no-stamp-refs) STAMP_REFS=0; shift ;;
    -h|--help)
      grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
      exit 0 ;;
    *) tsi_die "unknown arg '$1' (see --help)" ;;
  esac
done

case "$TRACKER" in
  github|linear|jira) ;;
  fake) ;;  # test-only no-network reference adapter (scripts/adapters/fake.sh)
  *) tsi_die "unknown --tracker '$TRACKER' (want: github|linear|jira)" ;;
esac

[[ -d "$TASKS_DIR" ]] || tsi_die "tasks dir '$TASKS_DIR' not found"

ADAPTER="$SELF_DIR/adapters/${TRACKER}.sh"
[[ -f "$ADAPTER" ]] || tsi_die "adapter not found: $ADAPTER"

# ----- Scratch -----
WORK="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/tsi-register.$$")"
mkdir -p "$WORK"
cleanup() { rm -rf "$WORK" 2>/dev/null || true; }
trap cleanup EXIT

SIGNED="$WORK/signed.tsv"     # id \t file \t title  (signed_off==true only)
EDGES="$WORK/edges.tsv"       # from_id \t to_id     (from depends_on to_id)
ALLIDS="$WORK/allids.txt"     # every spec id (signed or not) — for edge validation
: > "$SIGNED"; : > "$EDGES"; : > "$ALLIDS"

echo "REGISTER — tracker=$TRACKER tasks-dir=$TASKS_DIR dry-run=$DRY_RUN stamp-refs=$STAMP_REFS"
echo "----------------------------------------------------------------"

# ----- Step 1: collect the signed-off backlog -----
# bash 3.2 has no `lastpipe`, so a `... | while read` loop runs in a subshell and
# its variable writes are lost. We iterate the glob DIRECTLY (no pipe) so SKIPPED
# and the scratch files accumulate in THIS shell.
SKIPPED=""
OPTED_OUT=""
for f in "$TASKS_DIR"/T-*.md; do
  [[ -f "$f" ]] || continue
  id="$(tsi_id "$f")"
  [[ -n "$id" ]] || { echo "WARN: $f has no id: — skipping" >&2; continue; }
  echo "$id" >> "$ALLIDS"

  so="$(tsi_signed_off "$f")"
  title="$(tsi_title "$f")"
  if [[ "$so" != "true" ]]; then
    SKIPPED="${SKIPPED}${SKIPPED:+ }$id"
    continue
  fi
  # Signed off but explicitly NOT for a shared board (fixtures, budget-busters).
  if [[ "$(tsi_registerable "$f")" != "true" ]]; then
    OPTED_OUT="${OPTED_OUT}${OPTED_OUT:+ }$id"
    continue
  fi
  printf '%s\t%s\t%s\n' "$id" "$f" "$title" >> "$SIGNED"

  # Record edges: for each dep, an edge (id depends_on dep).
  for dep in $(tsi_depends_on "$f"); do
    printf '%s\t%s\n' "$id" "$dep" >> "$EDGES"
  done
done

# ----- Step 1a: LANDED — specs that finished, and still own their board issue -----
#
# `cvg transition <id> done` MOVES a spec into tasks/done/. This driver only ever
# globbed tasks/*.md, so a completed spec vanished from every set it reasons over
# and the WRITE path failed exactly the way the verify path did before a6ddefa:
# its dependents' depends_on edges looked dangling, and register refused the whole
# board with "blocked-by target not found". Reconciling the board after a task
# landed — the very next act the loop asks for — was impossible.
#
# Same distinction, same reason: a landed spec is KNOWN (it exists, it is signed,
# it owns an issue) but is NOT in the register SET. It is never re-upserted, both
# because it is not new work and because upsert seeds state from the DAG — pushing
# a finished issue back to Todo would be a regression written by the tool whose job
# is to mirror the specs. Its blocked-by links were set while it was active.
LANDED="$WORK/landed.txt"; : > "$LANDED"
if [[ -d "$TASKS_DIR/done" ]]; then
  for f in "$TASKS_DIR"/done/T-*.md; do
    [[ -e "$f" ]] || continue
    id="$(tsi_id "$f")"
    [[ -n "$id" ]] || continue
    echo "$id" >> "$ALLIDS"
    [[ "$(tsi_signed_off "$f")" == "true" ]] || continue
    [[ "$(tsi_registerable "$f")" == "true" ]] || continue
    echo "$id" >> "$LANDED"
  done
fi
sort -u -o "$LANDED" "$LANDED"
LANDED_COUNT="$(awk 'END{print NR+0}' "$LANDED")"

# KNOWN = the register set ∪ what already landed. "Does this id exist at all?"
KNOWN="$WORK/known.txt"
{ awk -F'\t' '{print $1}' "$SIGNED"; cat "$LANDED"; } | sort -u > "$KNOWN"

SIGNED_COUNT="$(awk 'END{print NR}' "$SIGNED")"
echo "signed-off specs: $SIGNED_COUNT"
[[ "$LANDED_COUNT" -gt 0 ]] && echo "landed (done/, already registered — not re-upserted): $LANDED_COUNT"
if [[ -n "$SKIPPED" ]]; then
  echo "skipped (un-gated, signed_off!=true): $SKIPPED"
fi
if [[ -n "$OPTED_OUT" ]]; then
  echo "skipped (register: false — not for a shared board): $OPTED_OUT"
fi
if [[ "$SIGNED_COUNT" -eq 0 ]]; then
  echo "nothing to register (no signed_off specs)."
  echo "REGISTER=EMPTY"
  exit 0
fi

# ----- Step 1b: validate edges reference registerable ids -----
# Every depends_on target must be a KNOWN spec — active or landed — else the
# blocked-by link has no issue to point at. Resolving against SIGNED alone made
# finishing a dependency into a hard stop. A dep on an un-gated / unknown id
# still is one.
MISSING=""
while IFS=$'\t' read -r from dep; do
  [[ -n "$dep" ]] || continue
  if ! grep -qxF "$dep" "$KNOWN"; then
    MISSING="${MISSING}${MISSING:+ }${from}->${dep}"
  fi
done < "$EDGES"
if [[ -n "$MISSING" ]]; then
  echo "ERROR: blocked-by target not found (dependency is neither active nor landed):" >&2
  echo "  $MISSING" >&2
  echo "  either sign off + register the dependency, or fix the stale depends_on." >&2
  echo "REGISTER=FAIL"
  exit 1
fi

# ----- Step 2: cycle detection + topological (build) order -----
# Kahn's algorithm over the signed-off subgraph. Node = spec id. A depends_on
# edge (a -> b) means b must come BEFORE a, so b has an out-edge to a in build
# terms. We compute in-degree over dependency edges and peel roots (no deps).
# Held entirely in scratch files → bash-3.2-safe, no associative arrays.
# Seed from KNOWN, not SIGNED: a landed node has no unmet dependency, so it peels
# first and lets its dependents follow. Seeding from SIGNED alone leaves every
# dependent of a finished task permanently blocked, and Kahn reports that deadlock
# as a "cycle" — a chain misdiagnosed as a loop, which is the worse failure because
# it points the reader at the specs instead of at the gate.
NODES="$WORK/nodes.txt"          # every known id (active + landed)
cp "$KNOWN" "$NODES"

REMAIN="$WORK/remain.txt"        # ids not yet emitted
REMEDGES="$WORK/remedges.tsv"    # edges (from depends_on to) still live
ORDER="$WORK/order.txt"          # topological build order (deps first)
cp "$NODES" "$REMAIN"
cp "$EDGES" "$REMEDGES"
: > "$ORDER"

# A node is a "root" (ready to emit) when it has no remaining depends_on edge,
# i.e. it never appears in column 1 of REMEDGES.
while [[ -s "$REMAIN" ]]; do
  ROOTS="$WORK/roots.txt"; : > "$ROOTS"
  while read -r n; do
    [[ -n "$n" ]] || continue
    if ! awk -F'\t' -v x="$n" '$1==x{f=1} END{exit f?0:1}' "$REMEDGES"; then
      echo "$n" >> "$ROOTS"
    fi
  done < "$REMAIN"

  if [[ ! -s "$ROOTS" ]]; then
    echo "ERROR: refusing to register — dependency cycle among:" >&2
    # The remaining nodes form the cycle set; print their live edges as evidence.
    while read -r n; do
      dl="$(awk -F'\t' -v x="$n" '$1==x{printf "%s ", $2}' "$REMEDGES")"
      [[ -n "$dl" ]] && echo "  $n depends_on: $dl" >&2
    done < "$REMAIN"
    echo "  a cycle is a spec bug (Pass 5B), not a board state. Fix depends_on upstream." >&2
    echo "REGISTER=FAIL"
    exit 1
  fi

  # Emit roots in a stable order; drop them from REMAIN and from REMEDGES targets.
  sort "$ROOTS" | while read -r r; do echo "$r"; done >> "$ORDER"
  grep -vxF -f "$ROOTS" "$REMAIN" > "$REMAIN.next" || true
  mv "$REMAIN.next" "$REMAIN"
  # Remove edges whose TARGET (col 2) is now emitted — those deps are satisfied.
  awk -F'\t' 'NR==FNR{done[$1]=1; next} !($2 in done)' "$ROOTS" "$REMEDGES" > "$REMEDGES.next" || true
  mv "$REMEDGES.next" "$REMEDGES"
done

# The peel ran over KNOWN so the topology is right; the WRITE set is only the
# active specs. UPSERT_ORDER preserves build order and drops what already landed.
UPSERT_ORDER="$WORK/upsert_order.txt"
if [[ -s "$LANDED" ]]; then
  grep -vxF -f "$LANDED" "$ORDER" > "$UPSERT_ORDER" || : > "$UPSERT_ORDER"
else
  cp "$ORDER" "$UPSERT_ORDER"
fi

echo "build order (deps first):"
awk '{printf "  %d. %s\n", NR, $0}' "$UPSERT_ORDER"
echo "----------------------------------------------------------------"

# ----- Step 3+4: drive the adapter (or PRINT the plan on --dry-run) -----
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN — no network, no adapter calls. This is what WOULD happen:"
  echo
  echo "[preflight] $ADAPTER preflight"
  echo
  echo "[upsert] one issue per signed-off spec, in build order:"
  echo "  (live run also seeds assignee/state/subscribers + honors any projection: block;"
  echo "   structure projection is ${CVG_PROJECTION_ENABLED:+ON}${CVG_PROJECTION_ENABLED:-off by default})"
  while read -r id; do
    title="$(awk -F'\t' -v x="$id" '$1==x{print $3}' "$SIGNED")"
    file="$(awk -F'\t' -v x="$id" '$1==x{print $2}' "$SIGNED")"
    echo "  $ADAPTER upsert --id $id --title \"$title\" --body-file <goal+exit-check of $file>"
    if [[ "$STAMP_REFS" -eq 1 ]]; then
      echo "    └─ would stamp receipt: tracker_ref: $TRACKER:<issue> into $file"
    fi
  done < "$UPSERT_ORDER"
  echo
  echo "[link] depends_on -> blocked-by (from -> to):"
  if [[ -s "$EDGES" ]]; then
    # Print links in build order of the FROM node for readability.
    while read -r id; do
      awk -F'\t' -v x="$id" '$1==x{print $2}' "$EDGES" | while read -r dep; do
        [[ -n "$dep" ]] && echo "  $ADAPTER link --from $id --to $dep   # $id blocked-by $dep"
      done
    done < "$UPSERT_ORDER"
  else
    echo "  (none — no depends_on edges among signed-off specs)"
  fi
  echo
  EDGE_COUNT="$(awk 'END{print NR+0}' "$EDGES")"
  echo "PLAN: upsert $SIGNED_COUNT issue(s), set $EDGE_COUNT blocked-by link(s)."
  # Ready set = active ids with no UNMET blocker. An edge to a landed spec is
  # satisfied, not blocking — otherwise the frontier freezes the moment its
  # predecessor finishes, which is the one time it must move.
  READY=""
  while read -r id; do
    [[ -n "$id" ]] || continue
    unmet=0
    awk -F'\t' -v x="$id" '$1==x{print $2}' "$EDGES" > "$WORK/deps.txt"
    while read -r dep; do
      [[ -n "$dep" ]] || continue
      grep -qxF "$dep" "$LANDED" || unmet=1
    done < "$WORK/deps.txt"
    [[ "$unmet" -eq 0 ]] && READY="${READY}${READY:+ }$id"
  done < "$UPSERT_ORDER"
  echo "ready set (no blocker): ${READY:-(none)}"
  echo
  echo "VERDICT: DRY-RUN OK (offline plan is consistent). Re-run without --dry-run to write."
  echo "REGISTER=DRY_RUN"
  exit 0
fi

# ----- Live path: preflight, then upsert, then link -----
echo "[preflight] $TRACKER"
if ! bash "$ADAPTER" preflight; then
  echo "STOP: adapter preflight failed — not half-registering the board." >&2
  echo "REGISTER=FAIL"
  exit 1
fi
echo

# ----- Step 0: structure pre-pass (T3; opt-in, DEFAULT OFF) -----
# When `cvg setup projection --enable` recorded a gate (bridged as CVG_PROJECTION_*),
# ensure the run's structure up front — Initiative -> Project -> phase Milestones —
# idempotently BY NAME, so a re-run reuses the same objects (never duplicates). OFF by
# default: unset gate => this whole block is skipped and register is byte-identical to
# before. Tracker-neutral: github/jira degrade the ensure verbs to no-ops, so enabling
# projection never breaks a non-Linear board. A structure miss is fail-soft (a WARN +
# skipped placement), never a half-registration.
PROJECTION_ON=0
RUN_PROJECT_ID=""
if [ "${CVG_PROJECTION_ENABLED:-}" = "1" ]; then
  PROJ_NAME="${TSI_PROJECTION_PROJECT:-}"
  INIT_NAME="${TSI_PROJECTION_INITIATIVE:-}"
  MILES="${TSI_PROJECTION_MILESTONES:-}"
  if [ -z "$PROJ_NAME" ]; then
    echo "WARN: projection enabled but projection_project is unset — skipping structure" >&2
    echo "      (set it with: cvg setup projection --project <name>)" >&2
  else
    echo "[structure] projection enabled — ensuring Initiative -> Project -> Milestones (idempotent by name)"
    RUN_PROJECT_ID="$(bash "$ADAPTER" project-ensure "$PROJ_NAME" 2>>"$WORK/adapter.log" || true)"
    echo "  project:    $PROJ_NAME -> ${RUN_PROJECT_ID:-(FAILED)}"
    if [ -z "$RUN_PROJECT_ID" ]; then
      echo "WARN: could not ensure project '$PROJ_NAME' — structural placement skipped this run" >&2
    else
      PROJECTION_ON=1
      # Nest the project under an initiative (ensure + link), when configured.
      if [ -n "$INIT_NAME" ]; then
        INIT_ID="$(bash "$ADAPTER" initiative-ensure "$INIT_NAME" "$RUN_PROJECT_ID" 2>>"$WORK/adapter.log" || true)"
        echo "  initiative: $INIT_NAME -> ${INIT_ID:-(skipped)}"
      fi
      # Pre-create the phase milestones so they exist even before a spec references one.
      if [ -n "$MILES" ]; then
        for ms in $(printf '%s' "$MILES" | tr ',' ' '); do
          [ -n "$ms" ] || continue
          MS_ID="$(bash "$ADAPTER" milestone-ensure "$RUN_PROJECT_ID" "$ms" 2>>"$WORK/adapter.log" || true)"
          echo "  milestone:  $ms -> ${MS_ID:-(skipped)}"
        done
      fi
    fi
  fi
  echo
fi

CREATED=0; UPDATED=0; LINKS=0; STAMPED=0

echo "[upsert] one issue per signed-off spec (build order)"
while read -r id; do
  file="$(awk -F'\t' -v x="$id" '$1==x{print $2}' "$SIGNED")"
  title="$(awk -F'\t' -v x="$id" '$1==x{print $3}' "$SIGNED")"

  # Build the issue body — the full, well-shaped projection of the spec (goal,
  # sizing, done-condition, behaviors, write surface, dependency graph, guardrails).
  # The dep list comes from the edge table so the body can draw the blocked-by graph.
  body="$WORK/body.$id.md"
  BODY_DEPS="$(awk -F'\t' -v x="$id" '$1==x{printf "%s ", $2}' "$EDGES")"
  tsi_issue_body "$file" "$BODY_DEPS" > "$body"

  # Triage seed: a `cvg` marker label plus real sizing/severity signal, and a
  # priority when the spec declares one. Empty fields are OMITTED — never ship a
  # bare `severity:` or an invented priority. Adapters seed this at create only.
  UP_ARGS=(--id "$id" --title "$title" --body-file "$body" --label "cvg")
  UP_EFF="$(tsi_field "$file" effort)"
  [ -n "$UP_EFF" ] && UP_ARGS+=(--label "effort:$UP_EFF")
  # Two INDEPENDENT fleet axes, both read off the spec:
  #   backend: WHICH ENGINE runs it (claude|codex|kimi|glm|<your-harness>)
  #   agent:   WHICH ROLE it needs (python-developer, …) — omitted when `any`,
  #            since "any" carries no signal and would just be board noise.
  UP_BACKEND="$(tsi_field "$file" execution_backend)"
  [ -n "$UP_BACKEND" ] && [ "$UP_BACKEND" != "(none)" ] && UP_ARGS+=(--label "backend:$UP_BACKEND")
  UP_AGENT="$(tsi_field "$file" agent)"
  [ -n "$UP_AGENT" ] && [ "$UP_AGENT" != "(none)" ] && [ "$UP_AGENT" != "any" ] && UP_ARGS+=(--label "agent:$UP_AGENT")
  UP_SEV="$(tsi_severity "$file")"
  [ -n "$UP_SEV" ] && [ "$UP_SEV" != "(none)" ] && UP_ARGS+=(--label "severity:$UP_SEV")
  # Native-field signal: the tier drives the tracker's own estimate (Linear's
  # T-shirt scale is XS1 S2 M3 L5 XL8 XXL13 — a 1:1 match), and a declared
  # due_date drives its date field. Adapters without an equivalent ignore these.
  [ -n "$UP_EFF" ] && UP_ARGS+=(--effort "$UP_EFF")
  UP_DUE="$(tsi_field "$file" due_date)"
  [ -n "$UP_DUE" ] && [ "$UP_DUE" != "(none)" ] && UP_ARGS+=(--due "$UP_DUE")

  # Spec-at-a-glance attributes for the marker's rich panel (Name=Value pairs).
  # Adapters that cannot render a panel ignore --attr / --spec-url.
  UP_ARGS+=(--attr "Spec=$id")
  [ -n "$UP_EFF" ]     && UP_ARGS+=(--attr "Size=$UP_EFF")
  [ -n "$UP_BACKEND" ] && [ "$UP_BACKEND" != "(none)" ] && UP_ARGS+=(--attr "Executor=$UP_BACKEND")
  UP_PROF="$(tsi_field "$file" profile)"
  [ -n "$UP_PROF" ] && UP_ARGS+=(--attr "Profile=$UP_PROF")
  UP_SIG="$(tsi_field "$file" signed_off_sig)"
  if [ -n "$UP_SIG" ] && [ "$UP_SIG" != "(none)" ]; then
    UP_ARGS+=(--attr "Sign-off=Tier 1 (HMAC sealed)")
  else
    UP_ARGS+=(--attr "Sign-off=Tier 2 (structural)")
  fi
  UP_SBY="$(tsi_field "$file" signed_off_by)"
  [ -n "$UP_SBY" ] && [ "$UP_SBY" != "(none)" ] && UP_ARGS+=(--attr "Signed off by=$UP_SBY")
  [ -n "${TSI_SPEC_BASE_URL:-}" ] && UP_ARGS+=(--spec-url "${TSI_SPEC_BASE_URL%/}/$file")
  UP_PRI="$(tsi_priority "$file")"
  [ -n "$UP_PRI" ] && [ "$UP_PRI" != "(none)" ] && UP_ARGS+=(--priority "$UP_PRI")

  # --- Native-field seed (T1): tracker-neutral flags the Linear adapter consumes
  # and github/jira/fake accept-and-ignore. All three are OPTIONAL and fail-soft on
  # the adapter side, so a plain register with no identity / no state names is
  # unaffected. Ownership: assignee + state are SEED-ONCE (create only), subscribers
  # UNION-merge — the adapter enforces that split; the driver just supplies signal.
  #   assignee: the most-specific identity KEY (agent role beats engine beats the
  #             `default` catch-all); the adapter resolves KEY -> person + fails soft.
  # "any" carries no routing signal (same as the label rule above), so it is NOT a
  # key — it falls through to the `default` catch-all. agent role beats engine.
  UP_ASSIGN="default"
  [ -n "$UP_BACKEND" ] && [ "$UP_BACKEND" != "(none)" ] && [ "$UP_BACKEND" != "any" ] && UP_ASSIGN="backend:$UP_BACKEND"
  [ -n "$UP_AGENT" ] && [ "$UP_AGENT" != "(none)" ] && [ "$UP_AGENT" != "any" ] && UP_ASSIGN="agent:$UP_AGENT"
  UP_ARGS+=(--assignee "$UP_ASSIGN")
  #   state: DAG position — a root (no depends_on) opens ready in Todo; a blocked
  #          spec waits in Backlog. Uses the SAME edge table the topo-sort is built on.
  if awk -F'\t' -v x="$id" '$1==x{f=1} END{exit f?0:1}' "$EDGES"; then
    UP_ARGS+=(--state "Backlog")
  else
    UP_ARGS+=(--state "Todo")
  fi
  #   subscribers: the human(s) who signed off (reuse $UP_SBY read above for the
  #                panel). Comma/space separated; each token its own --subscriber, and
  #                a name that doesn't resolve to a user is fail-soft skipped.
  if [ -n "$UP_SBY" ] && [ "$UP_SBY" != "(none)" ]; then
    for sub in $(printf '%s' "$UP_SBY" | tr ',' ' '); do
      [ -n "$sub" ] && UP_ARGS+=(--subscriber "$sub")
    done
  fi

  # --- Projection block (T2): per-spec `projection:` frontmatter. cycle/parent/sla
  # are NON-structural (they reference existing objects or set a scalar), so they are
  # honored on EVERY register. Structural placement (project/milestone) is gated on
  # the opt-in below, so a plain register never creates a Project. parent names a
  # SPEC id — the adapter resolves it to the parent issue via the shared marker.
  PJ_CYCLE="$(tsi_projection "$file" cycle)"
  [ -n "$PJ_CYCLE" ] && UP_ARGS+=(--cycle "$PJ_CYCLE")
  PJ_PARENT="$(tsi_projection "$file" parent)"
  [ -n "$PJ_PARENT" ] && UP_ARGS+=(--parent "$PJ_PARENT")
  PJ_SUBSORT="$(tsi_projection "$file" sub_sort)"
  [ -n "$PJ_SUBSORT" ] && UP_ARGS+=(--sub-sort "$PJ_SUBSORT")
  PJ_SLA="$(tsi_projection "$file" sla)"
  [ -n "$PJ_SLA" ] && UP_ARGS+=(--sla "$PJ_SLA")
  PJ_TEMPLATE="$(tsi_projection "$file" template)"
  [ -n "$PJ_TEMPLATE" ] && UP_ARGS+=(--template "$PJ_TEMPLATE")
  [ "$(tsi_projection "$file" use_default_template)" = "true" ] && UP_ARGS+=(--use-default-template)

  # --- Structural placement (T2/T3): ONLY when structure projection is enabled
  # (`cvg setup projection --enable`). Off by default => no --project/--milestone is
  # ever passed and a plain register stays byte-identical. The run-wide project
  # (ensured in Step 0) is the default; a per-spec `projection.project` overrides it,
  # and `projection.milestone` selects the phase within whichever project applies.
  if [ "$PROJECTION_ON" -eq 1 ]; then
    SPEC_PROJ_ID="$RUN_PROJECT_ID"
    PJ_PROJECT="$(tsi_projection "$file" project)"
    if [ -n "$PJ_PROJECT" ]; then
      SPEC_PROJ_ID="$(bash "$ADAPTER" project-ensure "$PJ_PROJECT" 2>>"$WORK/adapter.log" || true)"
    fi
    [ -n "$SPEC_PROJ_ID" ] && UP_ARGS+=(--project "$SPEC_PROJ_ID")
    PJ_MILE="$(tsi_projection "$file" milestone)"
    if [ -n "$PJ_MILE" ] && [ -n "$SPEC_PROJ_ID" ]; then
      MILE_ID="$(bash "$ADAPTER" milestone-ensure "$SPEC_PROJ_ID" "$PJ_MILE" 2>>"$WORK/adapter.log" || true)"
      [ -n "$MILE_ID" ] && UP_ARGS+=(--milestone "$MILE_ID")
    fi
  fi

  out="$(bash "$ADAPTER" upsert "${UP_ARGS[@]}" 2>>"$WORK/adapter.log")" \
    || { echo "ERROR: upsert failed for $id (see adapter.log)"; cat "$WORK/adapter.log" >&2; echo "REGISTER=FAIL"; exit 1; }
  echo "  upsert $id -> issue $out"

  # Stamp the RECEIPT back into the spec (best-effort — a receipt failure never
  # aborts a written board; the issue-side marker remains the idempotency key).
  if [[ "$STAMP_REFS" -eq 1 && -n "$out" ]]; then
    if tsi_set_tracker_ref "$file" "$TRACKER:$out" 2>>"$WORK/adapter.log"; then
      STAMPED=$((STAMPED + 1))
      echo "     receipt: tracker_ref: $TRACKER:$out -> $file"
    else
      echo "     WARN: could not stamp tracker_ref into $file (board unaffected; see adapter.log)" >&2
    fi
  fi
done < "$UPSERT_ORDER"

# Count created vs updated from the adapter log (adapters emit "created"/"updated").
# NB: `grep -c` prints "0" AND exits 1 on no match, so a `|| echo 0` fallback would
# DOUBLE it to "0\n0". Swallow the status with `|| true` and normalise to an integer.
CREATED="$(grep -c '^created ' "$WORK/adapter.log" 2>/dev/null || true)"; CREATED="${CREATED//[^0-9]/}"; CREATED="${CREATED:-0}"
UPDATED="$(grep -c '^updated ' "$WORK/adapter.log" 2>/dev/null || true)"; UPDATED="${UPDATED//[^0-9]/}"; UPDATED="${UPDATED:-0}"

echo
echo "[link] depends_on -> blocked-by"
while IFS=$'\t' read -r from dep; do
  [[ -n "$dep" ]] || continue
  bash "$ADAPTER" link --from "$from" --to "$dep" 2>>"$WORK/adapter.log" \
    || { echo "ERROR: link failed for $from blocked-by $dep"; cat "$WORK/adapter.log" >&2; echo "REGISTER=FAIL"; exit 1; }
  LINKS=$((LINKS + 1))
  echo "  $from blocked-by $dep"
done < "$EDGES"

# ----- Step 5: append-only health note (T3; opt-in) -----
# When structure projection is on, post ONE health update to the run's project — an
# append-only breadcrumb that this batch was projected. The specs are signed-off (the
# offline gate is green), so the rate is 100% of the registered count. Fail-soft: a
# health post never affects the registration outcome (same rule as the marker panel).
if [ "$PROJECTION_ON" -eq 1 ] && [ -n "$RUN_PROJECT_ID" ]; then
  echo
  echo "[health] posting an append-only project-update"
  bash "$ADAPTER" project-update --project "$RUN_PROJECT_ID" --pass-rate 100 --total "$SIGNED_COUNT" \
    2>>"$WORK/adapter.log" || echo "  WARN: health post failed (board unaffected; see adapter.log)" >&2
fi

echo
echo "----------------------------------------------------------------"
echo "REGISTERED: $SIGNED_COUNT issue(s) (created $CREATED, updated $UPDATED), $LINKS blocked-by link(s)."
[[ "$LANDED_COUNT" -gt 0 ]] && echo "left alone (landed, still on the board): $LANDED_COUNT"
[[ "$STAMP_REFS" -eq 1 ]] && echo "stamped $STAMPED tracker_ref receipt(s) back into the specs."
[[ -n "$SKIPPED" ]] && echo "skipped (un-gated): $SKIPPED"
[[ -n "$OPTED_OUT" ]] && echo "skipped (register: false): $OPTED_OUT"
echo "next: run verify-registration.sh --tracker $TRACKER to gate the mapping."
echo "REGISTER=OK"
