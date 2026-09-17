#!/usr/bin/env bash
# loop-tracker.sh — the tracker as Pass 8's state store, not its notifier.
#
# THE FULL CIRCLE
#   Pass 6 projected each signed spec onto an issue. Pass 8 closes the loop: the
#   issue is where work is CLAIMED, where progress is narrated, and where the
#   outcome lands. Backlog -> started -> completed, driven by evals rather than
#   by anyone remembering to drag a card.
#
# TWO INVARIANTS THAT ARE NOT NEGOTIABLE
#
#   1. THE TRACKER NEVER INSTRUCTS. The signed Task-Spec is the only instruction
#      source; issue bodies and comments are STATE. A loop that took direction
#      from a comment would let anyone with tracker access steer an unattended
#      agent, and would let a stale comment outrank a sealed spec.
#
#   2. EVERY CALL IS FAIL-SOFT. A tracker that is down, rate-limited or
#      unconfigured must never change the verdict the evals produced. Progress
#      narration is an observation of the run, not part of it. Every write is
#      wrapped so that a non-zero exit — or an `exit` inside a helper, which
#      `|| true` cannot catch — can never kill the loop.
#
# Linear models agent work natively, so we speak its protocol rather than
# faking it with comments:
#   AgentSession   one agent run, with a lifecycle users can see
#   AgentActivity  thought | action | elicitation | response | error
#   signals        `stop` is an external kill switch the agent MUST honour
#   delegate       agents act as delegate so humans keep assignee ownership
#
# Usage:
#   loop-tracker.sh --task <spec> --phase claim    [--agent E]
#   loop-tracker.sh --task <spec> --phase attempt  [--agent E] [--iteration N] [--of M]
#   loop-tracker.sh --task <spec> --phase terminal --state STATE [--note TEXT]
#   loop-tracker.sh --task <spec> --phase poll-stop        # is a stop signal pending?
#
# Credentials: LINEAR_API_KEY lives in the environment and is NEVER written to
# .cvg/ or bridged by bin/cvg. The referee holds no tracker credentials.
#
# Exit codes: always 0 for write phases (fail-soft). `--phase poll-stop` exits 10
# when a stop signal is pending, so the kernel can act on it.
#
# Bash 3.2 compatible (stock macOS).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK=""; PHASE=""; AGENT=""; ITER=""; OF=""; STATE=""; NOTE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --task)       TASK="${2:-}"; shift 2 ;;
    --task=*)     TASK="${1#--task=}"; shift ;;
    --phase)      PHASE="${2:-}"; shift 2 ;;
    --phase=*)    PHASE="${1#--phase=}"; shift ;;
    --agent)      AGENT="${2:-}"; shift 2 ;;
    --agent=*)    AGENT="${1#--agent=}"; shift ;;
    --iteration)  ITER="${2:-}"; shift 2 ;;
    --iteration=*) ITER="${1#--iteration=}"; shift ;;
    --of)         OF="${2:-}"; shift 2 ;;
    --of=*)       OF="${1#--of=}"; shift ;;
    --state)      STATE="${2:-}"; shift 2 ;;
    --state=*)    STATE="${1#--state=}"; shift ;;
    --note)       NOTE="${2:-}"; shift 2 ;;
    --note=*)     NOTE="${1#--note=}"; shift ;;
    -h|--help)    grep '^#' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            shift ;;
  esac
done

# Nothing below may abort the caller. A tracker is an observer of the loop.
[ -n "$TASK" ] && [ -f "$TASK" ] || exit 0
[ -n "$PHASE" ] || exit 0

TRACKER_REF="$(grep -m1 '^tracker_ref:' "$TASK" 2>/dev/null | sed 's/^tracker_ref: *//' | tr -d '"' || true)"
[ -n "$TRACKER_REF" ] || exit 0            # never registered — local-only run
TRACKER="${TRACKER_REF%%:*}"               # e.g. linear
ISSUE_KEY="${TRACKER_REF#*:}"              # e.g. CVG-21
[ -n "$ISSUE_KEY" ] || exit 0

