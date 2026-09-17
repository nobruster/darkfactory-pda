#!/usr/bin/env bash
# adapters/linear-structure.sh — T3 structure projection for the Linear backend.
#
# FUNCTION-ONLY companion (like linear-native.sh / linear-projection.sh): SOURCED
# by adapters/linear.sh behind an existence guard, AFTER the core helpers are
# defined and BEFORE _ln_main. It leans on the parent's _linear_gql / tsi_ln_die /
# _ln_is_uuid and defines: the ensure-by-name helpers, plus the verb handlers
# linear.sh dispatches (project-ensure | milestone-ensure | initiative-ensure |
# project-update | document).
#
# WHY ensure-by-name (not the issue marker): Projects, ProjectMilestones and
# Initiatives cannot carry the attachment-URL marker that makes an Issue
# idempotent (attachmentsForURL is an Issue-only mechanism). So structure keys on
# a DETERMINISTIC LOGICAL NAME and a local resolution cache:
#   1) consult .cvg/projection.lock (TSV: kind<TAB>logical_name<TAB>uuid) first;
#   2) re-validate a cached uuid against a LIVE name-query and self-heal on a 404;
#   3) else query the live board by name (team-scoped for projects/milestones,
#      workspace-scoped for initiatives) and reuse; else create, then cache.
# A re-run therefore resolves the SAME objects and never duplicates.
#
# projectUpdateCreate is the ONE deliberately NON-idempotent surface: an
# append-only health note, posted once per invocation, gated upstream behind
# projection_enabled. Everything else is fail-soft: a rejected optional structure
# never aborts a registration.

# ---------------------------------------------------------------------------
# .cvg/projection.lock — kind<TAB>logical_name<TAB>uuid resolution cache.
# ---------------------------------------------------------------------------
_ln_lock_file() {
  printf '%s' "${TSI_PROJECTION_LOCK:-${CVG_HOME_DIR:-.}/.cvg/projection.lock}"
}

# _ln_lock_get KIND NAME -> cached uuid (empty if absent). Exact kind+name match.
_ln_lock_get() {
  local kind="$1" name="$2" f
  case "$kind$name" in
    *$'\t'*|*$'\r'*|*$'\n'*) printf ''; return 0 ;;
  esac
  f="$(_ln_lock_file)"
  [ -f "$f" ] && [ ! -L "$f" ] || { printf ''; return 0; }
  awk -F'\t' -v k="$kind" -v n="$name" '$1==k && $2==n {print $3; exit}' "$f" 2>/dev/null || printf ''
}

# _ln_lock_put KIND NAME UUID -> record the mapping (replace an existing row,
# else append). Best-effort: a cache-write failure never aborts the caller.
_ln_lock_put() {
  local kind="$1" name="$2" uuid="$3" f dir tmp input
  [ -n "$uuid" ] || return 0
  case "$kind$name$uuid" in
    *$'\t'*|*$'\r'*|*$'\n'*) return 0 ;;
  esac
  f="$(_ln_lock_file)"
  # The cache is machine-local identity metadata. Refuse symlinks, write through
  # an unpredictable same-directory temporary, and keep it private just like
  # .cvg/config and .cvg/identity.
  if [ -L "$f" ] || { [ -e "$f" ] && [ ! -f "$f" ]; }; then
    return 0
  fi
  dir="$(dirname "$f")"
  mkdir -p "$dir" 2>/dev/null || return 0
  tmp="$(mktemp "$dir/.projection-lock.XXXXXX" 2>/dev/null)" || return 0
  chmod 600 "$tmp" 2>/dev/null || true
  input="/dev/null"
  [ -f "$f" ] && input="$f"
  awk -F'\t' -v k="$kind" -v n="$name" -v u="$uuid" '
    BEGIN{OFS="\t"; done=0}
    $1==k && $2==n {print k,n,u; done=1; next}
    {print}
    END{ if(!done) print k,n,u }
  ' "$input" > "$tmp" 2>/dev/null \
    && mv "$tmp" "$f" 2>/dev/null \
    && chmod 600 "$f" 2>/dev/null \
    || rm -f "$tmp" 2>/dev/null
  return 0
}

# _ln_issue_uuid_live_project UUID -> echo the project's id if it still exists
# live (used to self-heal a stale cached uuid). Empty on any miss.
_ln_project_alive() {
  local uuid="$1" resp
  [ -n "$uuid" ] || { printf ''; return 0; }
  resp="$(_linear_gql 'query($id:String!){ project(id:$id){ id } }' \
    "$(jq -n --arg id "$uuid" '{id:$id}')" 2>/dev/null)" || { printf ''; return 0; }
  printf '%s' "$resp" | jq -r '.data.project.id // empty' 2>/dev/null || printf ''
}

