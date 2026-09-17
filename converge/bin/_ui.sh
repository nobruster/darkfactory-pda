#!/usr/bin/env bash
# _ui.sh — cvg's shared presentation layer (sourced, never executed).
#
# The dep-free floor of the UX contract (cvg-todo.md R1.I; field research in
# temp/cli-ux-research-2026-07-19.md). Rules encoded here, verified against
# clig.dev / no-color.org / gh's design system:
#   - color only when stdout is an interactive TTY
#   - NO_COLOR set non-empty disables color (value ignored)
#   - CVG_COLOR=0 forces off, CVG_COLOR=1 forces on (flags/env > NO_COLOR)
#   - only the 8 basic ANSI colors — the universally reliable palette
#   - color enhances meaning, never carries it: every state is also a word
#
# Wrapped subcommand output NEVER passes through here — pass-through purity
# (byte parity with the underlying script) is eval-guarded.
#
# Portability: macOS system bash 3.2. No associative arrays, no ${var,,}.

# cvg_ui_init — decide color once, define the style vars.
# UI_GREEN/UI_YELLOW are part of the shared palette contract (stage strip,
# gate verdicts) even before every consumer exists.
# shellcheck disable=SC2034
cvg_ui_init() {
  local on=0
  if [ -t 1 ]; then on=1; fi
  if [ -n "${NO_COLOR:-}" ]; then on=0; fi
  case "${CVG_COLOR:-}" in
    0) on=0 ;;
    1) on=1 ;;
  esac

  if [ "$on" -eq 1 ]; then
    UI_RESET=$'\033[0m'
    UI_BOLD=$'\033[1m'
    UI_DIM=$'\033[2m'
    UI_CYAN=$'\033[36m'
    UI_GREEN=$'\033[32m'
    UI_YELLOW=$'\033[33m'
    UI_RED=$'\033[31m'
  else
    UI_RESET=''
    UI_BOLD=''
    UI_DIM=''
    UI_CYAN=''
    UI_GREEN=''
    UI_YELLOW=''
    UI_RED=''
  fi
}

# ui_rule — a horizontal rule matching the gate scripts' visual language.
ui_rule() {
  printf '%s────────────────────────────────────────────────────────%s\n' \
    "$UI_DIM" "$UI_RESET"
}

# ui_err <msg> — human-first error to stderr; most important info last
# stays the caller's job (clig.dev: rewrite errors for humans, red sparingly).
ui_err() {
  printf '%serror:%s %s\n' "$UI_RED" "$UI_RESET" "$*" >&2
}

cvg_ui_init
