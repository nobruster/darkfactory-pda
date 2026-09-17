#!/usr/bin/env bash
# test-cvg-doctor-host.sh — a missing prerequisite must be ONE command to find.
#
# WHY THIS EXISTS
# `shellcheck` was absent from a shell's PATH. safe-to-delegate passes
# --shellcheck-evals unconditionally, so the delegation gate BLOCKED and the spec was
# never stamped; `cvg bind` refuses an unsigned spec, so no execution profile was
# written; `cvg loop` then reported "Pass 6 runtime contract is missing". Every message
# in that chain was CORRECT and none of them was the cause, which sat three verbs
# upstream. It cost an hour of bisecting — including a commit CI had passed, because CI
# installs shellcheck explicitly.
#
# So the load-bearing rows here are not "does it list tools". They are:
#   [2] a missing REQUIRED tool fails CLOSED, and
#   [3] the report NAMES THE VERBS THAT BREAK — because "shellcheck: MISSING" is not
#       the finding; "you cannot sign, therefore cannot bind, therefore cannot loop" is.
#
# Also pinned: it must not depend on what it audits (pure bash — python3 is one of the
# things it checks), the token is the last stdout line, and it writes nothing.
#
# Hermetic: PATH is narrowed to synthesize absence. No installs, no network.
# Token: DOCTOR_HOST_TESTS=PASS | DOCTOR_HOST_TESTS=FAIL
# bash 3.2 safe. Deps: git, bash.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
CVG="$REPO/bin/cvg"

rows=0; failed=0
ok()  { printf '  ok   — %s\n' "$1"; rows=$((rows+1)); }
bad() { printf '  FAIL — %s\n' "$1"; rows=$((rows+1)); failed=$((failed+1)); }

echo "=================================================================="
echo "test-cvg-doctor-host.sh — a missing tool is one command to find"
echo "=================================================================="

TMP="$(mktemp -d -t cvg-doctor-host.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# Absence is synthesized by NARROWING PATH, never by uninstalling anything.
#
# The first attempt symlinked only the tools under test into a scratch bin — and the
# router itself needs dirname/uname/readlink, so the probe died inside cvg before
# reaching the check. Lesson kept: a sandbox that starves the harness tests the
# harness. So instead the rows lean on where these tools ACTUALLY live, which is also
# the real-world shape of the bug: shellcheck is a homebrew install, so dropping
# /opt/homebrew/bin from PATH reproduces exactly the environment that cost the hour.
SYS_PATH="/usr/bin:/bin:/usr/sbin:/sbin"
BREW_DIR="$(dirname "$(command -v shellcheck 2>/dev/null || echo /nonexistent/x)")"
# NOTE: a trailing comment starting with the word "shellcheck" is parsed as a
# directive (SC1126), so these are phrased around it.
PATH_OK="$BREW_DIR:$SYS_PATH"     # every required tool present

# For a tool that DOES live in /usr/bin (python3), mirror the system dirs and omit it.
mirror_without() { # mirror_without <dir> <tool>
  local out="$1" skip="$2" d f
  mkdir -p "$out"
  for d in /usr/bin /bin /usr/sbin /sbin; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
      [ -x "$f" ] || continue
      case "$(basename "$f")" in "$skip"|"$skip".*) continue ;; esac
      ln -sf "$f" "$out/$(basename "$f")" 2>/dev/null || true
    done
  done
}

# The linter may be installed by Homebrew or by a system package manager. A
# mirrored PATH that explicitly omits it is portable across both host shapes.
BINNS="$TMP/binns"
mirror_without "$BINNS" shellcheck
PATH_NOSC="$BINNS"

run() { # run <expected-exit> <PATH>; sets OUT/RC
  # Override PATH only. `env -i` was the first attempt and it strips PWD, which the
  # router needs for workspace resolution — the probe then failed on the router
  # rather than on the thing under test, which is its own small lesson.
  local want="$1" path="$2" rc=0
  OUT="$(env PATH="$path" bash "$CVG" doctor host 2>&1)" || rc=$?
  RC="$rc"
  [ "$rc" = "$want" ]
}
last() { printf '%s\n' "$OUT" | tail -1; }

# ---------------------------------------------------------------------------
echo
echo "[1] every required tool present reports a non-blocking verdict at exit 0"
# ---------------------------------------------------------------------------
if [ ! -x "$BREW_DIR/shellcheck" ]; then
  echo "  UNRUNNABLE — shellcheck is not installed, so the PRESENT case cannot be built."
  echo "  DOCTOR_HOST_TESTS=UNRUNNABLE"; exit 3
fi
if run 0 "$PATH_OK" && {
  [ "$(last)" = "DOCTOR_HOST=OK" ] || [ "$(last)" = "DOCTOR_HOST=DEGRADED" ]
}; then
  ok "every required tool present → exit 0 + OK or optional-only DEGRADED"
else
  bad "expected exit 0 + non-blocking host verdict (got $RC / $(last))"
fi
case "$OUT" in
  *shellcheck*) ok "the report names shellcheck explicitly (not a bare count)" ;;
  *) bad "shellcheck is not mentioned in a passing report" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[2] THE LOAD-BEARING ROW: a missing REQUIRED tool fails CLOSED"
# ---------------------------------------------------------------------------
if run 1 "$PATH_NOSC" && [ "$(last)" = "DOCTOR_HOST=MISSING" ]; then
  ok "no shellcheck → exit 1 + DOCTOR_HOST=MISSING (a doctor that shrugs is useless)"
else
  bad "expected exit 1 + DOCTOR_HOST=MISSING (got $RC / $(last))"
fi

