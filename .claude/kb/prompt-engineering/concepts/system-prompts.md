# System Prompts

> **Purpose**: Design effective system prompts that define persona, behavior, and constraints for LLMs
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

System prompts set the behavioral foundation for an LLM conversation. They define the model's role, expertise domain, output constraints, and guardrails. A well-designed system prompt reduces hallucinations, enforces consistent formatting, and establishes the boundaries within which the model operates. System prompts are processed before user messages and carry higher weight in most models.

## The Pattern

```python
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """You are a senior financial data analyst specializing in invoice processing.

## Role
- Extract and validate financial data from documents
- Flag anomalies or suspicious values
- Always provide confidence scores for extracted fields

## Constraints
- NEVER fabricate data that is not present in the document
- If a field cannot be found, return null with confidence 0.0
- Dates must be in ISO 8601 format (YYYY-MM-DD)
- Monetary amounts must be numeric without currency symbols
- Always respond in valid JSON format

## Quality Standards
- Double-check extracted numbers against document context
- Cross-validate totals against line item sums
- Flag discrepancies rather than silently correcting them
"""

def process_with_system_prompt(document: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract all data from:\n\n{document}"}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

## System Prompt Anatomy

| Section | Purpose | Required |
|---------|---------|----------|
| Role | Define expertise and persona | Yes |
| Task Scope | What the model should do | Yes |
| Constraints | What the model must NOT do | Yes |
| Output Format | Response structure rules | Yes |
| Quality Rules | Standards and checks | Recommended |
| Error Handling | What to do when uncertain | Recommended |

## Common Mistakes

### Wrong

```python
# Vague, no constraints, no format
system = "You are a helpful assistant."
```

### Correct

```python
# Specific role, clear constraints, defined output
system = """You are a medical record classifier.

Role: Classify clinical notes into ICD-10 categories.
Constraints: NEVER suggest diagnoses. Only classify based on explicit text.
Output: JSON with fields: code, description, confidence, evidence_quote.
Error: If uncertain, set confidence below 0.5 and explain in notes field."""
```

## Design Principles

1. **Be specific** -- Name the exact domain and expertise level
2. **Define boundaries** -- What the model must NOT do is as important as what it should
3. **Set output rules** -- Format, structure, and data type expectations
4. **Handle uncertainty** -- Tell the model what to do when it does not know
5. **Keep it focused** -- One clear role per system prompt, not multiple personas
6. **Test adversarially** -- Try to break the constraints with edge-case inputs

## Provider-Specific Notes

| Provider | System Prompt Support | Notes |
|----------|----------------------|-------|
| OpenAI | `role: "system"` message | Strong adherence, supports JSON mode |
| Anthropic | `system` parameter | Separate from messages, very strong adherence |
| Google Gemini | `system_instruction` | Part of model config, good adherence |
| OpenRouter | `role: "system"` message | Varies by underlying model |

## Related

- [Output Formatting](../concepts/output-formatting.md)
- [Few-Shot Prompting](../concepts/few-shot-prompting.md)
- [Prompt Template Pattern](../patterns/prompt-template.md)
