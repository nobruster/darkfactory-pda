#!/usr/bin/env bash
# adapters/fake.sh — an on-disk, NO-NETWORK tracker for tests + the reference impl.
#
# Implements the same five-verb contract as github.sh / linear.sh / jira.sh (see
# references/adapter-contract.md) against a local store under $TSI_FAKE_STORE, so
# register.sh's FULL live path — preflight, idempotent upsert, blocked-by link,
# list-ready, write-result — is exercised offline, deterministically, with no
# creds and no network. It is the smallest complete adapter: read it to learn the
# contract before writing a real one.
#
# NOT for production. register.sh / verify-registration.sh accept `--tracker fake`
# ONLY so the orchestration itself is testable; a real board is github|linear|jira.
#
# Store layout ($TSI_FAKE_STORE, default ./.tsi-fake-store):
#   issues.tsv   num \t extid \t title \t state(open|done)
#   links.tsv    from_extid \t to_extid          (from is blocked-by to)
#   counter      next issue number
#   bodies/<n>.md
#
# Deterministic ids: FAKE-1, FAKE-2, … in creation order. Idempotency key: the
# spec id, stored as the issue's extid (column 2) — the same "look up by id,
# update else create" rule every adapter upholds.
#
# Test hooks: TSI_FAKE_FAIL_PREFLIGHT=1 forces preflight to fail (to exercise the
# fail-closed path in register.sh).

set -euo pipefail

STORE="${TSI_FAKE_STORE:-./.tsi-fake-store}"
ISSUES="$STORE/issues.tsv"
LINKS="$STORE/links.tsv"
COUNTER="$STORE/counter"

tsi_fake_die() { echo "ERROR (fake adapter): $*" >&2; exit 1; }

_fake_init() {
  mkdir -p "$STORE/bodies"
  [[ -f "$ISSUES" ]]  || : > "$ISSUES"
  [[ -f "$LINKS" ]]   || : > "$LINKS"
  [[ -f "$COUNTER" ]] || echo 0 > "$COUNTER"
}

# extid -> "num<TAB>state" on stdout (empty if not found).
_fake_find() {
  awk -F'\t' -v e="$1" '$2==e{print $1"\t"$4; exit}' "$ISSUES"
}

# ---------------------------------------------------------------------------
# VERB: preflight — always reachable (no creds). Honors the test fail hook.
# ---------------------------------------------------------------------------
fake_preflight() {
  _fake_init
  if [[ "${TSI_FAKE_FAIL_PREFLIGHT:-0}" == "1" ]]; then
    echo "preflight failed: TSI_FAKE_FAIL_PREFLIGHT=1 (test hook)" >&2
    echo "remediation: unset TSI_FAKE_FAIL_PREFLIGHT" >&2
    return 1
  fi
  echo "preflight ok: fake tracker at $STORE"
  return 0
}

