#!/bin/bash
# run-tests.sh — pass-to-lesson v0.3.0 gate regression.
# Proves check-lesson.sh discriminates: the good modes fixture passes, the bad
# one fails for its intended (mode) reasons, back-compat holds (no modes: line
# → mode checks skip), every base-gate negative fails for its own reason,
# section names match exactly (no substring decoys), the per-block rules bite
# (breaks-downstream per component, ADEPT labels per block, all four review
# days), --immutable enforces "teaching changes nothing", and the last line is
# always exactly one CHECK_LESSON machine token. bash 3.2 safe.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CL="$HERE/../scripts/check-lesson.sh"
FX="$HERE/fixtures"
rows=0; failed=0

ok()  { printf 'ok   %s\n' "$1"; }
bad() { printf 'FAIL %s\n' "$1"; failed=$((failed + 1)); }

expect() { # <label> <expected-exit> <file>
  rows=$((rows + 1))
  local rc=0
  bash "$CL" "$3" >/dev/null 2>&1 || rc=$?
  if [ "$rc" -eq "$2" ]; then
    ok "$1 (exit $rc)"
  else
    bad "$1 (want exit $2, got $rc)"
  fi
}

expect_out() { # <label> <expected-exit> <file> <extended-regex that must match the output>
  rows=$((rows + 1))
  local rc=0 out
  out="$(bash "$CL" "$3" 2>&1)" || rc=$?
  if [ "$rc" -eq "$2" ] && printf '%s\n' "$out" | grep -qE "$4"; then
    ok "$1 (exit $rc)"
  else
    bad "$1 (want exit $2 + /$4/, got exit $rc)"
  fi
}

expect_token() { # <label> <expected-exit> <expected-last-line> <args...>
  local label="$1" want_rc="$2" want_tok="$3"
  shift 3
  rows=$((rows + 1))
  local rc=0 last
  last="$(bash "$CL" "$@" 2>/dev/null | tail -1)" || rc=$?
  if [ "$rc" -eq "$want_rc" ] && [ "$last" = "$want_tok" ]; then
    ok "$label (exit $rc, last line $want_tok)"
  else
    bad "$label (want exit $want_rc + last line '$want_tok', got exit $rc, '$last')"
  fi
}

# --- v0.2.0 rows: emitter-mode discrimination (kept green) ------------------
expect "good-modes fixture passes"  0 "$FX/lesson-good-modes.md"
expect "bad-modes fixture fails"    1 "$FX/lesson-bad-modes.md"

# the bad fixture must fail ONLY on modes — its base sections stay valid
BASE=$(bash "$CL" "$FX/lesson-bad-modes.md" 2>&1 | grep -c '^PASS  section present' || true)
rows=$((rows + 1))
if [ "$BASE" -eq 7 ]; then ok "bad fixture keeps 7 base sections (fails on modes only)"
else bad "bad fixture base sections = $BASE (want 7)"; fi

# --- machine token: CHECK_LESSON=<verdict> is the true LAST line ------------
expect_token "pass ends in the CHECK_LESSON=PASS token"  0 "CHECK_LESSON=PASS" "$FX/lesson-good-modes.md"
expect_token "fail ends in the CHECK_LESSON=FAIL token"  1 "CHECK_LESSON=FAIL" "$FX/lesson-bad-modes.md"

# --- usage errors → exit 2 (+ USAGE_ERROR token) -----------------------------
expect_token "no-args is a usage error"                  2 "CHECK_LESSON=USAGE_ERROR"
expect_token "missing file is a usage error"             2 "CHECK_LESSON=USAGE_ERROR" "$FX/does-not-exist.md"
expect_token "unknown extra arg is a usage error"        2 "CHECK_LESSON=USAGE_ERROR" "$FX/lesson-plain.md" --bogus
expect_token "--immutable without paths is a usage error" 2 "CHECK_LESSON=USAGE_ERROR" "$FX/lesson-plain.md" --immutable

# --- base-gate negatives: each fails for its own reason ----------------------
expect_out "missing required section fails"        1 "$FX/lesson-missing-section.md"    '^FAIL  section missing: Vocabulary'
expect_out "walkthrough without components fails"  1 "$FX/lesson-no-components.md"      'walkthrough has no components'
expect_out "empty decisions table fails"           1 "$FX/lesson-empty-decisions.md"    'decisions table empty'
expect_out "two check-yourself questions fail"     1 "$FX/lesson-two-questions.md"      'Check yourself: 2 question'
expect_out "six check-yourself questions fail"     1 "$FX/lesson-six-questions.md"      'Check yourself: 6 question'

