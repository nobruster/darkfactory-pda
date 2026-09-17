#!/usr/bin/env bash
# run-tests.sh — evidence-to-next-pass: the sequence engine, proven hermetically.
#
# Builds a throwaway workspace with the real `cvg init`, then fabricates each
# pass's evidence in order and asserts the conductor derives position, refuses
# early starts (pre), and verifies artifacts (post) — all from the floor, no
# stored state. No engine, no network, no credentials.
#
# Token: NEXT_PASS_TESTS=PASS | NEXT_PASS_TESTS=FAIL
# bash 3.2 safe.

set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SELF_DIR/../../.." && pwd)"
ENGINE="$REPO/skills/evidence-to-next-pass/scripts/next-pass.sh"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   — %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL — %s\n' "$1"; }

echo "=================================================================="
echo "evidence-to-next-pass — the descent, in order, every time"
echo "=================================================================="

T="$(mktemp -d -t conductor-tests.XXXXXX)"
trap 'rm -rf "$T"' EXIT
git -C "$T" init --quiet
( cd "$T" && CVG_PROJECT_ROOT="$T" bash "$REPO/bin/cvg" init >/dev/null )

run() {  # run <expected-exit> <args...> — captures OUT, returns 0 if exit matches
  local want="$1"; shift
  local rc=0
  OUT="$(cd "$T" && bash "$ENGINE" "$@" 2>&1)" || rc=$?
  [ "$rc" = "$want" ]
}

# --- empty workspace ---------------------------------------------------------
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=0$' \
  && ok "fresh workspace: next is pass 0" || bad "fresh workspace should point at pass 0 ($OUT)"

run 0 next --guided \
  && printf '%s' "$OUT" | grep -q '^GUIDED_CHAT=AWAITING_CHOICE$' \
  && printf '%s' "$OUT" | grep -q '\[CONTINUE\]' \
  && printf '%s' "$OUT" | grep -q '\[EXPLAIN\]' \
  && printf '%s' "$OUT" | grep -q '\[INSPECT\]' \
  && printf '%s' "$OUT" | grep -q '\[PAUSE\]' \
  && [ "$(printf '%s\n' "$OUT" | tail -1)" = "NEXT_PASS=0" ] \
  && ok "guided mode offers stable choices and preserves NEXT_PASS last" \
  || bad "guided mode must stop at a stable user-choice boundary ($OUT)"

run 2 pre 0 --guided && printf '%s' "$OUT" | grep -q '^NEXT_PASS=USAGE_ERROR$' \
  && ok "--guided belongs only to next" \
  || bad "pre/post must reject the guided presentation flag ($OUT)"

run 0 pre 0 && printf '%s' "$OUT" | grep -q '^PASS_PRE=OK$' \
  && ok "pass 0 has no doors before it" || bad "pre 0 should be OK on a fresh floor"

run 1 pre 5 && printf '%s' "$OUT" | grep -q '^PASS_PRE=MISSING$' \
  && printf '%s' "$OUT" | grep -q 'pass 0' \
  && ok "pre 5 refuses and names the missing passes" || bad "pre 5 must refuse on an empty floor"

run 1 post 0 && printf '%s' "$OUT" | grep -q '^PASS_POST=INCOMPLETE$' \
  && ok "post 0 reports no artifact yet" || bad "post 0 must be INCOMPLETE before the BRD exists"

# --- the descent, one artifact at a time ------------------------------------
touch "$T/cvg/docs/brd/shop.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=1$' \
  && ok "BRD in the typed folder: next is pass 1" || bad "after BRD, next should be 1 ($OUT)"
run 0 post 0 && printf '%s' "$OUT" | grep -q '^PASS_POST=OK$' \
  && printf '%s' "$OUT" | grep -q 'cvg capture' \
  && ok "post 0 sees the artifact and names the authoritative gate" || bad "post 0 should be OK now"

touch "$T/cvg/docs/tech-spec/shop.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=2$' \
  && ok "tech-spec: next is pass 2" || bad "after tech-spec, next should be 2"

touch "$T/cvg/docs/adrs/adr-001-storage.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=3$' \
  && ok "ADRs: next is pass 3" || bad "after ADRs, next should be 3"

mkdir -p "$T/cvg/sketch/swimlane-core" && touch "$T/cvg/sketch/swimlane-core/leg-1.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=4$' \
  && ok "swimlanes: next is pass 4 — the barrier" || bad "after swimlanes, next should be 4"

mkdir -p "$T/cvg/sketch/.consensus" && echo '{}' > "$T/cvg/sketch/.consensus/objection-log.json"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=5$' \
  && ok "objection log: next is pass 5 — the cornerstone" || bad "after the barrier, next should be 5"
