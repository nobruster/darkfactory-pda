# BRAINSTORM: ShopAgent Day 3 — Autonomous E-Commerce Agent

**Feature:** SHOPAGENT_DAY3
**Phase:** 0 — Brainstorm
**Date:** 2026-04-15
**Status:** COMPLETE — Ready for /define

---

## 1. Idea Summary

Build an autonomous e-commerce agent (Day 3 of Semana AI Data Engineer) that queries
Postgres (The Ledger) for exact data like revenue and orders, and Qdrant (The Memory)
for semantic search on customer reviews. Uses LangGraph ReAct pattern with Claude as LLM.
Needs a Chainlit chat interface with full-trace streaming, thinking visualization, and
tool-use steps visible in the UI.

**Core narrative:** "The agent decides alone" — the autonomy leap from Days 1-2 where
the human decided which store to query.

---

## 2. Discovery Questions & Answers

### Q1: SQL Tool — Open vs. Constrained?
**Options:** (a) Open SQL — agent writes arbitrary SQL | (b) Predefined queries from Day 2
**Answer:** **(a) Open SQL** — The agent generates SQL on the fly against the 3-table schema.
Rationale: The whole Day 3 narrative is autonomous decision-making. Constraining to 5
pre-built queries undermines the "agent decides" message. Claude is strong at SQL for
this simple schema. Live demo impact is much stronger with "ask ANY question."

### Q2: Agent Framework — Which LangChain API?
**Options:** (a) LangGraph `create_react_agent` (modern) | (b) Legacy `AgentExecutor` (deprecated)
**Answer:** **(a) LangGraph** — Native tool-calling via Claude's tool-use API, first-class
streaming support (critical for Chainlit), proper state management. Day 4's CrewAI builds
on modern patterns so this keeps progression coherent.

### Q3: Chainlit Thinking Visualization — How deep?
**Options:** (a) Steps only | (b) Steps + Thinking | (c) Full trace
**Answer:** **(c) Full trace** — Every LangGraph event streamed: token-by-token LLM output,
tool inputs/outputs, all intermediate state. Maximum transparency. Drives home the
"nothing hidden" philosophy for a live demo audience.

### Q4: Sample Collection (LLM Grounding)
**Source:** `gen/data/reviews/reviews.jsonl` (203 reviews in Portuguese) + Postgres schema
from `gen/init.sql` (3 tables: customers, products, orders) + Docker Compose infrastructure
already running from Days 1-2.
- Positive reviews: quality, fast delivery, good packaging
- Negative reviews: delivery delays, damaged products, bad support, wrong items
- Schema: customers (UUID, name, email, city, state, segment) → orders (FK, qty, total, status, payment) → products (name, category, price, brand)

---

## 3. Selected Approach

### Approach A: LangGraph ReAct + Raw SQL + Full Chainlit Streaming ⭐

```
User (Chainlit) → LangGraph ReAct Agent (Claude Sonnet)
                      ├── Tool: execute_sql(query: str)     → Postgres (psycopg2)
                      └── Tool: semantic_search(query: str)  → Qdrant (LlamaIndex)
```

**Why chosen:**
- Maximum flexibility (any SQL question, any semantic query)
- Maximum transparency (full trace in Chainlit)
- Matches Day 3 "agent decides alone" narrative
- Claude's native tool-calling is more reliable than text-parsed ReAct
- LangGraph streaming is first-class for Chainlit integration

### Rejected Approaches

**Approach B: Dual-Mode with SQL Validation Layer** — Adds read-only validation on generated
SQL. Rejected because local Docker demo doesn't need write protection. Production safety
is Day 4 territory.

**Approach C: Tool-per-Query (Predefined Functions)** — Each of the 5 existing queries becomes
its own tool. Rejected because it limits what the audience can ask, undermining autonomy narrative.

---

## 4. YAGNI — Removed Features

| Feature | Why removed |
|---------|-------------|
| Conversation memory/history | Day 3 is single-turn demo; multi-turn is Day 4 |
| Authentication/rate limiting | Local Docker, no need |
| SQL write protection | Local throwaway DB, adds demo complexity |
| Multiple LLM fallback | Single model (Claude Sonnet) sufficient |
| Custom Chainlit theme/branding | Distraction from agent logic |
| Error retry/fallback chains | Overengineering for live demo |

