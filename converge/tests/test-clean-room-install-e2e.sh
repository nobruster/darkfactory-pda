#!/usr/bin/env bash
# Prove the v0.2.0 experience from a stranger's empty Git repository.
# No installed file may depend on this source checkout after install.

set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$HERE/.." && pwd)"
ROOM="$(mktemp -d -t cvg-clean-room.XXXXXX)"
STUBS="$(mktemp -d -t cvg-clean-stubs.XXXXXX)"
SAFETY_ROOM="$(mktemp -d -t cvg-clean-safety.XXXXXX)"
PASS=0
FAIL=0

cleanup() {
  rm -rf "$ROOM" "$STUBS" "$SAFETY_ROOM"
}
trap cleanup EXIT

ok()  { PASS=$((PASS + 1)); printf '  ok   — %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  FAIL — %s\n' "$1" >&2; }
run_cvg() {
  (
    cd "$ROOM" || exit 1
    env -u CVG_HOME -u CVG_PROJECT_ROOT "$ROOM/bin/cvg" "$@"
  )
}
file_mode() {
  # GNU first: on Linux, BSD-style `stat -f` is FILESYSTEM status and exits 0
  # with the wrong answer, so it must be the fallback, never the first try.
  stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null || true
}

echo "=================================================================="
echo "v0.2.0 clean-room install → init → task → receipt → done"
echo "=================================================================="

git -C "$ROOM" init --quiet
git -C "$ROOM" config user.email clean-room@example.invalid
git -C "$ROOM" config user.name "Converge Clean Room"

INSTALL_OUT="$(bash "$SRC/install.sh" --target "$ROOM" --bin-dir "$ROOM/bin" 2>&1)"
INSTALL_RC=$?
if [ "$INSTALL_RC" -eq 0 ] && printf '%s\n' "$INSTALL_OUT" | grep -q '^INSTALL=OK$'; then
  ok "default install succeeds in pinned copy mode"
else
  bad "installer failed: $INSTALL_OUT"
fi

EXPECTED="$(find "$SRC/skills" -maxdepth 2 -name SKILL.md ! -path '*/task-spec/SKILL.md' | wc -l | tr -d ' ')"
AGENT_COUNT="$(find "$ROOM/.agents/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')"
CLAUDE_COUNT="$(find "$ROOM/.claude/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ')"
if [ "$AGENT_COUNT" = "$EXPECTED" ] && [ "$CLAUDE_COUNT" = "$EXPECTED" ]; then
  ok "Codex/Kimi shared skills and Claude Code skills are complete"
else
  bad "skill projections disagree (expected=$EXPECTED agents=$AGENT_COUNT claude=$CLAUDE_COUNT)"
fi

LINKS="$(find "$ROOM/bin" "$ROOM/.agents/skills" "$ROOM/.claude/skills" -type l -print)"
if [ -z "$LINKS" ] && [ -f "$ROOM/bin/cvg" ] && [ -f "$ROOM/bin/.cvg-ui.sh" ] \
  && [ -f "$ROOM/.agents/bin/_cvg_compose.py" ] \
  && [ -f "$ROOM/.agents/contracts/cli-command-matrix.json" ]; then
  ok "pinned install contains no source-checkout symlinks"
else
  bad "copy install still contains symlinks or an incomplete CLI: $LINKS"
fi

VERSION_OUT="$(run_cvg version 2>&1)"
if printf '%s\n' "$VERSION_OUT" | grep -Fq "tool: $ROOM/.agents" \
  && ! printf '%s\n' "$VERSION_OUT" | grep -Fq "tool: $SRC"; then
  ok "copied CLI discovers the consuming project's installed tool home"
else
  bad "copied CLI resolved the wrong tool package: $VERSION_OUT"
fi

INIT_ONE="$(run_cvg init 2>&1)"
INIT_TWO="$(run_cvg init 2>&1)"
if printf '%s\n' "$INIT_ONE" | grep -q '^CVG_INIT=OK$' \
  && printf '%s\n' "$INIT_TWO" | grep -q '^CVG_INIT=UNCHANGED$'; then
  ok "cvg init is non-clobbering and idempotent"
