#!/usr/bin/env bash
# test-cvg-doctor-evidence.sh — a gate's verdict is only as durable as its artifact.
#
# WHY THIS EXISTS
# On 2026-08-03 a live use case ran FOUR GREEN GATES over a workspace whose entire
# descent was untracked — BRD, tech-spec, six ADRs, eleven legs, the objection log.
# One `git clean -fd` from gone, and three parts of the method silently resting on
# nothing: Pass 4's sha256 provenance over the plan files, Pass 8's settlement (it
# commits), and `cvg lesson --immutable` (it reads `git status`). Nothing reported
# it, because no gate's job was to look.
#
# The row that matters most is [1]: the exact shape of that day — a fully populated
# workspace, zero of it tracked, and the check must fail closed and NAME which
# pass's evidence is at risk. "3 untracked files" is not the finding; "Pass 4 cannot
# prove provenance" is.
#
# Hermetic: throwaway git repos. No network, no engine.
# Token: DOCTOR_EVIDENCE_TESTS=PASS | DOCTOR_EVIDENCE_TESTS=FAIL
# bash 3.2 safe. Deps: git, python3.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
CVG="$REPO/bin/cvg"

rows=0; failed=0
ok()  { printf '  ok   — %s\n' "$1"; rows=$((rows+1)); }
bad() { printf '  FAIL — %s\n' "$1"; rows=$((rows+1)); failed=$((failed+1)); }

echo "=================================================================="
echo "test-cvg-doctor-evidence.sh — can git show the floor?"
echo "=================================================================="

TMP="$(mktemp -d -t cvg-doctor-evidence.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

mk_ws() { # mk_ws <dir> — a git repo with an initialized, populated workspace
  local d="$1"
  mkdir -p "$d"
  git -C "$d" init --quiet
  git -C "$d" config user.email t@t.t
  git -C "$d" config user.name t
  ( cd "$d" && CVG_PROJECT_ROOT="$d" bash "$CVG" init >/dev/null 2>&1 )
  printf 'the brief\n'      > "$d/cvg/docs/brd/thing.md"
  printf 'the spec\n'       > "$d/cvg/docs/tech-spec/thing.md"
  printf 'a decision\n'     > "$d/cvg/docs/adrs/0001-thing.md"
  mkdir -p "$d/cvg/swimlanes/core"
  printf 'a lane\n'         > "$d/cvg/swimlanes/core/_lane.md"
  printf 'a leg\n'          > "$d/cvg/swimlanes/core/leg-01-thing.md"
}

run() { # run <expected-exit> <workspace>; sets OUT
  local want="$1" d="$2" rc=0
  OUT="$(cd "$d" && bash "$CVG" doctor evidence 2>&1)" || rc=$?
  RC="$rc"
  [ "$rc" = "$want" ]
}
last() { printf '%s\n' "$OUT" | tail -1; }

# ---------------------------------------------------------------------------
echo
echo "[1] THE 2026-08-03 STATE: a full descent, none of it tracked"
# ---------------------------------------------------------------------------
W="$TMP/untracked"; mk_ws "$W"
if run 1 "$W" && [ "$(last)" = "DOCTOR_EVIDENCE=UNTRACKED" ]; then
  ok "a populated but untracked workspace fails closed (exit 1 + UNTRACKED)"
else
  bad "untracked evidence must fail closed (got exit $RC / $(last))"
fi
case "$OUT" in
  *"pass 3 · Decompose / 4 · Consensus"*)
    ok "it names the PASS at risk, not just a file count" ;;
  *) bad "the report should name which pass's evidence is untracked" ;;
esac
case "$OUT" in
  *"0 · Capture"*) ok "every populated area is attributed to its pass" ;;
  *) bad "Pass 0 evidence was not attributed" ;;
esac
case "$OUT" in
  *"git clean"*) ok "it says why this matters — one clean from unprovable" ;;
  *) bad "the failure should explain the consequence" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[2] committed → OK"
# ---------------------------------------------------------------------------
git -C "$W" add -A >/dev/null 2>&1
git -C "$W" commit -qm "record the descent" >/dev/null 2>&1
if run 0 "$W" && [ "$(last)" = "DOCTOR_EVIDENCE=OK" ]; then
  ok "once committed, the same workspace passes (exit 0 + OK)"
else
  bad "a tracked workspace must pass (got exit $RC / $(last))"
fi
case "$OUT" in
  *"git can show the floor"*) ok "the OK path states the claim it verified" ;;
  *) bad "the OK path should say what it proved" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[3] ONE untracked file among many tracked is still caught"