# ---------------------------------------------------------------------------
echo
echo "[3] ...and it names the VERBS that break, not just the tool"
# ---------------------------------------------------------------------------
case "$OUT" in
  *"blocks:"*) ok "the missing tool carries a 'blocks:' line" ;;
  *) bad "a missing tool must say what it breaks" ;;
esac
case "$OUT" in
  *"cvg tasks gate"*) ok "it names cvg tasks gate — where the block actually happens" ;;
  *) bad "the chain does not name the gate that blocks" ;;
esac
case "$OUT" in
  *"bind"*) ok "…and cvg bind, the second hop" ;;
  *) bad "the chain stops before bind" ;;
esac
case "$OUT" in
  *"loop"*) ok "…and cvg loop, where the symptom finally surfaced" ;;
  *) bad "the chain never reaches the loop, which is where the hour was lost" ;;
esac
case "$OUT" in
  *"brew install shellcheck"*) ok "and it prints the remedy, not just the diagnosis" ;;
  *) bad "no fix given for the missing tool" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "[4] an optional-but-load-bearing tool DEGRADES, it does not block"
# ---------------------------------------------------------------------------
# F-021: cvg lint needs bash 4 (associative arrays) against a stated 3.2 floor.
# Absent bash 4 the delegation path still works, so DEGRADED must NOT fail closed — a
# doctor that cries MISSING over an optional tool teaches you to ignore it.
#
# Note the probe searches ABSOLUTE candidates (/opt/homebrew/bin/bash, /usr/local/bin/bash,
# /bin/bash) on purpose, exactly as ts_require_bash4 does — so PATH cannot hide a bash 4
# and this case is only reachable on a host that genuinely has none. Skipped loudly
# rather than faked, because a row that cannot fail proves nothing.
_have_b4=0
for _c in /opt/homebrew/bin/bash /usr/local/bin/bash /bin/bash; do
  _m="$("$_c" -c 'echo ${BASH_VERSINFO[0]}' 2>/dev/null || echo 0)"
  case "$_m" in ''|*[!0-9]*) _m=0 ;; esac
  [ "$_m" -ge 4 ] && { _have_b4=1; break; }
done
if [ "$_have_b4" = 0 ]; then
  if run 0 "$PATH_OK" && [ "$(last)" = "DOCTOR_HOST=DEGRADED" ]; then
    ok "no bash 4 anywhere → exit 0 + DOCTOR_HOST=DEGRADED (not MISSING)"
  else
    bad "expected exit 0 + DOCTOR_HOST=DEGRADED (got $RC / $(last))"
  fi
  case "$OUT" in
    *"cvg lint"*) ok "and it names cvg lint as the verb that stops working" ;;
    *) bad "DEGRADED must say WHICH verb it costs you" ;;
  esac
else
  echo "  SKIP  — this host HAS a bash 4+, and the probe searches absolute paths by"
  echo "        design, so the DEGRADED case cannot be synthesized here. The bash-4"
  echo "        row is meaningful on a stock-macOS host with no homebrew bash."
fi

# ---------------------------------------------------------------------------
echo
echo "[5] it does not depend on what it audits"
# ---------------------------------------------------------------------------
# python3 is one of the checks, so the checker cannot be written in python3.
BINNP="$TMP/binnp"
mirror_without "$BINNP" python3
ln -sf "$BREW_DIR/shellcheck" "$BINNP/shellcheck" 2>/dev/null || true
if run 1 "$BINNP"; then
  case "$OUT" in
    *python3*MISSING*|*MISSING*python3*)
      ok "with python3 absent it still runs and REPORTS python3 missing" ;;
    *) bad "python3's absence was not reported (did the checker need python3?)" ;;
  esac
  [ "$(last)" = "DOCTOR_HOST=MISSING" ] \
    && ok "…and still emits its token, so a Manager can branch on it" \
    || bad "no token when python3 is absent (got $(last))"
else
  bad "a python3-less host must still produce a verdict (got $RC / $(last))"
fi

# ---------------------------------------------------------------------------
echo
echo "[6] read-only, and usage fails closed"
# ---------------------------------------------------------------------------
WS="$TMP/ws"; mkdir -p "$WS"; ( cd "$WS" && git init --quiet )
printf 'x\n' > "$WS/f.txt"
BEFORE="$(cd "$WS" && find . -type f -not -path './.git/*' -exec cksum {} + | sort)"
( cd "$WS" && env PATH="$PATH_OK" bash "$CVG" doctor host >/dev/null 2>&1 ) || true
AFTER="$(cd "$WS" && find . -type f -not -path './.git/*' -exec cksum {} + | sort)"
[ "$BEFORE" = "$AFTER" ] \
  && ok "asking about the host writes nothing" \
  || bad "doctor host mutated the workspace"

rc=0; OUT="$(bash "$CVG" doctor host --extra 2>&1)" || rc=$?
if [ "$rc" = 2 ] && [ "$(last)" = "DOCTOR_HOST=ERROR" ]; then
  ok "an unexpected argument → exit 2 + DOCTOR_HOST=ERROR"
else
  bad "expected exit 2 + DOCTOR_HOST=ERROR (got $rc / $(last))"
fi
rc=0; OUT="$(bash "$CVG" doctor nonsense 2>&1)" || rc=$?
case "$OUT" in
  *"host"*) ok "the unknown-subject error lists 'host' among the valid subjects" ;;
  *) bad "doctor's usage error does not mention the new subject" ;;
esac

# ---------------------------------------------------------------------------
echo
echo "=================================================================="
printf 'rows: %s   failed: %s\n' "$rows" "$failed"
if [ "$failed" -eq 0 ]; then
  echo "DOCTOR_HOST_TESTS=PASS"; exit 0
fi
echo "DOCTOR_HOST_TESTS=FAIL"; exit 1
