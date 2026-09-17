#!/usr/bin/env bash
# test-cvg-lesson.sh — the teaching companion's CLI door.
#
# WHY THIS EXISTS
# `pass-to-lesson` shipped a gate script, a machine token, and a workspace folder
# that `cvg init` creates (cvg/docs/lessons/) — and no way to reach any of it from
# the CLI. It was the only skill in the package with no verb, so the only way to
# run its gate was to know the path to a script inside the installed package. A
# capability an agent cannot find in `cvg help` or `cvg agent-context` is a
# capability that does not get used.
#
# This suite proves the door behaves like every other gate door:
#   1. byte-parity — the wrapped path decorates NOTHING (rule: wrap, don't rewrite)
#   2. the discovery contract — 0 found → exit 2, 1 → gates, >1 → exit 2 naming all
#   3. every exit-2 path still ends in the CHECK_LESSON=USAGE_ERROR token
#   4. --immutable reaches the checker intact, both verdicts
#   5. the verb is discoverable: help, agent-context, and the --json envelope
#   6. it is genuinely read-only — gating a lesson mutates nothing
#
# Hermetic: throwaway git repos, no engine, no tracker, no network.
# Token: CVG_LESSON=PASS | CVG_LESSON=FAIL
# bash 3.2 safe (stock macOS). Deps: git, diff, python3.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/.." && pwd)"
CVG="$REPO/bin/cvg"
CHECKER="$REPO/skills/pass-to-lesson/scripts/check-lesson.sh"
FX="$REPO/skills/pass-to-lesson/tests/fixtures"

rows=0; failed=0
ok()  { printf '  ok   — %s\n' "$1"; rows=$((rows + 1)); }
bad() { printf '  FAIL — %s\n' "$1"; rows=$((rows + 1)); failed=$((failed + 1)); }

echo "=================================================================="
echo "test-cvg-lesson.sh — cvg lesson is a real gate door"
echo "=================================================================="

for f in "$CVG" "$CHECKER" "$FX/lesson-good-modes.md" "$FX/lesson-bad-modes.md"; do
  [ -e "$f" ] || { echo "  FAIL — missing prerequisite: $f"; echo "CVG_LESSON=FAIL"; exit 1; }
done

WS="$(mktemp -d -t cvg-lesson.XXXXXX)"
trap 'rm -rf "$WS"' EXIT
git -C "$WS" init --quiet
git -C "$WS" config user.email "test@converge.local"
git -C "$WS" config user.name "converge test"
( cd "$WS" && CVG_PROJECT_ROOT="$WS" bash "$CVG" init >/dev/null 2>&1 )

# The workspace `cvg init` creates must already have somewhere to put a lesson —
# the folder and the verb have to agree, or discovery is pointing at nothing.
if [ -d "$WS/cvg/docs/lessons" ]; then
  ok "cvg init creates cvg/docs/lessons/ — the folder the verb discovers"
else
  bad "cvg init did not create cvg/docs/lessons/"
fi

run() { # run <expected-exit> <args...> — captures OUT
  local want="$1"; shift
  local rc=0
  OUT="$(cd "$WS" && bash "$CVG" "$@" 2>&1)" || rc=$?
  RC="$rc"
  [ "$rc" = "$want" ]
}

last_line() { printf '%s\n' "$OUT" | tail -1; }

# ---------------------------------------------------------------------------
echo
echo "[1] discovery: nothing to gate is a usage error, not a pass"
# ---------------------------------------------------------------------------
if run 2 lesson && [ "$(last_line)" = "CHECK_LESSON=USAGE_ERROR" ]; then
  ok "no lesson on the floor → exit 2 + CHECK_LESSON=USAGE_ERROR"
else
  bad "empty workspace should exit 2 with the usage token (got $RC / $(last_line))"
fi
if printf '%s\n' "$OUT" | grep -q 'cvg/docs/lessons/'; then
  ok "the failure names where it looked"
else
  bad "discovery failure must name cvg/docs/lessons/"
fi

# ---------------------------------------------------------------------------
echo
echo "[2] one lesson: it gates, and it decorates nothing"
# ---------------------------------------------------------------------------
LESSON="cvg/docs/lessons/lesson-pass-1-billing.md"
cp "$FX/lesson-good-modes.md" "$WS/$LESSON"

if run 0 lesson && [ "$(last_line)" = "CHECK_LESSON=PASS" ]; then
  ok "a gate-ready lesson passes → exit 0 + CHECK_LESSON=PASS"
else
  bad "the good fixture should pass through the verb (got $RC / $(last_line))"
fi

# Byte-parity is the load-bearing claim of every wrapped command: the verb may
# discover a target, but it may not touch what the checker says about it.
( cd "$WS" && bash "$CVG" lesson >"$WS/.via-verb" 2>&1 )
( cd "$WS" && bash "$CHECKER" "$LESSON" >"$WS/.via-script" 2>&1 )
if diff -q "$WS/.via-verb" "$WS/.via-script" >/dev/null 2>&1; then
  ok "byte-parity: cvg lesson == check-lesson.sh, byte for byte"