run 0 pre 5 && printf '%s' "$OUT" | grep -q '^PASS_PRE=OK$' \
  && ok "pre 5 opens once the barrier evidence exists" || bad "pre 5 should be OK now"

printf -- '---\nstatus: ready\n---\n' > "$T/cvg/tasks/T-20260730-first.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=5$' \
  && ok "an UNSIGNED spec does not close pass 5" || bad "unsigned spec must not advance the descent"

printf -- '---\nstatus: ready\nsigned_off: true\n---\n' > "$T/cvg/tasks/T-20260730-first.md"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=7$' \
  && ok "a SIGNED spec closes 5: next is pass 7 (6 is opt-in)" || bad "after a signed spec, next should be 7"

touch "$T/cvg/execution/T-20260730-first.profile.yaml"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=8$' \
  && ok "execution profile: next is pass 8 — the loop" || bad "after bind evidence, next should be 8"

echo '{}' > "$T/cvg/receipts/T-20260730-first.json"
run 0 next && printf '%s' "$OUT" | grep -q '^NEXT_PASS=DONE$' \
  && ok "receipt on the floor: the lane is DONE" || bad "after a receipt, next should be DONE"

run 0 next --guided \
  && printf '%s' "$OUT" | grep -q '^GUIDED_CHAT=DONE$' \
  && printf '%s' "$OUT" | grep -q '\[REVIEW\]' \
  && ! printf '%s' "$OUT" | grep -q '\[CONTINUE\]' \
  && [ "$(printf '%s\n' "$OUT" | tail -1)" = "NEXT_PASS=DONE" ] \
  && ok "guided completion offers review, teaching, or pause — never another pass" \
  || bad "guided completion must not invent more workflow ($OUT)"

# Public cvg routing must expose the pre/post verbs documented by the chat
# contract. A tiny version-only Task-Spec stub keeps this row hermetic; the
# conductor itself does not call the task engine.
FAKE_TASKSPEC="$T/fake-taskspec"
cat > "$FAKE_TASKSPEC" <<'SH'
#!/usr/bin/env bash
[ "${1:-}" = "version" ] && { echo 3.8.0; exit 0; }
exit 99
SH
chmod +x "$FAKE_TASKSPEC"
OUT="$(cd "$T" && CVG_HOME="$REPO" CVG_PROJECT_ROOT="$T" \
  CVG_TASKSPEC_BIN="$FAKE_TASKSPEC" bash "$REPO/bin/cvg" next pre 0 2>&1)"; RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '^PASS_PRE=OK$'; then
  ok "public cvg next pre N routes to the fail-closed pre-hook"
else
  bad "public cvg next pre N did not reach the pre-hook ($OUT)"
fi
OUT="$(cd "$T" && CVG_HOME="$REPO" CVG_PROJECT_ROOT="$T" \
  CVG_TASKSPEC_BIN="$FAKE_TASKSPEC" bash "$REPO/bin/cvg" next post 8 2>&1)"; RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '^PASS_POST=OK$'; then
  ok "public cvg next post N routes to the artifact check"
else
  bad "public cvg next post N did not reach the post-hook ($OUT)"
fi

# --- lanes, opt-in register, contracts ---------------------------------------
T2="$(mktemp -d -t conductor-tests2.XXXXXX)"
git -C "$T2" init --quiet
( cd "$T2" && CVG_PROJECT_ROOT="$T2" bash "$REPO/bin/cvg" init >/dev/null )
OUT="$(cd "$T2" && bash "$ENGINE" next --lane FAST 2>&1)"
printf '%s' "$OUT" | grep -q '^NEXT_PASS=5$' \
  && ok "FAST lane skips the design half: next is 5 on a fresh floor" \
  || bad "FAST lane should start at pass 5 ($OUT)"
rm -rf "$T2"

BEFORE="$(find "$T/cvg" -type f | wc -l | tr -d ' ')"
run 0 next || true
AFTER="$(find "$T/cvg" -type f | wc -l | tr -d ' ')"
[ "$BEFORE" = "$AFTER" ] && ok "the conductor is read-only — it wrote nothing" \
  || bad "the conductor mutated the workspace ($BEFORE -> $AFTER files)"

# The legacy flat layout must still read as complete — no workspace gets
# stranded by the folder change.
T4="$(mktemp -d -t conductor-tests4.XXXXXX)"
git -C "$T4" init --quiet
( cd "$T4" && CVG_PROJECT_ROOT="$T4" bash "$REPO/bin/cvg" init >/dev/null )
touch "$T4/cvg/docs/brd-legacy.md" "$T4/cvg/docs/tech-spec-legacy.md"
OUT="$(cd "$T4" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q '^NEXT_PASS=2$' \
  && ok "legacy flat brd-*/tech-spec-*.md still count as done" \
  || bad "the flat layout was stranded by the folder change ($OUT)"
rm -rf "$T4"

