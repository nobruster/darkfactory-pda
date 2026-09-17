#!/usr/bin/env bash
# adapters/jira.sh — Jira Cloud backend for task-specs-to-issues.  *** GATED ***
#
# STATUS: CODE-COMPLETE, GATED. All five verbs carry the REAL Jira Cloud REST v3
# request shapes and are fully implemented — preflight is live; upsert / link /
# list-ready / write-result (including the runtime Done-transition resolution) are
# complete. Write verbs stay behind an explicit TSI_JIRA_ENABLE=1 until a
# maintainer validates the payloads against a live project, so an unvalidated
# adapter can never silently half-register a board. Same five-verb contract as
# github.sh / linear.sh / fake.sh (see references/adapter-contract.md).
#
# Auth (Jira Cloud): HTTP Basic with `email:api_token`, base64-encoded.
#   JIRA_BASE_URL    — e.g. https://your-org.atlassian.net
#   JIRA_EMAIL       — the account email
#   JIRA_API_TOKEN   — an Atlassian API token
#   JIRA_PROJECT_KEY — the project the issues live under, e.g. ENG
#
# Idempotency key: the spec id in a `task-spec:<id>` LABEL plus a summary tag
# `[task-spec:<id>]`, looked up first with JQL (see references/idempotency-keys.md).
#
# Dependency edges use Jira issue links of type "Blocks": the dependency issue
# "blocks" the dependent, which Jira surfaces as "is blocked by" on the dependent.
#
# PROJECTION (Linear-only) verbs degrade to NO-OPS here — project-ensure /
# milestone-ensure / initiative-ensure / document echo a synthetic id and create
# nothing; project-update and users do nothing. upsert also accepts-and-discards
# the Linear projection flags (--assignee, --state, --subscriber, --project,
# --milestone, --cycle, --parent, --sub-sort, --template, --use-default-template,
# --sla). So a spec that projects into Linear still registers on a Jira board
# unchanged. These no-ops need NO creds and are NOT behind the TSI_JIRA_ENABLE
# write-gate, since they write nothing.

set -euo pipefail

JIRA_LABEL_PREFIX="${JIRA_LABEL_PREFIX:-task-spec}"

tsi_jira_die() { echo "ERROR (jira adapter): $*" >&2; exit 1; }

_jira_require_tools() {
  command -v curl >/dev/null 2>&1 || tsi_jira_die "curl not found on PATH"
  command -v jq >/dev/null 2>&1 || tsi_jira_die "jq not found on PATH"
}

_jira_auth_header() {
  [[ -n "${JIRA_EMAIL:-}" && -n "${JIRA_API_TOKEN:-}" ]] \
    || tsi_jira_die "JIRA_EMAIL / JIRA_API_TOKEN unset"
  printf 'Authorization: Basic %s' \
    "$(printf '%s:%s' "$JIRA_EMAIL" "$JIRA_API_TOKEN" | base64 | tr -d '\n')"
}

# Guard: refuse any WRITE verb unless the maintainer has explicitly promoted the
# adapter. Keeps "partial" honest — the shapes are here to read, not to fire.
_jira_require_enabled() {
  if [[ "${TSI_JIRA_ENABLE:-0}" != "1" ]]; then
    echo "jira adapter is GATED (code-complete, unvalidated): set TSI_JIRA_ENABLE=1 to run write verbs" >&2
    echo "validate the REST create/transition payloads against a live project, then enable" >&2
    exit 2
  fi
}

# ---------------------------------------------------------------------------
# VERB: preflight — LIVE. Confirm creds resolve against /myself.
# ---------------------------------------------------------------------------
jira_preflight() {
  _jira_require_tools
  for v in JIRA_BASE_URL JIRA_EMAIL JIRA_API_TOKEN JIRA_PROJECT_KEY; do
    if [[ -z "${!v:-}" ]]; then
      echo "preflight failed: $v unset" >&2
      echo "remediation: export JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN / JIRA_PROJECT_KEY, then re-run" >&2
      return 1
    fi
  done
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' \
    -H "$(_jira_auth_header)" -H "Accept: application/json" \
    "${JIRA_BASE_URL%/}/rest/api/3/myself")" || { echo "preflight failed: transport error" >&2; return 1; }
  if [[ "$code" != "200" ]]; then
    echo "preflight failed: /myself -> HTTP $code (check email/token)" >&2
    return 1
  fi
  echo "preflight ok: jira ${JIRA_BASE_URL} project ${JIRA_PROJECT_KEY}"
  return 0
}

