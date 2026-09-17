# BRD — Fixture: content-free scope bullets are not entries

<!-- The v0.4.0 seam: v0.3.1 counted any non-blank line as a scope entry, so
     '- none' satisfied the In side. v0.4.0 rejects bullets whose text is
     empty, 'nothing', 'none', or 'n/a' — this must FAIL with
     'Scope: In has no entries'. Everything else here is canonical-complete. -->

## Executive summary
Reports are slow and manual; a reporting lane fixes the wait.

## Problem
Monthly reports take 3 days (measured) to assemble by hand, and the delay
costs roughly $2,000/month (estimated) in analyst time.

**If we build nothing:** reports keep arriving late and decisions wait.

## Goals
- KPI-1 — report turnaround: 3 days → under 1 hour.

## Scope
**In:**
- none
- N/A
**Out:**
- rebuilding the source system

## Definition of success
A report that took days lands in under an hour, three months running.

## Stakeholders
- Head of Data — owner and decider.

## Risks
- Nobody reads the reports. Accepted with a usage check.

## Constraints
- $500/month ceiling.

## Open questions
- question: verify the $2,000/month analyst-time figure
  owner: Head of Data

## Source
Synthetic fixture for the Pass 0 gate regression suite.

## Sign-off
- Owner/decider: Head of Data — verdict: **approved — canonical**
- Date: 2026-07-19