# --- the teaching companion: named, never sequenced -------------------------
# A lesson is not a pass: it must never appear in the descent order, never gate
# anything, and never displace the machine token. But "a pass just closed" is
# exactly its trigger, so the conductor names it wherever there is something to
# teach — and stays quiet when there is not.
T5="$(mktemp -d -t conductor-tests5.XXXXXX)"
git -C "$T5" init --quiet
( cd "$T5" && CVG_PROJECT_ROOT="$T5" bash "$REPO/bin/cvg" init >/dev/null )
OUT="$(cd "$T5" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q 'cvg lesson' \
  && bad "a fresh floor has nothing to teach — the companion line must stay quiet" \
  || ok "fresh floor: no teaching offer (an always-on hint is noise)"

touch "$T5/cvg/docs/brd/shop.md"
OUT="$(cd "$T5" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q 'teach it   : cvg lesson' \
  && ok "once a pass has closed, the conductor names cvg lesson" \
  || bad "the companion should be offered after the first artifact lands ($OUT)"
[ "$(printf '%s\n' "$OUT" | tail -1)" = "NEXT_PASS=1" ] \
  && ok "the companion line never displaces the NEXT_PASS token" \
  || bad "NEXT_PASS must remain the last line of next"

OUT="$(cd "$T5" && bash "$ENGINE" post 0 2>&1)"
printf '%s' "$OUT" | grep -q 'teach it   : cvg lesson' \
  && [ "$(printf '%s\n' "$OUT" | tail -1)" = "PASS_POST=OK" ] \
  && ok "post N offers the lesson and keeps PASS_POST last" \
  || bad "post 0 should name the companion without displacing its token ($OUT)"

for L in FULL NORMAL FAST; do
  OUT="$(cd "$T5" && bash "$ENGINE" next --lane "$L" 2>&1)"
  printf '%s' "$OUT" | grep -qE '^  \[.\] pass (lesson|9)' \
    && bad "the companion leaked into the $L descent order — a lesson is not a pass" \
    || ok "$L order carries passes only; the companion is advisory"
done
rm -rf "$T5"

# --- THE BARRIER: evidence without consent must not advance the descent ------
# The 2026-08-03 regression. An objection log EXISTS the moment the adversary
# runs, so pass 4 read as complete while cvg review --check said FAIL with seven
# objections open. `next` is what an autonomous runner consults, so it pointed
# straight past the last human sign-off. Evidence is presence; consent is not.
T6="$(mktemp -d -t conductor-tests6.XXXXXX)"
git -C "$T6" init --quiet
( cd "$T6" && CVG_PROJECT_ROOT="$T6" bash "$REPO/bin/cvg" init >/dev/null )
touch "$T6/cvg/docs/brd/x.md" "$T6/cvg/docs/tech-spec/x.md" "$T6/cvg/docs/adrs/adr-001.md"
mkdir -p "$T6/cvg/swimlanes/core" && touch "$T6/cvg/swimlanes/core/_lane.md"
mkdir -p "$T6/cvg/swimlanes/.consensus"
# Downstream evidence too, so the refusal is proven to override later passes and
# not merely to fill a gap: a signed spec, a bind profile and a receipt all exist.
printf -- '---\nstatus: ready\nsigned_off: true\n---\n' > "$T6/cvg/tasks/T-20260803-x.md"
touch "$T6/cvg/execution/x.profile.yaml"; echo '{}' > "$T6/cvg/receipts/x.json"

# an objection nobody decided
cat > "$T6/cvg/swimlanes/.consensus/objection-log.json" <<'JSON'
{"objections":[{"id":"C1","severity":"critical",
  "proposal":{"disposition":"FIX","reason":"the read-only adversary did not implement the fix"}}]}
JSON
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q '^NEXT_PASS=4$' \
  && ok "an UNDECIDED objection log does not advance past the barrier" \
  || bad "next must stay at 4 while the barrier is open ($OUT)"
printf '%s' "$OUT" | grep -q '\[!\] pass 4' \
  && ok "the board marks the barrier [!] — artifact present, consent absent" \
  || bad "pass 4 should be marked [!] while objections are undecided"
OUT="$(cd "$T6" && bash "$ENGINE" pre 5 2>&1)" || true
printf '%s' "$OUT" | grep -q '^PASS_PRE=MISSING$' \
  && ok "the pre-hook refuses pass 5 behind an unsigned barrier (fail-closed)" \
  || bad "pre 5 must refuse while the barrier is open ($OUT)"

# the SAME log, now carrying an owner decision
cat > "$T6/cvg/swimlanes/.consensus/objection-log.json" <<'JSON'
{"objections":[{"id":"C1","severity":"critical",
  "proposal":{"disposition":"FIX","reason":"adversary advice"},
  "resolution":{"disposition":"FIX","decided_by":"owner","decided_at":"2026-08-03T12:00:00Z"}}]}