# ---------------------------------------------------------------------------
# VERB: upsert --id ID --title T --body-file F [--label L ...]
# ---------------------------------------------------------------------------
# Find-by-extid then update, else create. Echoes the issue ref (FAKE-N) on
# stdout; the created/updated note goes to stderr (register.sh greps it).
fake_upsert() {
  _fake_init
  local id="" title="" body_file="" labels="" prio="" effort="" due="" attrs="" specurl=""
  # Projection enrichment (T1/T2). The fake adapter does not project onto anything,
  # but — unlike the github/jira degrade, which discards — it CAPTURES these into the
  # meta file so the offline suite can assert the driver wired them correctly. Shift
  # widths MUST match linear.sh (every arg takes a value except bare --use-default-
  # template), or the arg parse desyncs.
  local assignee="" state="" subscribers="" project="" milestone="" cycle="" parent="" subsort="" template="" usedefault=0 sla=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id)        id="$2"; shift 2 ;;
      --title)     title="$2"; shift 2 ;;
      --body-file) body_file="$2"; shift 2 ;;
      --label)     labels="${labels}${labels:+ }$2"; shift 2 ;;
      --priority)  prio="$2"; shift 2 ;;
      --effort)    effort="$2"; shift 2 ;;
      --due)       due="$2"; shift 2 ;;
      --attr)      attrs="${attrs}${attrs:+;}$2"; shift 2 ;;
      --spec-url)  specurl="$2"; shift 2 ;;
      --assignee)             assignee="$2"; shift 2 ;;
      --state)                state="$2"; shift 2 ;;
      --subscriber)           subscribers="${subscribers}${subscribers:+ }$2"; shift 2 ;;
      --project)              project="$2"; shift 2 ;;
      --milestone)            milestone="$2"; shift 2 ;;
      --cycle)                cycle="$2"; shift 2 ;;
      --parent)               parent="$2"; shift 2 ;;
      --sub-sort)             subsort="$2"; shift 2 ;;
      --template)             template="$2"; shift 2 ;;
      --use-default-template) usedefault=1; shift ;;
      --sla)                  sla="$2"; shift 2 ;;
      *) tsi_fake_die "upsert: unknown arg '$1'" ;;
    esac
  done
  # Record the triage + projection the driver passed so tests can assert the wiring
  # offline (this file IS the observable surface for the register e2e suite).
  mkdir -p "$STORE/meta"
  printf 'labels=%s\npriority=%s\neffort=%s\ndue=%s\nattrs=%s\nspecurl=%s\nassignee=%s\nstate=%s\nsubscribers=%s\nproject=%s\nmilestone=%s\ncycle=%s\nparent=%s\nsubsort=%s\ntemplate=%s\nusedefault=%s\nsla=%s\n' \
    "$labels" "$prio" "$effort" "$due" "$attrs" "$specurl" \
    "$assignee" "$state" "$subscribers" "$project" "$milestone" "$cycle" "$parent" "$subsort" "$template" "$usedefault" "$sla" > "$STORE/meta/$id.txt"
  [[ -n "$id" ]]    || tsi_fake_die "upsert: --id required"
  [[ -n "$title" ]] || tsi_fake_die "upsert: --title required"

  local found num
  found="$(_fake_find "$id")"
  if [[ -n "$found" ]]; then
    num="$(printf '%s' "$found" | cut -f1)"
    local tmp="$ISSUES.tmp.$$"
    awk -F'\t' -v e="$id" -v t="$title" 'BEGIN{OFS="\t"} $2==e{$3=t} {print}' "$ISSUES" > "$tmp" && mv "$tmp" "$ISSUES"
    [[ -n "$body_file" && -f "$body_file" ]] && cp "$body_file" "$STORE/bodies/${num#FAKE-}.md"
    echo "updated $num ($id)" >&2
    echo "$num"
  else
    local n
    n="$(( $(cat "$COUNTER") + 1 ))"
    echo "$n" > "$COUNTER"
    num="FAKE-$n"
    printf '%s\t%s\t%s\t%s\n' "$num" "$id" "$title" "open" >> "$ISSUES"
    [[ -n "$body_file" && -f "$body_file" ]] && cp "$body_file" "$STORE/bodies/$n.md"
    echo "created $num ($id)" >&2
    echo "$num"
  fi
}

# ---------------------------------------------------------------------------
# VERB: link --from ID --to ID  (FROM is blocked-by TO). Idempotent (dedupes).
# ---------------------------------------------------------------------------
fake_link() {
  _fake_init
  local from_id="" to_id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from) from_id="$2"; shift 2 ;;
      --to)   to_id="$2"; shift 2 ;;
      *) tsi_fake_die "link: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$from_id" && -n "$to_id" ]] || tsi_fake_die "link: --from and --to required"
  [[ -n "$(_fake_find "$from_id")" ]] || tsi_fake_die "link: from-issue not found for $from_id"
  [[ -n "$(_fake_find "$to_id")" ]]   || tsi_fake_die "blocked-by target not found for $to_id"
  if ! awk -F'\t' -v a="$from_id" -v b="$to_id" '$1==a&&$2==b{f=1} END{exit f?0:1}' "$LINKS"; then
    printf '%s\t%s\n' "$from_id" "$to_id" >> "$LINKS"
  fi
  echo "linked: $from_id blocked-by $to_id" >&2
}

