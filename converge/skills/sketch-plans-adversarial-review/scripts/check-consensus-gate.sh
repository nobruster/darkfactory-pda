#!/usr/bin/env bash
# check-consensus-gate.sh — Converge Pass 4 (Consensus): the falsifiable exit gate.
#
# v0.4.0 — gates a STAMPED OBJECTION-LOG ARTIFACT (JSON), not plan prose. The
# dispatch (cvg review --adversary) writes swimlanes/.consensus/objection-log.json;
# this gate validates its structure + semantics + PROVENANCE (it re-hashes the live
# swimlane plans and requires they match the ones the adversary attacked). It never
# reads the model's judgment — only refuses to let a soft pass slip through.
#
# The pass is done only when: a DIFFERENT-FAMILY model attacked (not self-review),
# every objection is FIX-or-ACCEPT (ACCEPT names an owner), the fork is declared
# (in the artifact AND at the top of every swimlane PRD), and the plans have not
# drifted since the review. Fail-closed: a missing/malformed artifact is FAIL/EMPTY,
# never a pass.
#
# Usage:
#   check-consensus-gate.sh --dir swimlanes/                Gate the swimlane tree + its log
#   check-consensus-gate.sh --log path/to/log.json ...   Point at a specific artifact
#   check-consensus-gate.sh --author-family anthropic    Who wrote the plans (default anthropic)
#   check-consensus-gate.sh --help
#
# Agent contract: the LAST line is a stable machine token —
#   CHECK_CONSENSUS=OK | FAIL | EMPTY | USAGE_ERROR
# Exit: 0 = ok; 1 = check failed; 2 = nothing to gate / usage error.
# bash 3.2-safe; Python is stdlib-only (json, hashlib) — no pip, no jq.

set -euo pipefail

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
LOG=""
AUTHOR_FAMILY="anthropic"

usage() { sed -n '2,26p' "$0"; }
usage_error() { echo "ERROR: $*" >&2; usage >&2; echo "CHECK_CONSENSUS=USAGE_ERROR"; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h)       usage; exit 0 ;;
    --dir)           SKETCH_DIR="${2:?--dir needs a path}"; shift 2 ;;
    --log)           LOG="${2:?--log needs a path}"; shift 2 ;;
    --author-family) AUTHOR_FAMILY="${2:?--author-family needs a value}"; shift 2 ;;
    -*)              usage_error "unknown option: $1" ;;
    *)               SKETCH_DIR="$1"; shift ;;
  esac
done

[ -n "$LOG" ] || LOG="$SKETCH_DIR/.consensus/objection-log.json"

if [ ! -d "$SKETCH_DIR" ]; then
  echo "GATE: no swimlane tree at $SKETCH_DIR/ — run Pass 3 (reqs-to-swimlane-plans) first." >&2
  echo "CHECK_CONSENSUS=EMPTY"; exit 2
fi
if [ ! -f "$LOG" ]; then
  echo "GATE: no objection log at $LOG — run the adversary first (cvg review --adversary codex|kimi)." >&2
  echo "CHECK_CONSENSUS=EMPTY"; exit 2
fi

echo "== Converge Pass 4 · Consensus gate =="
echo "sketch: $SKETCH_DIR   log: $LOG   author-family: $AUTHOR_FAMILY"
echo

set +e
python3 - "$LOG" "$SKETCH_DIR" "$AUTHOR_FAMILY" <<'PY'
import json, sys, hashlib, glob, os, re

log_path, sketch, author_family = sys.argv[1], sys.argv[2], sys.argv[3]
rc = 0
def ok(m):   print("  ok   " + m)
def fail(m):
    global rc; print("  FAIL " + m); rc = 1

try:
    art = json.load(open(log_path))
except Exception as e:
    print("  FAIL objection-log is not valid JSON: %s" % e)
    sys.exit(1)

# [1] a DIFFERENT-FAMILY adversary attacked (H3/H4 — provenance, not a grep of a word)
adv = art.get("adversary", {}) or {}
fam = (adv.get("family") or "").strip().lower()
if not fam:
    fail("adversary.family missing — cannot prove a different model attacked")
