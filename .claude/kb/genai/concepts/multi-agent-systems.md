# Multi-Agent Systems

> **Purpose**: Orchestration patterns for coordinating multiple specialized LLM agents
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Multi-agent systems coordinate multiple specialized LLM agents to solve complex tasks that exceed the capabilities of a single agent. Each agent has a defined role, tools, and instructions. An orchestrator manages handoffs, state sharing, and task routing. In 2025-2026, 72% of enterprise AI projects involve multi-agent architectures.

## Core Topologies

```text
SEQUENTIAL         CONCURRENT          HUB-AND-SPOKE        MESH
A -> B -> C        A --|                    B                A <-> B
                   B --|-> Merge        /   |   \            |  X  |
                   C --|            A --  Hub  -- D           C <-> D
                                        \   |   /
                                            C
```

## The Pattern

```python
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

class AgentRole(Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    WRITER = "writer"
    REVIEWER = "reviewer"

@dataclass
class Agent:
    name: str
    role: AgentRole
    model: str  # e.g., "gpt-4o", "claude-sonnet"
    system_prompt: str
    tools: list[Callable] = field(default_factory=list)
    max_iterations: int = 5

@dataclass
class Handoff:
    from_agent: str
    to_agent: str
    condition: str  # natural language or code condition
    pass_context: bool = True

@dataclass
class Orchestrator:
    agents: dict[str, Agent]
    handoffs: list[Handoff]
    entry_agent: str

    def route(self, state: dict) -> str:
        """Determine next agent based on state."""
        current = state.get("current_agent", self.entry_agent)
        for handoff in self.handoffs:
            if handoff.from_agent == current:
                if self._evaluate_condition(handoff.condition, state):
                    return handoff.to_agent
        return current

    def _evaluate_condition(self, condition: str, state: dict) -> bool:
        return state.get("step_complete", False)
```

## Quick Reference

| Topology | Latency | Cost | Fault Tolerance | Use Case |
|----------|---------|------|-----------------|----------|
| Sequential | High | Low | Low | Step-by-step workflows |
| Concurrent | Low | High | Medium | Parallel analysis |
| Hub-and-Spoke | Medium | Medium | Medium | Centralized control |
| Mesh | Medium | High | High | Resilient systems |
| Hierarchical | Variable | Low | Medium | Plan-and-execute |

## Common Mistakes

### Wrong

```python
# Single monolithic agent doing everything
agent = Agent(
    name="do_everything",
    system_prompt="You are an expert at research, writing, coding, review...",
    tools=[search, write, code, review, deploy, monitor],  # too many tools
)
```

### Correct

```python
# Specialized agents with clear responsibilities
researcher = Agent(
    name="researcher",
    role=AgentRole.RESEARCHER,
    model="gpt-4o-mini",  # cheaper model for retrieval
    system_prompt="You research topics and return structured findings.",
    tools=[web_search, doc_search],
)
writer = Agent(
    name="writer",
    role=AgentRole.WRITER,
    model="claude-sonnet-4-20250514",  # stronger model for generation
    system_prompt="You write clear, accurate content from research.",
    tools=[],
)
orchestrator = Orchestrator(
    agents={"researcher": researcher, "writer": writer},
    handoffs=[Handoff("researcher", "writer", "research_complete")],
    entry_agent="researcher",
)
```

## Cost Optimization: Plan-and-Execute

```python
# Frontier model plans, cheaper models execute
plan_agent = Agent(name="planner", model="gpt-4o", role=AgentRole.PLANNER,
                   system_prompt="Break task into steps. Assign each to a worker.")
exec_agents = {
    "search": Agent(name="search", model="gpt-4o-mini", role=AgentRole.RESEARCHER,
                    system_prompt="Execute search step.", tools=[web_search]),
    "write": Agent(name="write", model="gpt-4o-mini", role=AgentRole.WRITER,
                   system_prompt="Execute writing step."),
}
# Result: ~90% cost reduction vs. frontier-for-everything
```

## Key Frameworks (2025-2026)

| Framework | Maintainer | Strength |
|-----------|-----------|----------|
| LangGraph | LangChain | Graph-based state machines |
| CrewAI | CrewAI Inc | Role-based agent crews |
| OpenAI Agents SDK | OpenAI | Native handoff protocols |
| AutoGen/Semantic Kernel | Microsoft | Enterprise multi-agent |
| Swarm (deprecated) | OpenAI | Replaced by Agents SDK |

## Related

- [State Machines](../concepts/state-machines.md)
- [Tool Calling](../concepts/tool-calling.md)
- [Agentic Workflow Pattern](../patterns/agentic-workflow.md)
