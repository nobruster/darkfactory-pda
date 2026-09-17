#!/usr/bin/env bash
# next-pass.sh — the conductor's derivation engine.
#
# Derives the descent's position from workspace EVIDENCE (files in cvg/),
# never from stored state: every pass leaves its artifact in a known folder,
# so "where are we" is always readable from the floor. Three verbs:
#
#   next [--guided] [--lane FULL|NORMAL|FAST]
#                                      evidence board + NEXT_PASS=<N|DONE>
#   pre  <N> [--lane ...]            fail-closed door: PASS_PRE=OK|MISSING
#   post <N>                         artifact check:   PASS_POST=OK|INCOMPLETE
#
# THE ONE RULE: evidence presence is not a verdict. This script sequences;
# the cvg gates decide. It refuses forward motion, it never grants a PASS.
# Read-only by design — it must never mutate the workspace it reads.
#
# It also NAMES the optional teaching companion (cvg lesson) wherever a pass has
# closed — advisory, never sequenced, never blocking: a lesson is not a pass.
#
# ONE EXCEPTION to "presence is not a verdict": an unsigned THE BARRIER (pass 4 —
# an objection log with undecided objections) marks [!] and stops `next`/`pre`
# from naming anything beyond it. Still no gate is run; it is a structural read.
#
# Pass 6 (Register) is opt-in: reported, never blocking.
# Tokens: NEXT_PASS= · PASS_PRE= · PASS_POST= · NEXT_PASS=USAGE_ERROR
# bash 3.2 safe. Deps: find, grep (+ python3, when present, for the barrier's
# provenance half — see barrier_open; without it that half is left to the gate).

set -euo pipefail

usage() {
  cat <<'EOF'
usage: next-pass.sh next [--guided] [--lane FULL|NORMAL|FAST]
       next-pass.sh pre  <pass-number> [--lane FULL|NORMAL|FAST]
       next-pass.sh post <pass-number>
EOF
}

# --- workspace resolution ----------------------------------------------------
# Explicit CVG_PROJECT_ROOT wins; otherwise walk up from PWD to the nearest
# directory carrying the .cvg control plane (same rule the cvg router uses).
resolve_ws() {
  if [ -n "${CVG_PROJECT_ROOT:-}" ] && [ -d "$CVG_PROJECT_ROOT/cvg" ]; then
    printf '%s\n' "$CVG_PROJECT_ROOT"
    return 0
  fi
  local dir="$PWD"
  while [ "$dir" != "/" ]; do
    if [ -d "$dir/.cvg" ] && [ -d "$dir/cvg" ]; then
      printf '%s\n' "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  echo "no Converge workspace found walking up from '$PWD' — run cvg init first" >&2
  return 1
}

# --- the pass map ------------------------------------------------------------
pass_name() {
  case "$1" in
    0) printf 'Capture' ;;    1) printf 'Intent' ;;
    2) printf 'Structure' ;;  3) printf 'Decompose' ;;
    4) printf 'Consensus' ;;  5) printf 'Tasking' ;;
    6) printf 'Register' ;;   7) printf 'Bind' ;;
    8) printf 'Loop' ;;       *) return 1 ;;
  esac
}

# Each pass skill owns its own steering prompt. Nothing is copied into the
# consuming project: the prompt ships with the package, so it can never go
# stale against the installed version.
pass_skill() {
  case "$1" in
    0) printf 'idea-to-brd' ;;
    1) printf 'brd-docs-to-tech-req' ;;
    2) printf 'tech-req-to-adrs' ;;
    3) printf 'reqs-to-swimlane-plans' ;;
    4) printf 'sketch-plans-adversarial-review' ;;
    5) printf 'task-spec' ;;
    6) printf 'task-specs-to-issues' ;;
    7) printf 'task-to-runtime-contract' ;;
    8) printf 'task-loop' ;;
    *) return 1 ;;
  esac
}

# The installed package root. CVG_TOOL_HOME is exported by the cvg router;
# standalone runs fall back to this checkout.
tool_home() {
  printf '%s' "${CVG_TOOL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
}

