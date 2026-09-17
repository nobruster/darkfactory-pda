# Trade-off Analysis

> **Purpose**: Structured decision matrix pattern for evaluating architectural alternatives
> **MCP Validated**: 2026-02-17

## When to Use

- Choosing between two or more architectural approaches
- Evaluating build vs buy decisions
- Selecting between cloud services or deployment strategies
- Any decision where multiple quality attributes are in tension

## Implementation

### Trade-off Analysis Template

```text
================================================================
ARCHITECTURE DECISION RECORD (ADR)
================================================================
Title: ADR-{NNN}: [Decision Title]
Date: YYYY-MM-DD
Status: [Proposed | Accepted | Superseded by ADR-XXX]
Deciders: [Names/Roles]
================================================================

CONTEXT:
  [2-3 sentences describing the problem and why a decision is needed]

CONSTRAINTS:
  - [Non-negotiable requirement 1]
  - [Non-negotiable requirement 2]
  - [Budget/timeline/compliance constraint]

CANDIDATES:
  A: [Option A name] - [1-line summary]
  B: [Option B name] - [1-line summary]
  C: [Option C name] - [1-line summary]

EVALUATION MATRIX:
┌──────────────────┬────────┬──────────┬──────────┬──────────┐
│ Criterion        │ Weight │ Option A │ Option B │ Option C │
├──────────────────┼────────┼──────────┼──────────┼──────────┤
│ [Criterion 1]    │   W1   │  S (W*S) │  S (W*S) │  S (W*S) │
│ [Criterion 2]    │   W2   │  S (W*S) │  S (W*S) │  S (W*S) │
│ [Criterion 3]    │   W3   │  S (W*S) │  S (W*S) │  S (W*S) │
│ [Criterion 4]    │   W4   │  S (W*S) │  S (W*S) │  S (W*S) │
│ [Criterion 5]    │   W5   │  S (W*S) │  S (W*S) │  S (W*S) │
├──────────────────┼────────┼──────────┼──────────┼──────────┤
│ TOTAL            │  100%  │  TOTAL_A │  TOTAL_B │  TOTAL_C │
└──────────────────┴────────┴──────────┴──────────┴──────────┘
  S = Score (1-5), W*S = Weighted Score

DECISION: [Option X]

RATIONALE:
  [2-3 sentences explaining why this option was chosen]

CONSEQUENCES:
  Positive:
  - [Benefit 1]
  - [Benefit 2]
  Negative:
  - [Trade-off accepted 1]
  - [Trade-off accepted 2]
  Risks:
  - [Risk 1 and mitigation]

REVIEW DATE: [When to revisit this decision]
================================================================
```

## Worked Example: Message Queue Selection

```text
================================================================
ADR-007: Message Queue for Event-Driven Pipeline
Date: 2026-02-17
Status: Proposed
================================================================

CONTEXT:
  We need an async message queue for our data pipeline. The system
  processes ~10K events/min with occasional bursts to 50K/min.
  Messages must be durable and support at-least-once delivery.

CONSTRAINTS:
  - Must run on GCP (existing infrastructure)
  - Budget: < $500/month at current scale
  - Team has no Kafka operational experience

EVALUATION MATRIX:
┌──────────────────┬────────┬──────────────┬──────────────┬──────────────┐
│ Criterion        │ Weight │ GCP Pub/Sub  │ Cloud Tasks  │ Self-hosted  │
│                  │        │              │              │ Kafka        │
├──────────────────┼────────┼──────────────┼──────────────┼──────────────┤
│ Team expertise   │  25%   │ 4 (1.00)     │ 3 (0.75)     │ 1 (0.25)     │
│ Ops overhead     │  25%   │ 5 (1.25)     │ 5 (1.25)     │ 1 (0.25)     │
│ Throughput       │  20%   │ 4 (0.80)     │ 2 (0.40)     │ 5 (1.00)     │
│ Cost at scale    │  15%   │ 3 (0.45)     │ 4 (0.60)     │ 2 (0.30)     │
│ Feature fit      │  15%   │ 4 (0.60)     │ 3 (0.45)     │ 5 (0.75)     │
├──────────────────┼────────┼──────────────┼──────────────┼──────────────┤
│ TOTAL            │ 100%   │ 4.10         │ 3.45         │ 2.55         │
└──────────────────┴────────┴──────────────┴──────────────┴──────────────┘

DECISION: GCP Pub/Sub

RATIONALE:
  Highest weighted score driven by team expertise and zero ops
  overhead. Throughput is sufficient for 50K/min bursts. Kafka
  would offer more features but operational cost is prohibitive.

CONSEQUENCES:
  Positive:
  - Zero infrastructure management
  - Native GCP IAM integration
  Negative:
  - 7-day message retention limit (vs unlimited in Kafka)
  - Less control over partitioning
  Risks:
  - Cost at very high scale (>1M msg/min) -- revisit at that point
================================================================
```

## Common Trade-off Pairs

| Tension | Option A | Option B | Resolution Strategy |
|---------|----------|----------|---------------------|
| Consistency vs Availability | Strong consistency | Eventual consistency | Choose per use case (CAP) |
| Speed vs Safety | Move fast, break things | Thorough review process | Risk-based: fast for low-risk |
| Build vs Buy | Custom solution | SaaS/managed service | Buy commodity, build differentiators |
| Simplicity vs Flexibility | Opinionated framework | Unopinionated library | Match to team skill level |
| Cost vs Performance | Cheaper, slower | Expensive, faster | Define SLO, spend to meet it |
| Coupling vs Autonomy | Shared libraries | Duplicated code | Shared for stable, duplicate for volatile |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Criteria count | 5-7 | More than 7 dilutes signal |
| Score range | 1-5 | Consistent scale across all criteria |
| Weight total | 100% | Must sum to exactly 100% |
| Review cadence | Quarterly | Re-evaluate major decisions |

## See Also

- [Technology Selection](../concepts/technology-selection.md)
- [Implementation Plan](../patterns/implementation-plan.md)
- [System Design](../patterns/system-design.md)