elif fam == author_family.strip().lower():
    fail("adversary.family == author (%s) — self-review; a DIFFERENT family must attack" % author_family)
else:
    ok("cross-family adversary: %s / %s (%s)" % (adv.get("engine_id","?"), adv.get("model","?"), fam))

# [2] verdict is a completed review (fail-closed on ABSTAIN/ERROR)
verdict = art.get("verdict", "")
if verdict not in ("PASS", "REVISE", "ABSTAIN", "ERROR"):
    fail("verdict not in {PASS,REVISE,ABSTAIN,ERROR}: %r" % verdict)
elif verdict in ("ABSTAIN", "ERROR"):
    fail("verdict is %s — not a completed review (fail-closed)" % verdict)
else:
    ok("verdict: %s" % verdict)

# [3] every objection FIX or ACCEPT; ACCEPT names an owner (H9); default-to-refuted (H6)
objs = art.get("objections", []) or []
if not objs:
    fail("no objections logged — the adversary blessed everything (default-to-refuted violated)")
else:
    bad = 0
    # THE ADVERSARY PROPOSES; ONLY THE OWNER RESOLVES.
    # Until 2026-08-03 this block accepted any objection carrying a disposition —
    # and the read-only adversary stamped disposition FIX on every objection it
    # filed ("the adversary did not implement the fix", risk "Open until …"). So
    # "all objections resolved" was satisfied by the ATTACKER'S OWN PROPOSAL and
    # Pass 4 could be passed by dispatching twice. Proposal and decision now live
    # in different fields: the referee writes only `proposal`, and `resolution`
    # exists solely because a human recorded one (cvg review --resolve), which is
    # the single judgment THE BARRIER exists to capture.
    for o in objs:
        oid = o.get("id", "?")
        if not o.get("severity"):
            fail("objection %s: missing severity" % oid); bad += 1
        res = o.get("resolution") or {}
        if not res:
            hint = " (the adversary proposed %r — that is a recommendation, not consent)" % (
                (o.get("proposal") or {}).get("disposition")) if o.get("proposal") else ""
            fail("objection %s: UNRESOLVED — no owner decision recorded%s. Record one: "
                 "cvg review --resolve %s --fix   (or --accept --owner <name> --risk <why>)"
                 % (oid, hint, oid))
            bad += 1
            continue
        disp = res.get("disposition")
        if disp not in ("FIX", "ACCEPT"):
            fail("objection %s: resolution.disposition must be FIX or ACCEPT (got %r)" % (oid, disp)); bad += 1
            continue
        # A decision nobody signed is indistinguishable from a machine's suggestion.
        if not (res.get("decided_by") or "").strip():
            fail("objection %s: resolution has no decided_by — only a human closes the barrier" % oid); bad += 1
        if not (res.get("decided_at") or "").strip():
            fail("objection %s: resolution has no decided_at timestamp" % oid); bad += 1
        if disp == "ACCEPT" and not (res.get("owner") or "").strip():
            fail("objection %s: ACCEPT requires a non-empty owner" % oid); bad += 1
        # The adversary's residual-risk note is an explicit statement that the risk
        # is still live. GREEN must not read past it.
        rr = (res.get("risk_residual") or "").strip()
        if re.match(r"^open\b", rr, re.I) or "open until" in rr.lower():
            fail("objection %s: resolution.risk_residual still reads %r — an open residual risk "
                 "cannot be GREEN; either close it or ACCEPT it with an owner" % (oid, rr[:60]))
            bad += 1
    if bad == 0:
        ok("%d objection(s), each decided by a human (FIX or ACCEPT; ACCEPT names an owner)" % len(objs))
    sev = [(o.get("severity") or "").lower() for o in objs]
    if not any(s in ("high", "critical") for s in sev) and verdict != "PASS":
        fail("no high/critical objection and verdict != PASS — weak/blessing review (H6)")

