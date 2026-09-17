# BRD — Fixture: sign-off date 2026-02-31 (calendar-impossible)

<!-- The v0.4.0 seam: the verdict is genuinely canonical and the date has a
     valid ISO SHAPE (month 02, day 31), but February 31st does not exist.
     v0.3.1's regex accepted it; v0.4.0's python3 datetime check must FAIL:
     a fabricated date cannot anchor the descent. Everything else here is
     canonical-complete. -->

## Executive summary
Invoice matching is manual; a matching lane fixes the toil.

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
- Date: 2026-02-31
