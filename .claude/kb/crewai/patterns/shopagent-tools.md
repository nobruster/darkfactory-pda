# ShopAgent MCP Tools

> **Purpose**: Custom tools connecting CrewAI agents to Supabase (SQL) and Qdrant (semantic search)
> **MCP Validated**: 2026-04-12

## When to Use

- Building the AnalystAgent tool that queries The Ledger (Supabase/Postgres)
- Building the ResearchAgent tool that searches The Memory (Qdrant)
- Registering tools to specific agents so each agent only accesses its designated store
- Switching between local Docker endpoints and cloud URLs via environment variables

## Implementation

```python
"""ShopAgent MCP tools — Supabase SQL and Qdrant semantic search."""
import json
import os
from typing import Any, ClassVar, Type

import httpx
from crewai.tools import BaseTool, tool
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint


# ---------------------------------------------------------------------------
# Tool 1: Supabase SQL Executor (The Ledger)
# ---------------------------------------------------------------------------

@tool("Supabase SQL Executor")
def supabase_execute_sql(query: str) -> str:
    """Execute a SQL query against the ShopAgent Postgres database.
    Use this to get exact metrics: revenue, order counts, customer segments.
    Available tables: customers, products, orders.
    Always write SELECT queries. Never mutate data."""
    url = os.getenv("SUPABASE_URL", "http://localhost:54321")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not key:
        return "Error: SUPABASE_SERVICE_KEY not set"

    try:
        resp = httpx.post(
            f"{url}/rest/v1/rpc/execute_sql",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=30.0,
        )
        resp.raise_for_status()
        rows: list[dict[str, Any]] = resp.json()
        if not rows:
            return "Query returned no results."
        # Format as pipe-delimited table for the agent
        headers = list(rows[0].keys())
        lines = [" | ".join(headers)]
        lines += [" | ".join(str(row.get(h, "")) for h in headers) for row in rows]
        return "\n".join(lines)
    except httpx.HTTPStatusError as exc:
        return f"SQL error {exc.response.status_code}: {exc.response.text}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


# ---------------------------------------------------------------------------
# Tool 2: Qdrant Semantic Search (The Memory)
# ---------------------------------------------------------------------------

class QdrantSearchInput(BaseModel):
    query: str = Field(..., description="Natural language query to search customer reviews")
    top_k: int = Field(default=5, description="Number of review results to return")


class QdrantSemanticSearchTool(BaseTool):
    """Search customer reviews in Qdrant using semantic similarity."""

    name: str = "Qdrant Semantic Search"
    description: str = (
        "Search customer reviews stored in Qdrant using semantic similarity. "
        "Use this to find complaints, sentiment themes, and customer feedback. "
        "The collection 'reviews' contains review_id, order_id, rating, comment, sentiment."
    )
    args_schema: ClassVar[Type[BaseModel]] = QdrantSearchInput

    def _run(self, query: str, top_k: int = 5) -> str:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        embed_url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        embed_key = os.getenv("SUPABASE_SERVICE_KEY", "")

        try:
            # Embed the query via the same Supabase/OpenAI integration
            embed_resp = httpx.post(
                f"{embed_url}/functions/v1/embed",
                headers={"Authorization": f"Bearer {embed_key}"},
                json={"input": query},
                timeout=15.0,
            )
            embed_resp.raise_for_status()
            vector: list[float] = embed_resp.json()["embedding"]
        except Exception as exc:
            return f"Embedding error: {exc}"

        try:
            client = QdrantClient(url=qdrant_url)
            hits: list[ScoredPoint] = client.search(
                collection_name="reviews",
                query_vector=vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            return f"Qdrant search error: {exc}"

        if not hits:
            return "No reviews found for this query."

        lines: list[str] = []
        for hit in hits:
            payload = hit.payload or {}
            rating = payload.get("rating", "?")
            sentiment = payload.get("sentiment", "unknown")
            comment = payload.get("comment", "")
            score = round(hit.score, 3)
            lines.append(f"[score={score} | rating={rating} | sentiment={sentiment}] {comment}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Exported instances — imported by crew.py
# ---------------------------------------------------------------------------

supabase_tool = supabase_execute_sql
qdrant_tool = QdrantSemanticSearchTool()
```

## Configuration

| Setting | Env Var | Local Default | Description |
|---------|---------|---------------|-------------|
| Supabase URL | `SUPABASE_URL` | `http://localhost:54321` | Postgres REST endpoint |
| Supabase key | `SUPABASE_SERVICE_KEY` | — | Service role key (never expose) |
| Qdrant URL | `QDRANT_URL` | `http://localhost:6333` | Vector DB endpoint |
| Embedding endpoint | `SUPABASE_URL` + `/functions/v1/embed` | Same host | Supabase Edge Function for embeddings |
| Top-K results | `top_k` param | `5` | Number of semantic review hits |

## Tool-to-Agent Registration

```python
from shopagent.tools import supabase_tool, qdrant_tool

analyst = Agent(
    config=agents_config["analyst"],
    tools=[supabase_tool],   # The Ledger only
)
researcher = Agent(
    config=agents_config["researcher"],
    tools=[qdrant_tool],     # The Memory only
)
reporter = Agent(
    config=agents_config["reporter"],
    tools=[],                # Synthesizes from context — no direct store access
)
```

## See Also

- [ShopAgent Crew](../patterns/shopagent-crew.md)
- [YAML Configuration](../patterns/yaml-configuration.md)
- [Qdrant Concepts](../../qdrant/index.md)
- [Supabase Concepts](../../supabase/index.md)