else
  bad "cvg init tokens were not OK then UNCHANGED"
fi

MISSING=""
for path in \
  .cvg/gate.yaml cvg/INDEX.md cvg/brain cvg/docs cvg/swimlanes cvg/tasks \
  cvg/tasks/done cvg/tasks/parked cvg/tasks/_state.yaml \
  cvg/tasks/_metrics.jsonl cvg/execution cvg/loop cvg/receipts; do
  [ -e "$ROOM/$path" ] || MISSING="$MISSING $path"
done
if [ -z "$MISSING" ]; then
  ok "canonical .cvg/ policy and cvg/ control plane are complete"
else
  bad "initializer missed:$MISSING"
fi

git -C "$SAFETY_ROOM" init --quiet
mkdir -p "$SAFETY_ROOM/redirect"
ln -s redirect "$SAFETY_ROOM/cvg"
UNSAFE_INIT="$(
  CVG_HOME="$ROOM/.agents" CVG_PROJECT_ROOT="$SAFETY_ROOM" \
    "$ROOM/bin/cvg" init 2>&1 || true
)"
if printf '%s\n' "$UNSAFE_INIT" | grep -q '^CVG_INIT=UNSAFE_PATH$' \
  && [ ! -e "$SAFETY_ROOM/redirect/INDEX.md" ]; then
  ok "initializer refuses symlinked control-plane paths without touching targets"
else
  bad "initializer followed or failed to classify a symlinked workspace"
fi

NON_GIT="$(mktemp -d -t cvg-clean-nongit.XXXXXX)"
NON_GIT_SIGN="$(
  CVG_HOME="$ROOM/.agents" CVG_PROJECT_ROOT="$NON_GIT" \
    "$ROOM/bin/cvg" setup signing 2>&1 || true
)"
if printf '%s\n' "$NON_GIT_SIGN" | grep -q '^SETUP_SIGNING=NOT_GIT$'; then
  ok "signing setup refuses a non-Git project instead of reporting false success"
else
  bad "signing setup did not fail closed outside Git"
fi
rm -rf "$NON_GIT"

GATE_OUT="$(run_cvg gate 2>&1)"
if printf '%s\n' "$GATE_OUT" | grep -q '^CHECK_GATE=OK$'; then
  ok "fresh repository write fence parses and is active"
else
  bad "fresh gate is not valid: $GATE_OUT"
fi

SIGN_ONE="$(run_cvg setup signing 2>&1)"
SIGN_TWO="$(run_cvg setup signing 2>&1)"
KEY="$ROOM/.git/info/taskspec-signing-key"
if printf '%s\n' "$SIGN_ONE" | grep -q '^SETUP_SIGNING=OK$' \
  && printf '%s\n' "$SIGN_TWO" | grep -q '^SETUP_SIGNING=UNCHANGED$' \
  && [ "$(file_mode "$KEY")" = "600" ]; then
  ok "signing setup is idempotent, Git-private, and mode 0600"
else
  bad "signing setup or permissions failed"
fi

SETUP_OUT="$(run_cvg setup 2>&1 || true)"
if printf '%s\n' "$SETUP_OUT" | grep -q 'workspace canonical' \
  && printf '%s\n' "$SETUP_OUT" | grep -q 'Tier-1 Task-Spec key provisioned'; then
  ok "setup reports workspace and signing readiness"
else
  bad "setup does not understand the initialized project: $SETUP_OUT"
fi

NEW_OUT="$(run_cvg tasks new path-proof XS any clean-room 2>&1)"
PATH_TASK="$(printf '%s\n' "$NEW_OUT" | sed -n 's/^Spec written: //p' | tail -1)"
PATH_ID="$(basename "$PATH_TASK" .md)"
if [ -f "$PATH_TASK" ] && [ ! -d "$ROOM/tasks" ]; then
  ok "task creation writes only to canonical cvg/tasks"
