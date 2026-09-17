# System Architecture Quick Reference

> Fast lookup tables. For detailed explanations, see linked files.
> **MCP Validated:** 2026-02-17

## Architecture Patterns at a Glance

| Pattern | Best For | Complexity | Scalability |
|---------|----------|------------|-------------|
| Monolith | MVPs, small teams | Low | Vertical |
| Layered | Enterprise CRUD apps | Low-Medium | Vertical |
| Microservices | Large teams, independent deploy | High | Horizontal |
| Event-Driven | Async workflows, decoupling | Medium-High | Horizontal |
| CQRS | Read/write asymmetry | High | Horizontal |
| Hexagonal | Testability, port swapping | Medium | Depends |
| Serverless | Bursty workloads, low ops | Medium | Auto |

## Quality Attributes (the "-ilities")

| Attribute | Metric | Typical Target |
|-----------|--------|----------------|
| Availability | Uptime % | 99.9% (8.7h/yr downtime) |
| Latency | p99 response time | < 500ms API, < 100ms cache |
| Throughput | Requests/sec | Varies by workload |
| Durability | Data loss tolerance | RPO < 1 hour |
| Maintainability | Change lead time | < 1 day for standard changes |

## Scaling Decision Matrix

| Signal | Strategy | Action |
|--------|----------|--------|
| CPU saturated | Vertical then horizontal | Scale up instance, then add replicas |
| Memory pressure | Vertical + caching | Add RAM, introduce Redis/Memcached |
| I/O bottleneck | Partitioning | Shard database, use read replicas |
| Traffic spikes | Auto-scaling | Configure HPA or serverless |
| Global latency | Distribution | Multi-region deploy, CDN, edge |

## Technology Selection Criteria

| Criterion | Weight | Questions to Ask |
|-----------|--------|------------------|
| Team expertise | High | Can the team ship with this in 2 weeks? |
| Community/support | High | Active maintainers? Stack Overflow answers? |
| Operational cost | Medium | TCO over 3 years? |
| Performance fit | Medium | Benchmarks for our workload? |
| Lock-in risk | Low-Med | Can we migrate away in < 1 quarter? |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Choose microservices for a 3-person team | Start monolith, extract services when needed |
| Optimize before measuring | Profile first, optimize the bottleneck |
| Pick tech because it is trending | Evaluate against weighted criteria matrix |
| Design for 10x current scale day one | Design for 3x, plan for 10x |
| Skip trade-off documentation | Record every ADR with context and consequences |

## CAP Theorem Quick Check

| Guarantee Pair | Sacrifice | Example Systems |
|----------------|-----------|-----------------|
| CP (Consistency + Partition) | Availability | HBase, MongoDB (strict) |
| AP (Availability + Partition) | Consistency | Cassandra, DynamoDB |
| CA (Consistency + Availability) | Partition tolerance | Traditional RDBMS (single node) |

## Related Documentation

| Topic | Path |
|-------|------|
| Design Patterns | `concepts/design-patterns.md` |
| Technology Selection | `concepts/technology-selection.md` |
| Scalability | `concepts/scalability.md` |
| Implementation Planning | `patterns/implementation-plan.md` |
| Trade-off Analysis | `patterns/trade-off-analysis.md` |
| Full Index | `index.md` |
