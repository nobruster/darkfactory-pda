# Pass 2 · Structure — requirements → ADRs

**Mission:** record the architecture as Architecture Decision Records — real
decisions with alternatives and consequences, not narration of whatever was
going to happen anyway.

**Inputs:** the gated tech spec at `cvg/docs/tech-spec/`.

**Procedure:**
1. Identify each load-bearing choice the requirements force: storage, tooling,
   layering, naming, run model, verification strategy. One ADR per decision.
2. Write each ADR to `cvg/docs/adrs/` with: context, the decision (stated in
   the imperative), alternatives considered and why they lost, and
   consequences — including the uncomfortable ones. Modal hedging ("we might",
   "could") belongs in Consequences, never in Decision.
3. Keep the set canonical: no two ADRs may decide the same thing, and no
   requirement may be left with its shaping decision unmade.
4. File the reasoning trail → `cvg/brain/decisions/`.

**Exit:** `cvg structure` → `CHECK_ADR=OK`. Use `--final` when nothing is
left proposed.

**Hands off to:** Pass 3 (Decompose), which splits the shaped work into
ordered swimlanes.
