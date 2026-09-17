#!/usr/bin/env python3
"""Generate a Pass 4 objection-log for a swimlane tree, with correct live hashes.
Usage: gen-log.py <sketch-dir> [mode]   mode in:
  good | same-family | unresolved | accept-no-owner | no-fork | no-objections
Writes <sketch>/.consensus/objection-log.json. Stdlib only (test helper)."""
import json, sys, hashlib, glob, os

sketch = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "good"

inputs = []
for f in sorted(glob.glob(os.path.join(sketch, "swimlane-*", "*.md"))):
    if os.path.basename(os.path.dirname(f)).startswith("."):
        continue
    rel = os.path.relpath(f, sketch)
    inputs.append({"path": rel, "sha256": hashlib.sha256(open(f, "rb").read()).hexdigest()})

log = {
    "schema_version": "1.0",
    "pass": "4-consensus",
    "adversary": {"engine_id": "codex", "model": "gpt-5-codex", "family": "openai",
                  "engine_version": "0.144.5", "sandbox_mode": "read-only"},
    "author": {"model": "claude", "family": "anthropic"},
    "verdict": "REVISE",
    "prompt_sha256": hashlib.sha256(b"attack-playbook-prompt").hexdigest(),
    "inputs": inputs,
    "objections": [
        {"id": "C1", "severity": "high", "attack_class": "cross-lane-interface",
         "swimlane": "swimlane-alpha", "location": {"plan_file": "swimlane-alpha/swimlane-alpha.plan.md", "section": "Seam"},
         "evidence": "beta reads a field alpha never emits",
         # A resolution is an OWNER decision: decided_by/decided_at are what make it
         # distinguishable from the adversary's proposal (which now lands in "proposal").
         "resolution": {"disposition": "FIX", "fixed_in": "swimlane-alpha.plan.md#Seam",
                        "decided_by": "owner-under-test", "decided_at": "2026-08-03T12:00:00Z"}},
        {"id": "C2", "severity": "medium", "attack_class": "unverified-assumption",
         "swimlane": "swimlane-alpha", "location": {"plan_file": "swimlane-alpha/swimlane-alpha.plan.md", "section": "Build order"},
         "evidence": "assumes src.* is single-writer",
         "resolution": {"disposition": "ACCEPT", "owner": "team-a", "reason": "accepted under current load",
                        "decided_by": "owner-under-test", "decided_at": "2026-08-03T12:00:00Z",
                        "risk_residual": "bounded: single-writer holds at current load"}},
    ],
    "fork": {"choice": "B", "reason": "every leg has a cheap runnable eval", "per_plan_declared": True},
    "open_questions": [{"q": "load ceiling?", "owner": "team-a", "blocks_build": False}],
    "rounds_run": 2,
}

if mode == "same-family":
    log["adversary"]["family"] = "anthropic"; log["adversary"]["engine_id"] = "claude"
elif mode == "unresolved":
    log["objections"][0]["resolution"] = {"disposition": None}
elif mode == "adversary-proposal-only":
    # THE regression for 2026-08-03: the adversary's own FIX proposal must never
    # satisfy the gate. This is the exact shape a fresh dispatch produces.
    log["objections"][0].pop("resolution", None)
    log["objections"][0]["proposal"] = {"disposition": "FIX",
        "reason": "the read-only adversary did not implement the fix",
        "risk_residual": "Open until the owner revises the plan"}
elif mode == "no-decider":
    log["objections"][0]["resolution"] = {"disposition": "FIX", "fixed_in": "x"}
elif mode == "open-residual-risk":
    log["objections"][0]["resolution"] = {"disposition": "FIX", "fixed_in": "x",
        "decided_by": "owner-under-test", "decided_at": "2026-08-03T12:00:00Z",
        "risk_residual": "Open until someone looks at it"}
elif mode == "accept-no-owner":
    log["objections"][1]["resolution"] = {"disposition": "ACCEPT", "owner": ""}
elif mode == "no-fork":
    log["fork"] = {"reason": "unsure"}
elif mode == "no-objections":
    log["objections"] = []

os.makedirs(os.path.join(sketch, ".consensus"), exist_ok=True)
with open(os.path.join(sketch, ".consensus", "objection-log.json"), "w") as fh:
    json.dump(log, fh, indent=2)
print("wrote %s objection-log (%d inputs)" % (mode, len(inputs)))