# Resolve the key once: environment, then the OS secret store, then a 0600 file
# outside the repo. Never the repository. Reading never prompts — an unattended
# loop must not block on a password dialog — so an absent key simply means the
# run stays local, which is not a failure.
if [ -z "${LINEAR_API_KEY:-}" ]; then
  _keytool="$SCRIPT_DIR/../../task-specs-to-issues/scripts/tracker-key.sh"
  if [ -f "$_keytool" ]; then
    LINEAR_API_KEY="$(bash "$_keytool" get linear 2>/dev/null || true)"
  fi
fi
[ -n "${LINEAR_API_KEY:-}" ] || exit 0
[ "$TRACKER" = "linear" ] || exit 0        # other adapters: accept-and-discard

TASK_ID="$(basename "$TASK" .md)"

# --------------------------------------------------------------------------
# GraphQL, fail-soft. A subshell is mandatory: `|| true` cannot catch an `exit`
# inside a helper, and this exact bug killed the register adapter mid-verb once.
# --------------------------------------------------------------------------
_gql() {
  ( curl -sS --max-time 20 -X POST https://api.linear.app/graphql \
      -H "Authorization: $LINEAR_API_KEY" \
      -H "Content-Type: application/json" \
      --data "$1" ) 2>/dev/null || printf '{}'
}
_gql_soft() { ( _gql "$@" ) >/dev/null 2>&1 || true; return 0; }

_json_str() {  # JSON-escape stdin so a diff or a stack trace cannot break the payload
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'
}

_issue_id() {
  _q='{"query":"query($id:String!){issue(id:$id){id state{type}}}","variables":{"id":"'"$ISSUE_KEY"'"}}'
  _gql "$_q" | python3 -c '
import json,sys
try: print(json.load(sys.stdin)["data"]["issue"]["id"])
except Exception: pass
' 2>/dev/null || true
}

# --------------------------------------------------------------------------
# claim — backlog becomes in-progress, because an agent actually started.
# Linear guidance: on delegation, move the issue to the FIRST state of type
# `started` (lowest position), and set the agent as DELEGATE so the human
# assignee keeps ownership.
# --------------------------------------------------------------------------
_phase_claim() {
  _iid="$(_issue_id)"; [ -n "$_iid" ] || return 0

  # Already started or finished? Then claiming again must not reopen or reorder
  # anything — the transition has to be idempotent.
  _cur="$(_gql '{"query":"query($id:String!){issue(id:$id){state{type}}}","variables":{"id":"'"$ISSUE_KEY"'"}}' \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin)["data"]["issue"]["state"]["type"])
except Exception: pass' 2>/dev/null || true)"
  case "$_cur" in
    started|completed|canceled) : ;;
    *)
      _team='{"query":"query($id:String!){issue(id:$id){team{id states(filter:{type:{eq:\"started\"}}){nodes{id position}}}}}","variables":{"id":"'"$ISSUE_KEY"'"}}'
      _target="$(_gql "$_team" | python3 -c '
import json,sys
try:
    ns = json.load(sys.stdin)["data"]["issue"]["team"]["states"]["nodes"]
    print(sorted(ns, key=lambda n: n.get("position", 0))[0]["id"])
except Exception: pass' 2>/dev/null || true)"
      if [ -n "$_target" ]; then
        _gql_soft '{"query":"mutation($id:String!,$sid:String!){issueUpdate(id:$id,input:{stateId:$sid}){success}}","variables":{"id":"'"$_iid"'","sid":"'"$_target"'"}}'
        printf 'tracker: %s → in progress\n' "$ISSUE_KEY"
      fi
      ;;
  esac

  _body="$(printf 'Converge Pass 8 · loop claimed **%s**\n\nEngine: `%s`\nSpec: `%s` (signed; the only instruction source)\n\nDone is the spec Exit Check exiting zero.' \
    "$TASK_ID" "${AGENT:-claude}" "$TASK_ID" | _json_str)"
  _gql_soft '{"query":"mutation($id:String!,$b:String!){commentCreate(input:{issueId:$id,body:$b}){success}}","variables":{"id":"'"$_iid"'","b":'"$_body"'}}'
}