# Absolute path to a pass's prompt inside the installed package.
prompt_path() {
  printf '%s/skills/%s/references/pass-prompt.md' "$(tool_home)" "$(pass_skill "$1")"
}

# The teaching companion is NOT a pass: it has no place in the descent order, no
# lane membership, and it never blocks. It is named here anyway because "a pass
# just closed" is precisely its trigger, and a companion nobody is told about is
# a companion nobody runs. Advisory only — it can never change a verdict.
companion_line() {
  printf '  teach it   : cvg lesson  (pass-to-lesson · %s/skills/pass-to-lesson/references/pass-prompt.md)\n' \
    "$(tool_home)"
}

# Guided mode is a CHAT boundary, not another workflow. It translates the
# conductor's derived position into stable user choices and stops. The skill
# owns how the agent responds; this script owns the evidence-derived position
# and shared vocabulary. No guided-session state is persisted.
guided_choices() {
  local next_pass="$1"
  echo
  if [ "$next_pass" = "DONE" ]; then
    echo 'guided chat — this lane has reached its evidence boundary'
    echo '  [REVIEW]  inspect the outcome and proof; read-only'
    echo '  [TEACH]   explain one closed pass with cvg lesson; optional'
    echo '  [PAUSE]   stop here; change nothing'
    echo '  agent contract: present these choices and wait; do not invent another pass'
    printf 'GUIDED_CHAT=DONE\n'
    return 0
  fi

  echo "guided chat — pass $next_pass · $(pass_name "$next_pass") is the safe boundary"
  echo '  [CONTINUE] run the pre-hook, load the printed pass prompt, and do this pass only (recommended)'
  echo '  [EXPLAIN]  explain purpose, inputs, output, and closing gate; read-only'
  echo '  [INSPECT]  show the evidence and blockers behind this position; read-only'
  echo '  [PAUSE]    stop here; change nothing'
  echo '  agent contract: present these choices and wait; never infer CONTINUE'
  printf 'GUIDED_CHAT=AWAITING_CHOICE\n'
}

gate_cmd() {
  case "$1" in
    0) printf 'cvg capture' ;;
    1) printf 'cvg intent' ;;
    2) printf 'cvg structure' ;;
    3) printf 'cvg decompose' ;;
    4) printf 'cvg review --check' ;;
    5) printf 'cvg tasks gate --stamp <spec>' ;;
    6) printf 'cvg register --check' ;;
    7) printf 'cvg bind --check --task <spec>' ;;
    8) printf 'cvg tasks accept <spec>' ;;
    *) return 1 ;;
  esac
}

lane_order() {
  case "$1" in
    FULL)   printf '0 1 2 3 4 5 7 8' ;;
    NORMAL) printf '1 2 5 7 8' ;;
    FAST)   printf '5 7 8' ;;
    *) return 1 ;;
  esac
}

