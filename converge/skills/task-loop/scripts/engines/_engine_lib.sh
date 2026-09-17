#!/usr/bin/env bash
# _engine_lib.sh — shared contract for Pass 8 execution engines.
#
# An engine adapter is the ONLY place that knows how a particular CLI is spelled.
# The loop kernel knows nothing about any vendor; it calls this contract:
#
#   bash engines/<name>.sh --available
#       exit 0 if the engine can actually run on this host. Nothing else.
#
#   bash engines/<name>.sh --prompt-file F --workdir D [--timeout SECONDS]
#                          [--model TIER] [--effort LEVEL]
#       run ONE attempt with a FRESH context, cwd = workdir. The transcript goes
#       to stdout. If the engine reports usage, the adapter emits one line
#       `ENGINE_TOKENS=<n>` so the kernel can debit its token budget.
#
#   --model is a FAMILY-NEUTRAL TIER — haiku | sonnet | opus — never a vendor
#   model id. Translating a tier into whatever this CLI actually calls it is the
#   adapter's whole job, for the same reason the kernel spells no vendor: the
#   kernel asks for "the cheap one" and each adapter knows its own spelling. An
#   adapter that cannot honour a tier ignores it rather than failing; a run that
#   dies because one engine renamed a model is worse than a run on the default.
#
# WHY EACH ATTEMPT IS A NEW PROCESS
#   A retry inside one session re-reads every prior failure, so cost grows
#   quadratically while attention degrades — and content pushed deep into a long
#   context is attended to least. A fresh process per attempt keeps each
#   iteration flat and forces state to live on disk, where it can be reviewed.
#
# WHY THE TIMEOUT IS NOT OPTIONAL
#   A hung engine must not hang the loop. This was observed live in Pass 4:
#   `codex exec` blocking at 0% CPU on a model round-trip. macOS ships neither
#   timeout(1) nor gtimeout, so a pure-bash watchdog enforces the same cap with
#   zero dependencies. A timeout normalizes to exit 124, the way timeout(1) does.
#
# Bash 3.2 compatible (stock macOS).

ENGINE_TIMEOUT="${ENGINE_TIMEOUT:-900}"

_eng_timeout_bin=""
if command -v timeout >/dev/null 2>&1; then _eng_timeout_bin="timeout"
elif command -v gtimeout >/dev/null 2>&1; then _eng_timeout_bin="gtimeout"; fi

# to <seconds> <cmd...> — run under a hard wall-clock cap; 124 on timeout.
to() {
  _to_secs="$1"; shift
  if [ -n "$_eng_timeout_bin" ]; then "$_eng_timeout_bin" "$_to_secs" "$@"; return $?; fi
  _to_flag="$(mktemp)"; _to_rc=0
  # Preserve stdin across the backgrounding. Bash redirects a background job's
  # stdin from /dev/null, so `to ... < prompt` silently delivers NOTHING — the
  # engine then reports "no prompt provided" and the loop records a failed
  # attempt whose real cause is the watchdog, not the model. Duplicating the
  # caller's stdin onto FD 3 and handing that to the job keeps the redirect
  # intact whichever timeout mechanism is in play.
  exec 3<&0
  "$@" <&3 &
  _to_pid=$!
  exec 3<&-
  ( sleep "$_to_secs"
    if kill -0 "$_to_pid" 2>/dev/null; then
      printf T > "$_to_flag"; kill -TERM "$_to_pid" 2>/dev/null
      sleep 2; kill -KILL "$_to_pid" 2>/dev/null
    fi ) &
  _to_wd=$!
  wait "$_to_pid" 2>/dev/null || _to_rc=$?
  kill "$_to_wd" 2>/dev/null || true; wait "$_to_wd" 2>/dev/null || true
  if [ -s "$_to_flag" ]; then rm -f "$_to_flag"; return 124; fi
  rm -f "$_to_flag"; return "$_to_rc"
}

# Parse the uniform adapter arguments into ENG_* variables.
#
# SC2034: ENG_MODEL and ENG_EFFORT are set here and read by the ADAPTER that
# sources this file, never inside it. That is the whole point of the split — the
# lib owns the contract, the adapter owns the vendor spelling — so "unused" is
# correct within this file and wrong about the program.
# shellcheck disable=SC2034
eng_parse_args() {
  ENG_MODE="run"; ENG_PROMPT=""; ENG_WORKDIR="$PWD"; ENG_TIMEOUT="$ENGINE_TIMEOUT"
  ENG_MODEL=""; ENG_EFFORT=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --available)     ENG_MODE="available"; shift ;;
      --prompt-file)   ENG_PROMPT="${2:?--prompt-file requires a path}"; shift 2 ;;
      --prompt-file=*) ENG_PROMPT="${1#--prompt-file=}"; shift ;;
      --workdir)       ENG_WORKDIR="${2:?--workdir requires a path}"; shift 2 ;;
      --workdir=*)     ENG_WORKDIR="${1#--workdir=}"; shift ;;
      --timeout)       ENG_TIMEOUT="${2:?--timeout requires seconds}"; shift 2 ;;
      --timeout=*)     ENG_TIMEOUT="${1#--timeout=}"; shift ;;
      --model)         ENG_MODEL="${2:?--model requires a tier}"; shift 2 ;;
      --model=*)       ENG_MODEL="${1#--model=}"; shift ;;
      --effort)        ENG_EFFORT="${2:?--effort requires a level}"; shift 2 ;;
      --effort=*)      ENG_EFFORT="${1#--effort=}"; shift ;;
      # An UNKNOWN argument still fails loudly — the contract is a contract. But
      # an unsupported VALUE for a known argument is ignored by the adapter, so
      # a renamed model tier degrades to the default instead of killing the run.
      *) printf 'ERROR: unknown engine argument %s\n' "$1" >&2; exit 2 ;;
    esac
  done
  if [ "$ENG_MODE" = "run" ]; then
    [ -n "$ENG_PROMPT" ] && [ -f "$ENG_PROMPT" ] || {
      printf 'ERROR: --prompt-file is required and must exist\n' >&2; exit 2; }
    [ -d "$ENG_WORKDIR" ] || { printf 'ERROR: --workdir does not exist\n' >&2; exit 2; }
  fi
}

# Report a timeout the same way for every engine so the kernel needs no special
# cases, and so a hang is never mistaken for a clean empty attempt.
eng_finish() {
  _rc="$1"
  if [ "$_rc" -eq 124 ]; then
    printf '\n[engine timed out after %ss — the attempt was killed]\n' "$ENG_TIMEOUT"
    return 124
  fi
  return "$_rc"
}