else
  bad "task creation produced a split root tasks backlog: $NEW_OUT"
fi
run_cvg transition "$PATH_ID" parked "clean-room path proof" >/dev/null 2>&1 || \
  bad "generated path-proof task could not be parked"
# The generated file intentionally still contains TODOs. Task-Spec 3.8 scans the
# complete lifecycle graph and correctly refuses an invalid parked node, so keep
# this path-only probe out of the real acceptance backlog.
rm -f "$ROOM/cvg/tasks/parked/$PATH_ID.md"
run_cvg tasks rebuild-state >/dev/null

printf '# clean-room readme\n' > "$ROOM/README.md"
SPEC_ID="T-20260602-golden"
SPEC="cvg/tasks/$SPEC_ID.md"
cp "$SRC/tests/fixtures/$SPEC_ID.md" "$ROOM/$SPEC"
git -C "$ROOM" add -A
git -C "$ROOM" commit --quiet -m "clean-room authorized baseline"

GATE_TASK_OUT="$(run_cvg tasks gate --stamp --stamp-by clean-room "$SPEC" 2>&1)"
if printf '%s\n' "$GATE_TASK_OUT" | grep -q '^TIER=1$'; then
  ok "installed task gate seals a Tier-1 Task-Spec"
else
  bad "installed task gate did not reach Tier 1: $GATE_TASK_OUT"
fi
git -C "$ROOM" add -A
git -C "$ROOM" commit --quiet -m "seal clean-room task"

BIND_OUT="$(run_cvg bind --task "$SPEC" 2>&1)"
if printf '%s\n' "$BIND_OUT" | grep -q '^CHECK_RUNTIME_CONTRACT=PASS$'; then
  ok "installed binder writes and verifies the execution profile"
else
  bad "runtime binding failed: $BIND_OUT"
fi
git -C "$ROOM" add -A
git -C "$ROOM" commit --quiet -m "bind clean-room execution policy"

printf 'NEVERMATCH\n' >> "$ROOM/README.md"
git -C "$ROOM" add README.md
git -C "$ROOM" commit --quiet -m "make task deterministically red"

cat > "$STUBS/cleanfix.sh" <<'STUB'
#!/usr/bin/env bash
set -uo pipefail
case "${1:-}" in --available) exit 0 ;; esac
sed -i.bak '/NEVERMATCH/d' README.md 2>/dev/null || true
rm -f README.md.bak
echo "clean-room stub fixed README.md"
STUB
chmod +x "$STUBS/cleanfix.sh"

LOOP_OUT="$(
  cd "$ROOM" && env -u CVG_HOME -u CVG_PROJECT_ROOT \
    PYTHONDONTWRITEBYTECODE=1 CVG_ENGINES_DIR="$STUBS" \
    "$ROOM/bin/cvg" loop --issue "$SPEC_ID" --agent cleanfix --isolation inplace 2>&1
)"
LOOP_RC=$?
if [ "$LOOP_RC" -eq 0 ] \
  && printf '%s\n' "$LOOP_OUT" | grep -qE '^TASK_LOOP=(SETTLED|LOCAL_SETTLED)$' \
  && grep -q '"result": *"pass"' "$ROOM/cvg/receipts/$SPEC_ID.json"; then
  ok "stub-engine loop turns RED green and writes a passing receipt"
else
  bad "clean-room loop did not settle: $LOOP_OUT"
fi

ACCEPTANCE_RECORD="$(find "$ROOM/cvg/.taskspec/acceptance/$SPEC_ID" -type f -name '*.json' -print 2>/dev/null | head -1)"
if grep -q '^accepted: true$' "$ROOM/$SPEC" \
  && [ -f "$ACCEPTANCE_RECORD" ] \
  && printf '%s\n' "$LOOP_OUT" | grep -q '^ACCEPTED=1$'; then
  ok "loop performs protected Task-Spec acceptance before settlement"
else
  bad "loop did not persist Task-Spec acceptance: $LOOP_OUT"