# --- evidence probes (presence only — instant, no gate execution) ------------
has_pass() {
  local n="$1"
  case "$n" in
    # Typed folder (canonical) OR the legacy flat prefix — a workspace created
    # before the layout change must still read as complete.
    0) [ -n "$(find "$WS/cvg/docs/brd" -maxdepth 1 -name '*.md' -print 2>/dev/null | head -1)" ] \
       || [ -n "$(find "$WS/cvg/docs" -maxdepth 1 -name 'brd-*.md' -print 2>/dev/null | head -1)" ] ;;
    1) [ -n "$(find "$WS/cvg/docs/tech-spec" -maxdepth 1 -name '*.md' -print 2>/dev/null | head -1)" ] \
       || [ -n "$(find "$WS/cvg/docs" -maxdepth 1 -name 'tech-spec-*.md' -print 2>/dev/null | head -1)" ] ;;
    2) [ -n "$(find "$WS/cvg/docs/adrs" -maxdepth 1 -name '*.md' -print 2>/dev/null | head -1)" ] ;;
    # A swimlane is recognized by holding a plan FILE, never by the folder's
    # name — a name match would lose the pass the moment the folder dropped its
    # redundant "swimlane-" prefix. Deliberately loose, like the check it
    # replaced: _lane.md, a legacy <seam>.plan.md, or even a bare leg all count
    # as "Pass 3 left something on the floor". Presence is not a verdict; the
    # cvg decompose gate is what decides. (.consensus/ holds .json, so the
    # *.md filter excludes the objection log without naming it.)
    3) [ -n "$(find "$LANES" -mindepth 2 -type f -name '*.md' -print 2>/dev/null | head -1)" ] ;;
    4) [ -f "$LANES/.consensus/objection-log.json" ] ;;
    5) find "$WS/cvg/tasks" -name 'T-*.md' -print 2>/dev/null \
         | while IFS= read -r f; do
             grep -q '^signed_off: true' "$f" && echo hit && break
           done | grep -q hit ;;
    # A tracker_ref that says "(none)" is the TEMPLATE's placeholder, and every
    # scaffolded spec carries one. Matching the field's PRESENCE therefore reported
    # Register as done for a workspace with zero issues on any board — uc-01 showed
    # [+] pass 6 with all four specs at `tracker_ref: (none)`. The probe has to look
    # at the value, not the key: same vacuous-pass shape as an eval that goes green
    # because its subject is absent.
    6) find "$WS/cvg/tasks" -name 'T-*.md' -print 2>/dev/null \
         | while IFS= read -r f; do
             grep -qE '^tracker_ref:[[:space:]]*[^[:space:]]' "$f" \
               && ! grep -qE '^tracker_ref:[[:space:]]*\(none\)[[:space:]]*$' "$f" \
               && echo hit && break
           done | grep -q hit ;;
    7) [ -n "$(find "$WS/cvg/execution" -type f ! -name '.gitkeep' -print 2>/dev/null | head -1)" ] ;;
    8) [ -n "$(find "$WS/cvg/receipts" -type f ! -name 'README.md' -print 2>/dev/null | head -1)" ] ;;
    *) return 1 ;;
  esac
}

# --- THE BARRIER is the one pass whose evidence can exist while CONSENT does not.
# Pass 4's artifact is an objection log, and a log full of objections nobody has
# decided is not consensus — it is the opposite. On 2026-08-03 this conductor said
# NEXT_PASS=5 while cvg review --check said CHECK_CONSENSUS=FAIL with seven
# objections open, two CRITICAL. "Presence is not a verdict" is right for passes
# 0-3, but Pass 4 is the last human sign-off before machines take over, and `next`
# is exactly the surface an autonomous loop consults to decide what to do. Pointing
# it past an unsigned barrier is the one place that rule becomes dangerous.
#
# This stays a STRUCTURAL read — no gate is executed and no verdict is invented,
# the same class of probe as "does a signed_off spec exist" for pass 5. It counts
# objections against recorded owner decisions; deliberately coarse, because
# cvg review --check remains the authority on whether consensus actually holds.
barrier_open() {
  local log="$LANES/.consensus/objection-log.json" n_obj n_dec
  [ -f "$log" ] || return 1
  n_obj="$(grep -c '"severity"' "$log" 2>/dev/null)" || n_obj=0
  n_dec="$(grep -c '"decided_by"' "$log" 2>/dev/null)" || n_dec=0
  # BARRIER_REASON tells the caller WHICH condition fired, so the remedy printed
  # matches the cause. Set on every open path; never read unless barrier_open said 0.
  BARRIER_REASON="undecided"
  [ "${n_obj:-0}" -gt "${n_dec:-0}" ] && return 0

  # THE SAME SURFACE LEAKED TWICE. The count above closed the first hole (objections
  # nobody decided). Later the same day it read GREEN again — every objection decided,
  # so `next` printed [+] for pass 4 and NEXT_PASS=7 — while `cvg review --check` said
  # RED: three plans had been SHARPENED AFTER the adversary read them
  # (foundation/leg-01-project.md and two models legs). Consent given to one text is
  # not consent to another, and Pass 5 had already decomposed the unreviewed version.
  #
  # So provenance is part of "is the barrier closed", not a detail only the gate owns.
  # This stays STRUCTURAL — it compares the sha256 the log ITSELF recorded for each
  # reviewed input against the file on disk. No gate runs and no verdict is invented.
  #
  # Deliberately asymmetric, to stay coarse in the direction that cannot cause a false
  # alarm: a MISSING inputs[] means "cannot verify here", and we leave that to the
  # gate, which fails on it explicitly. Only a RECORDED hash that no longer matches —
  # positive evidence of a post-review edit — reopens the barrier.
  command -v python3 >/dev/null 2>&1 || return 1
  BARRIER_REASON="stale"
  python3 - "$log" "$LANES" >/dev/null 2>&1 <<'PY' || return 0
import glob, hashlib, json, os, sys
log, lanes = sys.argv[1], sys.argv[2]
try:
    art = json.load(open(log, encoding="utf-8"))
except Exception:
    sys.exit(0)                      # an unreadable log is the gate's finding, not ours
inputs = {i["path"]: i.get("sha256")
          for i in (art.get("inputs") or []) if i.get("path")}
if not inputs:
    sys.exit(0)                      # no provenance recorded — the gate reports that
for f in sorted(glob.glob(os.path.join(lanes, "*", "*.md"))):
    rel = os.path.relpath(f, lanes)
    want = inputs.get(rel) or inputs.get(f)
    if not want:
        continue                     # unseen by the review — again, the gate's call
    try:
        got = hashlib.sha256(open(f, "rb").read()).hexdigest()
    except OSError:
        continue
    if got != want:
        sys.exit(1)                  # a reviewed plan changed → BARRIER OPEN
sys.exit(0)
PY
  return 1
}

