# BRD — Fixture: deploy runbook (canonical, DevOps domain)

## Executive summary
Deploys are slow and risky; a hardened runbook fixes the fear.

## Problem
Production deploys take 4 hours (measured) of hand-holding each, and about
2 rollbacks/month (estimated) burn the on-call rotation.

## Goals
- KPI-1 — deploy duration: 4 hours → under 30 minutes.

## Scope
**In:**
- a repeatable deploy runbook with a rollback drill
**Out:**
- replatforming the runtime

## Definition of success
A deploy is boring: under 30 minutes, rollback rehearsed, three months running.

## Stakeholders
- Platform Lead — owner and decider.

## Risks
- Nobody reads the reports. Accepted with a usage check.

## Constraints
- $500/month ceiling.

## Open questions
- question: verify the 2 rollbacks/month figure from the incident log
  owner: Platform Lead

## Source
Synthetic fixture for the Pass 0 gate regression suite.

## Sign-off
- Owner/decider: Platform Lead — verdict: **approved — canonical**
- Date: 2026-07-19
