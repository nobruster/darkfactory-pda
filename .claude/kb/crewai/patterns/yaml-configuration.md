# ShopAgent YAML Configuration

> **Purpose**: agents.yaml and tasks.yaml for the ShopAgent CrewAI crew
> **MCP Validated**: 2026-04-12

## When to Use

- Configuring the 3-agent ShopAgent crew declaratively
- Updating agent personas, goals, or backstories without touching Python
- Adding or reordering tasks in the sequential pipeline
- Passing runtime inputs (e.g., `{question}`) from `crew.kickoff(inputs=...)` into task descriptions

## Directory Structure

```
src/day4/shopagent/
├── config/
│   ├── agents.yaml     ← agent identity: role, goal, backstory
│   └── tasks.yaml      ← task instructions: description, expected_output, agent, context
├── crew.py             ← @CrewBase class wiring agents + tasks
├── tools.py            ← supabase_tool + qdrant_tool
└── app.py              ← Chainlit entry point
```

## agents.yaml

```yaml
# src/day4/shopagent/config/agents.yaml

analyst:
  role: "E-Commerce Data Analyst"
  goal: >
    Extract precise metrics from the ShopAgent database using SQL queries.
    Always return exact numbers backed by query results — never estimate.
  backstory: >
    You are an expert SQL analyst specialized in e-commerce data at scale.
    You query Supabase Postgres for exact figures: total revenue, order counts,
    payment method distributions, average ticket by customer segment, and
    product category rankings. Every number you report comes from a verified
    SQL query result. You know the schema by heart:
    customers (customer_id, name, email, city, state, segment),
    products (product_id, name, category, price, brand),
    orders (order_id, customer_id, product_id, qty, total, status, payment, created_at).

researcher:
  role: "Customer Experience Researcher"
  goal: >
    Analyze customer reviews and sentiment using semantic search in Qdrant.
    Identify recurring complaint themes, positive patterns, and emotional signals.
  backstory: >
    You are a customer experience researcher who understands what customers
    feel, not just what they buy. You search The Memory (Qdrant) for review
    themes, delivery complaints, product quality feedback, and NPS signals.
    You surface the human story behind the data: why customers churn, what
    delights them, and which friction points repeat. You cite specific review
    excerpts to support every finding.

reporter:
  role: "Executive Report Writer"
  goal: >
    Combine analyst SQL metrics and researcher sentiment insights into a
    concise, actionable executive report with concrete recommendations.
  backstory: >
    You are a senior business analyst who synthesizes quantitative data and
    qualitative insights for C-level stakeholders. Your reports are structured,
    evidence-based, and end with 3-5 prioritized recommendations. You never
    invent numbers — you reference the analyst's figures directly. You never
    speculate on sentiment — you cite the researcher's review excerpts. Your
    reports are in Portuguese and always include: executive summary, key metrics,
    customer voice highlights, and next steps.
```

## tasks.yaml

```yaml
# src/day4/shopagent/config/tasks.yaml

analysis_task:
  description: >
    Answer the following business question using SQL queries against the
    ShopAgent Postgres database:

    "{question}"

    Steps:
    1. Identify which tables are needed (customers, products, orders).
    2. Write and execute the appropriate SQL query via the Supabase SQL Executor tool.
    3. Interpret the results clearly with labels and units (R$, %, count).
    4. If multiple queries are needed, execute them sequentially and combine results.
  expected_output: >
    A structured summary of SQL query results with exact numbers, labels, and
    relevant breakdowns (by state, segment, category, or payment method as
    applicable). Include the SQL queries used for transparency.
  agent: analyst

research_task:
  description: >
    Research customer sentiment and review themes related to this question:

    "{question}"

    Steps:
    1. Extract the key semantic concepts from the question (e.g., delivery, quality, price).
    2. Run 2-3 semantic searches in Qdrant covering different angles of the topic.
    3. Identify recurring themes, complaints, and positive signals from review results.
    4. Note sentiment distribution (positive / neutral / negative) across retrieved reviews.
  expected_output: >
    A thematic summary of customer feedback organized by topic. Include direct
    review quotes (in Portuguese), sentiment labels, and frequency of recurring
    complaints or praise. Minimum 3 distinct themes identified.
  agent: researcher

report_task:
  description: >
    Generate a comprehensive executive report answering:

    "{question}"

    You have access to:
    - The analyst's SQL metrics (exact numbers from The Ledger)
    - The researcher's sentiment findings (review themes from The Memory)

    Structure the report as:
    1. Resumo Executivo (2-3 sentences)
    2. Metricas Principais (from analyst — with exact figures)
    3. Voz do Cliente (from researcher — with review excerpts)
    4. Recomendacoes (3-5 prioritized action items)
  expected_output: >
    A polished executive report in Portuguese combining quantitative metrics
    and qualitative insights. Actionable recommendations must reference specific
    data points from both the analyst and researcher findings.
  agent: reporter
  context:
    - analysis_task
    - research_task
```

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| Variable interpolation | `{question}` | Injected at `crew.kickoff(inputs={"question": ...})` |
| Task context | `[analysis_task, research_task]` | report_task reads both prior outputs |
| Agent assignment | `agent: analyst` | Each task binds to one agent by YAML key |
| Process | `Process.sequential` | Set in `crew.py`, not in YAML |

## See Also

- [ShopAgent Crew](../patterns/shopagent-crew.md)
- [ShopAgent MCP Tools](../patterns/shopagent-tools.md)
- [CrewAI Tasks](../concepts/tasks.md)
- [CrewAI Agents](../concepts/agents.md)
