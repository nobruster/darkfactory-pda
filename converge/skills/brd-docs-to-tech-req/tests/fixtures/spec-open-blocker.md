# Tech-Spec — Fixture: CI pipeline recovery lane (canonical, DevOps domain)

## Problem restated

Broken CI runs sit unnoticed for 45 minutes (measured) before anyone
reacts, and each week roughly 6 hours (estimated) of engineer time goes to
re-running and bisecting failed pipelines by hand. Solved means failures
are detected, triaged, and either auto-retried or escalated within a known
time bound.

## Scope

**In scope:**
- a recovery lane that watches pipeline runs and acts on failures
**Out of scope:**
- rewriting the CI system itself
- flaky-test elimination (its own brief)

## Requirements

- **R-1 (must).** A failed run is detected within 2 minutes of failure,
  measured failure-timestamp -> detection-timestamp, p95 <= 2 minutes.
- **R-2 (must).** Transient failures are retried at most 2 times; a run
  that fails 3 times escalates within 5 minutes to the on-call owner.
- **R-3 (should).** Weekly hand-triage time drops to under 1 hour.

## Success metrics

| Metric | Current | Target |
|---|---|---|
| Time to detect a failed run | 45 minutes | -> under 2 minutes |
| Weekly hand-triage time | 6 hours | -> under 1 hour |

## Data named

The lane consumes pipeline run records and job logs — the run id, status,
duration, and failing step — exactly as the CI system emits them.

## Open assumptions

- The CI system's webhook stream is reliable enough to build on.
  owner: Platform Lead

## Gap register

```yaml
- id: GAP-001
  type: number
  severity: blocker
  question: "Retry budget per day?"
  blocks: "R-2 acceptance"
  owner: "Platform Lead"
  resolution: (open)
```

## Sign-off

- **Owner/decider:** Platform Lead — verdict: **approved — canonical**
- **Date:** 2026-07-19
