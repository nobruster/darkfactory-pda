#!/usr/bin/env bash
# dispatch-review.sh — Converge Pass 4: frame → dispatch a headless adversary →
# stamp the objection log. The referee is never a player: it shells out to the
# engine's OWN CLI (which authenticates itself), read-only, wrapped in a timeout.
# PROVENANCE (adversary family + input hashes) is computed HERE, not self-reported
# by the engine — so it cannot be spoofed. Fail-closed: any failure => ERROR,
# never a pass.
#
# Usage:
#   dispatch-review.sh --adversary codex|kimi|claude [--dir sketch] [--out F]
#   dispatch-review.sh --help
# Engine command is env-overridable for testing: CVG_CODEX_CMD / CVG_KIMI_CMD /
#   CVG_CLAUDE_CMD (default: the bare binary). CVG_TIMEOUT_SECS (default 300).
#
# Token (last line): REVIEW=OK | ERROR | SKIP | TIMEOUT | USAGE_ERROR
# Exit: 0 ok · 20 engine unavailable(SKIP) · 21 timeout · 22 malformed(ERROR) · 2 usage
# bash 3.2-safe; Python stdlib-only (json/hashlib) for assembly. No jq.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PLAYBOOK="$HERE/../references/attack-playbook.md"
# The swimlane tree: canonical cvg/swimlanes/, legacy cvg/swimlanes/ (or a bare
# swimlanes/). Preference is by CONTENT, not existence — `cvg init` may have created
# an empty swimlanes/ beside a populated legacy swimlanes/, and picking the empty one
# would answer EMPTY and drop this workspace's Pass 3 evidence.
_lane_tree() {
  local c
  for c in swimlanes sketch; do
    if [ -d "$c" ] && [ -n "$(find "$c" -mindepth 2 -type f -name '*.md' -print 2>/dev/null | head -1)" ]; then
      printf '%s' "$c"; return 0
    fi
  done
  for c in swimlanes sketch; do
    if [ -d "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  printf 'swimlanes'
}
SKETCH_DIR="$(_lane_tree)"
ADVERSARY="codex"
AUTHOR_FAMILY="anthropic"
OUT=""
TIMEOUT="${CVG_TIMEOUT_SECS:-300}"

usage() { sed -n '2,20p' "$0"; }
uerr() { echo "ERROR: $*" >&2; echo "REVIEW=USAGE_ERROR"; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h)       usage; exit 0 ;;
    --adversary)     ADVERSARY="${2:?}"; shift 2 ;;
    --dir)           SKETCH_DIR="${2:?}"; shift 2 ;;
    --out)           OUT="${2:?}"; shift 2 ;;
    --author-family) AUTHOR_FAMILY="${2:?}"; shift 2 ;;
    --timeout)       TIMEOUT="${2:?}"; shift 2 ;;
    -*)              uerr "unknown option: $1" ;;
    *)               SKETCH_DIR="$1"; shift ;;
  esac
done
[ -n "$OUT" ] || OUT="$SKETCH_DIR/.consensus/objection-log.json"

case "$ADVERSARY" in
  codex)  FAMILY=openai;    CMD="${CVG_CODEX_CMD:-codex}";   KIND=codex ;;
  kimi)   FAMILY=moonshot;  CMD="${CVG_KIMI_CMD:-kimi}";     KIND=kimi ;;
  claude) FAMILY=anthropic; CMD="${CVG_CLAUDE_CMD:-claude}"; KIND=claude ;;
  *) uerr "unknown adversary '$ADVERSARY' (codex|kimi|claude)" ;;
esac

[ -d "$SKETCH_DIR" ] || uerr "no swimlane tree at $SKETCH_DIR/"
if [ "$FAMILY" = "$AUTHOR_FAMILY" ]; then
  echo "WARN: adversary '$ADVERSARY' is the SAME family as the author ($AUTHOR_FAMILY) — weak (self-preference). Prefer codex or kimi." >&2
fi
if ! command -v "$CMD" >/dev/null 2>&1; then
  echo "SKIP: adversary engine '$ADVERSARY' ($CMD) is not installed — try another --adversary or run cvg doctor." >&2
  echo "REVIEW=SKIP"; exit 20
