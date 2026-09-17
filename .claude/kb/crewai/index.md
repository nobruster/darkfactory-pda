# CrewAI Knowledge Base

> **Purpose**: Multi-agent AI orchestration framework for ShopAgent e-commerce analysis
> **MCP Validated**: 2026-02-17

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/agents.md](concepts/agents.md) | Agent definition, roles, goals, backstory |
| [concepts/crews.md](concepts/crews.md) | Crew composition and execution |
| [concepts/tasks.md](concepts/tasks.md) | Task specification and assignment |
| [concepts/tools.md](concepts/tools.md) | Tool integration with BaseTool and @tool |
| [concepts/memory.md](concepts/memory.md) | Short-term, long-term, entity memory |
| [concepts/processes.md](concepts/processes.md) | Sequential and hierarchical processes |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/shopagent-crew.md](patterns/shopagent-crew.md) | 3-agent ShopAgent crew (Analyst + Researcher + Reporter) |
| [patterns/shopagent-tools.md](patterns/shopagent-tools.md) | MCP tools for Supabase SQL and Qdrant semantic search |
| [patterns/yaml-configuration.md](patterns/yaml-configuration.md) | agents.yaml and tasks.yaml configuration |
| [patterns/chainlit-crewai.md](patterns/chainlit-crewai.md) | Chainlit conversational UI integration |
| [patterns/evaluation-observability.md](patterns/evaluation-observability.md) | DeepEval testing + LangFuse traces |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/crewai-config.yaml](specs/crewai-config.yaml) | Full configuration reference spec |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Agent** | LLM-powered process with role, goal, backstory, and tools |
| **Task** | Actionable unit assigned to an agent with expected output |
| **Crew** | Team of agents collaborating on tasks via a process |
| **Tool** | External capability registered to agents (SQL, semantic search) |
| **Memory** | Persistent context across short-term, long-term, entity stores |
| **Process** | Execution strategy: sequential or hierarchical |

---

## ShopAgent Architecture

| Agent | Role | Tool | Store |
|-------|------|------|-------|
| AnalystAgent | SQL data analyst | supabase_execute_sql | The Ledger (Postgres) |
| ResearchAgent | Customer experience researcher | qdrant_semantic_search | The Memory (Qdrant) |
| ReporterAgent | Executive report writer | (synthesis only) | Both via context |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/agents.md, concepts/tasks.md, concepts/crews.md |
| **Intermediate** | concepts/tools.md, concepts/memory.md, concepts/processes.md |
| **Advanced** | patterns/shopagent-crew.md, patterns/evaluation-observability.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| crewai-specialist | All files | CrewAI implementation and debugging |
| shopagent-builder | patterns/shopagent-crew.md | ShopAgent Day 4 build |
| genai-architect | patterns/shopagent-crew.md | Multi-agent architecture design |
