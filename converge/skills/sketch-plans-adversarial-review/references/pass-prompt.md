# Pass 4 · Consensus — THE BARRIER

**Mission:** have a *different model family* attack the plan, resolve every
objection with the human, and get the human's signature. This is the last
human sign-off before machines take over — treat it with that weight.

**Inputs:** the gated swimlane tree (`cvg/swimlanes/`).

**Procedure:**
1. Check readiness: `cvg doctor` (needs ≥2 engines, ≥1 cross-family). You
   never review your own plan — the referee dispatches the attack.
2. Dispatch: `cvg review --adversary codex` (or `kimi`, or a comma-list for
   two independent attacks merged into one stamped log). Expect `REVIEW=OK`.
3. Triage every objection *with the human*: for each one, either amend the
   plan (say what changed and where) or record a reasoned rejection. Never
   silently drop an objection — the gate reads the log.
4. If the plan changed, re-run the earlier gates the change touches
   (`cvg decompose`, at minimum) before proceeding.
5. The human signs. Only a human closes the barrier.

**Exit:** `cvg review --check` → `CHECK_CONSENSUS=OK` (structure, semantics,
and a provenance re-hash of the live plans — if the plans changed after the
review, the gate will know).

**Hands off to:** Pass 5 (Tasking) — the cornerstone. From here on, every
artifact is machine-checked.
