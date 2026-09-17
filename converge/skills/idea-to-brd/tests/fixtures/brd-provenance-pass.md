# BRD — Fixture: per-line provenance PASS (leap-day sign-off, hygiene WARNs)

<!-- The v0.4.0 positive: every numbered Problem line carries its tag on the
     line, and the sign-off date is 2024-02-29 — a REAL leap day the
     calendar check must accept. This fixture also deliberately trips two
     hygiene WARNs that must stay advisory (never fail): a >60-word
     executive summary and no named decider. -->

## Executive summary
Invoice matching is done by hand at month-end, and the finance team loses
days to it every cycle while vendors wait on answers. A matching lane takes
over the repetitive pairing work so the team spends its time on the
exceptions that actually need judgment. The pain is measured in days per
cycle and dollars per month, and success is a cycle that closes in hours
instead of days.

## Problem
Invoice matching takes 2 days (measured) per cycle and costs roughly
$1,500/month (estimated) in finance time.

**If we build nothing:** the toil continues and month-end keeps slipping.

## Goals
- KPI-1 — matching cycle: 2 days → under 2 hours.

## Scope
**In:**
- a matching lane over incoming invoices
**Out:**
- replacing the accounting tool

## Definition of success
A cycle that took days lands in under two hours, three cycles running.

## Stakeholders
- Finance Lead — owner.

## Risks
- Edge-case invoices pile up. Accepted with a weekly exception review.

## Constraints
- $300/month ceiling.

## Open questions
- question: verify the $1,500/month finance-time figure
  owner: Finance Lead

## Source
Synthetic fixture for the Pass 0 gate regression suite.

## Sign-off
- Owner: Finance Lead — verdict: **approved — canonical**
- Date: 2024-02-29
