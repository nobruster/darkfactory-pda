# BUILD REPORT: ShopAgent Day 3 — Autonomous E-Commerce Agent

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY3 |
| **Date** | 2026-04-15 |
| **DESIGN** | [DESIGN_SHOPAGENT_DAY3.md](../features/DESIGN_SHOPAGENT_DAY3.md) |
| **Status** | BUILD COMPLETE |

---

## Files Created

| # | File | Lines | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `src/day3/__init__.py` | 0 | Created | Package marker |
| 2 | `src/day3/requirements.txt` | 12 | Created | 12 dependencies (LangChain + LlamaIndex + Chainlit) |
| 3 | `src/day3/tools.py` | 101 | Created | Two @tool functions: execute_sql + semantic_search |
| 4 | `src/day3/agent.py` | 90 | Created | LangGraph ReAct agent, system prompt, create_agent() factory |
| 5 | `src/day3/chainlit_app.py` | 65 | Created | Full-trace streaming via astream_events v2 |

**Total:** 268 lines across 5 files

---

## Verification Results

| Check | Result |
|-------|--------|
| `py_compile tools.py` | PASS |
| `py_compile agent.py` | PASS |
| `py_compile chainlit_app.py` | PASS |
| No duplicate system prompt | PASS (single source in agent.py) |
| Dependency order correct | PASS (tools → agent → chainlit_app) |

---

## Architecture Decisions Implemented

| Decision | Implementation |
|----------|---------------|
| Open SQL via system prompt | Full schema (3 tables, 18 columns) embedded in SYSTEM_PROMPT |
| LangGraph create_react_agent | `langgraph.prebuilt.create_react_agent` with ChatAnthropic |
| Full-trace streaming | `astream_events(version="v2")` mapping to cl.Step and cl.Message |
| Reuse Day 2 patterns | psycopg2 + LlamaIndex/Qdrant with same env vars |

---

## Deviations from DESIGN

| Deviation | Reason |
|-----------|--------|
| Added `create_agent()` factory function | Avoids module-level agent instantiation; enables `streaming` toggle between CLI (agent.py) and UI (chainlit_app.py) |
| System prompt in agent.py only (not duplicated in chainlit_app.py) | DRY — chainlit_app.py imports `create_agent` which carries the prompt |
| Tool display names mapping | Added `TOOL_DISPLAY_NAMES` dict in chainlit_app.py for UI-friendly labels ("The Ledger (SQL)" instead of "execute_sql") |

---

## Acceptance Test Readiness

| ID | Test | Ready? | How to Verify |
|----|------|--------|---------------|
| AT-001 | SQL routing | Yes | Ask "Qual o faturamento por estado?" → should call execute_sql |
| AT-002 | Semantic routing | Yes | Ask "O que os clientes falam sobre entrega?" → should call semantic_search |
| AT-003 | Hybrid routing | Yes | Ask "Estados com mais reclamacoes e seu ticket medio" → should call both |
| AT-004 | SQL flexibility | Yes | Ask any ad-hoc SQL question → agent generates SQL on the fly |
| AT-005 | Full trace visible | Yes | All events streamed as cl.Step + cl.Message tokens |
| AT-006 | Error resilience | Yes | Tools return error strings instead of raising exceptions |
| AT-007 | Startup | Yes | `chainlit run src/day3/chainlit_app.py` |

---

## How to Run

```bash
# Prerequisites: Docker infra from Days 1-2 must be running
cd gen && docker compose up -d

# Install Day 3 dependencies
pip install -r src/day3/requirements.txt

# Option 1: CLI test (no UI)
python3 -m src.day3.agent

# Option 2: Chainlit UI (full experience)
chainlit run src/day3/chainlit_app.py
```

---

## Open Items

| Item | Severity | Notes |
|------|----------|-------|
| Assumption A-004 (LangGraph streaming with ChatAnthropic) | Must verify | Needs runtime test with actual API key |
| Assumption A-005 (Chainlit consumes astream_events) | Must verify | Needs runtime test with Chainlit running |

Both assumptions require a live environment (Docker + API key) to validate. They cannot be verified through syntax checking alone.

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_SHOPAGENT_DAY3.md` (after live demo validation)
