#!/usr/bin/env bash
# dispatch-review-multi.sh — Converge Pass 4, multi-engine adversary (the ATTACK
# half of the auto-loop). Dispatch TWO+ DIFFERENT-family critics (e.g. codex,kimi),
# each through the PROVEN single-engine dispatch-review.sh (reused verbatim via its
# --out), then MERGE their judgments into ONE referee-stamped objection-log. Two
# independent cross-family views beat one. The referee is still never a player:
# each engine authenticates itself; PROVENANCE (input hashes) is recomputed HERE,
# never trusted from a sub-log. Fail-closed: zero usable judgments, or no
# cross-family engine among them, => ERROR, never a pass.
#
# Usage:
#   dispatch-review-multi.sh --adversary codex,kimi [--dir sketch] [--out F]
#                            [--author-family anthropic]
# Engine cmds are env-overridable for tests (CVG_CODEX_CMD / CVG_KIMI_CMD / …),
# inherited by the single-engine dispatcher unchanged.
#
# Token (last line): REVIEW=OK | ERROR | SKIP | USAGE_ERROR
# Exit: 0 ok · 20 all engines unavailable (SKIP) · 22 malformed/no-cross-family · 2 usage
# bash 3.2-safe; Python stdlib-only (json/hashlib). No jq.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SINGLE="$HERE/dispatch-review.sh"
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
ADVLIST="codex,kimi"
AUTHOR_FAMILY="anthropic"
OUT=""

uerr() { echo "ERROR: $*" >&2; echo "REVIEW=USAGE_ERROR"; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h)       sed -n '2,20p' "$0"; exit 0 ;;
    --adversary)     ADVLIST="${2:?}"; shift 2 ;;
    # A wall-clock cap that only worked for ONE engine would be a trap: the
    # merged path is the slower one, so it needs the cap more, not less.
    --timeout)       TIMEOUT_SECS="${2:?}"; shift 2 ;;
    --dir)           SKETCH_DIR="${2:?}"; shift 2 ;;
    --out)           OUT="${2:?}"; shift 2 ;;
    --author-family) AUTHOR_FAMILY="${2:?}"; shift 2 ;;
    -*)              uerr "unknown option: $1" ;;
    *)               SKETCH_DIR="$1"; shift ;;
  esac
done
[ -n "$OUT" ] || OUT="$SKETCH_DIR/.consensus/objection-log.json"
[ -d "$SKETCH_DIR" ] || uerr "no swimlane tree at $SKETCH_DIR/"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# ── dispatch each engine through the proven single-engine path, per-engine --out ─
LOGS=""; SKIPS=0; ENGINES=0
OLDIFS="$IFS"; IFS=','
# shellcheck disable=SC2086  # intentional: split the comma-separated adversary list
set -- $ADVLIST
IFS="$OLDIFS"
for adv in "$@"; do
  [ -n "$adv" ] || continue
  ENGINES=$((ENGINES + 1))
  echo "cvg review · multi · dispatch → $adv" >&2
  rc=0
  out="$(bash "$SINGLE" --adversary "$adv" --dir "$SKETCH_DIR" \
           --out "$TMP/$adv.json" --author-family "$AUTHOR_FAMILY" \
           ${TIMEOUT_SECS:+--timeout "$TIMEOUT_SECS"})" || rc=$?
  tok="$(printf '%s\n' "$out" | grep -E '^REVIEW=' | tail -1 || true)"
  echo "    $adv → ${tok:-REVIEW=?} (exit $rc)" >&2
  printf '%s\n' "$tok" | grep -q 'REVIEW=SKIP' && SKIPS=$((SKIPS + 1)) || true
  [ -f "$TMP/$adv.json" ] && LOGS="$LOGS $TMP/$adv.json"
done

# all engines absent → honest SKIP (nothing was reviewed)
if [ -z "$LOGS" ] && [ "$SKIPS" -eq "$ENGINES" ] && [ "$ENGINES" -gt 0 ]; then
  echo "SKIP: none of the requested adversaries are installed — run cvg doctor." >&2
  echo "REVIEW=SKIP"; exit 20
fi

# ── MERGE: referee recomputes provenance; unions + renumbers objections ──────────
set +e
# shellcheck disable=SC2086  # intentional: $LOGS is a space-separated list of per-engine log paths
python3 - "$SKETCH_DIR" "$OUT" "$AUTHOR_FAMILY" $LOGS <<'PY'
import json, sys, hashlib, glob, os
sketch, out, author_family = sys.argv[1:4]
logs = sys.argv[4:]
if not logs:
    sys.stderr.write("ERROR: no adversary produced a usable judgment (fail-closed)\n")
    print("REVIEW=ERROR"); sys.exit(22)

# provenance the REFEREE computes (never trusted from a sub-log)

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

inputs = []
for f in sorted(glob.glob(os.path.join(sketch, "*", "*.md"))):
    if os.path.basename(os.path.dirname(f)).startswith("."):
        continue
    inputs.append({"path": os.path.relpath(f, sketch),
                   "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest()})

advs = []; objs = []; forks = []; xfam = False; verdict = "PASS"
for lp in logs:
    d = json.load(open(lp))
    a = d.get("adversary", {})
    advs.append(a)
    if a.get("family") and a.get("family") != author_family:
        xfam = True
    for o in d.get("objections", []):
        o = dict(o); o["raised_by"] = a.get("engine_id", "?"); objs.append(o)
    if d.get("fork"):
        forks.append(d["fork"])
    if d.get("verdict") == "REVISE" or d.get("objections"):
        verdict = "REVISE"

# cross-family is invariant, not preference — fail-closed if absent
if not xfam:
    sys.stderr.write("ERROR: no cross-family adversary among %d engine(s) — self-preference risk (fail-closed)\n" % len(advs))
    print("REVIEW=ERROR"); sys.exit(22)

# renumber ids C1..CN so they stay unique + match ^C[0-9]+ (keep the engine's own id)
for i, o in enumerate(objs, 1):
    if "id" in o:
        o["orig_id"] = o["id"]
    o["id"] = "C%d" % i

# a singular `adversary` (first cross-family) keeps the existing gate schema happy;
# `adversaries` carries the full multi record.
primary = next((a for a in advs if a.get("family") != author_family), advs[0])
log = {
    "schema_version": "1.0", "pass": "4-consensus", "mode": "multi-adversary",
    "adversary": primary, "adversaries": advs, "cross_family": xfam,
    "author": {"model": "claude", "family": author_family},
    "verdict": verdict, "inputs": inputs, "objections": demote_resolutions(objs),
    "cross_lane_interfaces": [], "fork": (forks[0] if forks else {}), "open_questions": [],
}
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
json.dump(log, open(out, "w"), indent=2)
print("merged %d objection(s) from %d adversary(ies) [%s] → %s"
      % (len(objs), len(advs), ",".join(a.get("engine_id", "?") for a in advs), out))
print("REVIEW=OK")
PY
PRC=$?
set -e
exit "$PRC"