---

## 5. Scope & File Manifest

**3 files, ~200 lines total:**

| File | Purpose | Key Detail |
|------|---------|------------|
| `src/day3/tools.py` | Two LangChain `@tool` functions | `execute_sql` (open SQL → Postgres via psycopg2) + `semantic_search` (query → Qdrant via LlamaIndex engine) |
| `src/day3/agent.py` | LangGraph ReAct agent | `ChatAnthropic(claude-sonnet-4-20250514)`, system prompt with full schema + dual-store explanation, test harness with 3 demo questions |
| `src/day3/chainlit_app.py` | Chainlit chat UI | Full-trace streaming of all LangGraph events, welcome message explaining The Ledger + The Memory |
| `src/day3/requirements.txt` | Day 3 dependencies | langchain-anthropic, langchain-core, langgraph, chainlit + Day 2 deps |

**Dependencies (new for Day 3):**
- `langchain-anthropic` — Claude integration
- `langchain-core` — Tool decorator, base classes
- `langgraph` — Modern ReAct agent with streaming
- `chainlit` — Chat interface

**Runtime:**
```bash
# Docker infra already running from Days 1-2
chainlit run src/day3/chainlit_app.py
```

---

## 6. Grounding Data

### Postgres Schema (The Ledger)
- `customers`: customer_id (UUID PK), name, email, city, state (CHAR 2), segment (premium/standard/basic)
- `products`: product_id (UUID PK), name, category, price (DECIMAL), brand
- `orders`: order_id (UUID PK), customer_id (FK), product_id (FK), qty (1-10), total, status (delivered/shipped/processing/cancelled), payment (pix/credit_card/boleto), created_at

### Qdrant Collection (The Memory)
- Collection: `shopagent_reviews` (203 documents)
- Fields: review_id, order_id, rating (1-5), comment (Portuguese), sentiment (positive/negative)
- Embedding: BAAI/bge-base-en-v1.5 via FastEmbed
- Themes: delivery speed, product quality, packaging, support quality, pricing

### Demo Questions (3 test cases)
1. "Qual o faturamento total por estado?" → should pick SQL (execute_sql)
2. "Quais clientes reclamam de entrega atrasada?" → should pick Qdrant (semantic_search)
3. "Top 3 estados com mais reclamacoes e seu faturamento" → should pick BOTH tools

---

## 7. Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangGraph (not legacy AgentExecutor) | Native tool-calling, streaming, modern API |
| SQL execution | Open SQL generation by Claude | Maximum flexibility, audience can ask anything |
| Vector search | LlamaIndex query engine over Qdrant | Reuses Day 2 pipeline, proven working |
| LLM | Claude Sonnet 4 (`claude-sonnet-4-20250514`) | Same model as Day 2, good balance of speed/quality |
| Streaming | Full trace (all LangGraph events) | Maximum transparency for live demo |
| Language | Portuguese (system prompt + responses) | Brazilian audience, matches review data |
| Connection | psycopg2 direct (not SQLAlchemy) | Consistent with Day 2's `ledger_queries.py` |

---

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude generates bad SQL | Demo fails | System prompt includes exact schema + examples |
| Qdrant collection not indexed | Semantic search empty | Prerequisite: Day 2 ingest must be complete |
| LangGraph API changes | Import errors | Pin versions in requirements.txt |
| Full trace too verbose in Chainlit | UI overwhelmed | Can filter event types if needed |

---

## 9. Quality Gate Checklist

- [x] Minimum 3 discovery questions asked (4 asked)
- [x] Sample collection question asked (Q4)
- [x] At least 2 approaches explored (3 explored)
- [x] YAGNI applied (6 features removed)
- [x] Minimum 2 validations completed (Q1 + Q5 scope validation)
- [x] User confirmed selected approach (Approach A)
- [x] Draft requirements included (Section 5 + 6)

---

## Next Step

```bash
/define .claude/sdd/features/BRAINSTORM_SHOPAGENT_DAY3.md
```
