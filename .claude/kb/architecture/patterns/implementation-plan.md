# Implementation Plan

> **Purpose**: Multi-phase implementation plan template with milestones, dependencies, and risk mitigation
> **MCP Validated**: 2026-02-17

## When to Use

- Breaking a large system design into deliverable phases
- Coordinating multi-team implementation with dependencies
- Providing stakeholders with timeline and milestone visibility
- Managing risk through incremental delivery and validation gates

## Implementation

### Phase Planning Template

```text
================================================================
PROJECT: [Project Name]
OWNER: [Team/Person]
START: [YYYY-MM-DD]    TARGET: [YYYY-MM-DD]
STATUS: [Planning | In Progress | Complete]
================================================================

PHASE 1: FOUNDATION                        [Weeks 1-2]
────────────────────────────────────────────────────────
  Objectives:
  - [ ] Set up repository and CI/CD pipeline
  - [ ] Define core data models and interfaces
  - [ ] Provision infrastructure (IaC)
  - [ ] Establish monitoring and alerting baseline

  Deliverables:
  - Working CI/CD with automated tests
  - Infrastructure deployed to dev environment
  - Core interfaces documented

  Exit Criteria:
  - All team members can build and deploy locally
  - CI pipeline passes on main branch
  - Infrastructure provisioned via Terraform

  Risks:
  | Risk                    | Impact | Likelihood | Mitigation         |
  |-------------------------|--------|------------|--------------------|
  | Infra provisioning delay| Medium | Low        | Pre-approved quotas|
  | Unclear requirements    | High   | Medium     | Spike in Week 1    |

────────────────────────────────────────────────────────
PHASE 2: CORE FUNCTIONALITY                [Weeks 3-6]
────────────────────────────────────────────────────────
  Objectives:
  - [ ] Implement primary business logic
  - [ ] Build data ingestion pipeline
  - [ ] Integrate with external dependencies
  - [ ] Write integration tests

  Dependencies:
  - Phase 1 exit criteria met
  - External API access credentials available
  - Data schemas finalized

  Deliverables:
  - End-to-end data flow working in staging
  - Integration test suite (>80% coverage on core paths)
  - Performance baseline established

  Exit Criteria:
  - Happy path works end-to-end in staging
  - No P0/P1 bugs open
  - Performance meets SLO targets

────────────────────────────────────────────────────────
PHASE 3: HARDENING                         [Weeks 7-8]
────────────────────────────────────────────────────────
  Objectives:
  - [ ] Error handling and edge cases
  - [ ] Load testing and performance optimization
  - [ ] Security review and remediation
  - [ ] Documentation and runbooks

  Deliverables:
  - Load test results showing system handles 3x expected load
  - Security review sign-off
  - Operations runbook complete

  Exit Criteria:
  - All P0/P1/P2 bugs resolved
  - Load test passes at target capacity
  - Runbook reviewed by on-call team

────────────────────────────────────────────────────────
PHASE 4: LAUNCH                            [Weeks 9-10]
────────────────────────────────────────────────────────
  Objectives:
  - [ ] Canary deployment (5% traffic)
  - [ ] Progressive rollout (25% -> 50% -> 100%)
  - [ ] Monitor error rates and latency
  - [ ] Retrospective and lessons learned

  Rollback Criteria:
  - Error rate > 1% (auto-rollback)
  - Latency p99 > 2x baseline (manual review)
  - Any data corruption detected (immediate rollback)

================================================================
```

## Dependency Tracking

```text
DEPENDENCY MAP:

Phase 1 ──────> Phase 2 ──────> Phase 3 ──────> Phase 4
   │                │                │
   │   ┌────────────┘                │
   │   │                             │
   │   v                             │
   │  External API ──────────────────┘
   │  Onboarding
   │
   └──> CI/CD Pipeline (blocks all subsequent phases)

CRITICAL PATH: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4
PARALLEL WORK: External API onboarding (during Phase 1-2)
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Phase duration | 2 weeks | Standard sprint length per phase |
| Buffer | 20% | Schedule buffer for unknowns |
| Checkpoint frequency | Weekly | Stakeholder sync cadence |
| Rollback window | 24 hours | Time to revert after launch |

## Milestone Tracking

```text
MILESTONE TRACKER:
┌─────────────┬────────────┬────────────┬──────────┐
│ Milestone   │ Target     │ Actual     │ Status   │
├─────────────┼────────────┼────────────┼──────────┤
│ Infra ready │ Week 2     │            │ On track │
│ Core E2E    │ Week 6     │            │ Pending  │
│ Load test   │ Week 8     │            │ Pending  │
│ GA launch   │ Week 10    │            │ Pending  │
└─────────────┴────────────┴────────────┴──────────┘
```

## Risk Matrix

```text
              HIGH IMPACT
                  │
    ┌─────────────┼─────────────┐
    │  MITIGATE   │  PREVENT    │
    │  (plan B)   │  (block)    │
    │             │             │
LOW ├─────────────┼─────────────┤ HIGH
LIKELIHOOD        │             LIKELIHOOD
    │  ACCEPT     │  MONITOR    │
    │  (log it)   │  (watch)    │
    │             │             │
    └─────────────┼─────────────┘
                  │
              LOW IMPACT
```

## See Also

- [System Design](../patterns/system-design.md)
- [Trade-off Analysis](../patterns/trade-off-analysis.md)
- [Design Patterns](../concepts/design-patterns.md)
