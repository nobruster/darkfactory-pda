# BRD — Fixture: reporting lane (canonical, data domain)

## Executive summary
Reports are slow and manual; a reporting lane fixes the wait.

## Problem
Monthly reports take 3 days (measured) to assemble by hand, and the delay
costs roughly $2,000/month (guessed) in analyst time.

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

None — nothing open.

## Source
Synthetic fixture for the Pass 0 gate regression suite.

## Sign-off
- Owner/decider: Head of Data — verdict: **approved — canonical**
- Date: 2026-07-19
