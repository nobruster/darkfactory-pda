# Guardrails

> **Purpose**: Safety guardrails for LLM applications -- input/output filtering, topic control, content safety
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Guardrails are programmable safety layers that intercept inputs and outputs of LLM systems to enforce policies. They prevent jailbreaks, block harmful content, restrict off-topic conversations, and validate output structure. In production, guardrails operate at multiple pipeline stages: pre-LLM (input rails), mid-pipeline (retrieval rails), and post-LLM (output rails).

## The Pattern

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from abc import ABC, abstractmethod

class RailAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"

@dataclass
class RailResult:
    action: RailAction
    message: Optional[str] = None
    modified_content: Optional[str] = None
    violated_policy: Optional[str] = None

class GuardRail(ABC):
    @abstractmethod
    def check(self, content: str, context: dict) -> RailResult:
        pass

class TopicRail(GuardRail):
    """Restrict conversation to allowed topics."""
    def __init__(self, allowed_topics: list[str], llm_classifier=None):
        self.allowed_topics = allowed_topics
        self.llm_classifier = llm_classifier

    def check(self, content: str, context: dict) -> RailResult:
        topic = self.llm_classifier.classify(content, self.allowed_topics)
        if topic in self.allowed_topics:
            return RailResult(action=RailAction.ALLOW)
        return RailResult(
            action=RailAction.BLOCK,
            message="I can only help with: " + ", ".join(self.allowed_topics),
            violated_policy="topic_restriction",
        )

class OutputFactualityRail(GuardRail):
    """Check output is grounded in provided context."""
    def check(self, content: str, context: dict) -> RailResult:
        retrieved = context.get("retrieved_chunks", "")
        if not retrieved:
            return RailResult(action=RailAction.ALLOW)
        is_grounded = self._check_grounding(content, retrieved)
        if is_grounded:
            return RailResult(action=RailAction.ALLOW)
        return RailResult(action=RailAction.MODIFY,
            modified_content="I don't have enough information to answer that.",
            violated_policy="factuality")
```

## Guardrail Pipeline

```text
User Input
    |
[Input Rails]  -- jailbreak detection, PII redaction, topic check
    |
[Retrieval Rails]  -- relevance filtering, content safety
    |
[LLM Generation]
    |
[Output Rails]  -- factuality check, toxicity filter, format validation
    |
Safe Response
```

## Quick Reference

| Rail | Stage | Latency | Technique |
|------|-------|---------|-----------|
| Jailbreak detection | Input | 50-200ms | Classifier (Llama Guard) |
| PII redaction | Input | 10-50ms | Regex + NER |
| Topic control | Input | 100-300ms | LLM classifier |
| Relevance filter | Retrieval | 10-50ms | Similarity threshold |
| Factuality check | Output | 200-500ms | LLM-as-judge |
| Toxicity filter | Output | 50-200ms | Classifier |
| Format validation | Output | 5-20ms | JSON Schema / Pydantic |

## NeMo Guardrails Configuration

```yaml
models:
  - type: main
    engine: openai
    model: gpt-4o
rails:
  input:
    flows:
      - self check input
  output:
    flows:
      - self check output
instructions:
  - type: general
    content: |
      You are a helpful customer support assistant.
      Only answer questions about our products and services.
```

## Common Mistakes

### Wrong

```python
# Guardrails only on output -- misses prompt injection
response = llm.generate(user_input)  # user_input could be a jailbreak
filtered = toxicity_filter(response)  # too late
```

### Correct

```python
pipeline = GuardrailPipeline(rails=[
    JailbreakDetector(),      # pre-LLM
    PIIRedactor(),
    TopicRail(["billing", "support"]),
    FactualityChecker(),      # post-LLM
    ToxicityFilter(),
    FormatValidator(schema),
])
result = pipeline.run(user_input)
```

## Related

- [State Machines](../concepts/state-machines.md)
- [Chatbot Architecture Pattern](../patterns/chatbot-architecture.md)
- [Tool Calling](../concepts/tool-calling.md)
