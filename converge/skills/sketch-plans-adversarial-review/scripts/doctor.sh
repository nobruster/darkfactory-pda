#!/usr/bin/env bash
# doctor.sh — cvg doctor: is the machine ready to dispatch a Pass 4 adversary?
# Per-engine PASS/SKIP (binary on PATH + version). Pass 4 needs >= 2 engines PASS
# with at least one CROSS-FAMILY (openai/moonshot/google), since the author is
# anthropic. Read-only; makes no LLM call. Token (last line): DOCTOR=OK|FAIL.
# bash 3.2-safe.
set -euo pipefail

# engine:family:env-override-var
ENGINES="codex:openai:CVG_CODEX_CMD kimi:moonshot:CVG_KIMI_CMD claude:anthropic:CVG_CLAUDE_CMD"

echo "== cvg doctor · Pass 4 adversary readiness =="
echo "author family: anthropic (a cross-family adversary is openai/moonshot/google)"
echo

PASS=0
XFAM=0
for spec in $ENGINES; do
  e="${spec%%:*}"; rest="${spec#*:}"; fam="${rest%%:*}"; var="${rest##*:}"
  cmd="${!var:-$e}"
  if command -v "$cmd" >/dev/null 2>&1; then
    ver="$("$cmd" --version 2>/dev/null | head -1 | tr -d '\n' | cut -c1-40 || true)"
    printf '  PASS  %-7s %-9s %s\n' "$e" "($fam)" "${ver:-installed}"
    PASS=$((PASS + 1))
    [ "$fam" != "anthropic" ] && XFAM=$((XFAM + 1))
  else
    printf '  SKIP  %-7s %-9s not installed (%s)\n' "$e" "($fam)" "$cmd"
  fi
done
echo
echo "engines ready: $PASS   cross-family: $XFAM"

if [ "$PASS" -ge 2 ] && [ "$XFAM" -ge 1 ]; then
  echo "READY — Pass 4 can dispatch a cross-family adversary (cvg review --adversary codex|kimi)."
  echo "DOCTOR=OK"; exit 0
else
  echo "NOT READY — need >= 2 engines and >= 1 cross-family (codex or kimi). Install one." >&2
  echo "DOCTOR=FAIL"; exit 1
fi