else
  bad "cvg lesson decorated the wrapped output:"
  diff "$WS/.via-script" "$WS/.via-verb" | sed 's/^/        /'
fi

# An explicit path must reach the checker unchanged too.
if run 0 lesson "$LESSON" && [ "$(last_line)" = "CHECK_LESSON=PASS" ]; then
  ok "an explicit path gates the same way discovery does"
else
  bad "explicit path should pass (got $RC / $(last_line))"
fi

# A failing gate must pass its FAIL through unmasked — exit 1, not 0, not 2.
cp "$FX/lesson-bad-modes.md" "$WS/$LESSON"
if run 1 lesson && [ "$(last_line)" = "CHECK_LESSON=FAIL" ]; then
  ok "a failing lesson fails the verb → exit 1 + CHECK_LESSON=FAIL (unmasked)"
else
  bad "a failing gate must surface as exit 1 + FAIL (got $RC / $(last_line))"
fi
cp "$FX/lesson-good-modes.md" "$WS/$LESSON"

# ---------------------------------------------------------------------------
echo
echo "[3] discovery: lessons accumulate, so >1 names them all"
# ---------------------------------------------------------------------------
SECOND="cvg/docs/lessons/lesson-pass-2-adrs.md"
cp "$FX/lesson-good-modes.md" "$WS/$SECOND"
if run 2 lesson && [ "$(last_line)" = "CHECK_LESSON=USAGE_ERROR" ]; then
  ok "two lessons → exit 2 + the usage token (never a silent pick)"
else
  bad "ambiguous discovery must exit 2 with the token (got $RC / $(last_line))"
fi
if printf '%s\n' "$OUT" | grep -q 'lesson-pass-1-billing.md' \
  && printf '%s\n' "$OUT" | grep -q 'lesson-pass-2-adrs.md'; then
  ok "the ambiguity error names every candidate it found"
else
  bad "ambiguous discovery must list both lessons"
fi
# ...and naming one still works while the other exists.
if run 0 lesson "$SECOND" && [ "$(last_line)" = "CHECK_LESSON=PASS" ]; then
  ok "naming one of many gates that one"
else
  bad "an explicit path must win over ambiguity (got $RC / $(last_line))"
fi
rm -f "$WS/$SECOND"

# ---------------------------------------------------------------------------
echo
echo "[4] flag contracts: every refusal ends in the machine token"
# ---------------------------------------------------------------------------
if run 2 lesson --bogus && [ "$(last_line)" = "CHECK_LESSON=USAGE_ERROR" ]; then
  ok "unknown flag → exit 2 + CHECK_LESSON=USAGE_ERROR"
else
  bad "unknown flag must exit 2 with the token (got $RC / $(last_line))"
fi
if run 2 lesson "$LESSON" --immutable && [ "$(last_line)" = "CHECK_LESSON=USAGE_ERROR" ]; then
  ok "--immutable with no paths → exit 2 + the token"
else
  bad "--immutable needs at least one path (got $RC / $(last_line))"
fi
if run 2 lesson a.md b.md && [ "$(last_line)" = "CHECK_LESSON=USAGE_ERROR" ]; then
  ok "two lesson targets → exit 2 (one lesson per gate)"
else
  bad "two targets must be a usage error (got $RC / $(last_line))"
fi

# ---------------------------------------------------------------------------
echo
echo "[5] --immutable: teaching changes nothing it taught"
# ---------------------------------------------------------------------------
TAUGHT="cvg/docs/tech-spec/billing.md"
printf 'the taught tech-spec\n' > "$WS/$TAUGHT"
git -C "$WS" add -A >/dev/null 2>&1
git -C "$WS" commit -qm "the pass that closed" >/dev/null 2>&1

if run 0 lesson --immutable "$TAUGHT" \
  && printf '%s\n' "$OUT" | grep -q '^PASS  immutable:' \
  && [ "$(last_line)" = "CHECK_LESSON=PASS" ]; then
  ok "--immutable reaches the checker: an untouched artifact passes"
else
  bad "--immutable clean should pass with a PASS immutable row (got $RC / $(last_line))"
fi

printf 'tampered by the lesson\n' >> "$WS/$TAUGHT"
if run 1 lesson --immutable "$TAUGHT" \
  && printf '%s\n' "$OUT" | grep -q '^FAIL  immutable:' \
  && [ "$(last_line)" = "CHECK_LESSON=FAIL" ]; then
  ok "--immutable bites: a modified taught artifact fails the gate"
else
  bad "a tampered artifact must fail through the verb (got $RC / $(last_line))"
fi
git -C "$WS" checkout -q -- "$TAUGHT"

