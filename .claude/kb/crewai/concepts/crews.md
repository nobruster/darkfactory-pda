# Crews

> **Purpose**: Compose teams of agents that collaborate to solve ShopAgent e-commerce analysis
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

A Crew is a team of agents working together on a list of tasks through a defined process. Crews are the primary execution unit in CrewAI. You configure agents, tasks, process type, memory, and callbacks, then call `kickoff()` to run the workflow. Crews can be defined in Python or declaratively via YAML with the `@CrewBase` decorator.

## The Pattern

```python
from crewai import Agent, Task, Crew, Process

analyst = Agent(
    role="E-Commerce Data Analyst",
    goal="Extract revenue and order metrics via SQL",
    backstory="Expert SQL analyst querying Supabase for exact e-commerce figures.",
    tools=[supabase_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)
researcher = Agent(
    role="Customer Experience Researcher",
    goal="Surface sentiment and complaint themes from review vectors",
    backstory="Searches Qdrant embeddings to identify recurring customer issues.",
    tools=[qdrant_tool],
    llm="anthropic/claude-sonnet-4-20250514",
)
reporter = Agent(
    role="Executive Report Writer",
    goal="Synthesize SQL metrics and review insights into an actionable report",
    backstory="Combines structured data and qualitative feedback into clear briefs.",
    llm="anthropic/claude-sonnet-4-20250514",
)

analysis_task = Task(
    description="Query revenue totals and order counts for {time_period}",
    expected_output="Revenue, order count, and top customer segments by SQL result",
    agent=analyst,
)
research_task = Task(
    description="Search reviews for sentiment and complaints in {time_period}",
    expected_output="Top complaint themes and satisfaction drivers with evidence",
    agent=researcher,
    context=[analysis_task],
)
report_task = Task(
    description="Write an executive e-commerce report combining metrics and sentiment",
    expected_output="Structured report with revenue, sentiment, and recommendations",
    agent=reporter,
    context=[analysis_task, research_task],
)

crew = Crew(
    agents=[analyst, researcher, reporter],
    tasks=[analysis_task, research_task, report_task],
    process=Process.sequential,
    memory=True,
    verbose=True,
)

result = crew.kickoff(inputs={"time_period": "last 30 days"})
print(result.raw)
```

## Quick Reference

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `agents` | list[Agent] | required | Participating agents |
| `tasks` | list[Task] | required | Tasks to execute |
| `process` | Process | `sequential` | Execution strategy |
| `memory` | bool | `False` | Enable crew memory |
| `cache` | bool | `True` | Cache tool results |
| `verbose` | bool | `False` | Detailed logging |
| `max_rpm` | int | `None` | Global rate limit |
| `manager_llm` | str | `None` | LLM for hierarchical manager |
| `manager_agent` | Agent | `None` | Custom manager agent |
| `planning` | bool | `False` | Enable auto-planning |
| `embedder` | dict | `None` | Custom embedder config |
| `output_log_file` | str | `None` | Save execution logs |
| `step_callback` | callable | `None` | Hook after each step |
| `task_callback` | callable | `None` | Hook after each task |

## YAML Configuration (@CrewBase)

```python
from crewai import CrewBase, agent, task, crew, Agent, Task, Crew, Process

@CrewBase
class ShopAgentCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self) -> Agent:
        return Agent(config=self.agents_config["analyst"], tools=[supabase_tool])

    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config["researcher"], tools=[qdrant_tool])

    @agent
    def reporter(self) -> Agent:
        return Agent(config=self.agents_config["reporter"])

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, process=Process.sequential, memory=True)
```

> Full YAML config: see [patterns/yaml-configuration.md](../patterns/yaml-configuration.md)

## Execution Methods

| Method | Use Case |
|--------|----------|
| `kickoff(inputs={})` | Standard sync execution |
| `kickoff_for_each(inputs=[])` | Batch processing multiple inputs |
| `akickoff(inputs={})` | Async execution |

## Common Mistakes

### Wrong

```python
# Hierarchical process without manager LLM
crew = Crew(agents=[a1, a2], tasks=[t1], process=Process.hierarchical)
```

### Correct

```python
crew = Crew(
    agents=[a1, a2],
    tasks=[t1],
    process=Process.hierarchical,
    manager_llm="anthropic/claude-sonnet-4-20250514",
)
```

## Related

- [Agents](../concepts/agents.md)
- [Tasks](../concepts/tasks.md)
- [Processes](../concepts/processes.md)
- [ShopAgent Crew Pattern](../patterns/shopagent-crew.md)
