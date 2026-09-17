# BRD — Fixture: impossible sign-off date (canonical verdict, invalid ISO)

<!-- The S7 seam: the verdict is genuinely canonical but the sign-off date
     is 9999-99-99 — month 99, day 99. v0.3.0's [0-9]{4}-[0-9]{2}-[0-9]{2}
     accepted it and PASSED. v0.3.1 must FAIL: a fabricated date cannot
     anchor the descent. Everything else here is canonical-complete. -->

## Executive summary
Invoice matching is manual; a matching lane fixes the toil.

## Problem
Invoice matching takes 2 days (measured) per cycle and costs roughly
$1,500/month (estimated) in finance time.

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
- Finance Lead — owner and decider.

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
- Owner/decider: Finance Lead — verdict: **approved — canonical**
- Date: 9999-99-99