# ---------------------------------------------------------------------------
# _ln_ensure_project NAME -> project UUID (cache -> live name-query -> create).
# ---------------------------------------------------------------------------
_ln_ensure_project() {
  local name="$1" cached live id=""
  [ -n "$name" ] || { printf ''; return 0; }
  [ -n "${LINEAR_TEAM_ID:-}" ] || { printf ''; return 0; }
  # 1) cache, re-validated live (self-heal a stale uuid).
  cached="$(_ln_lock_get project "$name")"
  if [ -n "$cached" ]; then
    live="$(_ln_project_alive "$cached")"
    if [ -n "$live" ]; then printf '%s' "$live"; return 0; fi
  fi
  # 2) live name-query, team-scoped.
  local resp
  resp="$(_linear_gql \
    'query($t:String!,$n:String!){ team(id:$t){ projects(filter:{ name:{ eq:$n } }){ nodes{ id name } } } }' \
    "$(jq -n --arg t "$LINEAR_TEAM_ID" --arg n "$name" '{t:$t,n:$n}')" 2>/dev/null)" || resp=""
  id="$(printf '%s' "$resp" | jq -r '.data.team.projects.nodes[0].id // empty' 2>/dev/null)" || id=""
  # 3) create.
  if [ -z "$id" ]; then
    resp="$(_linear_gql \
      'mutation($n:String!,$team:String!){ projectCreate(input:{ name:$n, teamIds:[$team] }){ success project{ id } } }' \
      "$(jq -n --arg n "$name" --arg team "$LINEAR_TEAM_ID" '{n:$n,team:$team}')" 2>/dev/null)" || resp=""
    id="$(printf '%s' "$resp" | jq -r '.data.projectCreate.project.id // empty' 2>/dev/null)" || id=""
  fi
  [ -n "$id" ] && _ln_lock_put project "$name" "$id"
  printf '%s' "$id"
}

# ---------------------------------------------------------------------------
# _ln_ensure_milestone PROJECT_UUID NAME -> milestone UUID (project-scoped).
# ---------------------------------------------------------------------------
_ln_ensure_milestone() {
  local proj="$1" name="$2" cached id="" resp
  [ -n "$proj" ] && [ -n "$name" ] || { printf ''; return 0; }
  cached="$(_ln_lock_get "milestone:$proj" "$name")"
  if [ -n "$cached" ]; then printf '%s' "$cached"; return 0; fi
  resp="$(_linear_gql \
    'query($p:String!){ project(id:$p){ projectMilestones{ nodes{ id name } } } }' \
    "$(jq -n --arg p "$proj" '{p:$p}')" 2>/dev/null)" || resp=""
  id="$(printf '%s' "$resp" | jq -r --arg n "$name" \
      '[.data.project.projectMilestones.nodes[]? | select(.name==$n) | .id][0] // empty' 2>/dev/null)" || id=""
  if [ -z "$id" ]; then
    resp="$(_linear_gql \
      'mutation($n:String!,$p:String!){ projectMilestoneCreate(input:{ name:$n, projectId:$p }){ success projectMilestone{ id } } }' \
      "$(jq -n --arg n "$name" --arg p "$proj" '{n:$n,p:$p}')" 2>/dev/null)" || resp=""
    id="$(printf '%s' "$resp" | jq -r '.data.projectMilestoneCreate.projectMilestone.id // empty' 2>/dev/null)" || id=""
  fi
  [ -n "$id" ] && _ln_lock_put "milestone:$proj" "$name" "$id"
  printf '%s' "$id"
}

# ---------------------------------------------------------------------------
# _ln_ensure_initiative NAME -> initiative UUID (WORKSPACE-scoped ensure-by-name).
# ---------------------------------------------------------------------------
_ln_ensure_initiative() {
  local name="$1" cached id="" resp
  [ -n "$name" ] || { printf ''; return 0; }
  cached="$(_ln_lock_get initiative "$name")"
  if [ -n "$cached" ]; then printf '%s' "$cached"; return 0; fi
  resp="$(_linear_gql \
    'query($n:String!){ initiatives(filter:{ name:{ eq:$n } }){ nodes{ id name } } }' \
    "$(jq -n --arg n "$name" '{n:$n}')" 2>/dev/null)" || resp=""
  id="$(printf '%s' "$resp" | jq -r '.data.initiatives.nodes[0].id // empty' 2>/dev/null)" || id=""
  if [ -z "$id" ]; then
    resp="$(_linear_gql \
      'mutation($n:String!){ initiativeCreate(input:{ name:$n }){ success initiative{ id } } }' \
      "$(jq -n --arg n "$name" '{n:$n}')" 2>/dev/null)" || resp=""
    id="$(printf '%s' "$resp" | jq -r '.data.initiativeCreate.initiative.id // empty' 2>/dev/null)" || id=""
  fi
  [ -n "$id" ] && _ln_lock_put initiative "$name" "$id"
  printf '%s' "$id"
}

# _ln_link_initiative_project INIT_UUID PROJ_UUID — nest the project under the
# initiative. Linear dedupes an identical pair, so this is safe to re-run.
_ln_link_initiative_project() {
  local init="$1" proj="$2"
  [ -n "$init" ] && [ -n "$proj" ] || return 0
  # MUST be _ln_gql_soft (a subshell): re-linking an ALREADY-linked pair makes Linear
  # return an error, and _linear_gql exits on error — a bare `|| true` would not catch
  # it, killing the verb before it printed the initiative id ("(skipped)" on re-runs).
  _ln_gql_soft \
    'mutation($i:String!,$p:String!){ initiativeToProjectCreate(input:{ initiativeId:$i, projectId:$p }){ success } }' \
    "$(jq -n --arg i "$init" --arg p "$proj" '{i:$i,p:$p}')"
  return 0
}