# '!' marks a pass whose artifact is on the floor but whose consent is not.
mark() {
  if [ "$1" = "4" ] && barrier_open; then printf '!'; return 0; fi
  if has_pass "$1"; then printf '+'; else printf '.'; fi
}

# --- argument parsing --------------------------------------------------------
CMD="${1:-}"
[ $# -gt 0 ] && shift
LANE="FULL"
TARGET=""
GUIDED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --guided) GUIDED=1; shift ;;
    --lane)   [ $# -ge 2 ] || { usage >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }
              LANE="$2"; shift 2 ;;
    --lane=*) LANE="${1#--lane=}"; shift ;;
    [0-8])    TARGET="$1"; shift ;;
    *) usage >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2 ;;
  esac
done
[ "$GUIDED" -eq 0 ] || [ "$CMD" = "next" ] \
  || { usage >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }
ORDER="$(lane_order "$LANE" 2>/dev/null)" \
  || { echo "unknown lane '$LANE' — FULL, NORMAL, or FAST" >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }

WS="$(resolve_ws)" || { printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }

# Pass 3 and Pass 4 both read the swimlane tree: canonical cvg/swimlanes/, with
# the legacy cvg/sketch/ still honored. Preferred by CONTENT, not existence — an
# empty canonical folder (created by a later `cvg init`) must never mask a
# populated legacy one, which would drop this workspace's Pass 3 evidence.
# NOTE: the literal "cvg/sketch" below is deliberate back-compat. Do not let a
# bulk rename rewrite it to the canonical name — that silently makes the
# fallback a no-op, which is exactly how this line broke once already.
LANES="$WS/cvg/swimlanes"
if [ -z "$(find "$LANES" -mindepth 2 -type f -name '*.md' -print 2>/dev/null | head -1)" ] \
   && [ -d "$WS/cvg/sketch" ]; then
  LANES="$WS/cvg/sketch"
fi