# ---------------------------------------------------------------------------
# VERB: upsert --id ID --title T --body-file F [--label L ...]   (GATED)
# ---------------------------------------------------------------------------
# Find-by-JQL on the task-spec label, then update, else create. Echoes the Jira
# issue key (e.g. ENG-42).
jira_upsert() {
  _jira_require_tools; _jira_require_enabled
  local id="" title="" body_file=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) id="$2"; shift 2 ;;
      --title) title="$2"; shift 2 ;;
      --body-file) body_file="$2"; shift 2 ;;
      --label) shift 2 ;;
      --priority) shift 2 ;;  # Jira priority ids are project-specific; not seeded here
      --effort)   shift 2 ;;  # story points live on a project-specific custom field
      --due)      shift 2 ;;  # duedate is settable; not seeded until validated live
      --attr)     shift 2 ;;  # no rich attachment panel
      --spec-url) shift 2 ;;
      # --- Linear projection args (T1/T2): accepted-and-discarded on Jira.
      #     Portability guarantee — the enrichment degrades to nothing. Shift
      #     widths MUST match linear.sh (every arg takes a value except the
      #     bare --use-default-template flag), or the arg parse desyncs.
      --assignee)             shift 2 ;;  # identity -> Linear assignee; not seeded on Jira
      --state)                shift 2 ;;  # register uses the runtime transition path instead
      --subscriber)           shift 2 ;;  # repeatable; Jira watchers not seeded here
      --project)              shift 2 ;;  # Linear project; distinct from JIRA_PROJECT_KEY
      --milestone)            shift 2 ;;  # Linear project-milestone; no seeded equivalent
      --cycle)                shift 2 ;;  # Linear cycle; no equivalent
      --parent)               shift 2 ;;  # Linear sub-issue; Jira sub-tasks not seeded here
      --sub-sort)             shift 2 ;;  # Linear subIssueSortOrder; no equivalent
      --template)             shift 2 ;;  # Linear issue template; no equivalent
      --use-default-template) shift   ;;  # bare flag (no value) — shift ONE
      --sla)                  shift 2 ;;  # Linear SLA; no equivalent
      *) tsi_jira_die "upsert: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$id" && -n "$title" && -f "$body_file" ]] || tsi_jira_die "upsert: --id --title --body-file required"

  local label="${JIRA_LABEL_PREFIX}:${id}" body existing
  body="$(cat "$body_file")"

  # 1) FIND: JQL search on the idempotency label.
  #    GET /rest/api/3/search?jql=project=KEY AND labels="task-spec:<id>"
  existing="$(curl -sS -G "${JIRA_BASE_URL%/}/rest/api/3/search" \
    -H "$(_jira_auth_header)" -H "Accept: application/json" \
    --data-urlencode "jql=project=${JIRA_PROJECT_KEY} AND labels=\"${label}\"" \
    --data-urlencode "fields=key" \
    | jq -r '.issues[0].key // empty')"

  if [[ -n "$existing" ]]; then
    # 2a) UPDATE: PUT /rest/api/3/issue/<key>
    curl -sS -X PUT "${JIRA_BASE_URL%/}/rest/api/3/issue/${existing}" \
      -H "$(_jira_auth_header)" -H "Content-Type: application/json" \
      --data "$(jq -n --arg title "$title" --arg body "$body" '
        { fields: {
            summary: $title,
            description: { type:"doc", version:1,
              content:[ { type:"paragraph", content:[ { type:"text", text:$body } ] } ] }
        } }')" >/dev/null
    echo "updated $existing ($id)" >&2
    echo "$existing"
  else
    # 2b) CREATE: POST /rest/api/3/issue
    local key
    key="$(curl -sS -X POST "${JIRA_BASE_URL%/}/rest/api/3/issue" \
      -H "$(_jira_auth_header)" -H "Content-Type: application/json" \
      --data "$(jq -n --arg proj "$JIRA_PROJECT_KEY" --arg title "[task-spec:${id}] ${title}" \
                     --arg body "$body" --arg label "$label" '
        { fields: {
            project: { key: $proj },
            issuetype: { name: "Task" },
            summary: $title,
            labels: [ $label ],
            description: { type:"doc", version:1,
              content:[ { type:"paragraph", content:[ { type:"text", text:$body } ] } ] }
        } }')" \
      | jq -r '.key')"
    echo "created $key ($id)" >&2
    echo "$key"
  fi
}