# ===========================================================================
# VERB HANDLERS — dispatched by linear.sh _ln_main.
# ===========================================================================

# project-ensure NAME  -> echo project UUID (stdout, for the caller to reuse).
ln_project_ensure() {
  _ln_require_tools
  [ -n "${LINEAR_TEAM_ID:-}" ] || tsi_ln_die "project-ensure: LINEAR_TEAM_ID unset"
  local name="${1:-}"
  [ -n "$name" ] || tsi_ln_die "project-ensure: NAME required"
  _ln_ensure_project "$name"
}

# milestone-ensure PROJECT_UUID NAME  -> echo milestone UUID.
ln_milestone_ensure() {
  _ln_require_tools
  local proj="${1:-}" name="${2:-}"
  [ -n "$proj" ] && [ -n "$name" ] || tsi_ln_die "milestone-ensure: PROJECT_UUID NAME required"
  _ln_ensure_milestone "$proj" "$name"
}

# initiative-ensure NAME  -> echo initiative UUID.
# initiative-ensure NAME [PROJECT_UUID]  -> echo initiative UUID; when a project
# uuid is given, nest it under the initiative (idempotent — Linear dedupes the pair).
ln_initiative_ensure() {
  _ln_require_tools
  local name="${1:-}" proj="${2:-}" id
  [ -n "$name" ] || tsi_ln_die "initiative-ensure: NAME required"
  id="$(_ln_ensure_initiative "$name")"
  if [ -n "$id" ] && [ -n "$proj" ]; then _ln_link_initiative_project "$id" "$proj"; fi
  printf '%s' "$id"
}

# project-update --project UUID --pass-rate N --total T
# Post ONE append-only health note. health = onTrack(>=0.9)/atRisk(>=0.6)/offTrack.
ln_project_update() {
  _ln_require_tools
  local proj="" rate="" total=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --project)   proj="$2"; shift 2 ;;
      --pass-rate) rate="$2"; shift 2 ;;
      --total)     total="$2"; shift 2 ;;
      *) tsi_ln_die "project-update: unknown arg '$1'" ;;
    esac
  done
  [ -n "$proj" ] || tsi_ln_die "project-update: --project required"
  local r="${rate:-0}" health body
  # Integer-safe threshold on a 0..100 percent (register passes an integer percent).
  if [ "$r" -ge 90 ] 2>/dev/null; then health="onTrack"
  elif [ "$r" -ge 60 ] 2>/dev/null; then health="atRisk"
  else health="offTrack"; fi
  body="cvg register — ${r}% of ${total:-?} signed-off eval(s) green. Projected by REGISTER ①."
  _ln_gql_soft \
    'mutation($p:String!,$b:String!,$h:ProjectUpdateHealthType){ projectUpdateCreate(input:{ projectId:$p, body:$b, health:$h }){ success } }' \
    "$(jq -n --arg p "$proj" --arg b "$body" --arg h "$health" '{p:$p,b:$b,h:$h}')"
  echo "project-update posted ($health)" >&2
  return 0
}

# document --title T --content-file F --project UUID
# Ensure-by-title under the project: update content on a hit, else create.
ln_document() {
  _ln_require_tools
  local title="" cfile="" proj=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --title)        title="$2"; shift 2 ;;
      --content-file) cfile="$2"; shift 2 ;;
      --project)      proj="$2"; shift 2 ;;
      *) tsi_ln_die "document: unknown arg '$1'" ;;
    esac
  done
  [ -n "$title" ] && [ -n "$proj" ] || tsi_ln_die "document: --title and --project required"
  local content="" resp existing
  [ -n "$cfile" ] && [ -f "$cfile" ] && content="$(cat "$cfile")"
  resp="$(_linear_gql \
    'query($p:String!){ project(id:$p){ documents{ nodes{ id title } } } }' \
    "$(jq -n --arg p "$proj" '{p:$p}')" 2>/dev/null)" || resp=""
  existing="$(printf '%s' "$resp" | jq -r --arg t "$title" \
      '[.data.project.documents.nodes[]? | select(.title==$t) | .id][0] // empty' 2>/dev/null)" || existing=""
  if [ -n "$existing" ]; then
    _ln_gql_soft \
      'mutation($id:String!,$c:String!){ documentUpdate(id:$id, input:{ content:$c }){ success } }' \
      "$(jq -n --arg id "$existing" --arg c "$content" '{id:$id,c:$c}')"
    echo "document updated ($title)" >&2
  else
    _ln_gql_soft \
      'mutation($t:String!,$c:String!,$p:String!){ documentCreate(input:{ title:$t, content:$c, projectId:$p }){ success document{ id } } }' \
      "$(jq -n --arg t "$title" --arg c "$content" --arg p "$proj" '{t:$t,c:$c,p:$p}')"
    echo "document created ($title)" >&2
  fi
  return 0
}
