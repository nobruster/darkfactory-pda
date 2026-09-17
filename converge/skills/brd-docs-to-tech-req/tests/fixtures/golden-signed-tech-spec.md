# Tech-Spec — The Analytical Backbone (phase one)

> Converge Pass 1 (Intent). Consumes `docs/brd-analytical-backbone.md`
> (canonical, signed 2026-07-19). Interrogation: three frontier rounds,
> 2026-07-19, owner answering (VP of Engineering — decider); locked
> decisions D1–D5 recorded in
> `brain/decisions/2026-07-19-pass1-round1-owner-answers.md`, gap
> resolutions D6–D8 (Round 3, at R1.C) in
> `brain/decisions/2026-07-19-pass1-round3-gap-resolutions.md`.
> Above the stack throughout — technology is decided at Pass 3.

**TL;DR:** A standalone near-real-time analytical backbone that answers
business questions in minutes, takes partner traffic off production, and
locks production — under $1,000/month.

**Outcome.** Anyone with a business question — partner or internal — gets
a correct, provably fresh answer from the backbone within its class SLA,
without touching the operational database. Production serves only
operations, verified by a lockdown that provably holds. The whole thing
runs end-to-end in production and entirely on a laptop.

## Problem restated

Everyone who needs an answer about the business — including our partners —
has exactly one place to get it: the operational database, which was never
built to answer questions, only to run the business. Partner query load is
crashing it, and even when it stays up, the business cannot see itself:
questions take days or go unanswered, and the roadmap runs on gut feel.
Solved means a separate analytical backbone holds a close-to-real-time
copy of what the business does; questions are answered from the backbone
within a known time bound and never from production; production is
provably closed to analytical traffic; and at least one roadmap decision
has been made because of what the backbone showed us — all inside
$1,000/month.

## Scope

**In scope (problem level):**
- A standalone analytical backbone, fully separate from the operational
  database, continuously fed from the four operational domains without
  adding analytical load to production.
- Freshness, answer-time, and honesty guarantees (the requirements below).
- Migrating today's partner analytical consumers onto the backbone, then
  locking production against analytical access.
- End-to-end operation in production, with the identical system runnable
  and verifiable locally by one engineer.

**Out of scope:**
- Any change to the operational system beyond the access lockdown — no
  scaling it up, no re-architecting it (BRD scope-out).
- AI capabilities — explicitly phase two (BRD scope-out).
- The silent-failure / incident-detection idea — parked for its own brief
  (BRD scope-out).
- The operational system's internal control ledger (the chaos ground
  truth) — never part of the analytical surface (terrain rule).
- Choice of data store, transform tooling, capture mechanism, or serving
  layer — Pass 3 decides the stack against ADRs.

## Requirements

Each requirement is falsifiable — a future eval passes or fails it — and
traces to a locked decision (D1–D8) or a BRD line.

### Must (the outcome fails without it)

- **R-1 · Freshness floor (D1; BRD Freshness).** Committed writes in the
  four operational domains are queryable in the backbone within
  **5 minutes at p99**, measured write-timestamp →
  first-queryable-timestamp (p99 is the normative bound — the eval and the
  guarantee are the same number, never "every write"). Eval: at least
  **1,000 sampled writes** across all four domains over a 24-hour window,
  probed at **≤ 30-second intervals**, show p99 lag ≤ 5 minutes. 5 minutes
  is the floor — the process default standard; phase one never relaxes it.
- **R-2 · Zero analytical load on production (BRD Scope-In).** The
  backbone's feed places **zero analytical queries** on the operational
  database. Definition (decidable by identity, never by judgment): an
  **analytical query** is any read on the operational database not issued
  by the operational application itself or by the backbone's capture
  connection, each identified by its own database principal; the count is
  observed from the database's query/connection log by principal.
  Capture overhead on production is measured (feed on vs. feed
  off, like-for-like load) and published; accepted bound (D6, owner call
  2026-07-19): **≤ 20% added p95 latency** hard ceiling, **15%** the
  working target. A deliberate loosening of the interrogator's 5%
  default — the owner judges the feed business-critical; the bound is
  re-examined at Pass 3 when the capture mechanism is chosen, and the
  measured number is published regardless.
