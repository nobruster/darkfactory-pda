#!/usr/bin/env bash
# Prove `cvg tasks plan` is a byte-transparent Task-Spec delegation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CVG="$ROOT/bin/cvg"
ROOM="$(mktemp -d -t cvg-tasks-plan.XXXXXX)"
trap 'rm -rf "$ROOM"' EXIT
STUB="$ROOM/taskspec"
ARGS="$ROOM/args"

cat > "$STUB" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = version ]; then
  printf '3.8.0\n'
  exit 0
fi
printf '%s\n' "$@" > "$TASKSPEC_STUB_ARGS"
printf 'TASK_PLAN=OK\n'
exit 0
STUB
chmod +x "$STUB"

OUT="$(
  cd "$ROOM" || exit 1
  CVG_HOME="$ROOT" CVG_PROJECT_ROOT="$ROOM" \
    CVG_TASKSPEC_BIN="$STUB" TASKSPEC_STUB_ARGS="$ARGS" \
    "$CVG" tasks plan --manifest seamwise/task-plan.json
)"
RC=$?

test "$RC" -eq 0
test "$OUT" = "TASK_PLAN=OK"
test "$(sed -n '1p' "$ARGS")" = "plan"
test "$(sed -n '2p' "$ARGS")" = "--manifest"
test "$(sed -n '3p' "$ARGS")" = "seamwise/task-plan.json"
test "$(wc -l < "$ARGS" | tr -d ' ')" -eq 3

if grep -R -n -E "cvg-plan-tasks|Yields at Pass 5B" "$ROOT/bin" "$ROOT/package.json" >/dev/null; then
  echo "Converge still packages an internal task planner" >&2
  echo "TASKS_PLAN_TESTS=FAIL"
  exit 1
fi

echo "TASKS_PLAN_TESTS=PASS"