case "$CMD" in
  next)
    echo "conductor — descent position (lane $LANE) at $WS"
    NEXT=""
    for p in $ORDER; do
      printf '  [%s] pass %s · %s\n' "$(mark "$p")" "$p" "$(pass_name "$p")"
      if [ -z "$NEXT" ] && ! has_pass "$p"; then NEXT="$p"; fi
    done
    if has_pass 6; then echo '  [+] pass 6 · Register (opt-in, never blocks)'; fi
    # Refuse to look past an unsigned barrier, even when later passes have
    # evidence: whatever is downstream was built on a plan nobody signed.
    case " $ORDER " in
      *" 4 "*)
        if barrier_open; then
          NEXT=4
          # Two different things reopen the barrier and they need two different
          # remedies. Printing the undecided-objections advice over a hash mismatch
          # sends the owner to `--resolve`, which has nothing left to resolve — a
          # correct RED with the wrong instruction still wastes the trip.
          if [ "${BARRIER_REASON:-undecided}" = "stale" ]; then
            echo '  ^ THE BARRIER is open: plan(s) were CHANGED after the adversary read'
            echo '    them, so the recorded consent no longer covers the current text.'
            echo '    Every objection is decided — sharpening the plans reopened it.'
            echo '    re-attack: cvg review --adversary <engine> --timeout 900'
            echo '    then     : cvg review --check'
          else
            echo '  ^ THE BARRIER is open: the objection log carries objections with no'
            echo '    owner decision. Nothing past pass 4 is dispatchable until it closes.'
            echo '    decide: cvg review --resolve <id|all> --fix   (or --accept --owner N --risk W)'
            echo '    then  : cvg review --check'
          fi
        fi ;;
    esac
    # Only offer teaching once something has actually closed — on a fresh floor
    # there is nothing to teach, and an always-on hint is noise, not guidance.
    CLOSED=""
    for p in $ORDER; do
      if has_pass "$p"; then CLOSED="$p"; fi
    done
    if [ -z "$NEXT" ]; then
      echo 'every pass in the lane has evidence on the floor'
      companion_line
      [ "$GUIDED" -eq 0 ] || guided_choices DONE
      printf 'NEXT_PASS=DONE\n'
    else
      echo "next: pass $NEXT · $(pass_name "$NEXT")"
      echo "  skill      : $(pass_skill "$NEXT")"
      echo "  steer with : $(prompt_path "$NEXT")"
      echo "  close with : $(gate_cmd "$NEXT")"
      if [ -n "$CLOSED" ]; then companion_line; fi
      [ "$GUIDED" -eq 0 ] || guided_choices "$NEXT"
      printf 'NEXT_PASS=%s\n' "$NEXT"
    fi
    ;;
  pre)
    [ -n "$TARGET" ] || { usage >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }
    # An unsigned barrier closes every door behind it. This is the hook an
    # autonomous runner calls before starting work, so it is the last chance to
    # stop a machine building on plans no human accepted.
    case " $ORDER " in
      *" 4 "*)
        if [ "$TARGET" -gt 4 ] 2>/dev/null && barrier_open; then
          echo "pass $TARGET ($(pass_name "$TARGET")) may not start — THE BARRIER (pass 4) has objections with no owner decision."
          echo "  decide: cvg review --resolve <id|all> --fix   (or --accept --owner N --risk W)"
          echo "  then  : cvg review --check   (it, not this hook, is the authority)"
          printf 'PASS_PRE=MISSING\n'
          exit 1
        fi ;;
    esac
    MISSING=""
    for p in $ORDER; do
      [ "$p" = "$TARGET" ] && break
      has_pass "$p" || MISSING="${MISSING}${MISSING:+ }$p"
    done
    if [ -n "$MISSING" ]; then
      echo "pass $TARGET ($(pass_name "$TARGET")) may not start — missing evidence from:"
      for p in $MISSING; do
        echo "  pass $p · $(pass_name "$p") — steer with $(pass_skill "$p") ($(prompt_path "$p"))"
      done
      printf 'PASS_PRE=MISSING\n'
      exit 1
    fi
    echo "pass $TARGET ($(pass_name "$TARGET")) may start — every prior lane pass left its evidence"
    printf 'PASS_PRE=OK\n'
    ;;
  post)
    [ -n "$TARGET" ] || { usage >&2; printf 'NEXT_PASS=USAGE_ERROR\n'; exit 2; }
    if has_pass "$TARGET"; then
      echo "pass $TARGET ($(pass_name "$TARGET")) left its artifact on the floor"
      echo "  authoritative verdict: $(gate_cmd "$TARGET")"
      companion_line
      printf 'PASS_POST=OK\n'
    else
      echo "pass $TARGET ($(pass_name "$TARGET")) left NO artifact in its folder"
      echo "  steer with: $(pass_skill "$TARGET") ($(prompt_path "$TARGET"))"
      printf 'PASS_POST=INCOMPLETE\n'
      exit 1
    fi
    ;;
  *)
    usage >&2
    printf 'NEXT_PASS=USAGE_ERROR\n'
    exit 2
    ;;
esac
