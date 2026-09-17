#!/usr/bin/env bash
# adapters/linear-native.sh — T1 native-field helpers for the Linear adapter.
#
# A FUNCTION-ONLY companion: linear.sh sources it (behind an existence guard) AFTER
# its core transport helpers are defined, so everything here leans on the parent's
# _linear_gql / tsi_ln_die / _ln_is_uuid instead of re-implementing them. There is
# NO dispatch and NO `main` call — sourcing this file only defines functions.
#
# These map signal a spec ALREADY carries onto Linear's native issue fields, with
# the same ownership split the label projection uses (see linear.sh):
#   * assigneeId    (from execution_backend / agent via .cvg/identity) CREATE-only
#   * stateId       (DAG root -> Todo, blocked -> Backlog)                CREATE-only
#   * subscriberIds (from signed_off_by)                                 union-merged
#
# Resolution is READ-ONLY and every miss is FAIL-SOFT: an unmapped key, an
# unresolvable email, or an absent state all echo empty so the caller simply OMITS
# the field. Union-merge never drops a human. A cosmetic projection field must
# never break a registration. See references/identity.md for the KEY=VALUE map.

set -euo pipefail

# ---------------------------------------------------------------------------
# _ln_identity_lookup KEY — echo the value mapped to KEY in
# $TSI_IDENTITY, falling back to `default`.
# ---------------------------------------------------------------------------
# The map is a plain KEY=VALUE file of CHOICES (never secrets): keys are
# `backend:<engine>`, `agent:<role>`, or `default`; values are a Linear user's
# email or uuid. Pure read — no network, no side effect — so it is safe to call on
# every register. Absent file / absent key / absent default all echo empty.
_ln_identity_lookup() {
  local key="$1" file="${TSI_IDENTITY:-}" val=""
  [[ -n "$key" ]] || { printf ''; return 0; }
  [[ -n "$file" && -f "$file" ]] || { printf ''; return 0; }
  # First exact `KEY=` hit wins (setup writes replace-or-append, so there is one);
  # everything after the first `=` is the value verbatim (an email/uuid has none).
  val="$(awk -F= -v k="$key" '$1 == k {sub(/^[^=]*=/, ""); print; exit}' "$file" 2>/dev/null)" || val=""
  # Fall back to the shared `default` mapping when this key is unmapped.
  if [[ -z "$val" && "$key" != "default" ]]; then
    val="$(awk -F= '$1 == "default" {sub(/^[^=]*=/, ""); print; exit}' "$file" 2>/dev/null)" || val=""
  fi
  printf '%s' "$val"
}

# ---------------------------------------------------------------------------
# _ln_resolve_user VALUE  — resolve an identity value to a Linear user UUID.
# ---------------------------------------------------------------------------
# A UUID passes straight through; anything else is treated as an email and looked
# up via users(filter:{email:{eq}}). Read-only and fail-soft: an empty input, a
# transport error, or an email with no matching user all echo empty so the caller
# omits assigneeId / drops the subscriber rather than aborting the registration.
_ln_resolve_user() {
  local val="$1" resp id=""
  [[ -n "$val" ]] || { printf ''; return 0; }
  if _ln_is_uuid "$val"; then printf '%s' "$val"; return 0; fi
  resp="$(_linear_gql \
    'query($e:String!){ users(filter:{ email:{ eq:$e } }){ nodes{ id } } }' \
    "$(jq -n --arg e "$val" '{e:$e}')" 2>/dev/null)" || { printf ''; return 0; }
  id="$(printf '%s' "$resp" | jq -r '.data.users.nodes[0].id // empty' 2>/dev/null)" || id=""
  printf '%s' "$id"
}

