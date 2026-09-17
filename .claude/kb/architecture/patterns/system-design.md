# System Design

> **Purpose**: End-to-end system design process with structured methodology and diagram templates
> **MCP Validated**: 2026-02-17

## When to Use

- Designing a new system or major subsystem from scratch
- Conducting system design reviews or architecture workshops
- Documenting existing system architecture for new team members
- Preparing architecture proposals for stakeholder approval

## Implementation

### System Design Process

```text
================================================================
SYSTEM DESIGN DOCUMENT
================================================================
System: [System Name]
Author: [Name]
Date: YYYY-MM-DD
Version: [1.0]
Status: [Draft | Review | Approved]
================================================================

1. REQUIREMENTS
───────────────────────────────────────────────────
  Functional:
  - FR-1: [The system shall...]
  - FR-2: [The system shall...]
  - FR-3: [The system shall...]

  Non-Functional:
  - NFR-1: Availability >= 99.9%
  - NFR-2: Latency p99 < 500ms
  - NFR-3: Throughput >= 1000 req/s
  - NFR-4: Data retention >= 90 days

  Constraints:
  - Cloud: [GCP | AWS | Azure]
  - Budget: [Monthly limit]
  - Compliance: [GDPR | SOC2 | HIPAA]
  - Team size: [N engineers]

2. HIGH-LEVEL ARCHITECTURE
───────────────────────────────────────────────────

  ┌─────────┐     ┌──────────────┐     ┌─────────────┐
  │ Clients │────>│ API Gateway  │────>│  Services   │
  │ Web/App │     │ (Auth, Rate  │     │  Layer      │
  └─────────┘     │  Limiting)   │     └──────┬──────┘
                  └──────────────┘            │
                                     ┌───────┼───────┐
                                     │       │       │
                               ┌─────┴──┐ ┌──┴────┐ ┌┴───────┐
                               │Service │ │Service│ │Service │
                               │   A    │ │   B   │ │   C    │
                               └───┬────┘ └───┬───┘ └───┬────┘
                                   │          │         │
                               ┌───┴──────────┴─────────┴───┐
                               │      Data Layer             │
                               │  ┌────────┐  ┌───────────┐ │
                               │  │  DB    │  │  Cache    │ │
                               │  └────────┘  └───────────┘ │
                               └─────────────────────────────┘

3. COMPONENT BREAKDOWN
───────────────────────────────────────────────────
  ┌──────────────┬───────────────┬────────────────┐
  │ Component    │ Responsibility│ Technology     │
  ├──────────────┼───────────────┼────────────────┤
  │ API Gateway  │ Auth, routing │ Cloud Run      │
  │ Service A    │ Core logic    │ Python/FastAPI │
  │ Service B    │ Data process  │ Python/Celery  │
  │ Service C    │ Notifications │ Cloud Functions│
  │ Database     │ Persistence   │ Cloud SQL      │
  │ Cache        │ Hot data      │ Redis/Memorystore│
  │ Queue        │ Async work    │ Pub/Sub        │
  │ Storage      │ Files/blobs   │ GCS            │
  └──────────────┴───────────────┴────────────────┘

4. DATA FLOW
───────────────────────────────────────────────────

  Request Flow (Synchronous):
  Client -> Gateway -> Service A -> DB -> Response

  Event Flow (Asynchronous):
  Service A -> Pub/Sub -> Service B -> DB
                      └-> Service C -> Notification

  Data Flow Diagram:
  ┌────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐
  │ Ingest ├───>│ Process ├───>│  Store  ├───>│Query │
  │ (API)  │    │(Transform)   │  (DB)   │    │(API) │
  └────────┘    └─────────┘    └─────────┘    └──────┘
       │                            │
       v                            v
  ┌─────────┐                 ┌──────────┐
  │  Queue  │                 │  Backup  │
  │(Pub/Sub)│                 │  (GCS)   │
  └─────────┘                 └──────────┘

5. FAILURE MODES
───────────────────────────────────────────────────
  ┌─────────────────┬──────────────┬──────────────┐
  │ Failure         │ Impact       │ Mitigation   │
  ├─────────────────┼──────────────┼──────────────┤
  │ DB unavailable  │ Full outage  │ Read replica │
  │ Service crash   │ Partial      │ Auto-restart │
  │ Queue backlog   │ Latency      │ Auto-scale   │
  │ Cache miss storm│ DB overload  │ Circuit break│
  │ Region failure  │ Full outage  │ Multi-region │
  └─────────────────┴──────────────┴──────────────┘

6. CAPACITY ESTIMATION
───────────────────────────────────────────────────
  Users: [N] DAU
  Requests: [N] req/sec (peak: [N*3])
  Storage: [N] GB/month growth
  Bandwidth: [N] GB/month

  Compute sizing:
  - Service A: [N] instances x [size]
  - Service B: [N] instances x [size]
  - Database: [size] with [N] read replicas

================================================================
```

## Architecture Diagram Templates

### Serverless Event-Driven (GCP)

```text
┌──────────┐    ┌─────────┐    ┌───────────┐    ┌──────────┐
│   GCS    ├───>│ Pub/Sub ├───>│ Cloud Run ├───>│ BigQuery │
│ (Upload) │    │ (Event) │    │ (Process) │    │ (Store)  │
└──────────┘    └────┬────┘    └─────┬─────┘    └──────────┘
                     │               │
                     │          ┌────┴─────┐
                     │          │ Langfuse │
                     │          │ (Monitor)│
                     │          └──────────┘
                     │
                ┌────┴─────┐
                │ Dead     │
                │ Letter Q │
                └──────────┘
```

### Multi-Tier Web Application

```text
┌─────────┐   ┌───────────┐   ┌──────────┐   ┌──────────┐
│  CDN    │   │   Load    │   │  App     │   │  Cache   │
│(Static) │   │ Balancer  │   │ Servers  │   │ (Redis)  │
└─────────┘   └─────┬─────┘   └────┬─────┘   └────┬─────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                  │
                           ┌──────┴──────┐
                           │  Database   │
                           │  Primary +  │
                           │  Replicas   │
                           └─────────────┘
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Design doc sections | 6 | Requirements through Capacity |
| Review rounds | 2 | Design review iterations |
| Diagram format | ASCII | Portable, version-controllable |
| Capacity buffer | 3x | Design for 3x current peak |

## Example Usage

To create a system design, follow these steps:

1. Gather requirements (functional + non-functional)
2. Sketch high-level architecture (boxes and arrows)
3. Break down into components with technology choices
4. Map data flows (sync and async paths)
5. Identify failure modes and mitigations
6. Estimate capacity and cost

Each step produces a section of the design document above.

## See Also

- [Design Patterns](../concepts/design-patterns.md)
- [Scalability](../concepts/scalability.md)
- [Implementation Plan](../patterns/implementation-plan.md)
- [Trade-off Analysis](../patterns/trade-off-analysis.md)
