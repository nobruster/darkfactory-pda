# DESIGN: ShopAgent Day 3 — Autonomous E-Commerce Agent

> Technical design for an autonomous LangGraph agent with dual-store routing (Postgres SQL + Qdrant semantic) and full-trace Chainlit streaming.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY3 |
| **Date** | 2026-04-15 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SHOPAGENT_DAY3.md](./DEFINE_SHOPAGENT_DAY3.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌─────��────────────────��──────────────────────────────────────────────┐
│                        CHAINLIT UI (Browser)                        │
│                                                                     │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐   │
│  │  User Input  │───→│  Full-trace streaming (astream_events)  │   │
│  └─────���───────┘    │  • LLM tokens  → cl.Message.stream_token│   ��
│                      │  • Tool start  → cl.Step.__aenter__     │   │
│                      │  • Tool end    → cl.Step.__aexit__      │   │
│                      └���─────────────────────────────────────────��   │
└───���─────────────────────────────┬────────────────────────��──────────┘
                                  │ HTTP (localhost:8000)
                                  ▼
┌──────���────────────────────────────���──────────────────────────��──────┐
│                     chainlit_app.py                                  │
│                                                                     │
│  @cl.on_chat_start  →  create agent, store in session               │
│  @cl.on_message     →  agent.astream_events() → stream to UI       │
└────���────────────────────────────┬─────────��─────────────────────────┘
                                  │
                                  ▼
┌─────────���───────────────────────────────────────────────────────��───┐
│                          agent.py                                    │
│                                                                     │
│  LangGraph create_react_agent                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  ChatAnthropic(claude-sonnet-4-20250514, temperature=0)       │ │
│  │                                                                │ │
│  │  System Prompt: Portuguese, full schema, dual-store rules      │ │
│  │                                                                │ │
│  │  ReAct Loop:                                                   │ │
│  │    Think → Choose Tool → Execute → Observe → Think → Answer   │ │
│  └───���────────────────────────────────────────────────────────────┘ │
│                        │                   │                        │
│                  ┌─────┘                   └─────┐                  │
│                  ▼                               ▼                  │
│  ┌──────────────────────────┐  ┌────────────��──────────────────┐   │
│  │   execute_sql(query)     │  │  semantic_search(question)    │   │
│  │   @tool from tools.py    │  │  @tool from tools.py          │   │
│  └────────────┬─────────────┘  └──────────────┬────────────────┘   │
└───────────────┼────��───────────────────────────┼───────────��────────┘
                │                                │
                ▼                                ▼
┌──────────────────────────┐  ┌────────��───────────��──────────────┐
│   Postgres (The Ledger)  │  │   Qdrant (The Memory)             │
│   localhost:5432         │  │   localhost:6333                   │
│   psycopg2 connection    │  │   LlamaIndex query engine         │
│                          │  │   BAAI/bge-base-en-v1.5           │
│   Tables:                │  │                                   │
│   • customers            │  │   Collection:                     │
│   • products             │  │   • shopagent_reviews (203 docs)  │
│   • orders               │  │                                   │
└────────────────���─────────┘  └───────���───────────────────���───────┘
         Docker                          Docker
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `tools.py` | Two LangChain tools: SQL execution + semantic search | `@tool` decorator, psycopg2, LlamaIndex + Qdrant |
| `agent.py` | ReAct agent with system prompt and dual-store routing | LangGraph `create_react_agent`, `ChatAnthropic` |
| `chainlit_app.py` | Chat UI with full-trace streaming | Chainlit lifecycle hooks, `astream_events` v2 |
| `.chainlit/config.toml` | Chainlit configuration (already exists) | `cot = "full"` already set |

---

## Key Decisions

### Decision 1: Open SQL Generation via System Prompt

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-15 |

**Context:** The agent needs to answer any SQL question against a 3-table schema. We must decide how it learns the schema.

**Choice:** Embed the full Postgres schema (tables, columns, types, constraints, relationships) directly in the agent's system prompt. The agent generates SQL on the fly.

**Rationale:** The schema is small (3 tables, 18 columns) — fits easily in a system prompt without wasting context. Claude excels at SQL generation for schemas of this size. This gives maximum flexibility — the audience can ask ANY question during the live demo.

**Alternatives Rejected:**
1. Predefined query catalog — Rejected because it limits questions to 5 pre-built queries, undermining the autonomy narrative
2. Schema discovery at runtime (information_schema) — Rejected because it adds latency (extra query per request) and complexity for no benefit when schema is static

**Consequences:**
- Trade-off: Agent may occasionally generate invalid SQL for very complex queries
- Benefit: Audience can ask arbitrary questions, creating a powerful "wow" moment

---

### Decision 2: LangGraph create_react_agent (Not Legacy AgentExecutor)

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-15 |

**Context:** LangChain has two agent APIs — the modern LangGraph-based `create_react_agent` and the deprecated `AgentExecutor`.

**Choice:** Use `langgraph.prebuilt.create_react_agent` with Claude's native tool-calling.

**Rationale:** Native tool-calling is more reliable than text-parsed ReAct (no "Action: ..." string parsing). First-class `astream_events` support is critical for Chainlit integration. Day 4's CrewAI builds on modern patterns.

**Alternatives Rejected:**
1. Legacy `AgentExecutor` �� Deprecated, prompt-based tool parsing is brittle with Claude, poor streaming support

**Consequences:**
- Trade-off: Requires `langgraph` dependency (adds ~5MB)
- Benefit: Reliable tool routing, clean streaming, future-proof

---

### Decision 3: Full-Trace Streaming via astream_events v2

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-15 |

**Context:** Chainlit needs to display the agent's reasoning process in real-time.

**Choice:** Use `agent.astream_events(version="v2")` to capture all events: LLM token generation, tool starts, tool completions. Map each event type to a Chainlit UI element (Message tokens, Steps).

**Rationale:** The agenda explicitly states "Pensamento passo a passo visivel" (step-by-step thinking visible). Full trace provides maximum transparency. The existing `.chainlit/config.toml` already has `cot = "full"`.

**Alternatives Rejected:**
1. `agent.ainvoke()` (no streaming) — Black box UX; user waits 10-20 seconds with no feedback
2. `agent.astream()` (message-level) — Shows final messages but not intermediate tool calls

**Consequences:**
- Trade-off: Full trace can be verbose for complex multi-tool queries
- Benefit: Audience sees exactly how the agent reasons — the core teaching moment of Day 3

---

### Decision 4: Reuse Day 2 Connection Patterns

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-15 |

**Context:** Day 2 already has working Postgres (`psycopg2`) and Qdrant (`LlamaIndex`) connections.

**Choice:** Replicate the same connection patterns in `tools.py` — same env vars, same connection functions, same LlamaIndex settings.

**Rationale:** Participants already understand these patterns from Day 2. Consistency reduces cognitive load. The tools should feel like "wrapping Day 2 code in a @tool decorator."

**Alternatives Rejected:**
1. Import from `src/day2/` — Creates cross-day dependency; each day should be self-contained
2. SQLAlchemy instead of psycopg2 — Different from Day 2; unnecessary abstraction for raw SQL

**Consequences:**
- Trade-off: Minor code duplication between Day 2 and Day 3
- Benefit: Each day stands alone; participants can understand Day 3 without Day 2 context

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `src/day3/__init__.py` | Create | Package marker | (general) | None |
| 2 | `src/day3/tools.py` | Create | Two @tool functions: execute_sql + semantic_search | @shopagent-builder | None |
| 3 | `src/day3/agent.py` | Create | LangGraph ReAct agent with system prompt | @shopagent-builder | 2 |
| 4 | `src/day3/chainlit_app.py` | Create | Chainlit UI with full-trace streaming | @shopagent-builder | 2, 3 |
| 5 | `src/day3/requirements.txt` | Create | Day 3 Python dependencies | @shopagent-builder | None |

**Total Files:** 5

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @shopagent-builder | 2, 3, 4, 5 | Domain specialist for ShopAgent components by day; understands dual-store architecture, LangGraph patterns, Chainlit integration |
| (general) | 1 | Trivial file (empty `__init__.py`) |

**Agent Discovery:**
- Scanned: `.claude/agents/**/*.md`
- Matched by: "ShopAgent" domain, Day 3 scope, LangChain + Chainlit KB domains

---

## Code Patterns

### Pattern 1: LangChain @tool with Real Database Connection

```python
"""Tools wrap Day 2's connection patterns in @tool decorators."""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@tool
def execute_sql(query: str) -> str:
    """Execute SQL against Postgres (The Ledger) for EXACT data.

    Use for: revenue, counts, averages, orders, products, customers.
    Tables: customers, products, orders (see schema in system prompt).
    """
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "shopagent"),
        user=os.environ.get("POSTGRES_USER", "shopagent"),
        password=os.environ.get("POSTGRES_PASSWORD", "shopagent"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        result_lines = [" | ".join(columns)]
        for row in rows:
            result_lines.append(" | ".join(str(v) for v in row))
        return "\n".join(result_lines)
    except Exception as e:
        return f"SQL Error: {e}"
    finally:
        conn.close()
```

### Pattern 2: LangGraph Agent with System Prompt

```python
"""Agent uses create_react_agent with a Portuguese system prompt containing the full schema."""
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from tools import execute_sql, semantic_search

SYSTEM_PROMPT = """Voce e o ShopAgent, um assistente de e-commerce...

## The Ledger (Postgres) — Dados Exatos
{full schema here}

## The Memory (Qdrant) — Significado
{review collection description}

Regras:
- Para numeros/totais/medias → execute_sql
- Para opinioes/reclamacoes/sentimentos → semantic_search
- Para perguntas hibridas → use AMBAS as ferramentas
- Sempre responda em Portugues
"""

llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
agent = create_react_agent(model=llm, tools=[execute_sql, semantic_search], prompt=SYSTEM_PROMPT)
```

### Pattern 3: Chainlit Full-Trace Streaming

```python
"""Map every LangGraph event to a Chainlit UI element."""
import chainlit as cl

@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")
    msg = cl.Message(content="")
    tool_steps = {}

    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": message.content}]},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            token = event["data"]["chunk"].content
            if isinstance(token, str) and token:
                await msg.stream_token(token)

        elif kind == "on_tool_start":
            step = cl.Step(name=event["name"], type="tool")
            await step.__aenter__()
            step.input = str(event["data"].get("input", ""))
            tool_steps[event["run_id"]] = step

        elif kind == "on_tool_end":
            step = tool_steps.pop(event["run_id"], None)
            if step:
                step.output = str(event["data"].get("output", ""))[:500]
                await step.__aexit__(None, None, None)

    await msg.send()
```

---

## Data Flow

```text
1. User types question in Chainlit chat
   │  "Qual o faturamento dos clientes que reclamam de entrega?"
   ▼
2. chainlit_app.py receives cl.Message, retrieves agent from session
   │
   ▼
3. agent.astream_events() starts LangGraph ReAct loop
   │
   ▼
4. LLM (Claude Sonnet) reads system prompt + user question
   │  Thinks: "I need complaints (semantic) and revenue (SQL)"
   ▼
5a. Tool Call: semantic_search("reclamacoes de entrega")
    │  → LlamaIndex embeds query → Qdrant similarity search
    │  → Returns: 23 relevant reviews with order_ids
    │  → Chainlit: cl.Step("semantic_search") shows input/output
    ▼
5b. Tool Call: execute_sql("SELECT c.state, AVG(o.total)...")
    │  → psycopg2 executes SQL → Returns tabular data
    │  → Chainlit: cl.Step("execute_sql") shows SQL + results
    ▼
6. LLM synthesizes final answer from both tool outputs
   │  "Os clientes que reclamam de entrega estao concentrados em SP (R$347)..."
   │  → Chainlit: msg.stream_token() for each token
   ▼
7. msg.send() finalizes the response in the UI
```

---

## Integration Points

| External System | Integration Type | Authentication | Port |
|-----------------|-----------------|----------------|------|
| Postgres | psycopg2 direct connection | User/password from .env | 5432 |
| Qdrant | qdrant_client HTTP | None (local) | 6333 |
| Anthropic API | langchain-anthropic SDK | ANTHROPIC_API_KEY from .env | HTTPS |

---

## Testing Strategy

| Test Type | Scope | Method | Coverage Goal |
|-----------|-------|--------|---------------|
| Smoke | Tool connectivity | Run `python -c "from tools import ..."` | Both tools import and connect |
| Manual E2E | Full agent flow | Run Chainlit app, ask 3 demo questions | AT-001 through AT-005 |
| Live Demo | All acceptance tests | Instructor tests during workshop | AT-001 through AT-007 |

**Note:** Formal unit testing is explicitly out of scope (DEFINE Section: Out of Scope). Day 4 introduces DeepEval for LLM evaluation. Day 3 validates through live demo.

---

## Error Handling

| Error Type | Handling Strategy | User-Visible? |
|------------|-------------------|---------------|
| Postgres connection failure | Return `"Erro: Nao foi possivel conectar ao Postgres..."` from tool | Yes — agent relays tool error |
| Invalid SQL generated | psycopg2 raises exception, tool returns `"SQL Error: {e}"` | Yes — agent may retry with corrected SQL |
| Qdrant connection failure | LlamaIndex raises, tool catches and returns error string | Yes — agent relays tool error |
| Empty Qdrant results | Tool returns `"Nenhum review encontrado"` | Yes — agent explains no results |
| Anthropic API timeout | LangGraph propagates, Chainlit shows error | Yes — browser shows error state |

---

## Configuration

| Config Key | Source | Default | Description |
|------------|--------|---------|-------------|
| `POSTGRES_HOST` | .env | `localhost` | Postgres host |
| `POSTGRES_PORT` | .env | `5432` | Postgres port |
| `POSTGRES_DB` | .env | `shopagent` | Database name |
| `POSTGRES_USER` | .env | `shopagent` | Database user |
| `POSTGRES_PASSWORD` | .env | `shopagent` | Database password |
| `QDRANT_URL` | .env | `http://localhost:6333` | Qdrant HTTP endpoint |
| `QDRANT_COLLECTION` | .env | `shopagent_reviews` | Qdrant collection name |
| `ANTHROPIC_API_KEY` | .env | (required) | Claude API key |

**All config already defined in `.env.example` — no new env vars needed.**

---

## Security Considerations

- **Open SQL execution:** Agent can run any SQL including DELETE/DROP. Acceptable because this is a local Docker environment with throwaway data. Production (Day 4) should use read-only Supabase credentials.
- **No input sanitization:** Tool descriptions guide the LLM, not user input validation. Acceptable for workshop context.
- **API key exposure:** `ANTHROPIC_API_KEY` loaded from .env, never hardcoded. `.env` is in `.gitignore`.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Python `print()` for tool executions (visible in terminal running Chainlit) |
| Tracing | Chainlit's built-in step visualization (full trace via `cot = "full"`) |
| Metrics | None for Day 3 — LangFuse observability is Day 4 |

---

## System Prompt Specification

The system prompt is the most critical piece of the agent — it determines routing accuracy. Here is the complete prompt to embed in `agent.py`:

```
Voce e o ShopAgent, um assistente inteligente de e-commerce. Voce tem acesso a dois
stores de dados e deve decidir qual usar para cada pergunta.

## The Ledger (Postgres) — Dados Exatos
Use a ferramenta execute_sql para perguntas sobre numeros, totais e dados estruturados.

Schema do banco de dados:

CREATE TABLE customers (
    customer_id UUID PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    city        VARCHAR(100),
    state       CHAR(2),
    segment     VARCHAR(20) -- 'premium', 'standard', 'basic'
);

CREATE TABLE products (
    product_id UUID PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    category   VARCHAR(100) NOT NULL,
    price      DECIMAL(10,2) NOT NULL,
    brand      VARCHAR(100)
);

CREATE TABLE orders (
    order_id    UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(customer_id),
    product_id  UUID REFERENCES products(product_id),
    qty         INTEGER,
    total       DECIMAL(10,2),
    status      VARCHAR(20), -- 'delivered', 'shipped', 'processing', 'cancelled'
    payment     VARCHAR(20), -- 'pix', 'credit_card', 'boleto'
    created_at  TIMESTAMPTZ DEFAULT now()
);

## The Memory (Qdrant) — Significado
Use a ferramenta semantic_search para perguntas sobre opinioes, reclamacoes e sentimentos.
A colecao contem 203 reviews de clientes em portugues com campos:
review_id, order_id, rating (1-5), comment (texto), sentiment (positive/negative).

## Regras de Roteamento
1. Numeros, totais, medias, contagens, faturamento → execute_sql
2. Opinioes, reclamacoes, sentimentos, temas de reviews → semantic_search
3. Perguntas hibridas (ex: "faturamento dos que reclamam") → use AMBAS
4. Sempre responda em Portugues
5. Ao usar SQL, escreva queries SELECT validas para o schema acima
6. Ao combinar resultados, explique como os dados se relacionam
```

---

## Dependencies (requirements.txt)

```text
langchain-anthropic>=0.3.0
langchain-core>=0.3.0
langgraph>=0.2.0
chainlit>=2.0.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
llama-index-core>=0.12.0
llama-index-vector-stores-qdrant>=0.4.0
llama-index-embeddings-fastembed>=0.3.0
fastembed>=0.4.0
llama-index-llms-anthropic>=0.6.0
qdrant-client>=1.12.0
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-15 | design-agent | Initial version |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SHOPAGENT_DAY3.md`
