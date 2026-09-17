# Pass 1 · Intent — BRD → testable requirements

**Mission:** derive a technical requirements spec from the BRD in which every
single requirement is *testable* — phrased so a machine (or a person with a
checklist) can answer pass/fail without interpretation.

**Inputs:** the signed BRD at `cvg/docs/brd/`. Held-back material stays
closed.

**Procedure:**
1. Extract every claim the BRD makes and rewrite it as a requirement with an
   observable outcome. "Numbers are checked, not just computed" becomes a
   requirement naming *which* checks exist and *where* they run.
2. Name every blocker honestly. A blocker's resolution must be affirmative
   and substantive — "TBD", "pending", or a blank are unresolved, and the
   gate fails closed on them.
3. Write `cvg/docs/tech-spec/<slug>.md`: requirements (numbered, testable),
   data contracts, constraints inherited from the BRD, resolved blockers,
   non-goals.
4. File judgment calls → `cvg/brain/decisions/`, working notes →
   `cvg/brain/transcripts/`.
5. Review with the human if anything forced a choice the BRD didn't make.

**Exit:** `cvg intent` → `CHECK_TECH_SPEC=PASS`.

**Hands off to:** Pass 2 (Structure), which records how the system will be
shaped to meet these requirements.
