# Tech-Spec — Fixture: fenced sign-off example must not authorize

## Problem restated

Broken CI runs sit unnoticed for 45 minutes (measured) before anyone
reacts, and each week roughly 6 hours (estimated) of engineer time goes to
re-running failed pipelines by hand.

## Scope

**In scope:**
- a recovery lane that watches pipeline runs and acts on failures
**Out of scope:**
- rewriting the CI system itself

## Requirements

- **R-1 (must).** A failed run is detected within 2 minutes of failure,
  measured failure-timestamp -> detection-timestamp, p95 <= 2 minutes.
- **R-2 (should).** Weekly hand-triage time drops to under 1 hour.

## Success metrics

| Metric | Current | Target |
|---|---|---|
| Time to detect a failed run | 45 minutes | -> under 2 minutes |

## Data named

The lane consumes pipeline run records and job logs — run id, status,
duration, failing step — exactly as the CI system emits them.

## Open assumptions

- The CI system's webhook stream is reliable enough to build on.
  owner: Platform Lead

## Source

The example below shows what a SIGNED spec's block will look like once the
owner approves — an illustration, not a verdict:

```markdown
## Sign-off
- Owner/decider: Platform Lead — verdict: **approved — canonical**
- Date: 2026-07-19
```

## Sign-off

- **Owner/decider:** Platform Lead — verdict: pending — still reviewing
- **Date:** (unset)
