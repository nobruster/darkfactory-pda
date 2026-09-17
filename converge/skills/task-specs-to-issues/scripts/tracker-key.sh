#!/usr/bin/env bash
# tracker-key.sh — resolve (or store) a tracker API key ONCE, outside the repo.
#
# THE PROBLEM THIS SOLVES
#   Re-exporting LINEAR_API_KEY in every shell is friction that eventually gets
#   "solved" the wrong way: someone pastes it into a committed file. Making the
#   safe path the easy path is the actual control here.
#
# THE RULE THAT DOES NOT CHANGE
#   The key never enters the repository. Not `.cvg/`, not the worktree, not a
#   dotfile the working tree can see. `.cvg/` records CHOICES (which tracker,
#   which team) and never CREDENTIALS. What changes is only WHERE outside the
#   repo the key may live, so you set it once instead of every session.
#
# RESOLUTION ORDER (first hit wins)
#   1. the environment            — CI, and anyone who prefers explicit
#   2. the OS secret store        — macOS Keychain, or secret-tool on Linux
#   3. ~/.config/converge/<t>.key — a 0600 fallback, outside the repo, gitignored
#                                   by virtue of not being in the repo at all
#
# Reading is silent and never prompts: an unattended loop must not block on a
# password dialog. If nothing resolves, callers degrade to local-only.
#
# Usage:
#   tracker-key.sh get linear                 print the key, or exit 1
#   tracker-key.sh set linear                 store it (reads stdin, never argv)
#   tracker-key.sh status linear              where it resolves from, no secret
#
# The key is deliberately NOT accepted as an argument — argv is visible in `ps`
# and lands in shell history.
#
# Bash 3.2 compatible (stock macOS).
set -uo pipefail

ACTION="${1:-status}"
TRACKER="${2:-linear}"

case "$TRACKER" in
  linear) ENV_VAR="LINEAR_API_KEY" ;;
  github) ENV_VAR="GITHUB_TOKEN" ;;
  jira)   ENV_VAR="JIRA_API_TOKEN" ;;
  *)      printf 'ERROR: unknown tracker %s\n' "$TRACKER" >&2; exit 2 ;;
esac

SERVICE="converge-$TRACKER"
FALLBACK="$HOME/.config/converge/$TRACKER.key"

_from_env()      { eval "printf '%s' \"\${$ENV_VAR:-}\""; }
_from_keychain() {
  command -v security >/dev/null 2>&1 || return 1
  security find-generic-password -s "$SERVICE" -a "$USER" -w 2>/dev/null
}
_from_secrettool() {
  command -v secret-tool >/dev/null 2>&1 || return 1
  secret-tool lookup service "$SERVICE" username "$USER" 2>/dev/null
}
_from_file() { [ -f "$FALLBACK" ] && cat "$FALLBACK" 2>/dev/null; }

resolve() {  # prints key + sets SOURCE; rc 1 when nothing resolves
  local v
  v="$(_from_env)";        [ -n "$v" ] && { SOURCE="environment ($ENV_VAR)"; printf '%s' "$v"; return 0; }
  v="$(_from_keychain)";   [ -n "$v" ] && { SOURCE="macOS Keychain ($SERVICE)"; printf '%s' "$v"; return 0; }
  v="$(_from_secrettool)"; [ -n "$v" ] && { SOURCE="secret-tool ($SERVICE)"; printf '%s' "$v"; return 0; }
  v="$(_from_file)";       [ -n "$v" ] && { SOURCE="$FALLBACK"; printf '%s' "$v"; return 0; }
  SOURCE=""
  return 1
}

case "$ACTION" in
  get)
    resolve || exit 1
    ;;

  set)
    # stdin only — argv is visible in `ps` and lands in shell history.
    if [ -t 0 ]; then
      printf 'Paste the %s API key (input hidden), then Enter:\n' "$TRACKER" >&2
      stty -echo 2>/dev/null; IFS= read -r KEY; stty echo 2>/dev/null; printf '\n' >&2
    else
      IFS= read -r KEY
    fi
    [ -n "${KEY:-}" ] || { printf 'ERROR: empty key, nothing stored\n' >&2; exit 2; }

    if command -v security >/dev/null 2>&1; then
      security delete-generic-password -s "$SERVICE" -a "$USER" >/dev/null 2>&1 || true
      if security add-generic-password -s "$SERVICE" -a "$USER" -w "$KEY" -U >/dev/null 2>&1; then
        printf 'stored in the macOS Keychain as %s (never in the repo)\n' "$SERVICE"
        printf 'TRACKER_KEY=STORED\n'; exit 0
      fi
    fi
    if command -v secret-tool >/dev/null 2>&1; then
      if printf '%s' "$KEY" | secret-tool store --label="converge $TRACKER" \
           service "$SERVICE" username "$USER" >/dev/null 2>&1; then
        printf 'stored via secret-tool as %s (never in the repo)\n' "$SERVICE"
        printf 'TRACKER_KEY=STORED\n'; exit 0
      fi
    fi
    mkdir -p "$(dirname "$FALLBACK")" 2>/dev/null
    ( umask 077; printf '%s' "$KEY" > "$FALLBACK" )
    chmod 600 "$FALLBACK" 2>/dev/null
    printf 'no OS secret store available — stored 0600 at %s\n' "$FALLBACK"
    printf 'This is outside the repository and cannot be committed.\n'
    printf 'TRACKER_KEY=STORED\n'
    ;;

  status)
    if resolve >/dev/null; then
      printf '%s key: resolves from %s\n' "$TRACKER" "$SOURCE"
      printf 'TRACKER_KEY=OK\n'
    else
      printf '%s key: not found.\n' "$TRACKER"
      printf '  store it once:  cvg setup key %s\n' "$TRACKER"
      printf '  or export %s for this shell only\n' "$ENV_VAR"
      printf 'TRACKER_KEY=ABSENT\n'
      exit 1
    fi
    ;;

  *)
    printf 'usage: tracker-key.sh get|set|status [linear|github|jira]\n' >&2
    exit 2
    ;;
esac