# ---------------------------------------------------------------------------
# The dangerous version is not an empty repo — it is a mostly-committed workspace
# with the newest artifact missing, because that reads as healthy at a glance.
printf 'a second leg, forgotten\n' > "$W/cvg/swimlanes/core/leg-02-forgotten.md"
if run 1 "$W" && [ "$(last)" = "DOCTOR_EVIDENCE=UNTRACKED" ]; then
  ok "a single forgotten artifact among tracked ones still fails"
else
  bad "one untracked file must not be lost in the noise (got exit $RC)"
fi
case "$OUT" in
  *leg-02-forgotten.md*) ok "and it names the file, so the fix is obvious" ;;
  *) bad "the untracked file should be named" ;;
esac
rm -f "$W/cvg/swimlanes/core/leg-02-forgotten.md"

# ---------------------------------------------------------------------------
echo
echo "[4] .gitkeep placeholders are not evidence"
# ---------------------------------------------------------------------------
# `cvg init` seeds .gitkeep files. Counting those as untracked evidence would make
# every fresh workspace fail for a reason that has nothing to do with the descent —
# a check that cries wolf on day one is a check nobody keeps.
FRESH="$TMP/fresh"; mkdir -p "$FRESH"
git -C "$FRESH" init --quiet
git -C "$FRESH" config user.email t@t.t; git -C "$FRESH" config user.name t
( cd "$FRESH" && CVG_PROJECT_ROOT="$FRESH" bash "$CVG" init >/dev/null 2>&1 )
if run 0 "$FRESH" && [ "$(last)" = "DOCTOR_EVIDENCE=OK" ]; then
  ok "a freshly initialized workspace passes (.gitkeep is not evidence)"
else
  bad "a fresh init must not fail on its own placeholders (got exit $RC / $(last))"
fi

# ---------------------------------------------------------------------------
echo
echo "[5] no git at all → NOT_GIT, fail closed"
# ---------------------------------------------------------------------------
NOGIT="$TMP/nogit"; mkdir -p "$NOGIT"
( cd "$NOGIT" && CVG_PROJECT_ROOT="$NOGIT" bash "$CVG" init >/dev/null 2>&1 ) || true
mkdir -p "$NOGIT/cvg/docs/brd"; printf 'x\n' > "$NOGIT/cvg/docs/brd/x.md"
rc=0; OUT="$(cd "$NOGIT" && CVG_PROJECT_ROOT="$NOGIT" bash "$CVG" doctor evidence 2>&1)" || rc=$?
if [ "$rc" -eq 1 ] && [ "$(last)" = "DOCTOR_EVIDENCE=NOT_GIT" ]; then
  ok "no repository → exit 1 + NOT_GIT (exploring is fine, settling is not)"
else
  bad "a non-git workspace should be NOT_GIT at exit 1 (got exit $rc / $(last))"
fi
case "$OUT" in
  *"SETTLING is not"*|*"settling"*) ok "it distinguishes exploring from settling" ;;
  *) bad "NOT_GIT should say why it matters for Pass 8" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[6] contracts: read-only, tokens, discoverability"
# ---------------------------------------------------------------------------
B="$(git -C "$W" status --porcelain | sort)"
( cd "$W" && bash "$CVG" doctor evidence >/dev/null 2>&1 ) || true
A="$(git -C "$W" status --porcelain | sort)"
if [ "$B" = "$A" ]; then
  ok "read-only — the check changed nothing"
else
  bad "doctor evidence mutated the workspace"
fi
rc=0; OUT="$(cd "$W" && bash "$CVG" doctor evidence extra 2>&1)" || rc=$?
if [ "$rc" -eq 2 ] && [ "$(last)" = "DOCTOR_EVIDENCE=ERROR" ]; then
  ok "an unexpected argument is a usage error ending in the token"
else
  bad "extra args should exit 2 + DOCTOR_EVIDENCE=ERROR (got $rc / $(last))"
fi
HELP="$(bash "$CVG" help 2>&1 || true)"
case "$HELP" in
  *"doctor evidence"*) ok "cvg help lists the subject" ;;
  *) bad "cvg help does not mention doctor evidence" ;;
esac
if bash "$CVG" agent-context 2>&1 | python3 -c '
import json,sys
m=json.load(sys.stdin)
c=[x for x in m["commands"] if x["name"]=="doctor evidence"]
assert len(c)==1
assert "DOCTOR_EVIDENCE=OK|UNTRACKED|NOT_GIT|ERROR" in c[0]["emits_tokens"]
assert c[0]["mutating"] is False
' 2>/dev/null; then
  ok "agent-context declares it read-only with its token set"
else
  bad "agent-context entry missing or wrong"
fi

echo
echo "=================================================================="
printf 'rows: %s   failed: %s\n' "$rows" "$failed"
if [ "$failed" -eq 0 ]; then echo "DOCTOR_EVIDENCE_TESTS=PASS"; exit 0; fi
echo "DOCTOR_EVIDENCE_TESTS=FAIL"; exit 1
