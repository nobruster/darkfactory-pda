# Chain-of-Thought Prompting

> **Purpose**: Guide LLMs through explicit step-by-step reasoning to improve accuracy on complex tasks
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

Chain-of-Thought (CoT) prompting instructs the model to reason step by step before producing a final answer. LLMs often fail not because they lack knowledge, but because they skip reasoning steps. CoT exposes the model's thought process, making outputs more accurate, auditable, and reliable -- especially for logic, math, and multi-step extraction tasks.

## The Pattern

```python
from openai import OpenAI

client = OpenAI()

COT_PROMPT = """You are an expert data analyst.

## Task
Analyze the following financial data and determine the quarterly growth rate.

## Instructions
Think through this step by step:
1. Identify the revenue for each quarter
2. Calculate the difference between consecutive quarters
3. Compute the percentage change
4. Provide the final growth rate

## Important
Show your reasoning for each step before giving the final answer.

## Data
{data}

## Output Format
Return JSON with fields: steps (list of reasoning strings), final_answer (float), confidence (float 0-1)
"""

def analyze_with_cot(data: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {"role": "system", "content": "You reason step by step before answering."},
            {"role": "user", "content": COT_PROMPT.format(data=data)}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

## Quick Reference

| Variant | When to Use | Notes |
|---------|-------------|-------|
| Zero-shot CoT | Simple reasoning, add "think step by step" | Minimal prompt change |
| Few-shot CoT | Complex logic, provide worked examples | Higher accuracy, more tokens |
| Self-consistency | High-stakes, sample multiple paths then vote | Best accuracy, highest cost |

## Common Mistakes

### Wrong

```python
# No reasoning requested -- LLM jumps to answer
prompt = "What is the quarterly growth rate? Data: {data}"
```

### Correct

```python
# Explicit reasoning steps before answer
prompt = """Think step by step:
1. First, identify the relevant numbers
2. Then, calculate the differences
3. Finally, compute the percentage

Show your work, then provide the final answer.

Data: {data}"""
```

## When NOT to Use CoT

- Simple lookups or classifications (adds unnecessary tokens)
- When latency is critical and accuracy is already high
- For tasks with single-step answers (e.g., sentiment: positive/negative)

## Self-Consistency Extension

```python
import json
from collections import Counter

def cot_with_self_consistency(prompt: str, n_samples: int = 5) -> str:
    """Sample multiple CoT paths, return majority answer."""
    answers = []
    for _ in range(n_samples):
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.7,  # Higher temp for diverse paths
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        answers.append(result.get("final_answer"))

    # Majority vote
    most_common = Counter(answers).most_common(1)[0][0]
    return most_common
```

## Related

- [Structured Extraction](../concepts/structured-extraction.md)
- [Validation Prompts](../patterns/validation-prompts.md)
- [Multi-Pass Extraction](../patterns/multi-pass-extraction.md)