# ---------------------------------------------------------------------------
# VERB: link --from ID --to ID   (GATED)
# ---------------------------------------------------------------------------
# depends_on(FROM -> TO) becomes a "Blocks" link: TO blocks FROM (Jira shows
# FROM "is blocked by" TO).  POST /rest/api/3/issueLink
jira_link() {
  _jira_require_tools; _jira_require_enabled
  local from_id="" to_id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from) from_id="$2"; shift 2 ;;
      --to) to_id="$2"; shift 2 ;;
      *) tsi_jira_die "link: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$from_id" && -n "$to_id" ]] || tsi_jira_die "link: --from and --to required"

  local from_key to_key
  from_key="$(_jira_find_key "$from_id")"; [[ -n "$from_key" ]] || tsi_jira_die "link: from-issue not found for $from_id"
  to_key="$(_jira_find_key "$to_id")";     [[ -n "$to_key" ]]   || tsi_jira_die "blocked-by target not found for $to_id"

  curl -sS -X POST "${JIRA_BASE_URL%/}/rest/api/3/issueLink" \
    -H "$(_jira_auth_header)" -H "Content-Type: application/json" \
    --data "$(jq -n --arg out "$to_key" --arg in "$from_key" '
      { type: { name: "Blocks" },
        outwardIssue: { key: $out },
        inwardIssue:  { key: $in } }')" >/dev/null
  echo "linked: $from_id blocked-by $to_id" >&2
}

# Helper: resolve a spec id -> Jira key via the idempotency label.
_jira_find_key() {
  local id="$1" label="${JIRA_LABEL_PREFIX}:$1"
  curl -sS -G "${JIRA_BASE_URL%/}/rest/api/3/search" \
    -H "$(_jira_auth_header)" -H "Accept: application/json" \
    --data-urlencode "jql=project=${JIRA_PROJECT_KEY} AND labels=\"${label}\"" \
    --data-urlencode "fields=key" \
    | jq -r '.issues[0].key // empty'
}

# ---------------------------------------------------------------------------
# VERB: list-ready   (GATED)
# ---------------------------------------------------------------------------
# Ready = registered, not Done, and no unresolved "is blocked by" link. JQL can
# express most of this; the blocker-resolution check is done client-side over the
# `issuelinks` field. Echoes issue keys, one per line.
jira_list_ready() {
  _jira_require_tools; _jira_require_enabled
  curl -sS -G "${JIRA_BASE_URL%/}/rest/api/3/search" \
    -H "$(_jira_auth_header)" -H "Accept: application/json" \
    --data-urlencode "jql=project=${JIRA_PROJECT_KEY} AND labels IN (${JIRA_LABEL_PREFIX}) AND statusCategory != Done" \
    --data-urlencode "fields=key,issuelinks" \
    | jq -r '
      .issues[]
      | select(
          [ .fields.issuelinks[]?
            | select(.type.inward == "is blocked by")
            | .inwardIssue.fields.status.statusCategory.key
            | select(. != "done")
          ] | length == 0
        )
      | .key'
}

# ---------------------------------------------------------------------------
# VERB: write-result --issue KEY --status pass|fail [--pr URL] [--reason TEXT]  (PARTIAL)
# ---------------------------------------------------------------------------
# The LOOP's write side. Adds a comment; on pass, transitions to Done. The
# transition id is project-specific — resolve via GET /issue/<key>/transitions.
jira_write_result() {
  _jira_require_tools; _jira_require_enabled
  local issue="" status="" pr="" reason=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --issue) issue="$2"; shift 2 ;;
      --status) status="$2"; shift 2 ;;
      --pr) pr="$2"; shift 2 ;;
      --reason) reason="$2"; shift 2 ;;
      *) tsi_jira_die "write-result: unknown arg '$1'" ;;
    esac
  done
  [[ -n "$issue" ]] || tsi_jira_die "write-result: --issue required"
  case "$status" in pass|fail) ;; *) tsi_jira_die "write-result: --status must be pass|fail" ;; esac

  local comment
  if [[ "$status" == "pass" ]]; then comment="eval GREEN — done.${pr:+ PR: $pr}"; else comment="eval RED — parked.${reason:+ reason: $reason}"; fi
  # POST /rest/api/3/issue/<key>/comment
  curl -sS -X POST "${JIRA_BASE_URL%/}/rest/api/3/issue/${issue}/comment" \
    -H "$(_jira_auth_header)" -H "Content-Type: application/json" \
    --data "$(jq -n --arg body "$comment" '
      { body: { type:"doc", version:1,
        content:[ { type:"paragraph", content:[ { type:"text", text:$body } ] } ] } }')" >/dev/null

  if [[ "$status" == "pass" ]]; then
    # Resolve the Done transition at RUNTIME. Transition ids are workflow/project
    # specific and MUST NOT be hard-coded: GET the transitions available from the
    # issue's current status, then pick the one whose TARGET status category is
    # "done" (`.to.statusCategory.key == "done"`). This is the standard Jira Cloud
    # v3 pattern and is portable across differently-named Done columns.
    local tid
    tid="$(curl -sS -G "${JIRA_BASE_URL%/}/rest/api/3/issue/${issue}/transitions" \
      -H "$(_jira_auth_header)" -H "Accept: application/json" \
      | jq -r '.transitions[]? | select(.to.statusCategory.key=="done") | .id' | head -1)"
    if [[ -z "$tid" ]]; then
      # No done-category transition from here (already done, or a workflow gap).
      echo "write-result: no 'done'-category transition available from ${issue}'s current status — commented only" >&2
      echo "commented $issue (pass; transition skipped)"
      return 0
    fi
    curl -sS -X POST "${JIRA_BASE_URL%/}/rest/api/3/issue/${issue}/transitions" \
      -H "$(_jira_auth_header)" -H "Content-Type: application/json" \
      --data "$(jq -n --arg id "$tid" '{ transition: { id: $id } }')" >/dev/null
    echo "done $issue (pass, transition $tid)"
  else
    echo "commented $issue (fail)"
  fi
}