# ---------------------------------------------------------------------------
echo
echo "[6] the verb is discoverable, and read-only"
# ---------------------------------------------------------------------------
HELP="$(bash "$CVG" help 2>&1)"
if printf '%s\n' "$HELP" | grep -q '^  lesson '; then
  ok "cvg help lists the lesson verb"
else
  bad "cvg help does not mention lesson — an undiscoverable verb is unused"
fi
if printf '%s\n' "$HELP" | grep -q 'CHECK_LESSON'; then
  ok "cvg help names the token the verb emits"
else
  bad "cvg help should name CHECK_LESSON"
fi

MANIFEST="$(bash "$CVG" agent-context 2>&1)"
if printf '%s\n' "$MANIFEST" | python3 -c '
import json, sys
m = json.load(sys.stdin)
cmds = [c for c in m["commands"] if c["name"].startswith("lesson")]
assert len(cmds) == 1, f"expected exactly one lesson command, got {len(cmds)}"
c = cmds[0]
assert "CHECK_LESSON=PASS|FAIL|USAGE_ERROR" in c["emits_tokens"], c["emits_tokens"]
assert c["mutating"] is False, "the lesson gate must be declared read-only"
assert "pass-to-lesson/check-lesson.sh" == c["wraps"], c["wraps"]
assert c["converge_pass"] is None, "a lesson belongs to no pass"
assert "pass-prompt.md" in c["description"], "the manifest should name the steering prompt"
' 2>/dev/null; then
  ok "agent-context declares lesson: token, read-only, wrapped script, no pass"
else
  bad "agent-context entry for lesson is missing or wrong"
fi

ENV_OUT="$(cd "$WS" && bash "$CVG" lesson --json 2>&1)"
if printf '%s\n' "$ENV_OUT" | python3 -c '
import json, sys
e = json.load(sys.stdin)
assert e["ok"] is True, e
assert e["command"] == "lesson", e["command"]
assert e["token"] == "CHECK_LESSON=PASS", e["token"]
assert e["verdict"] == "PASS", e["verdict"]
assert e["changed"] is False, "a gate must never report a change"
assert e["converge_pass"] is None, e["converge_pass"]
' 2>/dev/null; then
  ok "--json envelope carries the token, the verdict, and changed=false"
else
  bad "the --json envelope for lesson is wrong: $ENV_OUT"
fi

# The gate must leave the workspace exactly as it found it.
BEFORE="$(cd "$WS" && git status --porcelain | sort)"
BEFORE_N="$(cd "$WS" && find cvg -type f | wc -l | tr -d ' ')"
( cd "$WS" && bash "$CVG" lesson >/dev/null 2>&1 )
( cd "$WS" && bash "$CVG" lesson --immutable "$TAUGHT" >/dev/null 2>&1 )
AFTER="$(cd "$WS" && git status --porcelain | sort)"
AFTER_N="$(cd "$WS" && find cvg -type f | wc -l | tr -d ' ')"
if [ "$BEFORE" = "$AFTER" ] && [ "$BEFORE_N" = "$AFTER_N" ]; then
  ok "gating a lesson is read-only — nothing added, nothing changed"
else
  bad "cvg lesson mutated the workspace ($BEFORE_N -> $AFTER_N files)"
fi

# ---------------------------------------------------------------------------
echo
echo "[7] the companion ships its own steering prompt"
# ---------------------------------------------------------------------------
PROMPT="$REPO/skills/pass-to-lesson/references/pass-prompt.md"
if [ -f "$PROMPT" ]; then
  ok "references/pass-prompt.md ships with the skill"
else
  bad "the companion has no steering prompt — every other pass skill owns one"
fi
if grep -q 'cvg lesson' "$PROMPT" 2>/dev/null && grep -q 'cvg/docs/lessons/' "$PROMPT" 2>/dev/null; then
  ok "the prompt names its exit gate and its typed folder"
else
  bad "the steering prompt must name cvg lesson and cvg/docs/lessons/"
fi
# The conductor names the companion wherever a pass has closed, so an agent
# reading `cvg next` learns the door exists without being told.
NEXT_OUT="$(cd "$WS" && bash "$CVG" next 2>&1)"
if printf '%s\n' "$NEXT_OUT" | grep -q 'cvg lesson'; then
  ok "cvg next names the companion once a pass has closed"
else
  bad "cvg next should offer the teaching companion when there is something to teach"
fi
if [ "$(printf '%s\n' "$NEXT_OUT" | tail -1 | cut -d= -f1)" = "NEXT_PASS" ]; then
  ok "the companion line never displaces the conductor's machine token"
else
  bad "NEXT_PASS must remain the last line of cvg next"
fi

echo
echo "=================================================================="
printf 'rows: %s   failed: %s\n' "$rows" "$failed"
if [ "$failed" -eq 0 ]; then
  echo "CVG_LESSON=PASS"
  exit 0
fi
echo "CVG_LESSON=FAIL"
exit 1