- **R-3 · Answer-time SLA by question class (D2; BRD KPI-1).** Business
  questions classify as **small** (a known metric looked up — answer
  ≤ **5 minutes**), **medium** (analysis across domains with existing
  data — ≤ **30 minutes**), **hard** (a brand-new question needing new
  modeling — ≤ **60 minutes**, the BRD's under-1-hour ceiling). Eval:
  timed question-to-answer drills using only the backbone, against
  **Q-SET-1** — a named deliverable: a fixed set of at least 6 questions
  spanning all four domains and all three classes (e.g., revenue by
  product over time, partner activity, payment-failure patterns), each
  question pre-assigned its class by the owner at drill design (class is
  data in the artifact, never judged at run time). Correctness oracle:
  each question carries a pre-computed answer key derived from the source
  operational records at drill design; the eval harness may read the
  `_control` ledger as verification ground truth — a verifier is not a
  business/analytical consumer, the terrain fence stays for the product
  surface. Each class passes when its drill reaches the keyed answer
  within its SLA.
- **R-4 · Never silently wrong (D4).** Every answer surface exposes the
  data's as-of freshness. When the feed is late or broken, consumers see
  staleness — never fabricated, interpolated, or padded values; what is
  served is exactly what the source system committed. Staleness beyond
  **15 minutes** (3× the freshness floor) raises an alert to the on-call
  owner named in the backbone runbook (a Pass 6 deliverable — the name
  lives there, not here). Eval: an induced feed stoppage surfaces visibly
  rising staleness on the answer surface and fires the alert no later than
  **20 minutes** after the last successful update — the 15-minute
  threshold plus a 5-minute detection budget, one threshold, not two.
- **R-5 · Partner migration, then lockdown (D3; BRD KPI-2, hard
  requirement).** All current partner analytical consumers — enumerated in
  the **partner registry**, a migration-planning deliverable (D8) that is
  the decidable meaning of "all" — are migrated to
  the backbone; only then is analytical read access to the operational
  database revoked, and a post-revocation access attempt **provably
  fails**; then a **7-consecutive-day** observation window records **zero
  analytical queries** on the operational database (per R-2's definition,
  observed by principal). The order is fixed:
  the flip happens after the last partner migrates, never before.
  Migration proceeds in **elected waves** (D8): partners are selected into
  waves whose composition and order are decided at migration planning —
  the acceptance criteria above never depended on the order.
- **R-6 · Cost ceiling (BRD constraint, measured).** Total monthly running
  cost of the backbone — every recurring cost attributable to operating it
  (infrastructure, storage, egress, monitoring/alerting, licenses), read
  from provider billing exports; one-time build labor excluded — is
  ≤ **$1,000**, demonstrated over one full calendar month of phase-one
  operation with real partner traffic.
- **R-7 · Local end-to-end iteration (BRD constraint).** One engineer,
  from a fresh checkout and with no production credentials, brings up the
  full backbone locally — feed, store, and answer surface — and verifies a
  change end-to-end (reference change class for the drill: one transform
  edit plus its answer-surface effect). Target loop time (D7, owner call
  2026-07-19): **≤ 15 minutes** from fresh checkout to a verified change,
  for phase one (v1).
- **R-8 · Phase-one load (D5).** The backbone serves **100 analytical
  queries per day** — the owner's sizing floor, per day, not per week —
  with every class SLA in R-3 holding at the daily peak. Load shape for
  drills (R-8 and R-9): the daily volume with a **peak hour carrying
  ≥ 20% of it**; SLAs are measured during the peak hour.

### Should

- **R-9 · Growth headroom (D5, growth estimate).** A load drill at **3×**
  the sizing floor (300 queries/day) completes with no SLA breach — modest
  growth must not force re-architecture inside phase one.
- **R-10 · Staleness is auditable (D4, owner's strategy).** Every
  staleness event — lag exceeding the R-1 floor of 5 minutes (recording
  starts at the floor; alerting stays at R-4's 15) — is recorded with its
  start, duration, and affected domains, so the strategy for fresher data
  is driven by evidence — the owner's stated intent behind "hand over the
  truth."

### Could

- **R-11 · Partner onboarding speed (BRD Stakeholders — partner
  consumers; A-2).** A newly authorized partner consumer goes from access
  granted to first successful query in ≤ **1 business day** (owner's
  business calendar), using a written runbook rather than bespoke
  engineering work.

### Won't (deliberate, phase one)

- **W-1** — Scaling or re-architecting the operational system (BRD
  scope-out; the lockdown is the only touch).
- **W-2** — AI capabilities; phase two, unlocked by this backbone.
- **W-3** — Silent-failure / incident-detection product; separate brief.

## Success metrics (current → target, traced to BRD KPIs)

| Metric | Current | Target | Traces to |
|---|---|---|---|
| Time to answer, by class | days, or impossible without querying production | small ≤ 5 min · medium ≤ 30 min · hard ≤ 60 min | KPI-1; D2 |
| Analytical traffic on the operational database | all of it | **zero**, held for a 7-day observation window after lockdown | KPI-2; D3 |
| Feature-priority decisions backed by backbone analytics | 0 | ≥ 1 within phase one | KPI-3 |
| Data freshness (write → queryable) | no analytical copy exists | ≤ 5 minutes, p99 | BRD Freshness; D1 |
| Answers carrying visible as-of freshness | n/a (no surface exists) | 100%, with staleness > 15 min alerted | D4 |
| Monthly running cost | $0 (nothing exists) | ≤ $1,000/month, measured over a full month | BRD constraint |

Baseline caveat: the BRD's pain numbers (outage count, firefighting
hours/week) remain `(estimated)`/`(guessed)` — see A-3; targets above do
not depend on them. KPI-3 deliberately carries no R-id: it is a business
outcome the owner measures, not a system requirement an eval can force.

## Data named (problem level)

The backbone consumes the business records of the four operational
domains — **customers, products, orders, payments** — and their change
events, exactly as the operational system commits them (per R-4, no
enrichment that fabricates what the source did not say). Consumers of the
backbone: up to ~10 partner organizations `(estimated)` and internal
business/product leadership. The operational system's internal control
ledger is explicitly not part of this surface.

## Open assumptions & gap register

Assumptions (each owned):

- **A-1 · Stack preference stays quarantined.** The owner's verbatim stack
  preference is recorded in the BRD's open questions and deliberately not
  consulted here; Pass 3 grounds and decides the stack against ADRs.
  Owner: VP of Engineering.
- **A-2 · Load planning numbers are estimates.** ≤ 10 partner
  organizations and modest data growth `(estimated)` — confirmed as
  planning numbers by the owner (Round 2, 2026-07-19); re-validated when
  partner migration planning starts. Owner: VP of Engineering.
- **A-3 · Pain baselines still unquantified.** Outage count and
  firefighting hours/week remain `(estimated)`/`(guessed)` from the BRD's
  open question; they affect narrative baselines only, never a target.
  Owner: VP of Engineering.

Gap register (typed records; a blocker left `(open)` shuts the gate — none
here are blockers):

```yaml
- id: GAP-001
  type: number
  severity: minor
  question: "What capture overhead on production is acceptable? Proposed
    default: feed-on vs feed-off adds < 5% to production's p95 latency
    under like-for-like load."
  blocks: "the acceptance threshold of R-2's overhead clause (its
    zero-analytical-queries clause is unaffected)"
  owner: "VP of Engineering"
  resolution: "RESOLVED 2026-07-19 (D6, Round 3): <= 20% added p95 latency
    hard ceiling, 15% working target — deliberate loosening of the 5%
    default (feed judged business-critical); re-examined at Pass 3 when
    the capture mechanism is chosen"
- id: GAP-002
  type: number
  severity: minor
  question: "What is the target time for the local end-to-end loop?
    Proposed default: <= 15 minutes from fresh checkout to a verified
    change."
  blocks: "the acceptance threshold of R-7 (the loop itself is required
    regardless)"
  owner: "VP of Engineering"
  resolution: "RESOLVED 2026-07-19 (D7, Round 3): <= 15 minutes confirmed
    for phase one (v1)"
- id: GAP-003
  type: scope
  severity: minor
  question: "Per-partner migration sequencing — who moves first, and in
    what order? (The flip moment itself is settled: after the last
    partner, D3.)"
  blocks: "execution planning of R-5, not its acceptance criteria"
  owner: "VP of Engineering"
  resolution: "RESOLVED 2026-07-19 (D8, Round 3): migration in ELECTED
    WAVES — partners selected into waves; wave composition and order
    decided at migration planning, not in this spec (a process rule;
    R-5's acceptance criteria never depended on the order)"
```

## Sign-off

- **Owner/decider:** VP of Engineering (Luan Moreno, persona) — verdict: **approved — canonical**
- **Date:** 2026-07-19

Gate H1 taken: verdict given 2026-07-19 ("I guess it's canonical — content
polished and well-matured"), conditional on an agentic-execution review;
the review returned SUFFICIENT-WITH-FIXES and all blocker/should-fix edits
were applied before this signature (B-2 analytical-query definition, B-3
Q-SET-1 oracle, B-4 p99 normative, S-1..S-7, N-1..N-4). Record:
`brain/decisions/2026-07-19-pass1-round3-gap-resolutions.md` + this block.