# ---------------------------------------------------------------------------
# VERB: list-ready — open issues with no OPEN blocker. Echoes refs, one per line.
# ---------------------------------------------------------------------------
fake_list_ready() {
  _fake_init
  local num ext title state dep dstate blocked
  while IFS=$'\t' read -r num ext title state; do
    [[ -n "$num" ]] || continue
    [[ "$state" == "open" ]] || continue
    blocked=0
    for dep in $(awk -F'\t' -v e="$ext" '$1==e{print $2}' "$LINKS"); do
      dstate="$(awk -F'\t' -v e="$dep" '$2==e{print $4; exit}' "$ISSUES")"
      if [[ "$dstate" == "open" ]]; then blocked=1; break; fi
    done
    [[ "$blocked" -eq 0 ]] && echo "$num"
  done < "$ISSUES"
  # Contract: list-ready exits 0 on success even if the last issue was blocked
  # (a trailing false `[[ ]] && echo` would otherwise leave a non-zero status,
  # and a caller that does `list-ready > f || : > f` would discard the output).
  return 0
}

# ---------------------------------------------------------------------------
# VERB: write-result --issue REF --status pass|fail [--pr URL] [--reason TEXT]
# ---------------------------------------------------------------------------
# The LOOP's write side (Pass 8), not registration. On pass, marks the issue done.
fake_write_result() {
  _fake_init
  local issue="" status="" pr="" reason=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --issue)  issue="$2"; shift 2 ;;
      --status) status="$2"; shift 2 ;;
      --pr)     pr="$2"; shift 2 ;;
      --reason) reason="$2"; shift 2 ;;
      *) tsi_fake_die "write-result: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$issue" ]] || tsi_fake_die "write-result: --issue required"
  case "$status" in pass|fail) ;; *) tsi_fake_die "write-result: --status must be pass|fail" ;; esac

  # Accept a raw ref (FAKE-N) or a spec extid.
  local num
  if awk -F'\t' -v e="$issue" '$1==e{f=1} END{exit f?0:1}' "$ISSUES"; then
    num="$issue"
  else
    num="$(_fake_find "$issue" | cut -f1)"
  fi
  [[ -n "$num" ]] || tsi_fake_die "write-result: issue not found: $issue"

  if [[ "$status" == "pass" ]]; then
    local tmp="$ISSUES.tmp.$$"
    awk -F'\t' -v n="$num" 'BEGIN{OFS="\t"} $1==n{$4="done"} {print}' "$ISSUES" > "$tmp" && mv "$tmp" "$ISSUES"
    echo "completed $num (pass)${pr:+ PR: $pr}"
  else
    echo "commented $num (fail)${reason:+ reason: $reason}"
  fi
}

# ---------------------------------------------------------------------------
# PROJECTION verbs (T2/T3) — DETERMINISTIC, on-disk, no network.
# ---------------------------------------------------------------------------
# The reference adapter models the Linear projection surface faithfully enough to
# test the driver's Step-0 pre-pass offline: structure ensure is IDEMPOTENT BY NAME
# (the returned id is a slug of the name, so a re-run resolves the SAME id and never
# duplicates — exactly the guarantee linear-structure.sh gives via projection.lock).
# Every ensure is logged to $STORE/structure.tsv so a test can assert what was built.

# Slugify a logical name into a stable, filesystem-safe id fragment.
_fake_slug() { printf '%s' "$1" | tr -cs 'A-Za-z0-9' '-' | sed -E 's/^-+//; s/-+$//'; }

# Record a structure ensure (kind<TAB>name<TAB>id), deduped, for test assertions.
_fake_structure_log() {
  _fake_init
  local kind="$1" name="$2" fid="$3" f="$STORE/structure.tsv"
  [[ -f "$f" ]] || : > "$f"
  if ! awk -F'\t' -v k="$kind" -v n="$name" '$1==k&&$2==n{f=1} END{exit f?0:1}' "$f"; then
    printf '%s\t%s\t%s\n' "$kind" "$name" "$fid" >> "$f"
  fi
}