fi

# ── FRAME: the critic prompt = the playbook + every plan file ─────────────────
PROMPT="$(mktemp)"; JUDG="$(mktemp)"
trap 'rm -f "$PROMPT" "$JUDG"' EXIT
{
  cat "$PLAYBOOK" 2>/dev/null || true
  echo; echo "=== PLANS TO ATTACK (swimlanes/<seam>/) ==="
  # Any non-dot subdir is a lane (.consensus/ holds the log, not plans). Matching
  # on "swimlane-*" would silently attack nothing once the prefix was dropped.
  for f in "$SKETCH_DIR"/*/*.md; do
    [ -e "$f" ] || continue
    case "$(basename "$(dirname "$f")")" in .*) continue ;; esac
    echo; echo "----- $f -----"; cat "$f"
  done
} > "$PROMPT"

# ── DISPATCH: headless, read-only, wrapped in a wall-clock cap ────────────────
# The mandatory-timeout invariant is NON-negotiable: a hung engine (observed live
# — codex exec blocking at 0% CPU on the model round-trip) must not hang the
# referee forever. timeout(1) is GNU coreutils and macOS ships neither timeout nor
# gtimeout, so we cannot depend on them. If present we use them; otherwise a pure-
# bash watchdog enforces the SAME cap with zero dependencies (rule 5). Either way a
# timeout normalizes to exit 124 → REVIEW=TIMEOUT (fail-closed). bash 3.2-safe.
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then TIMEOUT_BIN="gtimeout"; fi
to() {
  if [ -n "$TIMEOUT_BIN" ]; then "$TIMEOUT_BIN" "$TIMEOUT" "$@"; return $?; fi
  # pure-bash watchdog: background the engine; a sibling sleeper TERM/KILLs it if it
  # outlives $TIMEOUT, leaving a marker so we can report 124 like timeout(1) does.
  local flag rc=0 cmd_pid wd_pid
  flag="$(mktemp)"
  # Bash gives a BACKGROUND job stdin from /dev/null, so `to ... < "$PROMPT"`
  # delivered nothing and `codex exec -` reported "No prompt provided via
  # stdin" — a promptless adversary whose review still parsed. Duplicating the
  # caller's stdin onto FD 3 keeps the redirect intact. This only ever bit hosts
  # without timeout(1)/gtimeout, i.e. stock macOS, which is the portability
  # floor this project targets.
  exec 3<&0
  "$@" <&3 &
  cmd_pid=$!
  exec 3<&-
  ( sleep "$TIMEOUT"
    if kill -0 "$cmd_pid" 2>/dev/null; then
      printf T > "$flag"; kill -TERM "$cmd_pid" 2>/dev/null
      sleep 2; kill -KILL "$cmd_pid" 2>/dev/null
    fi ) &
  wd_pid=$!
  wait "$cmd_pid" 2>/dev/null || rc=$?
  kill "$wd_pid" 2>/dev/null || true; wait "$wd_pid" 2>/dev/null || true
  if [ -s "$flag" ]; then rm -f "$flag"; return 124; fi
  rm -f "$flag"; return "$rc"
}

echo "cvg review · dispatch → $ADVERSARY ($FAMILY) · read-only · cap ${TIMEOUT}s (${TIMEOUT_BIN:-bash-watchdog})" >&2
RC=0
case "$KIND" in
  codex)  to "$CMD" exec --sandbox read-only - < "$PROMPT" > "$JUDG" 2>/dev/null || RC=$? ;;
  kimi)   to "$CMD" --output-format text -p "$(cat "$PROMPT")" > "$JUDG" 2>/dev/null || RC=$? ;;
  claude) to "$CMD" -p "$(cat "$PROMPT")" --output-format json --tools Read,Grep --disallowedTools "Edit,Write" > "$JUDG" 2>/dev/null || RC=$? ;;
esac
if [ "$RC" -eq 124 ]; then echo "TIMEOUT after ${TIMEOUT}s." >&2; echo "REVIEW=TIMEOUT"; exit 21; fi

# ── ASSEMBLE + STAMP: provenance computed by the referee, not the engine ──────
ENGINE_VERSION="$("$CMD" --version 2>/dev/null | head -1 | tr -d '\n' | cut -c1-40 || true)"
export CVG_PROMPT="$PROMPT"
set +e
python3 - "$JUDG" "$SKETCH_DIR" "$OUT" "$ADVERSARY" "$FAMILY" "$ENGINE_VERSION" "$KIND" <<'PY'
import json, sys, hashlib, glob, os, re
judg_p, sketch, out, engine, family, ver, kind = sys.argv[1:8]
raw = open(judg_p, encoding="utf-8", errors="replace").read()
# extract the engine's JUDGMENT json (objections/verdict/fork). A real engine wraps
# the JSON in reasoning prose (and may emit ndjson/stream-json event lines), so we
# scan every '{' with raw_decode — tolerant of surrounding text — and take the first
# object that looks like a judgment. Prefer the RICHEST such object (most objections)
# so a stream-json envelope's inner judgment beats a bare {"type":...} event.
judg = None
_best = -1
dec = json.JSONDecoder()
i, n = 0, len(raw)
while i < n:
    b = raw.find("{", i)
    if b < 0:
        break
    try:
        c, end = dec.raw_decode(raw, b)
    except ValueError:
        i = b + 1
        continue
    i = max(end, b + 1)
    if isinstance(c, dict) and ("objections" in c or "verdict" in c):
        score = len(c.get("objections", [])) if isinstance(c.get("objections"), list) else 0
        if score > _best:
            judg, _best = c, score
if judg is None:
    sys.stderr.write("ERROR: adversary produced no parseable judgment JSON (fail-closed)\n"); sys.exit(22)
# provenance the REFEREE computes (not self-reported)
inputs = []
for f in sorted(glob.glob(os.path.join(sketch, "*", "*.md"))):
    if os.path.basename(os.path.dirname(f)).startswith("."): continue
    rel = os.path.relpath(f, sketch)
    inputs.append({"path": rel, "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest()})
prompt_sha = hashlib.sha256(open(os.environ.get("CVG_PROMPT", "/dev/null"), "rb").read()).hexdigest() if os.environ.get("CVG_PROMPT") else ""

# THE ADVERSARY PROPOSES; ONLY THE OWNER RESOLVES.
# A read-only attacker cannot fix a plan, so anything it writes under
# "resolution" is a RECOMMENDATION — and on 2026-08-03 that distinction was the
# difference between a barrier and a rubber stamp: the engine stamped
# disposition FIX on every objection it filed, the gate asked only "does each
# objection have a disposition?", and Pass 4 went GREEN with seven criticals
# open. The referee therefore demotes any engine-supplied resolution to
# "proposal" and NEVER emits "resolution" itself. Absence is the default, so the
# gate fails closed until a human records a decision (cvg review --resolve).
def demote_resolutions(objs):
    out = []
    for o in (objs or []):
        if isinstance(o, dict):
            o = dict(o)
            if "resolution" in o:
                if "proposal" not in o:
                    o["proposal"] = o.pop("resolution")
                else:
                    o.pop("resolution", None)
        out.append(o)
    return out

log = {
    "schema_version": "1.0", "pass": "4-consensus",
    "adversary": {"engine_id": engine, "model": judg.get("model", engine), "family": family,
                  "engine_version": ver or "unknown", "sandbox_mode": "read-only"},
    "author": {"model": "claude", "family": "anthropic"},
    "verdict": judg.get("verdict", "REVISE"),
    "prompt_sha256": prompt_sha,
    "inputs": inputs,
    "objections": demote_resolutions(judg.get("objections", [])),
    "cross_lane_interfaces": judg.get("cross_lane_interfaces", []),
    "fork": judg.get("fork", {}),
    "open_questions": judg.get("open_questions", []),
    "rounds_run": judg.get("rounds_run", 1),
}
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
json.dump(log, open(out, "w"), indent=2)
print("stamped %d objection(s), %d input(s) → %s" % (len(log["objections"]), len(inputs), out))
PY
PRC=$?
set -e

if [ "$PRC" -ne 0 ]; then echo "REVIEW=ERROR"; exit 22; fi
echo "REVIEW=OK"
exit 0
