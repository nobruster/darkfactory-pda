# CrewAI Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Installation

| Command | Purpose |
|---------|---------|
| `pip install crewai` | Core framework |
| `pip install 'crewai[tools]'` | Framework + built-in tools |
| `crewai create crew my_project` | Scaffold new project |

## Core Components

| Component | Class | Key Parameters |
|-----------|-------|----------------|
| Agent | `Agent` | `role`, `goal`, `backstory`, `tools`, `llm`, `memory` |
| Task | `Task` | `description`, `expected_output`, `agent`, `tools`, `context` |
| Crew | `Crew` | `agents`, `tasks`, `process`, `memory`, `verbose` |

## ShopAgent Crew

| Agent | Tool | Store |
|-------|------|-------|
| AnalystAgent | `supabase_execute_sql` | Postgres (The Ledger) |
| ResearchAgent | `qdrant_semantic_search` | Qdrant (The Memory) |
| ReporterAgent | (none — synthesis) | Both via task context |

## Process Types

| Process | Use Case | Manager Required |
|---------|----------|------------------|
| `Process.sequential` | ShopAgent default (Analyst → Researcher → Reporter) | No |
| `Process.hierarchical` | Manager delegates to agents dynamically | Yes (`manager_llm`) |

## Memory Types

| Type | Storage | Scope |
|------|---------|-------|
| Short-Term | ChromaDB + RAG | Current session |
| Long-Term | SQLite3 | Cross-session persistence |
| Entity | ChromaDB + RAG | Products, customers, segments |

## Key Decorators

| Decorator | Target | Purpose |
|-----------|--------|---------|
| `@CrewBase` | Class | Auto-load YAML config |
| `@agent` | Method | Define agent from config |
| `@task` | Method | Define task from config |
| `@crew` | Method | Define crew assembly |
| `@tool` | Function | Create custom tool |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| ShopAgent standard report | Sequential, single crew |
| Complex open-ended investigation | Hierarchical with manager |
| Need agents to remember past queries | `memory=True` on Crew |
| Custom Supabase/Qdrant integration | `@tool` or `BaseTool` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Skip `expected_output` on tasks | Always define structured output |
| Use hierarchical without `manager_llm` | Set `manager_llm` or `manager_agent` |
| Give all tools to all agents | Register tools to specialist agents only |
| Enable memory without embedder config | Set embedder when using non-OpenAI LLMs |
| Hardcode LLM in agents | Use env vars or YAML config |

## Related Documentation

| Topic | Path |
|-------|------|
| ShopAgent Crew | `patterns/shopagent-crew.md` |
| MCP Tools | `patterns/shopagent-tools.md` |
| YAML Config | `patterns/yaml-configuration.md` |
| Chainlit Integration | `patterns/chainlit-crewai.md` |
| Evaluation + Observability | `patterns/evaluation-observability.md` |
