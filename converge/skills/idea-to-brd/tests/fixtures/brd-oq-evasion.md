# BRD — Fixture: open questions outside the record shape (fails closed)

<!-- The S2 seam: the Open questions section carries a real, unowned
     question — but written as a numbered bold line instead of the
     '- question:' / 'owner:' record shape. v0.3.0 counted this as "none
     recorded" and PASSED (fail-open). v0.3.1 must FAIL CLOSED in canonical
     mode (draft: advisory): the gate cannot verify ownership of what it
     cannot parse. Everything else here is canonical-complete. -->

## Executive summary
Release notes are assembled by hand; a changelog lane fixes the toil.

## Problem
Release notes take 3 hours (measured) per release, twice a month, roughly
$900/month (estimated) of engineer time.

## Goals
- KPI-1 — notes assembly: 3 hours → under 15 minutes.

## Scope
**In:**
- a changelog lane fed from merged work
**Out:**
- rewriting the release process

## Definition of success
Notes assemble themselves in minutes, three releases running.

## Stakeholders
- Release Manager — owner and decider.

## Risks
- Nobody reads the notes. Accepted with an open-rate check.

## Constraints
- $200/month ceiling.

## Open questions
1. **Question:** does marketing also consume these notes? (owner: ???)

## Source
Synthetic fixture for the Pass 0 gate regression suite.

## Sign-off
- Owner/decider: Release Manager — verdict: **approved — canonical**
- Date: 2026-07-19
