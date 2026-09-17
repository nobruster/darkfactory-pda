# Chainlit + CrewAI Integration

> **Purpose**: Connect ShopAgent CrewAI crew to Chainlit conversational interface with per-agent step visibility
> **MCP Validated**: 2026-04-12

## When to Use

- Day 4 conversational UI for the multi-agent ShopAgent
- Showing AnalystAgent, ResearchAgent, and ReporterAgent as distinct expandable steps in the chat
- Giving users real-time feedback on which agent is working and what it produced
- Running the crew asynchronously so the Chainlit event loop stays unblocked

## Implementation

```python
"""ShopAgent Chainlit app — CrewAI crew with per-agent step visibility."""
import asyncio
from typing import Any

import chainlit as cl
from crewai.agents.agent_builder.base_agent_executor_mixin import CrewAgentExecutorMixin

from shopagent.crew import ShopAgentCrew


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize a fresh crew instance per chat session."""
    crew_instance = ShopAgentCrew()
    cl.user_session.set("crew", crew_instance)
    await cl.Message(
        content=(
            "ShopAgent Multi-Agent pronto!\n\n"
            "3 agentes especializados a postos:\n"
            "- AnalystAgent — consultas SQL no The Ledger\n"
            "- ResearchAgent — busca semantica no The Memory\n"
            "- ReporterAgent — relatorio executivo consolidado\n\n"
            "Faca sua pergunta sobre vendas, clientes ou satisfacao."
        )
    ).send()


# ---------------------------------------------------------------------------
# Step tracking via task callback
# ---------------------------------------------------------------------------

def make_task_callback(steps: dict[str, cl.Step]):
    """Return a synchronous callback that CrewAI can call after each task."""

    def task_callback(task_output: Any) -> None:
        agent_name = getattr(task_output, "agent", "Agent")
        raw_output = getattr(task_output, "raw", "") or str(task_output)
        truncated = raw_output[:600] + ("…" if len(raw_output) > 600 else "")

        # CrewAI callbacks are sync — use run_coroutine_threadsafe
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_update_step(steps, agent_name, truncated))

    return task_callback


async def _update_step(steps: dict[str, cl.Step], agent_name: str, output: str) -> None:
    if agent_name in steps:
        steps[agent_name].output = output
        await steps[agent_name].update()
    else:
        step = cl.Step(name=agent_name, type="run")
        await step.__aenter__()
        step.output = output
        await step.__aexit__(None, None, None)
        steps[agent_name] = step


# ---------------------------------------------------------------------------
# Main message handler
# ---------------------------------------------------------------------------

@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Kick off the ShopAgent crew and surface each agent as a Chainlit Step."""
    crew_instance: ShopAgentCrew = cl.user_session.get("crew")

    # Pre-create steps for all 3 agents so they appear in order
    agent_labels = {
        "analyst": "AnalystAgent — The Ledger (SQL)",
        "researcher": "ResearchAgent — The Memory (Semantic)",
        "reporter": "ReporterAgent — Relatorio Executivo",
    }
    steps: dict[str, cl.Step] = {}
    step_objects: list[cl.Step] = []

    for key, label in agent_labels.items():
        step = cl.Step(name=label, type="run")
        steps[key] = step
        step_objects.append(step)
        await step.__aenter__()
        step.output = "Aguardando..."
        await step.update()

    # Build crew with task callback wired in
    crew = crew_instance.crew()
    crew.task_callback = make_task_callback(steps)

    # Run the crew in a thread so the async event loop stays free
    result = await asyncio.to_thread(
        crew.kickoff,
        inputs={"question": message.content},
    )

    # Close all steps
    for step in step_objects:
        await step.__aexit__(None, None, None)

    await cl.Message(content=str(result.raw)).send()
```

## UI Behavior

```
User: "Analise de vendas e sentimento por estado"

┌─ AnalystAgent — The Ledger (SQL)           [run]
│  SP: R$ 127.430 | RJ: R$ 89.210 | MG: R$ 68.440
│  Query: SELECT state, SUM(total) ...
│
├─ ResearchAgent — The Memory (Semantic)      [run]
│  Temas: entrega atrasada (SP, 34%), produto danificado (RJ, 18%)
│  Reviews: "Demorou 15 dias" · "Veio amassado"
│
└─ ReporterAgent — Relatorio Executivo        [run]
   Resumo: SP lidera em faturamento mas tem maior volume de reclamacoes...

Final answer: [full executive report in Portuguese]
```

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| Step type | `"run"` | Renders play icon; collapsible in Chainlit UI |
| Output truncation | 600 chars | Prevents step overflow for long agent responses |
| `asyncio.to_thread` | Required | CrewAI kickoff is synchronous; must not block event loop |
| Session scope | `cl.user_session` | Each chat gets its own `ShopAgentCrew` instance |
| `task_callback` | `make_task_callback` | Registered on the `Crew` object before kickoff |

## Running Locally

```bash
# From src/day4/
chainlit run app.py -w

# Example questions that exercise all 3 agents:
# "Relatorio completo de satisfacao do cliente"
# "Quais estados tem mais reclamacoes e qual o impacto no faturamento?"
# "Analise o segmento Premium: receita e sentimento"
```

## See Also

- [CrewAI ShopAgent Crew](../../crewai/patterns/shopagent-crew.md)
- [ShopAgent MCP Tools](../../crewai/patterns/shopagent-tools.md)
- [LangChain Chainlit Integration](../patterns/langchain-integration.md)
