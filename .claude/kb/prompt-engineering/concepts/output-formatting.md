# Output Formatting

> **Purpose**: Enforce reliable JSON and structured output from LLMs using prompts, API features, and validation
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

Getting consistent structured output from LLMs requires a combination of prompt engineering, API-level constraints, and post-processing validation. The most reliable approach is: define a schema in the prompt, enable JSON mode at the API level, and validate with Pydantic. This achieves over 99% schema adherence in production.

## The Pattern

```python
import json
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List
from openai import OpenAI

client = OpenAI()

class TaskResult(BaseModel):
    status: str = Field(description="completed | failed | partial")
    summary: str = Field(description="Brief result summary")
    items: List[dict] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    errors: Optional[List[str]] = None

FORMATTING_PROMPT = """Analyze the following data and return results.

## Output Format
Return a JSON object with exactly these fields:
- status (string): "completed", "failed", or "partial"
- summary (string): Brief description of results
- items (array): List of extracted items as objects
- confidence (float): 0.0 to 1.0 confidence score
- errors (array|null): List of error messages or null

## Example Output
{{
  "status": "completed",
  "summary": "Extracted 3 items from document",
  "items": [{{"name": "Item A", "value": 100}}],
  "confidence": 0.92,
  "errors": null
}}

## Data
{data}
"""

def get_structured_output(data: str) -> TaskResult:
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[{"role": "user", "content": FORMATTING_PROMPT.format(data=data)}],
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content
    return TaskResult.model_validate_json(raw)
```

## API-Level JSON Enforcement

| Provider | Method | Reliability |
|----------|--------|-------------|
| OpenAI | `response_format={"type": "json_object"}` | High |
| OpenAI | `response_format={"type": "json_schema", "json_schema": ...}` | Highest |
| Anthropic | Tool use with schema (recommended) | High |
| Google Gemini | `response_mime_type="application/json"` | High |

## Validation Pipeline

```python
def parse_with_retry(raw_json: str, model_class: type, max_retries: int = 2) -> BaseModel:
    """Parse JSON with retry on validation failure."""
    for attempt in range(max_retries + 1):
        try:
            return model_class.model_validate_json(raw_json)
        except ValidationError as e:
            if attempt == max_retries:
                raise
            # Re-prompt with error context for repair
            raw_json = repair_json(raw_json, str(e))
    raise ValueError("Exceeded max retries")

def repair_json(broken_json: str, error_msg: str) -> str:
    """Ask LLM to fix malformed JSON."""
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[{"role": "user", "content": f"""Fix this JSON. Error: {error_msg}

Broken JSON:
{broken_json}

Return ONLY the corrected JSON, nothing else."""}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

## Common Mistakes

### Wrong

```python
# No format enforcement -- output may include markdown, text, etc.
prompt = "Return the data as JSON"
```

### Correct

```python
# Schema in prompt + API enforcement + Pydantic validation
prompt = "Return ONLY a JSON object matching this schema: {schema}"
# Plus: response_format={"type": "json_object"}
# Plus: Pydantic.model_validate_json(response)
```

## Formatting Strategies Summary

| Strategy | Reliability | Complexity | Use When |
|----------|------------|------------|----------|
| Prompt-only | Medium | Low | Quick prototypes |
| Prompt + JSON mode | High | Low | Most production use |
| Prompt + JSON Schema mode | Highest | Medium | Strict schemas |
| Prompt + Tool Use | Highest | Medium | Anthropic Claude |
| Prompt + Instructor lib | Highest | Low | Python projects |

## Related

- [Structured Extraction](../concepts/structured-extraction.md)
- [Document Extraction Pattern](../patterns/document-extraction.md)
- [Prompt Template Pattern](../patterns/prompt-template.md)
