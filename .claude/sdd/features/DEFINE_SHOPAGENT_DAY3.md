# DEFINE: ShopAgent Day 3 — Autonomous E-Commerce Agent

> Autonomous LangGraph agent that decides which data store to query (Postgres for exact data, Qdrant for semantic search) with a full-trace Chainlit chat interface.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY3 |
| **Date** | 2026-04-15 |
| **Author** | define-agent (from BRAINSTORM_SHOPAGENT_DAY3) |
| **Status** | Ready for Design |
| **Clarity Score** | 15/15 |

---

## Problem Statement

During Days 1-2, participants built two data stores (Postgres + Qdrant) but had to manually decide which one to query for each question. There is no autonomous system that can receive a natural-language question in Portuguese, reason about whether it needs exact data (SQL) or semantic meaning (vector search), execute the right query, and present results through a conversational interface. Day 3 must close this gap — the agent decides alone.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Workshop Participant | AI Data Engineer student (200+ attendees) | Must manually decide "is this a SQL question or a semantic question?" for every query against their data |
| Instructor (Luan) | Live demo presenter | Needs a visually compelling, reliable demo that shows autonomous agent reasoning in real-time |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Agent autonomously routes questions to the correct store (SQL vs. semantic) without human intervention |
| **MUST** | Agent generates valid SQL on the fly for any question about the 3-table Postgres schema |
| **MUST** | Agent performs semantic search against Qdrant for review-related questions |
| **MUST** | Agent handles hybrid questions that require BOTH stores in sequence |
| **MUST** | Chainlit chat interface streams full agent trace (thinking, tool calls, tool results, final answer) |
| **MUST** | All interactions in Portuguese (system prompt, tool descriptions, agent responses) |
| **SHOULD** | Agent explains its reasoning before each tool call (visible chain-of-thought) |
| **COULD** | Welcome message in Chainlit explains the two stores to orient first-time users |

---

## Success Criteria

- [ ] Agent correctly routes "Qual o faturamento total por estado?" to `execute_sql` (SQL-only question)
- [ ] Agent correctly routes "Quais clientes reclamam de entrega atrasada?" to `semantic_search` (semantic-only question)
- [ ] Agent correctly uses BOTH tools for "Top 3 estados com mais reclamacoes e seu faturamento" (hybrid question)
- [ ] SQL tool returns valid tabular results from Postgres for at least 5 different ad-hoc questions
- [ ] Semantic search returns relevant review excerpts with similarity scores from Qdrant
- [ ] Chainlit UI renders agent thinking steps, tool invocations, and tool results in real-time
- [ ] Full round-trip (question → reasoning → tool calls → answer) completes in under 30 seconds
- [ ] Application starts with `chainlit run src/day3/chainlit_app.py` and no manual configuration

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | SQL routing | Agent is running, Postgres has data | User asks "Qual o faturamento por estado?" | Agent calls `execute_sql` with valid SQL, returns state/revenue table |
| AT-002 | Semantic routing | Agent is running, Qdrant has 203 reviews indexed | User asks "O que os clientes falam sobre entrega?" | Agent calls `semantic_search`, returns relevant review excerpts |
| AT-003 | Hybrid routing | Both stores available | User asks "Estados com mais reclamacoes e seu ticket medio" | Agent calls `semantic_search` first (find complaints), then `execute_sql` (calculate revenue), combines both |
| AT-004 | SQL flexibility | Postgres has data | User asks "Quantos pedidos via Pix no ultimo mes?" | Agent generates correct SQL with payment='pix' filter and date clause |
| AT-005 | Full trace visible | Chainlit UI is open | User sends any question | UI shows: thinking step → tool call with arguments → tool result → final answer |
| AT-006 | Error resilience | Postgres is running, Qdrant is running | User asks a vague question like "me conta tudo" | Agent attempts reasonable interpretation, does not crash |
| AT-007 | Startup | Docker infra running (postgres + qdrant) | Run `chainlit run src/day3/chainlit_app.py` | App starts, shows welcome message, accepts questions |

---

## Out of Scope

