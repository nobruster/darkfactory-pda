# Falsifiable requirements — how to rewrite a vague brief line into a spec line

Pass 1's gate is **falsifiability, not completeness**. A requirement belongs in
the tech-spec only if a future eval could pass or fail it. This reference shows
how to turn a vague brief line into a falsifiable requirement — and what to do
with the ones that resist.

## The test

A requirement is falsifiable when you can answer all three:

1. **What is measured?** — a named quantity (a latency, a row count, a freshness
   lag, an error rate), not an adjective.
2. **Against what threshold?** — a number with a unit and a comparator
   (`<= 5 s`, `>= 99 %`, `no more than 1 per 10k`).
3. **On what input?** — the condition it holds under (which data, which load,
   which window), so the eval is repeatable.

If any answer is "it depends" or "everyone knows", it is not yet a requirement.
Either pin it to a number or send it to **open assumptions with a named owner**.
Do not soften it into the spec.

## The rewrite pattern

> **current → target, under a named condition, traced to a client KPI.**

Every requirement is phrased so an eval could decide it, and every success
metric is written as `current → target` where `current` is the baseline pulled
from the BRD. If the baseline is unknown, that unknown is itself an open
assumption owned by the client — not a blank.

## Examples (vague → falsifiable)

| Vague brief line | Why it fails | Falsifiable rewrite |
|---|---|---|
| "The dashboard should be fast." | No quantity, no threshold, no input. | "A standard revenue-by-month query returns in **≤ 3 s** (p95) over the last 12 months of orders. Current: 45 s → Target: ≤ 3 s." |
| "Data should be reasonably fresh." | "Reasonably" is not measurable. | "Facts reflect source records landed within the last **15 minutes** at least **99 %** of the day. Current: ~6 h batch → Target: ≤ 15 min." |
| "Reports must be accurate." | No definition of accurate, no tolerance. | "Reconciled revenue matches the source ledger to **within $0.01** for every closed day. Current: unreconciled → Target: 0 discrepancies." |
| "It should scale." | No load, no ceiling. | "Sustains the modelled outputs at **10× current daily volume (≈ 2M orders/day)** with query latency still ≤ 3 s (p95)." |
| "Give the team self-serve analytics." | A capability, not a bar. | "**≥ 90 %** of the 20 named questions in the BRD are answerable without engineering help, measured against the question list. Current: 0/20 self-serve → Target: ≥ 18/20." |
| "Handle bad records gracefully." | "Gracefully" is unfalsifiable. | "Malformed source rows are quarantined, not dropped: **100 %** of rejects are recoverable from a rejects location; a run with ≤ **0.5 %** rejects still completes." |

Note what each rewrite keeps: a measured quantity, a numeric threshold with a
unit, the input it holds under, and (for metrics) a `current → target` pair
traced to a client KPI. Note what each rewrite drops: the adjective.

## Stay above the stack

Falsifiable is **not** the same as technical. A good Pass 1 requirement says
*what the engine must do and how well* — never *how*.

- ✅ "A revenue-by-month query returns in ≤ 3 s (p95) over 12 months of orders."
- ❌ "A dbt model materializes a `fct_orders` star schema in DuckDB."

The second names a stack (dbt, DuckDB, a schema) and a design — that is **Pass 3's**
job, not Pass 1's. If a client hands you a stack preference, accept the intent
and record it as an open assumption for Pass 3; keep the requirement measurable
and technology-free.

The source data is named at the **problem level** — "order, payment, customer,
and product records" — not as columns or a DDL. Naming the shape of the source
is required; naming its schema is a leak.

## When a line refuses to become falsifiable

Some brief lines genuinely cannot be pinned yet — the baseline is unknown, the
threshold is a business call above the engagement's pay grade, or the scope
boundary is unclear. Do **not** invent a number and do **not** stall.

Move the line to **Open assumptions** with:

- your **best default answer** so momentum holds, and
- the **named client stakeholder** who owns the real answer.

Example:

> **Assumption A3 — Freshness target.** BRD says "near real-time." Default
> assumed: **≤ 15 min** end-to-end. Owner: **Dana Okafor, Head of Analytics
> (client)** — confirm before sign-off.

That is a legitimate Pass 1 output. A named, owned assumption is honest; a
softened requirement that no eval can decide is not.

## Quick self-check before the gate

For each requirement, confirm:

- [ ] It carries a **stable id** (`R-n` for requirements, `W-n` for wishes/wonts) that evals, ADRs, and gap records can cite.
- [ ] It names a **measured quantity**, not an adjective.
- [ ] It has a **numeric threshold with a unit and a comparator** — on its own line(s), not just somewhere in the spec.
- [ ] It states the **input/condition** it holds under.
- [ ] Success metrics read **current → target**, each traced to a **BRD KPI**.
- [ ] It names **no technology, schema, engine, or framework**.
- [ ] Anything that can't meet the above is in **open assumptions with an owner**.

The bundled verifier checks the mechanical parts of this:

```bash
bash .claude/skills/brd-docs-to-tech-req/scripts/check-tech-spec.sh cvg/docs/tech-spec-analytical-engine.md
```

It PASSES only when the required sections are present, requirements carry
measurable thresholds, and metrics read current → target — and it WARNS on
any stack term that leaked in (per-domain buckets from
[leak-terms.txt](leak-terms.txt)), on requirement bullets without a stable
`R-n`/`W-n` id, and on any `R-n`/`W-n` whose own line(s) carry no number,
unit, or comparator.