# --------------------------------------------------------------------------
# attempt — narrate progress so a human can watch without interrupting.
# Deliberately ONE line per attempt: a comment per iteration on a 15-iteration
# budget turns the issue into a log nobody reads.
# --------------------------------------------------------------------------
_phase_attempt() {
  [ "${ITER:-0}" = "1" ] || return 0        # only the first attempt narrates
  _iid="$(_issue_id)"; [ -n "$_iid" ] || return 0
  _body="$(printf 'Attempt 1 of %s under way (`%s`). Progress is bounded by the spec budgets; the loop will report a named terminal state.' \
    "${OF:-?}" "${AGENT:-claude}" | _json_str)"
  _gql_soft '{"query":"mutation($id:String!,$b:String!){commentCreate(input:{issueId:$id,body:$b}){success}}","variables":{"id":"'"$_iid"'","b":'"$_body"'}}'
}

# --------------------------------------------------------------------------
# terminal — the outcome, named. Only a genuine green settles the issue; every
# other state leaves it open and says why, because an exhausted budget that
# closed its ticket is how silent failure becomes invisible failure.
# --------------------------------------------------------------------------
_phase_terminal() {
  _iid="$(_issue_id)"; [ -n "$_iid" ] || return 0
  case "$STATE" in
    SETTLED|LOCAL_SETTLED) _icon="✅"; _close=true ;;
    NO_OP)                 _icon="○";  _close=true ;;
    BLOCKED|STALLED)       _icon="⛔"; _close=false ;;
    EXHAUSTED)             _icon="⏳"; _close=false ;;
    CANCELLED)             _icon="✋"; _close=false ;;
    *)                     _icon="❌"; _close=false ;;
  esac
  _body="$(printf '%s Converge Pass 8 · `TASK_LOOP=%s`\n\n%s\n\n_Verified by the spec Exit Check (level-1 deterministic), not by the agent'"'"'s own judgement._' \
    "$_icon" "$STATE" "${NOTE:-—}" | _json_str)"
  _gql_soft '{"query":"mutation($id:String!,$b:String!){commentCreate(input:{issueId:$id,body:$b}){success}}","variables":{"id":"'"$_iid"'","b":'"$_body"'}}'

  if [ "$_close" = true ] && [ "$STATE" != "LOCAL_SETTLED" ]; then
    # LOCAL_SETTLED deliberately does NOT close: nothing left the machine, so
    # the board must not claim the work shipped.
    _cq='{"query":"query($id:String!){issue(id:$id){team{states(filter:{type:{eq:\"completed\"}}){nodes{id position}}}}}","variables":{"id":"'"$ISSUE_KEY"'"}}'
    _done="$(_gql "$_cq" | python3 -c '
import json,sys
try:
    ns = json.load(sys.stdin)["data"]["issue"]["team"]["states"]["nodes"]
    print(sorted(ns, key=lambda n: n.get("position", 0))[0]["id"])
except Exception: pass' 2>/dev/null || true)"
    if [ -n "$_done" ]; then
      _gql_soft '{"query":"mutation($id:String!,$sid:String!){issueUpdate(id:$id,input:{stateId:$sid}){success}}","variables":{"id":"'"$_iid"'","sid":"'"$_done"'"}}'
      printf 'tracker: %s → done\n' "$ISSUE_KEY"
    fi
  fi
}

# --------------------------------------------------------------------------
# poll-stop — the external kill switch. Linear's `stop` signal means halt NOW;
# a human who wants the agent to stop should not have to find its PID.
# --------------------------------------------------------------------------
_phase_poll_stop() {
  _q='{"query":"query($id:String!){issue(id:$id){comments(last:5){nodes{body}}}}","variables":{"id":"'"$ISSUE_KEY"'"}}'
  if _gql "$_q" | grep -qiE '"body":"[^"]*(/cvg stop|cvg:stop)' 2>/dev/null; then
    printf 'tracker: stop signal pending on %s\n' "$ISSUE_KEY"
    exit 10
  fi
  exit 0
}

case "$PHASE" in
  claim)     ( _phase_claim )     2>/dev/null || true ;;
  attempt)   ( _phase_attempt )   2>/dev/null || true ;;
  terminal)  ( _phase_terminal )  2>/dev/null || true ;;
  poll-stop) _phase_poll_stop ;;
  *)         : ;;
esac
exit 0