- **Conversation memory/history** — Each question is independent; multi-turn context is Day 4 (CrewAI)
- **SQL write protection** — Local Docker DB is throwaway; production safety deferred to Day 4
- **Authentication/rate limiting** — Local-only, no external access
- **Multiple LLM fallback** — Single model (Claude Sonnet 4) is sufficient
- **Custom Chainlit theme/branding** — Default theme; visual polish is Day 4
- **Error retry/fallback chains** — Overengineering for a live demo
- **Unit tests for tools** — Day 3 validates through live demo; formal testing is Day 4 (DeepEval)

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Must reuse Day 2 infrastructure: Postgres (localhost:5432) + Qdrant (localhost:6333) | No new Docker services; agent connects to existing containers |
| Technical | Must use LangGraph `create_react_agent` (not legacy AgentExecutor) | Modern API; requires `langgraph` dependency |
| Technical | Must use `ChatAnthropic` with `claude-sonnet-4-20250514` | Consistent with Day 2 LLM choice |
| Technical | Qdrant search must use LlamaIndex query engine with `BAAI/bge-base-en-v1.5` embeddings | Reuses Day 2 ingest pipeline; same embedding model |
| Technical | Python 3.11+ with type hints | Project convention |
| Timeline | Must be built during a live 40-minute coding block (22h00-22h40 on 2026-04-15) | Code must be concise (~200 lines across 3 files) |
| Dependency | Day 2 ingest must be complete (Postgres populated, Qdrant indexed) | Agent has no data to query otherwise |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `src/day3/` | Follows per-day directory convention |
| **KB Domains** | langchain, chainlit, genai, qdrant, supabase, python | Agent framework, UI, architecture patterns, both data stores |
| **IaC Impact** | None — reuses Day 2 Docker infrastructure | No new services or config changes |

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| customers | Postgres table | ~500 rows (ShadowTraffic generated) | Static after Day 1 ingest | gen/shadowtraffic.json |
| products | Postgres table | ~50 rows | Static after Day 1 ingest | gen/shadowtraffic.json |
| orders | Postgres table | ~2000+ rows (continuously generated) | Real-time via ShadowTraffic | gen/shadowtraffic.json |
| reviews | Qdrant collection `shopagent_reviews` | 203 documents | Static after Day 2 ingest | gen/data/reviews/reviews.jsonl |

### Schema Contract (Postgres — The Ledger)

| Table | Column | Type | Constraints | PII? |
|-------|--------|------|-------------|------|
| customers | customer_id | UUID | PK | No |
| customers | name | VARCHAR(255) | NOT NULL | Yes |
| customers | email | VARCHAR(255) | NOT NULL | Yes |
| customers | city | VARCHAR(100) | | No |
| customers | state | CHAR(2) | | No |
| customers | segment | VARCHAR(20) | CHECK: premium/standard/basic | No |
| products | product_id | UUID | PK | No |
| products | name | VARCHAR(255) | NOT NULL | No |
| products | category | VARCHAR(100) | NOT NULL | No |
| products | price | DECIMAL(10,2) | CHECK > 0 | No |
| products | brand | VARCHAR(100) | | No |
| orders | order_id | UUID | PK | No |
| orders | customer_id | UUID | FK → customers | No |
| orders | product_id | UUID | FK → products | No |
| orders | qty | INTEGER | CHECK 1-10 | No |
| orders | total | DECIMAL(10,2) | CHECK >= 0 | No |
| orders | status | VARCHAR(20) | CHECK: delivered/shipped/processing/cancelled | No |
| orders | payment | VARCHAR(20) | CHECK: pix/credit_card/boleto | No |
| orders | created_at | TIMESTAMPTZ | DEFAULT now() | No |

### Schema Contract (Qdrant — The Memory)

| Field | Type | Notes |
|-------|------|-------|
| review_id | UUID | Document ID |
| order_id | UUID | FK → orders (in metadata) |
| rating | INTEGER (1-5) | Star rating |
| comment | TEXT (Portuguese) | Embedded via BAAI/bge-base-en-v1.5 |
| sentiment | STRING | positive / negative |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Docker infra (Postgres + Qdrant) is running from Days 1-2 | Agent cannot connect to either store; startup fails | [x] Validated via docker-compose.yml |
| A-002 | Qdrant collection `shopagent_reviews` is populated with 203 reviews | Semantic search returns empty results | [x] Validated via reviews.jsonl (203 lines) |
| A-003 | Claude Sonnet 4 generates valid SQL for this 3-table schema | Agent returns errors or wrong data for SQL questions | [x] Validated — schema is simple, Claude excels at SQL |
| A-004 | LangGraph `create_react_agent` supports `ChatAnthropic` with tool streaming | Agent doesn't stream properly in Chainlit | [ ] Must verify at build time |
| A-005 | Chainlit can consume LangGraph's `astream_events` for full trace | UI doesn't render intermediate steps | [ ] Must verify at build time |
| A-006 | `ANTHROPIC_API_KEY` is set in `.env` | LLM calls fail with auth error | [x] Validated via .env.example |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Specific: manual store routing → autonomous routing. Clear who (participants), clear impact (agent decides alone) |
| Users | 3 | Two personas: workshop participant (200+ students) and instructor (live demo). Pain points documented |
| Goals | 3 | 8 goals with MoSCoW priority. MUST goals are testable (routing, SQL generation, streaming) |
| Success | 3 | 8 measurable criteria with specific test questions, performance target (<30s), and startup command |
| Scope | 3 | 7 items explicitly excluded with rationale. Each maps to a Day 4 upgrade. Constraints include timeline (40-min coding block) |
| **Total** | **15/15** | |

---

## Open Questions

None — ready for Design. All architectural decisions were resolved in the BRAINSTORM phase:
- Open SQL (not constrained) ✓
- LangGraph (not legacy AgentExecutor) ✓
- Full trace streaming (not filtered) ✓
- Scope validated by user ✓

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-15 | define-agent | Initial version from BRAINSTORM_SHOPAGENT_DAY3.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_SHOPAGENT_DAY3.md`
