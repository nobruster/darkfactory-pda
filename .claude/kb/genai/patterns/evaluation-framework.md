# Evaluation Framework Pattern

> **Purpose**: LLM and RAG evaluation using LLM-as-judge, RAGAS metrics, and automated quality pipelines
> **MCP Validated**: 2026-02-17

## When to Use

- Measuring RAG pipeline quality (faithfulness, relevance, recall)
- Evaluating LLM output quality without manual annotation
- A/B testing prompt versions or model changes
- Continuous quality monitoring in production

## Implementation

```python
from dataclasses import dataclass, field
from typing import Optional, Callable

@dataclass
class EvalSample:
    question: str
    contexts: list[str]
    answer: str
    ground_truth: Optional[str] = None

@dataclass
class EvalResult:
    sample: EvalSample
    scores: dict[str, float]
    feedback: dict[str, str] = field(default_factory=dict)

class EvaluationFramework:
    def __init__(self, judge_model: str = "gpt-4o"):
        self.judge_model = judge_model
        self.metrics: dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.metrics["faithfulness"] = self._eval_faithfulness
        self.metrics["answer_relevancy"] = self._eval_answer_relevancy
        self.metrics["context_precision"] = self._eval_context_precision

    def evaluate(self, samples: list[EvalSample],
                 metrics: Optional[list[str]] = None) -> list[EvalResult]:
        """Evaluate a batch of samples across specified metrics."""
        metrics = metrics or list(self.metrics.keys())
        results = []
        for sample in samples:
            scores, feedback = {}, {}
            for name in metrics:
                scorer = self.metrics.get(name)
                if scorer:
                    score, reason = scorer(sample)
                    scores[name] = score
                    feedback[name] = reason
            results.append(EvalResult(sample=sample, scores=scores, feedback=feedback))
        return results

    def _eval_faithfulness(self, sample: EvalSample) -> tuple[float, str]:
        """Check if answer is grounded in provided contexts."""
        prompt = f"""Judge faithfulness. What fraction of claims in the ANSWER
are supported by the CONTEXT?
CONTEXT: {chr(10).join(sample.contexts)}
ANSWER: {sample.answer}
Score 0.0-1.0. JSON: {{"score": <float>, "reason": "<str>"}}"""
        result = self._call_judge(prompt)
        return result["score"], result["reason"]

    def _eval_answer_relevancy(self, sample: EvalSample) -> tuple[float, str]:
        """Check if answer addresses the question."""
        prompt = f"""Judge answer relevancy.
QUESTION: {sample.question}
ANSWER: {sample.answer}
Score 0.0-1.0. JSON: {{"score": <float>, "reason": "<str>"}}"""
        result = self._call_judge(prompt)
        return result["score"], result["reason"]

    def _eval_context_precision(self, sample: EvalSample) -> tuple[float, str]:
        """Check if retrieved contexts are relevant to the question."""
        prompt = f"""Judge context precision.
QUESTION: {sample.question}
CONTEXTS: {chr(10).join(f'[{i+1}] {c}' for i, c in enumerate(sample.contexts))}
Score = relevant/total. JSON: {{"score": <float>, "reason": "<str>"}}"""
        result = self._call_judge(prompt)
        return result["score"], result["reason"]
```

## RAGAS Integration

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

def evaluate_with_ragas(questions, contexts, answers, ground_truths=None):
    """Evaluate RAG pipeline using RAGAS framework."""
    data = {"question": questions, "contexts": contexts, "answer": answers}
    if ground_truths:
        data["ground_truth"] = ground_truths
    dataset = Dataset.from_dict(data)
    metrics = [faithfulness, answer_relevancy, context_precision]
    if ground_truths:
        metrics.append(context_recall)
    return evaluate(dataset=dataset, metrics=metrics)

# Example
result = evaluate_with_ragas(
    questions=["What is RAG?"],
    contexts=[["RAG combines retrieval with generation to ground LLM responses."]],
    answers=["RAG retrieves relevant documents before generation."],
    ground_truths=["RAG retrieves external knowledge to augment LLM generation."],
)
# {'faithfulness': 0.95, 'answer_relevancy': 0.92, 'context_precision': 1.0, 'context_recall': 0.88}
```

## LLM-as-Judge Best Practices

| Practice | Description |
|----------|-------------|
| Use structured output | JSON responses with score + reason |
| Calibrate with humans | Align judge scores with expert annotations |
| Use frontier models | GPT-4o or Claude for judging accuracy |
| Include rubrics | Explicit scoring criteria in the prompt |
| Multi-judge consensus | Average scores from multiple judge runs |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `judge_model` | `gpt-4o` | Model used for LLM-as-judge |
| `batch_size` | `50` | Samples per evaluation batch |
| `min_faithfulness` | `0.85` | Alert threshold for faithfulness |
| `min_relevancy` | `0.80` | Alert threshold for relevancy |

## CI/CD Quality Gate

```python
def ci_evaluation_gate(pipeline, test_dataset, thresholds):
    """Fail build if quality drops below thresholds."""
    results = evaluate_pipeline(pipeline, test_dataset)
    avg_scores = aggregate_scores(results)
    failures = []
    for metric, threshold in thresholds.items():
        if avg_scores.get(metric, 0) < threshold:
            failures.append(f"{metric}: {avg_scores[metric]:.2f} < {threshold}")
    if failures:
        raise QualityGateError(f"Quality gate failed: {'; '.join(failures)}")
    return avg_scores

thresholds = {"faithfulness": 0.85, "answer_relevancy": 0.80, "context_precision": 0.75}
ci_evaluation_gate(rag_pipeline, test_set, thresholds)
```

## See Also

- [RAG Pipeline](../patterns/rag-pipeline.md)
- [RAG Architecture](../concepts/rag-architecture.md)
- [Guardrails](../concepts/guardrails.md)
