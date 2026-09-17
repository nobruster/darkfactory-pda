# Design Patterns

> **Purpose**: Common architecture patterns for structuring systems at different scales
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Architecture patterns are proven structural blueprints that define how system components
are organized, communicate, and evolve. Choosing the right pattern depends on team size,
deployment constraints, scalability requirements, and the nature of the domain. Each pattern
makes explicit trade-offs between complexity, flexibility, and operational overhead.

## Pattern Catalog

### 1. Layered (N-Tier)

```text
┌─────────────────────────┐
│    Presentation Layer    │  UI, API Gateway
├─────────────────────────┤
│    Business Logic Layer  │  Services, Rules
├─────────────────────────┤
│    Data Access Layer     │  Repositories, ORM
├─────────────────────────┤
│    Database Layer        │  PostgreSQL, BigQuery
└─────────────────────────┘
```

- **When**: CRUD-heavy applications, clear separation of concerns
- **Trade-off**: Simple to understand but tight vertical coupling

### 2. Microservices

```text
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Service A │  │ Service B │  │ Service C │
│  (Users)  │  │ (Orders)  │  │(Payments) │
└─────┬─────┘  └─────┬─────┘  └─────┬─────┘
      │              │              │
      └──────────────┼──────────────┘
                     │
              ┌──────┴──────┐
              │  API Gateway │
              │  / Mesh      │
              └─────────────┘
```

- **When**: Large teams (>20 engineers), independent deployment needed
- **Trade-off**: Operational complexity for deployment independence

### 3. Event-Driven

```text
┌──────────┐     ┌───────────────┐     ┌──────────┐
│ Producer │────>│  Message Bus  │────>│ Consumer │
│ Service  │     │ (Pub/Sub,     │     │ Service  │
└──────────┘     │  Kafka, SQS)  │     └──────────┘
                 └───────┬───────┘
                         │
                 ┌───────┴───────┐
                 │   Consumer    │
                 │   Service 2   │
                 └───────────────┘
```

- **When**: Asynchronous workflows, decoupled producers/consumers
- **Trade-off**: Eventual consistency for loose coupling

### 4. CQRS (Command Query Responsibility Segregation)

```text
         ┌─────────────┐
         │   Client     │
         └──┬───────┬───┘
   Write    │       │   Read
   ┌────────┴──┐ ┌──┴────────┐
   │  Command  │ │   Query   │
   │  Service  │ │  Service  │
   └─────┬─────┘ └─────┬─────┘
         │              │
   ┌─────┴─────┐ ┌─────┴─────┐
   │ Write DB  │ │  Read DB  │
   │ (Primary) │ │ (Replica) │
   └───────────┘ └───────────┘
```

- **When**: Read/write ratio > 10:1, different read/write models
- **Trade-off**: Complexity for read/write optimization

### 5. Hexagonal (Ports & Adapters)

```text
              ┌──────────────────┐
   Adapters   │                  │   Adapters
  ┌────────┐  │   Domain Core    │  ┌────────┐
  │REST API├──┤                  ├──┤  DB    │
  └────────┘  │  Business Logic  │  └────────┘
  ┌────────┐  │  (Pure, no I/O)  │  ┌────────┐
  │  CLI   ├──┤                  ├──┤ Queue  │
  └────────┘  │   Ports define   │  └────────┘
              │   interfaces     │
              └──────────────────┘
```

- **When**: High testability needed, multiple input/output channels
- **Trade-off**: Abstraction overhead for flexibility

## Pattern Selection Guide

| Factor | Monolith/Layered | Microservices | Event-Driven | Hexagonal |
|--------|-----------------|---------------|--------------|-----------|
| Team size | 1-10 | 10+ | Any | Any |
| Deploy frequency | Weekly | Daily/hourly | Event-based | Any |
| Data consistency | Strong | Eventual | Eventual | Strong |
| Testing ease | Medium | Hard (integration) | Hard (async) | Easy |
| Initial velocity | Fast | Slow | Medium | Medium |

## Common Mistakes

### Wrong

Choosing microservices for a new project with a team of 3 engineers, leading to
excessive operational overhead, network debugging, and slow feature delivery.

### Correct

Start with a well-structured monolith using clean boundaries (modules/packages).
Extract services only when you have evidence: team scaling, independent deploy needs,
or different scaling requirements per component.

## Related

- [Technology Selection](../concepts/technology-selection.md)
- [Scalability](../concepts/scalability.md)
- [System Design](../patterns/system-design.md)
