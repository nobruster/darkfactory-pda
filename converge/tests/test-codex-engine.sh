#!/usr/bin/env bash
# A provider child that outlives `codex exec` must not hold the loop open.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTER="$ROOT/skills/task-loop/scripts/engines/codex.sh"
ROOM="$(mktemp -d -t cvg-codex-engine-test.XXXXXX)"
trap 'rm -rf "$ROOM"' EXIT

cat > "$ROOM/fake-codex" <<'FAKE'
#!/usr/bin/env bash
( sleep 3 ) &
printf 'FAKE_CODEX=COMPLETE\n'
exit 0
FAKE
chmod +x "$ROOM/fake-codex"
printf 'Implement the fixture.\n' > "$ROOM/prompt.md"

started="$(date +%s)"
output="$(CVG_CODEX_CMD="$ROOM/fake-codex" bash "$ADAPTER" \
  --prompt-file "$ROOM/prompt.md" --workdir "$ROOM" --timeout 10 2>&1)"
rc=$?
elapsed=$(( $(date +%s) - started ))

if [ "$rc" -eq 0 ] \
  && [ "$elapsed" -lt 2 ] \
  && printf '%s\n' "$output" | grep -q '^FAKE_CODEX=COMPLETE$'; then
  printf 'CODEX_ENGINE_PIPE=PASS elapsed=%ss\n' "$elapsed"
  exit 0
fi

printf 'CODEX_ENGINE_PIPE=FAIL rc=%s elapsed=%ss output=%s\n' \
  "$rc" "$elapsed" "$output" >&2
exit 1
