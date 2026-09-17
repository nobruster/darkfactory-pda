# Agentic Workflow Pattern

> **Purpose**: Multi-step agent workflow with plan-and-execute orchestration for complex tasks
> **MCP Validated**: 2026-02-17

## When to Use

- Complex tasks requiring multiple reasoning steps and tool calls
- Tasks that benefit from decomposition into subtasks
- Workflows where cheaper models can execute plans from frontier models
- Scenarios needing iterative refinement with self-correction

## Architecture

```text
                    +-------------------+
                    |   User Request    |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Planner Agent   |  (frontier model: GPT-4o, Claude Opus)
                    | - Decompose task  |
                    | - Assign workers  |
                    | - Define success  |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v------+ +----v-------+ +----v--------+
     | Worker Agent 1 | | Worker 2   | | Worker 3    |  (cheaper models)
     | (Research)     | | (Analyze)  | | (Write)     |
     +--------+------+ +----+-------+ +----+--------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v----------+
                    |  Reviewer Agent   |  (frontier model)
                    | - Check quality   |
                    | - Request revise  |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Final Output    |
                    +-------------------+
```

## Implementation

```python
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import asyncio

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"

@dataclass
class Task:
    id: str
    description: str
    assigned_agent: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    max_retries: int = 2
    retry_count: int = 0

@dataclass
class Plan:
    goal: str
    tasks: list[Task]
    success_criteria: str

class AgenticWorkflow:
    def __init__(self, planner_model: str, worker_model: str, reviewer_model: str):
        self.planner_model = planner_model
        self.worker_model = worker_model
        self.reviewer_model = reviewer_model
        self.state: dict[str, Any] = {}

    async def run(self, user_request: str) -> str:
        # Step 1: Plan
        plan = await self._plan(user_request)

        # Step 2: Execute tasks respecting dependencies
        for task in self._topological_sort(plan.tasks):
            await self._execute_task(task)

        # Step 3: Review and iterate
        review = await self._review(plan)
        if review.needs_revision:
            revised_tasks = [t for t in plan.tasks if t.status == TaskStatus.NEEDS_REVISION]
            for task in revised_tasks:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    await self._execute_task(task)

        # Step 4: Synthesize final output
        return await self._synthesize(plan)

    async def _plan(self, request: str) -> Plan:
        """Frontier model decomposes request into tasks."""
        prompt = f"""Decompose this request into executable tasks.
For each task specify: id, description, assigned_agent, dependencies.

Request: {request}

Return as structured JSON."""
        response = await self._call_llm(self.planner_model, prompt)
        return self._parse_plan(response)

    async def _execute_task(self, task: Task):
        """Worker model executes a single task."""
        # Gather dependency results
        dep_context = {dep: self.state.get(dep) for dep in task.dependencies}
        prompt = f"""Execute this task:
{task.description}

Context from previous steps:
{dep_context}"""
        task.status = TaskStatus.RUNNING
        try:
            result = await self._call_llm(self.worker_model, prompt)
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.state[task.id] = result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = str(e)

    async def _review(self, plan: Plan) -> "ReviewResult":
        """Frontier model reviews all task outputs."""
        results = {t.id: t.result for t in plan.tasks}
        prompt = f"""Review these results against the success criteria.

Goal: {plan.goal}
Success Criteria: {plan.success_criteria}
Results: {results}

For each task, respond: PASS or NEEDS_REVISION with feedback."""
        return await self._call_llm(self.reviewer_model, prompt)
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `planner_model` | `gpt-4o` | Frontier model for planning and review |
| `worker_model` | `gpt-4o-mini` | Cheaper model for task execution |
| `max_retries` | `2` | Max revision attempts per task |
| `timeout_seconds` | `120` | Per-task execution timeout |
| `parallel_execution` | `True` | Execute independent tasks concurrently |

## Example Usage

```python
workflow = AgenticWorkflow(
    planner_model="gpt-4o",
    worker_model="gpt-4o-mini",
    reviewer_model="gpt-4o",
)

result = await workflow.run(
    "Research the top 3 competitors in the LLM observability space, "
    "analyze their pricing models, and write a comparison report."
)
```

## Cost Comparison

```text
Frontier-only:  10 steps x $0.01/step = $0.10 per workflow
Plan-and-Execute: 2 frontier + 8 cheap = (2 x $0.01) + (8 x $0.001) = $0.028
Savings: ~72% cost reduction
```

## See Also

- [Multi-Agent Systems](../concepts/multi-agent-systems.md)
- [Tool Calling](../concepts/tool-calling.md)
- [Evaluation Framework](../patterns/evaluation-framework.md)
