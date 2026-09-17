# Memory

> **Purpose**: Enable agents to retain context across tasks and sessions for ShopAgent cross-session learning
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

CrewAI Memory allows agents to retain historical context during and across task executions. There are three built-in memory types: Short-Term Memory (session context via ChromaDB), Long-Term Memory (cross-session persistence via SQLite3), and Entity Memory (structured knowledge about entities via ChromaDB). Memory is enabled at the crew level and shared across all agents in that crew.

## The Pattern

```python
from crewai import Crew, Agent, Task, Process

analyst = Agent(
    role="E-Commerce Data Analyst",
    goal="Extract revenue and order metrics, learning which SQL queries produce reliable results",
    backstory="You query Supabase Postgres and remember which queries returned accurate figures.",
    tools=[supabase_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)

researcher = Agent(
    role="Customer Experience Researcher",
    goal="Surface complaint themes from reviews, recalling patterns from past searches",
    backstory="You search Qdrant and remember which review themes recur across analysis runs.",
    tools=[qdrant_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)

crew = Crew(
    agents=[analyst, researcher],
    tasks=[...],
    process=Process.sequential,
    memory=True,  # Enables STM, LTM, and Entity memory
    verbose=True,
)

result = crew.kickoff(inputs={"time_period": "last 30 days"})
```

## Quick Reference

| Memory Type | Storage | Embeddings | Scope |
|-------------|---------|------------|-------|
| Short-Term (STM) | ChromaDB | Yes (RAG) | Current session |
| Long-Term (LTM) | SQLite3 | No | Cross-session |
| Entity | ChromaDB | Yes (RAG) | People, systems, concepts |

## Custom Embedder Configuration

```python
crew = Crew(
    agents=[analyst, researcher],
    tasks=[...],
    process=Process.sequential,
    memory=True,
    embedder={
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
        },
    },
    verbose=True,
)
```

## Memory Reset Operations

```python
# Reset specific memory types
crew.reset_memories(command_type="short")     # Short-term
crew.reset_memories(command_type="long")      # Long-term
crew.reset_memories(command_type="entity")    # Entity
crew.reset_memories(command_type="knowledge") # Knowledge store
```

## Storage Configuration

```bash
# Default: platform-specific via appdirs package
# Custom: set environment variable
export CREWAI_STORAGE_DIR="/data/crewai/memory"
```

## ShopAgent Memory Use Case

```python
# STM: current analysis session context (SQL results, review themes found)
# LTM: cross-run learning (which SQL queries work, which complaint themes recur)
# Entity: knowledge about segments (e.g., "Premium segment drives 40% of revenue")

crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.sequential,
    memory=True,
    embedder={
        "provider": "openai",
        "config": {"model": "text-embedding-3-small"},
    },
)

# First run: learns revenue patterns and top complaint themes
crew.kickoff(inputs={"time_period": "last 30 days"})

# Second run: recalls which SQL queries were reliable and which
# complaint themes appeared before — faster, more focused analysis
crew.kickoff(inputs={"time_period": "last 7 days"})
```

## Common Mistakes

### Wrong

```python
# Enabling memory without an embedder when using non-OpenAI models
crew = Crew(agents=[a], tasks=[t], memory=True, llm="anthropic/claude-sonnet-4-20250514")
```

### Correct

```python
# Explicitly set embedder when not using OpenAI as primary LLM
crew = Crew(
    agents=[a], tasks=[t], memory=True,
    embedder={"provider": "openai", "config": {"model": "text-embedding-3-small"}},
)
```

## Related

- [Crews](../concepts/crews.md)
- [Agents](../concepts/agents.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