# ---------------------------------------------------------------------------
# PROJECTION verbs (T2/T3) — PORTABILITY NO-OPS
# ---------------------------------------------------------------------------
# The Linear adapter grows a projection surface (projects, milestones,
# initiatives, documents, an append-only project-update health timeline, and a
# people directory). None of it maps onto a Jira board, so here every verb
# DEGRADES SILENTLY — accepts (and ignores) its args, echoes a clearly-fake id
# when a caller captures one, and exits 0. Unlike the write verbs, these need
# NO creds and are NOT behind TSI_JIRA_ENABLE: a no-op cannot half-register a
# board, and the degrade must hold even when Jira is unconfigured.

# Echo an obviously-fake id so a caller capturing stdout keeps working.
_jira_noop_id() { printf 'jira-noop-%s\n' "$1"; }

# project-ensure NAME | milestone-ensure PROJECT NAME | initiative-ensure NAME
jira_ensure_noop() {
  local kind="${1:-structure}"
  echo "note: '${kind}-ensure' is a no-op on the jira backend (Linear structure projection degrades)" >&2
  _jira_noop_id "$kind"
}

# document --title T --content-file F --project P
jira_document_noop() {
  echo "note: 'document' is a no-op on the jira backend (Linear document projection degrades)" >&2
  _jira_noop_id document
}

# project-update --project P --pass-rate N --total T
jira_project_update_noop() {
  echo "note: 'project-update' is a no-op on the jira backend (Linear health projection degrades)" >&2
  return 0
}

# users  (identity directory for `cvg setup identity`) — no Linear directory here.
jira_users_noop() {
  echo "note: 'users' is a no-op on the jira backend (no Linear directory to enumerate)" >&2
  return 0
}

# ---------------------------------------------------------------------------
# VERB: list-issues — EVERY registered issue as  extid<TAB>key  (parity gate).
# ---------------------------------------------------------------------------
# The full registered set (all statuses), keyed on the spec id recovered from the
# per-id `task-spec:<id>` label. Backs verify-registration's 1:1 gate. Read-only;
# same JQL label filter as list-ready.
jira_list_issues() {
  _jira_require_tools; _jira_require_enabled
  curl -sS -G "${JIRA_BASE_URL%/}/rest/api/3/search" \
    -H "$(_jira_auth_header)" -H "Accept: application/json" \
    --data-urlencode "jql=project=${JIRA_PROJECT_KEY} AND labels IN (${JIRA_LABEL_PREFIX})" \
    --data-urlencode "fields=key,labels" \
    | jq -r --arg pfx "${JIRA_LABEL_PREFIX}:" '
      .issues[]?
      | . as $i
      | ( [ $i.fields.labels[]? | select(startswith($pfx)) | ltrimstr($pfx) ][0] // "" ) as $ext
      | select($ext != "")
      | "\($ext)\t\($i.key)"'
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
_jira_main() {
  local verb="${1:-}"
  [[ $# -gt 0 ]] && shift || true
  case "$verb" in
    preflight)    jira_preflight "$@" ;;
    upsert)       jira_upsert "$@" ;;
    link)         jira_link "$@" ;;
    list-ready)   jira_list_ready "$@" ;;
    list-issues)  jira_list_issues "$@" ;;
    write-result) jira_write_result "$@" ;;
    project-ensure)    jira_ensure_noop project "$@" ;;
    milestone-ensure)  jira_ensure_noop milestone "$@" ;;
    initiative-ensure) jira_ensure_noop initiative "$@" ;;
    project-update)    jira_project_update_noop "$@" ;;
    document)          jira_document_noop "$@" ;;
    users)             jira_users_noop "$@" ;;
    ""|-h|--help)
      grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
      ;;
    *) tsi_jira_die "unknown verb '$verb' (want: preflight|upsert|link|list-ready|list-issues|write-result|project-ensure|milestone-ensure|initiative-ensure|project-update|document|users)" ;;
  esac
}

_jira_main "$@"