# --- exact section names: a substring decoy must not satisfy a section -------
expect_out "decoy 'Notes on why this pass exists' fails" 1 "$FX/lesson-decoy-section.md" '^FAIL  section missing: Why this pass exists'

# --- per-block precision ------------------------------------------------------
expect_out "one component lacking breaks-downstream fails" 1 "$FX/lesson-component-no-breaks.md" "lack 'what breaks downstream'"
expect_out "ADEPT labels must hold per block"              1 "$FX/lesson-adept-unbalanced.md"    '^FAIL  adept: 1 of 2 ADEPT block'
expect_out "review needs all four day checkpoints"         1 "$FX/lesson-review-missing-day.md"  'missing: 21'

# --- back-compat: no modes: line → mode checks skip, gate still passes -------
expect "plain lesson without a modes line passes" 0 "$FX/lesson-plain.md"

# --- --immutable: teaching changes nothing (temp git repo) --------------------
TMPREPO="$(mktemp -d "${TMPDIR:-/tmp}/cvg-lesson-repo.XXXXXX")"
NOREPO="$(mktemp -d "${TMPDIR:-/tmp}/cvg-lesson-norepo.XXXXXX")"
trap 'rm -rf "$TMPREPO" "$NOREPO"' EXIT

git -C "$TMPREPO" init -q
cp "$FX/lesson-plain.md" "$TMPREPO/lesson.md"
printf 'artifact v1\n' > "$TMPREPO/artifact-a.md"
printf 'artifact v1\n' > "$TMPREPO/artifact-b.md"
git -C "$TMPREPO" add artifact-a.md artifact-b.md
git -C "$TMPREPO" -c user.email=test@example.com -c user.name=test -c commit.gpgsign=false commit -qm fixtures

rows=$((rows + 1))
rc=0
out="$(cd "$TMPREPO" && bash "$CL" lesson.md --immutable artifact-a.md artifact-b.md 2>&1)" || rc=$?
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^PASS  immutable:'; then
  ok "immutable: clean artifacts pass"
else
  bad "immutable clean (want exit 0 + PASS immutable, got exit $rc)"
fi

printf 'tampered\n' >> "$TMPREPO/artifact-a.md"
rows=$((rows + 1))
rc=0
out="$(cd "$TMPREPO" && bash "$CL" lesson.md --immutable artifact-a.md artifact-b.md 2>&1)" || rc=$?
if [ "$rc" -eq 1 ] \
  && printf '%s\n' "$out" | grep -q '^FAIL  immutable:' \
  && [ "$(printf '%s\n' "$out" | tail -1)" = "CHECK_LESSON=FAIL" ]; then
  ok "immutable: a modified artifact fails the gate"
else
  bad "immutable modified (want exit 1 + FAIL immutable + FAIL token, got exit $rc)"
fi
git -C "$TMPREPO" checkout -q -- artifact-a.md

printf 'referenced but never committed\n' > "$TMPREPO/artifact-c.md"
rows=$((rows + 1))
rc=0
out="$(cd "$TMPREPO" && bash "$CL" lesson.md --immutable artifact-c.md 2>&1)" || rc=$?
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -q '^FAIL  immutable:'; then
  ok "immutable: an untracked-but-referenced artifact fails the gate"
else
  bad "immutable untracked (want exit 1 + FAIL immutable, got exit $rc)"
fi

cp "$FX/lesson-plain.md" "$NOREPO/lesson.md"
printf 'artifact v1\n' > "$NOREPO/artifact.md"
rows=$((rows + 1))
rc=0
out="$(cd "$NOREPO" && bash "$CL" lesson.md --immutable artifact.md 2>&1)" || rc=$?
if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | grep -q '^WARN  --immutable'; then
  ok "immutable: outside a git repo it warns and skips (never crashes)"
else
  bad "immutable outside-repo (want exit 0 + WARN, got exit $rc)"
fi

printf 'rows: %s  failed: %s\n' "$rows" "$failed"
[ "$failed" -eq 0 ]
