# Tools

> **Purpose**: Integrate external capabilities into agents via BaseTool and @tool decorator
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

CrewAI Tools are external capabilities registered to agents at runtime. Tools give agents deterministic access to APIs, databases, file systems, and services. There are two ways to create tools: the `@tool` decorator for simple functions and subclassing `BaseTool` for complex integrations. The `crewai-tools` package provides built-in tools.

## The Pattern

```python
from crewai.tools import tool
import psycopg2
import os

@tool("Supabase SQL Executor")
def supabase_execute_sql(query: str) -> str:
    """Execute a SQL query against the Supabase Postgres Ledger and return results.
    Use this when you need exact revenue totals, order counts, customer segments,
    or any structured e-commerce metric that requires a SQL query."""
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    conn.close()
    return str([dict(zip(columns, row)) for row in rows])
```

## Quick Reference

| Approach | Best For | Complexity |
|----------|----------|------------|
| `@tool` decorator | Simple stateless functions | Low |
| `BaseTool` subclass | Stateful, validated inputs | Medium |
| Built-in tools | Common operations | None |

## BaseTool Pattern

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Filter
import os

class QdrantSearchInput(BaseModel):
    query: str = Field(description="Natural language query to search review vectors")
    top_k: int = Field(default=5, description="Number of top results to return")

class QdrantSemanticSearch(BaseTool):
    name: str = "Qdrant Semantic Search"
    description: str = (
        "Search customer review vectors in Qdrant (The Memory) using semantic similarity. "
        "Returns the most relevant reviews for a given topic, complaint, or sentiment query."
    )
    args_schema: type[BaseModel] = QdrantSearchInput

    def _run(self, query: str, top_k: int = 5) -> str:
        client = QdrantClient(url=os.environ["QDRANT_URL"])
        results = client.query(
            collection_name="reviews",
            query_text=query,
            limit=top_k,
        )
        return str([
            {"score": r.score, "comment": r.document, "sentiment": r.metadata.get("sentiment")}
            for r in results
        ])
```

## Built-in Tools

| Tool | Package | Purpose |
|------|---------|---------|
| `SerperDevTool` | crewai-tools | Web search |
| `ScrapeWebsiteTool` | crewai-tools | Web scraping |
| `FileReadTool` | crewai-tools | Read files |
| `DirectoryReadTool` | crewai-tools | List directory |
| `CodeInterpreterTool` | crewai-tools | Execute code |
| `JSONSearchTool` | crewai-tools | Search JSON/RAG |

## Registering Tools to Agents

```python
from crewai import Agent

# AnalystAgent: SQL access to The Ledger
analyst = Agent(
    role="E-Commerce Data Analyst",
    goal="Query Supabase for exact revenue and order metrics",
    backstory="...",
    tools=[supabase_execute_sql],
)

# ResearchAgent: semantic search in The Memory
researcher = Agent(
    role="Customer Experience Researcher",
    goal="Surface sentiment and complaint themes from review vectors",
    backstory="...",
    tools=[QdrantSemanticSearch()],
)

# Tools can also be set at task level (overrides agent tools)
task = Task(
    description="Query total revenue for the last 30 days",
    expected_output="Revenue total from Supabase SQL",
    agent=analyst,
    tools=[supabase_execute_sql],  # Only this tool available
)
```

## Common Mistakes

### Wrong

```python
# Missing docstring means agents cannot decide when to use the tool
@tool("My Tool")
def my_tool(x: str) -> str:
    return x.upper()
```

### Correct

```python
@tool("Supabase SQL Executor")
def supabase_execute_sql(query: str) -> str:
    """Execute a SQL query against Supabase Postgres and return row results as a list of dicts.
    Use this when you need exact figures: revenue totals, order counts, or segment breakdowns."""
    ...
```

## Related

- [Agents](../concepts/agents.md)
- [Tasks](../concepts/tasks.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
