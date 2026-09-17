# BRD — The Analytical Backbone (phase one of the modernization)

> Captured via Converge Pass 0 (frontier-rounds interview, 2026-07-17).
> Owner's voice throughout. No requirements, no solution shape, no technology
> decisions — those belong to the passes below.

## Executive summary

Partners fire their analytical questions at our operational database — the
only place data lives — and it's crashing under them while the business
flies blind. Phase one: a standalone, near-real-time analytical backbone
partners plug into; production then gets locked to analytical traffic.
Ceiling $1,000/month. Unlocks data-driven prioritization and the AI-first
phase two.

## Problem

Our operational database is the only place our data lives, so everyone —
including our partners — goes there for answers. Partners have plugged their
analytical questions directly into the operational system, and that load is
crashing it: we have had several outages (estimated), and three days ago a
major one took us offline with 3-4 hours (estimated) spent rescuing data. The
team carries a growing firefighting burden on top of normal operations —
hours per week currently unknown (guessed); see open questions.

Underneath the outages sits the real problem: we have no analytical backbone
at all. The business has no complete sight of what happens inside its own
operational system, so feature priorities are decided on gut feel while our
competitors are already analyzing their operations and pushing frontiers.

**If we build nothing:** the operational system keeps taking analytical
traffic it was never meant to serve, the outages continue, and the business
stays blind — prioritization stays gut-driven, the data-driven and AI-first
ambitions stay locked, and competitors keep pulling ahead. That cost is not
tolerable; this brief exists instead of a no-go record.

## Goals & KPIs

- **KPI-1 — time to answer.** A business question about our operations is
  answered in **under 1 hour** — today it takes days or is simply impossible
  without querying production directly.
- **KPI-2 — production untouched.** Analytical traffic on the operational
  database goes from **all of it today → zero** once consumers are moved to
  the backbone and production is locked.
- **KPI-3 — decisions from data.** Feature-priority decisions backed by
  backbone analytics: **0 today → at least 1** within phase one.
- **Freshness.** Answers reflect the operational system **close to
  real-time** — day-old batch answers will not make anyone leave production
  alone. This is acknowledged as the hard part of the problem.

## Scope

**In:**
- A standalone analytical backbone, completely separate from the operational
  database, fed from our four operational domains (customers, products,
  orders, payments) **without adding load to production**.
- Near-real-time freshness of the data in the backbone.
- Partners plug into the backbone as consumers — moving their analytical
  traffic off production is part of phase one (low-hanging fruit: the only
  reason they are on production is that nothing else exists).
- Locking production away from analytical consumers once the backbone is
  established (hard requirement, born from the pre-mortem).
- Running end-to-end in production, with the team able to build and evolve
  it locally first.

**Out:**
- Any change to the operational system itself beyond the access lockdown
  (no scaling it up, no re-architecting it).
- The AI capabilities — explicitly **phase two**, unlocked by this backbone.
- The silent-failure / incident-detection idea — parked as its own one-line
  stub for a separate brief.

**Undecided:** none material — the freshness boundary was resolved to
near-real-time during capture.

## Definition of success

Three months from now: the analytical backbone runs end-to-end in
production; operational data flows into it close to real-time; questions
that used to hit the operational database are answered from the backbone in
under an hour; production takes zero analytical traffic and is locked to
analytical consumers; and at least one feature-priority decision has been
made because of something the backbone showed us.

## Stakeholders

- **VP of Engineering — owner and decider.** Six months in seat; gathered
  this need from the whole team; vision: unlock the analytical backbone to
  become data-driven and AI-first. Breaks all ties.
- **Partner integration teams** — today's involuntary cause of the pain,
  tomorrow's first-class consumers of the backbone.
- **Operations / on-call team** — carries the outage and firefighting burden.
- **Business / product leadership** — consumes the analytics to reorder the
  roadmap.

## Risks

From the pre-mortem ("it shipped and failed — what killed it?"):

- **Partners keep querying production anyway.** Not accepted — mitigated by
  the hard requirement above: once the backbone stands, production access is
  locked for analytical consumers.
- **Cost outgrows the phase-one budget as the backbone evolves.** Accepted
  in writing: $1,000/month is the phase-one ceiling; the owner deliberately
  plans to add horsepower, capacity, and budget as adoption grows.
- **The business never looks at the analytics and the roadmap stays
  gut-driven.** Accepted with a check: KPI-3 / the success definition
  requires at least one real decision from backbone data in phase one.

## Constraints

- **Budget: $1,000/month total (measured — hard ceiling for phase one).**
- Small team, no new hires.
- The team must be able to test and change everything **locally and
  rapidly** — iteration speed is a hard business requirement given team
  size.
- Phase one must land fast enough to justify phase two (no fixed date
  given).

## Open questions

- question: put real numbers on the pain — outage count/frequency to date and
  firefighting hours per week (currently estimated/guessed)
  owner: VP of Engineering
- question: owner's stack preference, recorded verbatim for Pass 3 — DuckDB
  locally for the MVP, MotherDuck for production, dbt for transformations, a
  change-data-capture mechanism reading the operational database's
  write-ahead log (to be verified), Docker-based local development;
  orchestration engine unnamed. Preference, not a decision — Converge
  grounds and decides the stack at Pass 3.
  owner: VP of Engineering
- question: partner migration mechanics — sequencing and the moment the
  production lockdown flips on
  owner: VP of Engineering

## Source

Converge Pass 0 frontier-rounds interview, 2026-07-17 — three rounds, voice,
Luan Moreno answering as owner (VP of Engineering persona). Terrain read
before questioning: the operational PostgreSQL (customers,
products, orders, payments; deterministic seed 42), `src/README.md` (the
analytical lane explicitly does not exist yet). Parked stub from
scope-check: silent-failure detection idea (own BRD later).

## Sign-off

- **Owner/decider:** VP of Engineering (Luan Moreno, persona) — verdict: **approved — canonical**
- **Date:** 2026-07-19
