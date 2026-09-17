# BRD — Fixture: '## Problematic' must not satisfy '## Problem'

<!-- The v0.4.0 seam: v0.3.1's substring heading match let '## Problematic'
     stand in for the required '## Problem' section. v0.4.0 anchors headings
     exactly (name + whitespace or end of line), so this must FAIL with
     'section missing: Problem'. Everything else here is canonical-complete. -->

## Executive summary
Reports are slow and manual; a reporting lane fixes the wait.

## Problematic
Monthly reports take 3 days (measured) to assemble by hand, and the delay
costs roughly $2,000/month (estimated) in analyst time.

**If we build nothing:** reports keep arriving late and decisions wait.

## Goals
- KPI-1 — report turnaround: 3 days → under 1 hour.

## Scope
**In:**
- a reporting lane fed from the operational records
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