JSON
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -qE '^NEXT_PASS=(DONE|5|7|8)$' \
  && ok "once decided, the barrier stops blocking and the descent moves on" \
  || bad "a decided log must let next advance ($OUT)"
OUT="$(cd "$T6" && bash "$ENGINE" pre 5 2>&1)"
printf '%s' "$OUT" | grep -q '^PASS_PRE=OK$' \
  && ok "the pre-hook opens once a human has decided" \
  || bad "pre 5 should be OK after the barrier closes ($OUT)"

# --- THE SECOND LEAK on the same surface: consent to a text that no longer exists.
# Every objection decided, so the count-based check said the barrier was SHUT — and
# `next` said NEXT_PASS=7 over three plans that had been sharpened AFTER the
# adversary read them. Found live in uc-01 while `cvg review --check` said RED.
printf 'the plan the adversary actually read\n' > "$T6/cvg/swimlanes/core/_lane.md"
REVIEWED_SHA="$(shasum -a 256 "$T6/cvg/swimlanes/core/_lane.md" | awk '{print $1}')"
cat > "$T6/cvg/swimlanes/.consensus/objection-log.json" <<JSON
{"inputs":[{"path":"core/_lane.md","sha256":"$REVIEWED_SHA"}],
 "objections":[{"id":"C1","severity":"critical",
  "proposal":{"disposition":"FIX","reason":"adversary advice"},
  "resolution":{"disposition":"FIX","decided_by":"owner","decided_at":"2026-08-03T12:00:00Z"}}]}
JSON
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -qE '^NEXT_PASS=(DONE|5|7|8)$' \
  && ok "a decided log whose plan hashes still MATCH advances (no false alarm)" \
  || bad "matching provenance must not reopen the barrier ($OUT)"

# now sharpen the plan, exactly as a human closing an objection would
printf 'the plan after the owner sharpened it\n' > "$T6/cvg/swimlanes/core/_lane.md"
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q '^NEXT_PASS=4$' \
  && ok "a plan CHANGED after review reopens the barrier — consent does not transfer" \
  || bad "a post-review plan edit must stop next at 4 ($OUT)"
printf '%s' "$OUT" | grep -q '\[!\] pass 4' \
  && ok "and the board marks it [!], not [+]" \
  || bad "pass 4 must be [!] when provenance is stale"
printf '%s' "$OUT" | grep -q 'CHANGED after the adversary' \
  && ok "the remedy names the REAL cause (re-attack), not --resolve" \
  || bad "a stale-provenance barrier must not print the undecided-objection advice"
OUT="$(cd "$T6" && bash "$ENGINE" pre 7 2>&1)" || true
printf '%s' "$OUT" | grep -q '^PASS_PRE=MISSING$' \
  && ok "the pre-hook refuses pass 7 behind a stale barrier (fail-closed)" \
  || bad "pre 7 must refuse while provenance is stale ($OUT)"

# --- Pass 6's probe must read the VALUE, not the key. Every scaffolded spec carries
# `tracker_ref: (none)`, so matching the field's presence reported Register as done
# for a workspace with zero issues on any board. uc-01 showed [+] pass 6 that way.
printf -- '---\nstatus: ready\nsigned_off: true\ntracker_ref: (none)\n---\n' \
  > "$T6/cvg/tasks/T-20260803-x.md"
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q '\[+\] pass 6' \
  && bad "tracker_ref: (none) is the template placeholder — Register is NOT done" \
  || ok "tracker_ref: (none) does not count as Register (the placeholder is not a ref)"
printf -- '---\nstatus: ready\nsigned_off: true\ntracker_ref: linear:CVG-42\n---\n' \
  > "$T6/cvg/tasks/T-20260803-x.md"
OUT="$(cd "$T6" && bash "$ENGINE" next 2>&1)"
printf '%s' "$OUT" | grep -q '\[+\] pass 6' \
  && ok "a real tracker_ref does count as Register" \
  || bad "a genuine tracker_ref must register as pass 6 ($OUT)"
rm -rf "$T6"

run 2 bogus && printf '%s' "$OUT" | grep -q '^NEXT_PASS=USAGE_ERROR$' \
  && ok "unknown verb is a usage error (exit 2)" || bad "unknown verb must exit 2"
run 2 next --lane WARP && printf '%s' "$OUT" | grep -q '^NEXT_PASS=USAGE_ERROR$' \
  && ok "unknown lane is a usage error (exit 2)" || bad "unknown lane must exit 2"

echo "------------------------------------------------------------------"
echo "RESULTS: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
  echo "NEXT_PASS_TESTS=PASS"
else
  echo "NEXT_PASS_TESTS=FAIL"; exit 1
fi
