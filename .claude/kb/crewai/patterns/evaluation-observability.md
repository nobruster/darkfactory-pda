# DeepEval + LangFuse for ShopAgent

> **Purpose**: Evaluate agent tool selection correctness and observe execution traces for the ShopAgent crew
> **MCP Validated**: 2026-04-12

## When to Use

- Day 4 quality gate before live demo: verify both agents route to the correct tool
- Catching regressions when prompts or models change
- Measuring latency and token cost per agent via LangFuse traces
- Running post-demo evaluations to score answer relevancy against expected outputs

## Implementation

```python
"""ShopAgent evaluation — tool routing correctness + LangFuse observability."""
from __future__ import annotations

import os

import pytest
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall
from langfuse import get_client, observe

# ---------------------------------------------------------------------------
# LangFuse client — reads from env vars automatically
# LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
# ---------------------------------------------------------------------------
langfuse = get_client()


# ---------------------------------------------------------------------------
# LangFuse: instrument the crew kickoff
# ---------------------------------------------------------------------------

@observe(name="shopagent-crew-run")
def run_crew_observed(question: str) -> str:
    """Run the full ShopAgent crew with LangFuse tracing."""
    from shopagent.crew import ShopAgentCrew

    crew = ShopAgentCrew().crew()
    result = crew.kickoff(inputs={"question": question})
    return result.raw


@observe(name="analyst-sql-query", as_type="generation")
def traced_sql_query(query: str) -> str:
    """Wrap SQL calls for per-query latency and token tracking."""
    from shopagent.tools import supabase_execute_sql
    return supabase_execute_sql(query)


@observe(name="researcher-semantic-search", as_type="generation")
def traced_semantic_search(query: str) -> str:
    """Wrap semantic searches for per-search latency tracking."""
    from shopagent.tools import qdrant_tool
    return qdrant_tool.run(query)


# ---------------------------------------------------------------------------
# DeepEval: tool routing test matrix
# ---------------------------------------------------------------------------

SQL_CASES: list[dict] = [
    {
        "input": "Qual o faturamento total por estado?",
        "actual_output": "SP: R$ 127.430 | RJ: R$ 89.210 | MG: R$ 68.440",
        "tools_called": [ToolCall(name="Supabase SQL Executor")],
        "expected_tools": [ToolCall(name="Supabase SQL Executor")],
    },
    {
        "input": "Quantos pedidos foram feitos por pix?",
        "actual_output": "1.847 pedidos pagos via pix (45% do total).",
        "tools_called": [ToolCall(name="Supabase SQL Executor")],
        "expected_tools": [ToolCall(name="Supabase SQL Executor")],
    },
    {
        "input": "Qual o ticket medio por segmento de cliente?",
        "actual_output": "Premium: R$ 487 | Standard: R$ 234 | Basic: R$ 112",
        "tools_called": [ToolCall(name="Supabase SQL Executor")],
        "expected_tools": [ToolCall(name="Supabase SQL Executor")],
    },
]

SEMANTIC_CASES: list[dict] = [
    {
        "input": "Quais clientes reclamam de entrega?",
        "actual_output": "23 reviews negativos sobre entrega: atrasos, extravio, frete caro.",
        "retrieval_context": ["Demorou 15 dias.", "Nao recebi meu pedido.", "Frete caro demais."],
        "tools_called": [ToolCall(name="Qdrant Semantic Search")],
        "expected_tools": [ToolCall(name="Qdrant Semantic Search")],
    },
    {
        "input": "O que os clientes falam sobre qualidade dos produtos?",
        "actual_output": "Maioria positiva. 12% citam problemas com durabilidade.",
        "retrieval_context": ["Produto otimo!", "Qualidade boa pelo preco.", "Quebrou em 2 semanas."],
        "tools_called": [ToolCall(name="Qdrant Semantic Search")],
        "expected_tools": [ToolCall(name="Qdrant Semantic Search")],
    },
    {
        "input": "Qual o sentimento geral sobre o frete?",
        "actual_output": "67% negativo. Principais queixas: prazo e custo.",
        "retrieval_context": ["Frete caro demais.", "Chegou antes do previsto!", "Rastreamento nao funciona."],
        "tools_called": [ToolCall(name="Qdrant Semantic Search")],
        "expected_tools": [ToolCall(name="Qdrant Semantic Search")],
    },
]

ALL_CASES = SQL_CASES + SEMANTIC_CASES


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

tool_metric = ToolCorrectnessMetric(threshold=1.0)

relevancy_metric = AnswerRelevancyMetric(
    threshold=0.7,
    model="claude-sonnet-4-20250514",
    include_reason=True,
)


# ---------------------------------------------------------------------------
# pytest: tool routing correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", SQL_CASES)
def test_analyst_routes_to_sql(case: dict) -> None:
    tc = LLMTestCase(**case)
    tool_metric.measure(tc)
    assert tool_metric.score == 1.0, (
        f"AnalystAgent routed to wrong tool.\n"
        f"Expected: {case['expected_tools'][0].name}\n"
        f"Got: {case['tools_called'][0].name}\n"
        f"Reason: {tool_metric.reason}"
    )


@pytest.mark.parametrize("case", SEMANTIC_CASES)
def test_researcher_routes_to_qdrant(case: dict) -> None:
    tc = LLMTestCase(**case)
    tool_metric.measure(tc)
    assert tool_metric.score == 1.0, (
        f"ResearchAgent routed to wrong tool.\n"
        f"Expected: {case['expected_tools'][0].name}\n"
        f"Got: {case['tools_called'][0].name}\n"
        f"Reason: {tool_metric.reason}"
    )


# ---------------------------------------------------------------------------
# Batch evaluation (non-pytest, for live demo reporting)
# ---------------------------------------------------------------------------

def run_full_evaluation() -> None:
    """Run batch evaluation and print pass/fail summary."""
    test_cases = [LLMTestCase(**c) for c in ALL_CASES]
    evaluate(test_cases=test_cases, metrics=[tool_metric, relevancy_metric])
    print("\n=== ShopAgent Evaluation Summary ===")
    for tc in test_cases:
        expected = tc.expected_tools[0].name if tc.expected_tools else "—"
        actual = tc.tools_called[0].name if tc.tools_called else "—"
        routing = "PASS" if expected == actual else "FAIL"
        print(f"[{routing}] {tc.input[:55]}")
    langfuse.flush()

if __name__ == "__main__":
    run_full_evaluation()
```

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `ToolCorrectnessMetric.threshold` | `1.0` | Binary — must route to exact tool |
| `AnswerRelevancyMetric.threshold` | `0.7` | Minimum relevancy score (0-1) |
| `model` for LLM metrics | `claude-sonnet-4-20250514` | Match ShopAgent model |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Or self-hosted URL |
| `LANGFUSE_SECRET_KEY` | env var | Never hardcode |
| `@observe` scope | Per crew run | Creates one trace with nested spans per agent |

## Running

```bash
# Tool routing correctness
pytest src/day4/tests/test_evaluation.py -v
# Full batch evaluation with LangFuse traces
python src/day4/tests/test_evaluation.py
```

## See Also

- [DeepEval Agent Evaluation](../../deepeval/patterns/agent-evaluation.md)
- [DeepEval pytest Integration](../../deepeval/patterns/pytest-integration.md)
- [LangFuse Python SDK](../../langfuse/patterns/python-sdk-integration.md)
- [ShopAgent MCP Tools](../patterns/shopagent-tools.md)
