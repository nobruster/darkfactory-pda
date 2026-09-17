# Processes

> **Purpose**: Control execution flow with sequential and hierarchical process strategies
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

CrewAI Processes define how tasks are distributed and executed within a crew. There are two process types: Sequential (tasks run one after another in order) and Hierarchical (a manager agent coordinates and delegates tasks to workers). The process type determines the collaboration pattern between agents.

## The Pattern

```python
from crewai import Crew, Process

# Sequential: tasks execute in list order
sequential_crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.sequential,
    verbose=True,
)

# Hierarchical: manager delegates tasks to best-fit agents
hierarchical_crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.hierarchical,
    manager_llm="anthropic/claude-sonnet-4-20250514",
    verbose=True,
)
```

## Quick Reference

| Feature | Sequential | Hierarchical |
|---------|------------|--------------|
| Execution order | Fixed (list order) | Manager decides |
| Manager required | No | Yes |
| Delegation | No delegation | Manager delegates |
| Task reassignment | Not supported | Manager can reassign |
| Best for | Linear workflows | Complex decision trees |
| Predictability | High | Medium |
| Token cost | Lower | Higher (manager overhead) |

## Sequential Process

```python
from crewai import Agent, Task, Crew, Process

# ShopAgent: analyst → researcher → reporter (fixed order)
analyst = Agent(
    role="E-Commerce Data Analyst",
    goal="Query Supabase Postgres for revenue, order counts, and customer segments",
    backstory="Expert SQL analyst — every number comes from a verified query result.",
    tools=[supabase_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)
researcher = Agent(
    role="Customer Experience Researcher",
    goal="Surface sentiment and complaint themes from Qdrant review vectors",
    backstory="Searches The Memory to identify recurring customer issues.",
    tools=[qdrant_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)
reporter = Agent(
    role="Executive Report Writer",
    goal="Synthesize SQL metrics and review insights into actionable executive reports",
    backstory="Combines structured ledger data and qualitative feedback into clear briefs.",
    llm="anthropic/claude-sonnet-4-20250514",
)

analysis_task = Task(description="Query revenue and orders for last 30 days", expected_output="...", agent=analyst)
research_task = Task(description="Search reviews for complaint themes", expected_output="...", agent=researcher, context=[analysis_task])
report_task = Task(description="Write executive e-commerce report", expected_output="...", agent=reporter, context=[analysis_task, research_task])

crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.sequential,
)
result = crew.kickoff(inputs={"time_period": "last 30 days"})
```

## Hierarchical Process

```python
from crewai import Agent, Task, Crew, Process

# Manager decides which specialist handles each analysis need
crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.hierarchical,
    manager_llm="anthropic/claude-sonnet-4-20250514",
    verbose=True,
)

# Or use a custom manager agent
shop_manager = Agent(
    role="ShopAgent Orchestrator",
    goal="Coordinate e-commerce analysis and ensure complete reports",
    backstory="You oversee the ShopAgent crew, delegating to specialists.",
)
crew = Crew(
    agents=[analyst, researcher, reporter], tasks=[analysis_task, research_task, report_task],
    process=Process.hierarchical, manager_agent=shop_manager,
)
```

## Choosing a Process

| Scenario | Recommended |
|----------|-------------|
| Standard e-commerce report (SQL → reviews → report) | Sequential |
| Open-ended investigation with unknown data sources | Hierarchical |
| Cost-sensitive production workloads | Sequential |
| Ad-hoc queries where agent selection varies by input | Hierarchical |

## Common Mistakes

### Wrong

```python
# Hierarchical without manager_llm causes runtime error
crew = Crew(
    agents=[a1, a2], tasks=[t1, t2],
    process=Process.hierarchical,  # Missing manager_llm!
)
```

### Correct

```python
crew = Crew(
    agents=[a1, a2], tasks=[t1, t2],
    process=Process.hierarchical,
    manager_llm="anthropic/claude-sonnet-4-20250514",
)
```

## Related

- [Crews](../concepts/crews.md)
- [Agents](../concepts/agents.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
