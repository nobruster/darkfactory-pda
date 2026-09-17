# Technology Selection

> **Purpose**: Structured framework for evaluating and selecting technologies
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Technology selection is the disciplined process of choosing tools, frameworks, languages,
and platforms based on weighted criteria rather than hype or familiarity. Poor technology
choices compound over years, while good choices amplify team productivity. The key is to
make trade-offs explicit and decisions reversible where possible.

## The Framework

```text
┌──────────────────────────────────────────────────┐
│           TECHNOLOGY SELECTION PROCESS            │
├──────────────────────────────────────────────────┤
│  1. Define Requirements (functional + non-func)  │
│  2. Identify Candidates (3-5 options)            │
│  3. Define Weighted Criteria                     │
│  4. Score Each Candidate                         │
│  5. Validate with Spike/PoC                      │
│  6. Record Decision (ADR)                        │
└──────────────────────────────────────────────────┘
```

## Evaluation Criteria

### Must-Have Criteria (Go/No-Go)

| Criterion | Question | Disqualify If |
|-----------|----------|---------------|
| License | Compatible with our project? | GPL in proprietary product |
| Security | Known unpatched CVEs? | Critical CVEs, no maintainer |
| Platform | Runs on our target infra? | No support for our cloud/OS |
| Compliance | Meets regulatory requirements? | Cannot meet data residency |

### Weighted Scoring Criteria

| Criterion | Weight | Score 1-5 | Description |
|-----------|--------|-----------|-------------|
| Team expertise | 25% | 1=none, 5=expert | Current team proficiency |
| Community health | 20% | 1=dead, 5=thriving | Contributors, releases, docs |
| Performance fit | 15% | 1=poor, 5=exceeds | Benchmarks for our workload |
| Operational cost | 15% | 1=expensive, 5=cheap | TCO: license + infra + people |
| Migration ease | 10% | 1=locked-in, 5=portable | Effort to switch away |
| Integration | 10% | 1=isolated, 5=rich | Ecosystem compatibility |
| Learning curve | 5% | 1=steep, 5=trivial | Time to first productive use |

## Decision Matrix Template

```text
Technology Selection: [DECISION TITLE]
Date: YYYY-MM-DD
Status: [Proposed | Accepted | Deprecated]

Candidates:
┌─────────────────┬────────┬──────────┬──────────┬──────────┐
│ Criterion (Wt)  │ Wt     │ Option A │ Option B │ Option C │
├─────────────────┼────────┼──────────┼──────────┼──────────┤
│ Team expertise  │ 25%    │ 4 (1.00) │ 3 (0.75) │ 2 (0.50) │
│ Community       │ 20%    │ 4 (0.80) │ 5 (1.00) │ 3 (0.60) │
│ Performance     │ 15%    │ 3 (0.45) │ 4 (0.60) │ 5 (0.75) │
│ Cost            │ 15%    │ 4 (0.60) │ 3 (0.45) │ 4 (0.60) │
│ Migration ease  │ 10%    │ 3 (0.30) │ 4 (0.40) │ 2 (0.20) │
│ Integration     │ 10%    │ 5 (0.50) │ 4 (0.40) │ 3 (0.30) │
│ Learning curve  │  5%    │ 4 (0.20) │ 3 (0.15) │ 2 (0.10) │
├─────────────────┼────────┼──────────┼──────────┼──────────┤
│ TOTAL           │ 100%   │ 3.85     │ 3.75     │ 3.05     │
└─────────────────┴────────┴──────────┴──────────┴──────────┘

Decision: Option A
Rationale: Highest weighted score; team already proficient.
```

## Red Flags in Technology Choices

| Red Flag | Risk | Mitigation |
|----------|------|------------|
| No release in 12+ months | Abandoned project | Check GitHub pulse, forks |
| Single maintainer | Bus factor = 1 | Evaluate fork-ability |
| No production references | Unproven at scale | Require PoC with load test |
| Requires major refactor | High adoption cost | Spike first, estimate effort |
| Vendor lock-in, no export | Trapped if pricing changes | Demand data portability |

## Common Mistakes

### Wrong

Selecting a technology because "it is popular on Hacker News" or because one engineer
is enthusiastic about it, without evaluating against team-wide criteria or conducting
a proof-of-concept spike.

### Correct

Run a structured evaluation with weighted criteria, validate the top candidate with
a time-boxed spike (1-2 days), and record the decision as an Architecture Decision
Record (ADR) with context, options considered, and consequences.

## Related

- [Design Patterns](../concepts/design-patterns.md)
- [Trade-off Analysis](../patterns/trade-off-analysis.md)
- [Implementation Plan](../patterns/implementation-plan.md)