# project-ensure NAME | initiative-ensure NAME  -> deterministic id (echoed).
fake_ensure() {
  local kind="$1"; shift || true
  local name="${1:-}"
  [[ -n "$name" ]] || tsi_fake_die "${kind}-ensure: NAME required"
  local fid; fid="FAKE-$(printf '%s' "$kind" | tr '[:lower:]' '[:upper:]')-$(_fake_slug "$name")"
  _fake_structure_log "$kind" "$name" "$fid"
  echo "$fid"
}

# milestone-ensure PROJECT_ID NAME -> deterministic id, scoped to the project id.
fake_milestone_ensure() {
  local proj="${1:-}" name="${2:-}"
  [[ -n "$proj" && -n "$name" ]] || tsi_fake_die "milestone-ensure: PROJECT_ID NAME required"
  local fid; fid="FAKE-MILE-$(_fake_slug "$proj")-$(_fake_slug "$name")"
  _fake_structure_log "milestone:$proj" "$name" "$fid"
  echo "$fid"
}

# project-update --project P --pass-rate N --total T  -> append-only health log.
fake_project_update() {
  _fake_init
  local proj="" rate="" total=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project)   proj="$2"; shift 2 ;;
      --pass-rate) rate="$2"; shift 2 ;;
      --total)     total="$2"; shift 2 ;;
      *) tsi_fake_die "project-update: unknown arg '$1'" ;;
    esac
  done
  printf 'project=%s\trate=%s\ttotal=%s\n' "$proj" "$rate" "$total" >> "$STORE/health.tsv"
  echo "project-update posted (fake)" >&2
  return 0
}

# document --title T --content-file F --project P -> ensure-by-title (logged).
fake_document() {
  _fake_init
  local title="" cfile="" proj=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title)        title="$2"; shift 2 ;;
      --content-file) cfile="$2"; shift 2 ;;
      --project)      proj="$2"; shift 2 ;;
      *) tsi_fake_die "document: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$title" && -n "$proj" ]] || tsi_fake_die "document: --title and --project required"
  local fid; fid="FAKE-DOC-$(_fake_slug "$proj")-$(_fake_slug "$title")"
  _fake_structure_log "document:$proj" "$title" "$fid"
  echo "$fid"
}

# users -> id<TAB>name<TAB>email. One synthetic identity makes
# `cvg setup identity` and the identity contract exercisable offline; a
# real adapter enumerates the board.
fake_users() {
  printf 'FAKE-USER-1\tFake Tester\ttester@example.invalid\n'
}

# ---------------------------------------------------------------------------
# VERB: list-issues — EVERY registered issue as  extid<TAB>ref  (the parity gate).
# ---------------------------------------------------------------------------
# Unlike list-ready (roots only), this is the FULL registered set, keyed on the
# spec id (extid, column 2 of the store). verify-registration.sh diffs it against
# the signed-off specs to prove 1:1 — count parity, no orphan, no missing, no
# double-registration. The store's extid column IS the marker every real adapter
# recovers from its issue body/attachment/label.
fake_list_issues() {
  _fake_init
  awk -F'\t' 'NF>=2 && $2!="" {print $2"\t"$1}' "$ISSUES"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
_fake_main() {
  local verb="${1:-}"
  [[ $# -gt 0 ]] && shift || true
  case "$verb" in
    preflight)    fake_preflight "$@" ;;
    upsert)       fake_upsert "$@" ;;
    link)         fake_link "$@" ;;
    list-ready)   fake_list_ready "$@" ;;
    list-issues)  fake_list_issues "$@" ;;
    write-result) fake_write_result "$@" ;;
    project-ensure)    fake_ensure project "$@" ;;
    initiative-ensure) fake_ensure initiative "$@" ;;
    milestone-ensure)  fake_milestone_ensure "$@" ;;
    project-update)    fake_project_update "$@" ;;
    document)          fake_document "$@" ;;
    users)             fake_users "$@" ;;
    ""|-h|--help)
      grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
      ;;
    *) tsi_fake_die "unknown verb '$verb' (want: preflight|upsert|link|list-ready|list-issues|write-result|project-ensure|milestone-ensure|initiative-ensure|project-update|document|users)" ;;
  esac
}

_fake_main "$@"