# ---------------------------------------------------------------------------
# _ln_state_id NAME_OR_TYPE  — resolve a workflow-state NAME (or type) to its id.
# ---------------------------------------------------------------------------
# register seeds `--state Todo` for a DAG root and `--state Backlog` for a blocked
# issue. Resolution reads the team's workflow states and matches, in order:
#   1) a state whose NAME equals the argument, case-insensitively;
#   2) else a state of the mapped TYPE — Todo -> `unstarted`, Backlog -> `backlog`
#      (any other argument is tried as a literal type) — so a team that renamed its
#      columns still resolves.
# stateId is CREATE-only upstream (the loop owns transitions after, so a re-sync
# would fight Pass-8 Done moves), so this only ever seeds the opening column.
# Empty on any miss -> the caller omits stateId.
_ln_state_id() {
  local want="$1" resp lc want_type id=""
  [[ -n "$want" ]] || { printf ''; return 0; }
  [[ -n "${LINEAR_TEAM_ID:-}" ]] || { printf ''; return 0; }
  resp="$(_linear_gql 'query($id:String!){ team(id:$id){ states{ nodes{ id name type } } } }' \
    "$(jq -n --arg id "$LINEAR_TEAM_ID" '{id:$id}')" 2>/dev/null)" || { printf ''; return 0; }
  lc="$(printf '%s' "$want" | tr '[:upper:]' '[:lower:]')"
  # 1) case-insensitive NAME match. `[...][0] // empty` (not `| head -1`) so a
  # closed pipe can't SIGPIPE the pipeline under `set -o pipefail`.
  id="$(printf '%s' "$resp" | jq -r --arg n "$lc" \
      '[.data.team.states.nodes[]? | select((.name|ascii_downcase)==$n) | .id][0] // empty' 2>/dev/null)" || id=""
  if [[ -n "$id" ]]; then printf '%s' "$id"; return 0; fi
  # 2) fall back to a state TYPE.
  case "$lc" in
    todo)    want_type="unstarted" ;;
    backlog) want_type="backlog" ;;
    *)       want_type="$lc" ;;
  esac
  id="$(printf '%s' "$resp" | jq -r --arg t "$want_type" \
      '[.data.team.states.nodes[]? | select(.type==$t) | .id][0] // empty' 2>/dev/null)" || id=""
  printf '%s' "$id"
}

# ---------------------------------------------------------------------------
# _ln_merge_subscribers ISSUE_UUID "val val ..."  — union the issue's current
# subscribers with the resolved values; echo the merged JSON array of user ids.
# ---------------------------------------------------------------------------
# subscriberIds REPLACES the set on an issueUpdate, exactly like labelIds, so a
# blind write would drop whoever a human had subscribed. We read the existing
# subscribers first and UNION the resolved values onto them (| unique), so the set
# only ever GROWS — a human subscriber is never dropped. Each value is resolved via
# _ln_resolve_user (uuid passthrough / email lookup); an unresolvable value is
# skipped. Fail-soft: any error falls back to the existing set unchanged.
_ln_merge_subscribers() {
  local issue="$1" vals="${2:-}" resp existing add="" v uid addj="[]"
  resp="$(_linear_gql 'query($id:String!){ issue(id:$id){ subscribers{ nodes{ id } } } }' \
    "$(jq -n --arg id "$issue" '{id:$id}')" 2>/dev/null)" || resp=""
  existing="$(printf '%s' "$resp" | jq -c '[.data.issue.subscribers.nodes[]?.id]' 2>/dev/null)" || existing="[]"
  [[ -n "$existing" ]] || existing="[]"
  # Resolve each requested value; keep only the hits (if/fi keeps the loop body's
  # last status 0 under `set -e`, mirroring _ln_label_ids).
  for v in $vals; do
    uid="$(_ln_resolve_user "$v" || true)"
    if [[ -n "$uid" ]]; then add="${add}${add:+ }${uid}"; fi
  done
  [[ -n "$add" ]] && addj="$(printf '%s\n' $add | jq -R . | jq -s -c .)"
  jq -c -n --argjson a "$existing" --argjson b "$addj" '($a + $b) | unique' 2>/dev/null || printf '%s' "$existing"
}
