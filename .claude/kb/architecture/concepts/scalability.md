# Scalability

> **Purpose**: Strategies for scaling systems to handle growth in load, data, and users
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Scalability is the ability of a system to handle increased load without degradation in
performance or availability. Scaling strategies fall into two categories: vertical (bigger
machines) and horizontal (more machines). The right approach depends on the bottleneck type,
cost constraints, and consistency requirements.

## Scaling Dimensions

```text
┌─────────────────────────────────────────────────┐
│              SCALING DIMENSIONS                  │
├─────────────┬─────────────┬─────────────────────┤
│   Compute   │   Storage   │     Network         │
│  CPU / RAM  │  Disk / DB  │   Bandwidth / CDN   │
├─────────────┼─────────────┼─────────────────────┤
│  Scale up   │  Partition  │   Edge caching      │
│  Scale out  │  Replicate  │   Load balancing     │
│  Auto-scale │  Tier       │   Multi-region       │
└─────────────┴─────────────┴─────────────────────┘
```

## Vertical vs Horizontal Scaling

| Aspect | Vertical (Scale Up) | Horizontal (Scale Out) |
|--------|--------------------|-----------------------|
| Method | Bigger machine | More machines |
| Limit | Hardware ceiling | Coordination complexity |
| Cost curve | Linear then exponential | Linear (commodity HW) |
| Downtime | Usually required | Zero-downtime possible |
| Consistency | Simple (single node) | Requires coordination |
| Best for | Databases, legacy apps | Stateless services, web tier |

## Common Scaling Strategies

### 1. Caching Layers

```text
┌────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│ Client ├───>│   CDN    ├───>│  App     ├───>│  DB    │
└────────┘    │ (Edge)   │    │  Cache   │    │        │
              │ Static   │    │ (Redis)  │    │        │
              └──────────┘    └──────────┘    └────────┘
              TTL: hours      TTL: minutes    Source of truth
```

| Cache Layer | Latency | Hit Rate Target | Invalidation |
|-------------|---------|-----------------|--------------|
| Browser/CDN | < 10ms | > 90% static | TTL-based |
| Application (Redis) | < 5ms | > 80% hot data | Write-through / Event |
| Database query cache | < 1ms | > 70% | Auto on write |

### 2. Database Scaling

```text
                  ┌──────────────┐
                  │   Primary    │
                  │   (Write)    │
                  └──────┬───────┘
                         │ Replication
              ┌──────────┼──────────┐
              │          │          │
        ┌─────┴────┐ ┌──┴───────┐ ┌┴─────────┐
        │ Replica 1│ │ Replica 2│ │ Replica 3│
        │ (Read)   │ │ (Read)   │ │ (Read)   │
        └──────────┘ └──────────┘ └──────────┘
```

| Strategy | When to Use | Complexity |
|----------|------------|------------|
| Read replicas | Read-heavy workloads (>5:1 read/write) | Low |
| Vertical partition | Different access patterns per table group | Medium |
| Horizontal shard | Single table > 1TB or > 50k writes/sec | High |
| CQRS split | Separate read/write models needed | High |

### 3. Horizontal Compute Scaling

```text
              ┌────────────────┐
              │ Load Balancer  │
              └───┬────┬────┬──┘
                  │    │    │
            ┌─────┴┐ ┌┴────┴┐ ┌──────┐
            │Node 1│ │Node 2│ │Node N│
            └──────┘ └──────┘ └──────┘
            Stateless instances (auto-scaled)
```

| Scaling Signal | Metric | Auto-scale Rule |
|---------------|--------|-----------------|
| CPU utilization | > 70% avg | Add instance per 20% over |
| Request queue depth | > 100 pending | Add instance per 50 pending |
| Memory usage | > 80% | Add instance (or scale up) |
| Custom metric | Latency p99 > SLO | Add instance |

## Scalability Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Shared mutable state | Contention, locks | Stateless services + external store |
| Synchronous chains | Cascading latency | Async messaging, circuit breakers |
| Unbounded queries | DB resource exhaustion | Pagination, query limits |
| No backpressure | Overload cascades | Rate limiting, queue-based intake |
| Premature optimization | Wasted effort | Measure first, scale the bottleneck |

## Common Mistakes

### Wrong

Sharding a database at 100GB because "we might grow" -- adding massive operational
complexity (cross-shard joins, rebalancing) without evidence of need.

### Correct

Start with read replicas and caching. Monitor query performance. Shard only when
vertical scaling and read replicas are insufficient, and design the shard key
based on actual access patterns (not theoretical future patterns).

## Related

- [Design Patterns](../concepts/design-patterns.md)
- [System Design](../patterns/system-design.md)
- [Trade-off Analysis](../patterns/trade-off-analysis.md)
