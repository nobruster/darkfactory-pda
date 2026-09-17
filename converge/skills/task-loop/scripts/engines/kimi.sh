#!/usr/bin/env bash
# kimi.sh — Pass 8 execution engine: Kimi CLI, headless.
#
# Kimi is the cross-family option. It matters for Pass 8 for the same reason it
# matters at Pass 4: when the maker and the checker share a model family, the
# grade drifts up while quality does not. Running the loop on kimi and the
# tier-2 judge on claude (or the reverse) makes the separation real rather than
# nominal.
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_engine_lib.sh"
eng_parse_args "$@"

CMD="${CVG_KIMI_CMD:-kimi}"
[ "$ENG_MODE" = "available" ] && { command -v "$CMD" >/dev/null 2>&1; exit $?; }

RC=0
cd "$ENG_WORKDIR" || exit 4
# Kimi exposes one family with a turbo/standard split, so the three tiers
# collapse onto two. Collapsing is honest; inventing a third id would not be.
ENG_ARGS=()
case "$ENG_MODEL" in
  haiku)         ENG_ARGS+=(--model kimi-k2-turbo-preview) ;;
  sonnet|opus)   ENG_ARGS+=(--model kimi-k2-0905-preview) ;;
  *)             : ;;
esac

to "$ENG_TIMEOUT" "$CMD" --output-format text \
  "${ENG_ARGS[@]+"${ENG_ARGS[@]}"}" -p "$(cat "$ENG_PROMPT")" </dev/null 2>&1 || RC=$?

eng_finish "$RC"