# [4] fork is the single task-driven path (v3.4 — the fork is collapsed).
# Converge no longer chooses between plan-driven (A) and task-driven (B): everything
# decomposes to task-specs (task-spec is the six-tier sizing engine). The field is
# kept for the provenance record but must be B; A (plan-driven / SDD) is retired.
fork = art.get("fork", {}) or {}
if fork.get("choice") == "A":
    fail("fork.choice is 'A' (plan-driven) — RETIRED. Converge is single-path: consensus always hands off to task-driven decomposition (Fork B). Set fork.choice: B. See references/the-fork.md")
elif fork.get("choice") != "B":
    fail("fork.choice must be B (task-driven — the single path) (got %r)" % fork.get("choice"))
elif not (fork.get("reason") or "").strip():
    fail("fork declared but carries no reason")
else:
    ok("fork: B (task-driven, single path) — %s" % ((fork.get("reason") or "")[:60]))

# [5] fork line at the top of EVERY swimlane PRD (dir-per-swimlane)
def lane_dirs(root):
    """Every swimlane dir under root, as (dir, prd). A lane is identified by
    CONTAINING a lane PRD — _lane.md (canonical) or <name>.plan.md (legacy) —
    never by the folder's name, so dropping the redundant "swimlane-" prefix
    cannot make the barrier silently find nothing to gate."""
    out = []
    for d in sorted(glob.glob(os.path.join(root, "*", ""))):
        if os.path.basename(os.path.dirname(d)).startswith("."):
            continue
        lane = os.path.join(d, "_lane.md")
        if os.path.exists(lane):
            out.append((d, lane)); continue
        legacy = sorted(glob.glob(os.path.join(d, "*.plan.md")))
        if legacy:
            out.append((d, legacy[-1]))
    return out

LANES = lane_dirs(sketch)
prds = [prd for _, prd in LANES]
if not prds:
    fail("no swimlane PRDs (%s/<seam>/_lane.md, or the legacy %s/swimlane-*/swimlane-*.plan.md) — nothing to gate" % (sketch, sketch))
else:
    missing = []
    for p in prds:
        head = "".join(open(p, encoding="utf-8", errors="replace").readlines()[:15])
        if not (re.search(r"FORK[:\s]*[AB]\b", head, re.I) and re.search(r"plan-driven|task-driven", head, re.I)):
            missing.append(os.path.basename(os.path.dirname(p)))
    if missing:
        fail("fork not declared at the top of PRD(s): %s" % ", ".join(missing))
    else:
        ok("fork line present at the top of all %d swimlane PRD(s)" % len(prds))

# [6] PROVENANCE — the adversary attacked the LIVE plans (H3 anti-spoof)
inputs = {}
for i in (art.get("inputs", []) or []):
    if i.get("path"):
        inputs[i["path"]] = i.get("sha256")
if not inputs:
    fail("no inputs[] provenance — cannot prove the adversary saw the real plans")
else:
    live = sorted(f for d, _ in LANES for f in glob.glob(os.path.join(d, "*.md")))
    stale, unseen = [], []
    for f in live:
        rel = os.path.relpath(f, sketch)
        want = inputs.get(rel) if rel in inputs else inputs.get(f)
        if want is None:
            unseen.append(rel); continue
        got = hashlib.sha256(open(f, "rb").read()).hexdigest()
        if got != want:
            stale.append(rel)
    if unseen:
        fail("plan(s) not in the reviewed inputs[] — the review is incomplete: %s" % ", ".join(unseen[:4]))
    if stale:
        fail("plan(s) changed since the review (hash mismatch) — re-review: %s" % ", ".join(stale[:4]))
    if not unseen and not stale:
        ok("provenance verified: every current plan is the one attacked (%d files)" % len(live))

sys.exit(rc)
PY
PYRC=$?
set -e

echo
if [ "$PYRC" -eq 0 ]; then
  echo "GATE: GREEN — consensus reached (different-family attack, all objections resolved, fork named, provenance intact). Hand off per the fork."
  echo "CHECK_CONSENSUS=OK"
  exit 0
else
  echo "GATE: RED — fix the FAILs above. Sharpen in place, name the fork, or re-run the adversary; do NOT add scope." >&2
  echo "CHECK_CONSENSUS=FAIL"
  exit 1
fi
