# Agents

> **Purpose**: Define autonomous AI agents with roles, goals, and tools for ShopAgent e-commerce workflows
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

A CrewAI Agent is an LLM-powered autonomous unit defined by a role, goal, and backstory. Each agent can execute tasks, call external tools, query memory, make decisions, and delegate work to other agents. Agents are the building blocks of every crew.

## The Pattern

```python
from crewai import Agent

analyst = Agent(
    role="E-Commerce Data Analyst",
    goal="Extract precise revenue, order, and customer metrics via SQL queries",
    backstory=(
        "You are an expert SQL analyst specialized in e-commerce data. "
        "You query Supabase Postgres for exact numbers: revenue, order counts, "
        "payment distributions, and customer segment metrics. You never guess "
        "numbers — every figure comes from a SQL query result."
    ),
    tools=[supabase_tool],
    llm="anthropic/claude-sonnet-4-20250514",
    memory=True,
    verbose=True,
    max_iter=5,
    allow_delegation=False,
)
```

## Quick Reference

| Parameter | Type | Default | Notes |
| --------- | ---- | ------- | ----- |
| `role` | str | required | Agent's job title / function |
| `goal` | str | required | What the agent aims to achieve |
| `backstory` | str | required | Context for persona consistency |
| `tools` | list | `[]` | Tools available to the agent |
| `llm` | str/LLM | default | Model identifier or LLM instance |
| `memory` | bool | `False` | Enable agent-level memory |
| `verbose` | bool | `False` | Enable detailed logging |
| `max_iter` | int | `20` | Max reasoning iterations |
| `max_rpm` | int | `None` | Rate limit for API calls |
| `allow_delegation` | bool | `True` | Can delegate to other agents |
| `step_callback` | callable | `None` | Hook after each reasoning step |
| `function_calling_llm` | str | `None` | Separate LLM for tool calls |

## YAML Configuration

```yaml
# config/agents.yaml
analyst:
  role: "E-Commerce Data Analyst"
  goal: "Extract precise revenue, order, and customer metrics via SQL queries"
  backstory: >
    You are an expert SQL analyst specialized in e-commerce data.
    You query Supabase Postgres for exact numbers and never guess figures.
  max_iter: 5
  verbose: true

researcher:
  role: "Customer Experience Researcher"
  goal: "Surface customer sentiment and complaint themes from review vectors"
  backstory: >
    You search Qdrant for review embeddings and synthesize sentiment patterns,
    recurring complaints, and satisfaction drivers from customer feedback.
  max_iter: 5
  verbose: true
```

```python
from crewai import Agent, CrewBase, agent

@CrewBase
class ShopAgentCrew:
    agents_config = "config/agents.yaml"

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            tools=[supabase_tool],
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[qdrant_tool],
        )
```

## Common Mistakes

### Wrong

```python
# Missing backstory leads to generic, unfocused responses
agent = Agent(
    role="Analyst",
    goal="Analyze things",
)
```

### Correct

```python
# Specific role, goal, and backstory produce focused behavior
agent = Agent(
    role="E-Commerce Data Analyst",
    goal="Return exact revenue totals and order counts from Supabase Postgres",
    backstory=(
        "You specialize in e-commerce SQL. You query orders, customers, and "
        "products tables to return precise figures — never estimates."
    ),
    tools=[supabase_tool],
    max_iter=5,
)
```

## Related

- [Tasks](../concepts/tasks.md)
- [Crews](../concepts/crews.md)
- [Tools](../concepts/tools.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
