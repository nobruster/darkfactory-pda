# Tasks

> **Purpose**: Define actionable units of work assigned to agents with structured outputs
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

A Task is the actionable unit that an agent executes within a crew. Each task has a description, expected output, and is assigned to a specific agent. Tasks can depend on other tasks via the `context` parameter, enabling data flow between pipeline stages. Tasks support structured output via Pydantic models.

## The Pattern

```python
from crewai import Task, Agent
from pydantic import BaseModel
from typing import List

class ShopAgentReport(BaseModel):
    time_period: str
    total_revenue: float
    order_count: int
    top_segment: str
    top_complaint: str
    recommendations: List[str]

analyst = Agent(role="E-Commerce Data Analyst", goal="...", backstory="...")

analysis_task = Task(
    description=(
        "Query Supabase Postgres for revenue totals, order counts, and top customer "
        "segments for {time_period}. Return exact figures from SQL results only."
    ),
    expected_output="Revenue total, order count, and top segment with SQL evidence",
    agent=analyst,
    output_pydantic=ShopAgentReport,
)
```

## Quick Reference

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `description` | str | required | What the agent should do |
| `expected_output` | str | required | What the output should look like |
| `agent` | Agent | `None` | Agent assigned to execute |
| `tools` | list | `[]` | Task-specific tools (override agent) |
| `context` | list[Task] | `[]` | Upstream tasks providing input |
| `output_pydantic` | BaseModel | `None` | Structured output model |
| `output_json` | type | `None` | JSON output schema |
| `output_file` | str | `None` | Write output to file |
| `async_execution` | bool | `False` | Run asynchronously |
| `human_input` | bool | `False` | Require human approval |
| `callback` | callable | `None` | Post-execution hook |

## YAML Configuration

```yaml
# config/tasks.yaml
analysis_task:
  description: >
    Query Supabase Postgres for revenue totals, order counts, and top customer
    segments for {time_period}. Return exact SQL results — no estimates.
  expected_output: >
    Revenue total, order count, payment method distribution,
    and top customer segment with supporting SQL query result.
  agent: analyst

research_task:
  description: >
    Search Qdrant review vectors for customer complaints and sentiment
    themes in {time_period}. Surface top issues with supporting evidence.
  expected_output: >
    Top 3 complaint themes, average sentiment score, and satisfaction drivers
    with representative review excerpts.
  agent: researcher
  context:
    - analysis_task

report_task:
  description: >
    Write an executive e-commerce report combining SQL metrics and review insights.
    Include revenue highlights, sentiment summary, and actionable recommendations.
  expected_output: >
    Structured executive report with revenue section, customer sentiment section,
    and 3-5 prioritized recommendations.
  agent: reporter
  context:
    - analysis_task
    - research_task
```

## Task Context and Structured Output

```python
# ShopAgent flow: analysis → research → report (with Pydantic output)
from pydantic import BaseModel, Field
from typing import List, Literal

class ShopAgentReport(BaseModel):
    total_revenue: float = Field(description="Total revenue in BRL")
    order_count: int = Field(description="Total confirmed orders")
    top_segment: str = Field(description="Highest-revenue customer segment")
    sentiment: Literal["positive", "neutral", "negative"]
    top_complaint: str = Field(description="Most frequent complaint theme")
    recommendations: List[str] = Field(description="Prioritized action items")

analysis_task = Task(
    description="Query revenue and order metrics for {time_period}",
    expected_output="Revenue totals and order counts from SQL",
    agent=analyst,
)
research_task = Task(
    description="Search reviews for sentiment and complaint themes",
    expected_output="Top complaint themes with sentiment scores",
    agent=researcher,
    context=[analysis_task],  # receives SQL metrics as context
)
report_task = Task(
    description="Synthesize metrics and sentiment into executive report",
    expected_output="Structured report with revenue, sentiment, recommendations",
    agent=reporter,
    context=[analysis_task, research_task],  # receives both outputs
    output_pydantic=ShopAgentReport,
)
```

## Common Mistakes

### Wrong

```python
# Missing expected_output leads to unfocused agent behavior
task = Task(description="Check the orders", agent=analyst)
```

### Correct

```python
task = Task(
    description="Query total revenue and order count for the last 30 days from Supabase",
    expected_output="JSON with total_revenue (float), order_count (int), and top_segment (str)",
    agent=analyst,
)
```

## Related

- [Agents](../concepts/agents.md)
- [Crews](../concepts/crews.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