fi

DONE_OUT="$(run_cvg transition "$SPEC_ID" done "clean-room settlement" 2>&1)"
DONE_SPEC="$ROOM/cvg/tasks/done/$SPEC_ID.md"
if [ -f "$DONE_SPEC" ] && printf '%s\n' "$DONE_OUT" | grep -q "$SPEC_ID: ready -> done"; then
  ok "accepted task with a passing receipt moves atomically to done"
else
  bad "settled task did not move to done: $DONE_OUT"
fi

DONE_VALIDATE="$(run_cvg tasks validate --no-state "cvg/tasks/done/$SPEC_ID.md" 2>&1)"
if printf '%s\n' "$DONE_VALIDATE" | grep -q '^OK:' \
  && grep -q '^accepted: true$' "$DONE_SPEC"; then
  ok "done Task-Spec validates with its acceptance envelope"
else
  bad "done Task-Spec is not self-consistent: $DONE_VALIDATE"
fi

if python3 - "$ROOM" "$SPEC_ID" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
task_id = sys.argv[2]
receipt_path = root / "cvg" / "receipts" / f"{task_id}.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
profile_path = root / receipt["execution_profile"]["path"]
assert receipt["result"] == "pass"
assert receipt["task_id"] == task_id
assert hashlib.sha256(profile_path.read_bytes()).hexdigest() == receipt["execution_profile"]["sha256"]

events = [
    json.loads(line)
    for line in (root / "cvg/tasks/_metrics.jsonl").read_text(encoding="utf-8").splitlines()
    if line
]
assert any(row.get("event") == "created" for row in events)
assert any(row.get("task") == task_id and row.get("event") == "accepted" for row in events)
assert any(
    row.get("task") == task_id
    and row.get("event") == "status_change"
    and row.get("to") == "done"
    for row in events
)
PY
then
  ok "receipt hash chain and lifecycle event ledger agree"
else
  bad "receipt hashes or JSONL lifecycle events disagree"
fi

TASKSPEC_REBUILD_BIN="${TASKSPEC_BIN:-${CVG_TASKSPEC_BIN:-taskspec}}"
TASKSPEC_BACKLOG_DIR="$ROOM/cvg/tasks" "$TASKSPEC_REBUILD_BIN" rebuild-state >/dev/null
STATE_ONE="$(shasum -a 256 "$ROOM/cvg/tasks/_state.yaml" | awk '{print $1}')"
TASKSPEC_BACKLOG_DIR="$ROOM/cvg/tasks" "$TASKSPEC_REBUILD_BIN" rebuild-state >/dev/null
STATE_TWO="$(shasum -a 256 "$ROOM/cvg/tasks/_state.yaml" | awk '{print $1}')"
if [ "$STATE_ONE" = "$STATE_TWO" ] \
  && grep -q "path: tasks/done/$SPEC_ID.md" "$ROOM/cvg/tasks/_state.yaml" \
  && grep -q 'done: 1' "$ROOM/cvg/tasks/_state.yaml" \
  && grep -q 'parked: 0' "$ROOM/cvg/tasks/_state.yaml"; then
  ok "derived state is deterministic, relative, and complete"
else
  bad "derived state is not reproducible or disagrees with task frontmatter"
fi

SOURCE_REFS="$(grep -R -l -F "$SRC" "$ROOM/bin" "$ROOM/.agents/skills" "$ROOM/.claude/skills" 2>/dev/null || true)"
if [ -z "$SOURCE_REFS" ]; then
  ok "installed tool surface contains no source-checkout path"
else
  bad "installed files retain source checkout references: $SOURCE_REFS"
fi

echo "------------------------------------------------------------------"
if [ "$FAIL" -eq 0 ]; then
  printf 'CLEAN_ROOM_E2E=PASS checks=%s\n' "$PASS"
  exit 0
fi
printf 'CLEAN_ROOM_E2E=FAIL failed=%s total=%s\n' "$FAIL" "$((PASS + FAIL))" >&2
exit 1
