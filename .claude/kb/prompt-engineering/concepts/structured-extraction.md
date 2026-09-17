# Structured Extraction

> **Purpose**: Extract typed, validated data fields from unstructured documents using LLM prompts
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

Structured extraction combines precise prompt instructions with schema enforcement to pull specific data fields from documents (invoices, contracts, reports). The key pattern is: define a schema, instruct the LLM to populate it, and validate the output programmatically. This achieves over 99% schema adherence when combined with Pydantic validation.

## The Pattern

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from openai import OpenAI

client = OpenAI()

class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class InvoiceData(BaseModel):
    invoice_number: str = Field(description="Unique invoice identifier")
    date: str = Field(description="Invoice date in ISO 8601 format")
    vendor_name: str = Field(description="Name of the vendor/supplier")
    total_amount: float = Field(description="Total amount without currency symbol")
    line_items: List[dict] = Field(default_factory=list)
    vendor_address: Optional[Address] = None

EXTRACTION_PROMPT = """You are an expert data extraction assistant.

## Task
Extract the following fields from the provided document.

## Schema
{schema}

## Rules
1. If a field is not found, return null
2. Dates must be ISO 8601 format (YYYY-MM-DD)
3. Amounts must be numeric (no currency symbols)
4. Return ONLY valid JSON matching the schema

## Document
{document_text}
"""

def extract_invoice(document_text: str) -> InvoiceData:
    schema = InvoiceData.model_json_schema()
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.0,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(
            schema=schema, document_text=document_text
        )}],
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content
    return InvoiceData.model_validate_json(raw)
```

## Quick Reference

| Component | Purpose | Notes |
|-----------|---------|-------|
| Pydantic schema | Define expected fields and types | Single source of truth |
| JSON mode | Force valid JSON response | `response_format={"type": "json_object"}` |
| Temperature 0.0 | Deterministic extraction | No creative variation |
| Null handling | Missing fields return None | Use `Optional` types |

## Common Mistakes

### Wrong

```python
# Vague prompt, no schema, no validation
prompt = "Extract data from this invoice and return JSON."
```

### Correct

```python
# Explicit schema, clear rules, validated output
prompt = """Extract these exact fields:
- invoice_number (string): Unique identifier
- date (string): ISO 8601 format
- total_amount (float): Numeric, no currency symbol

Return ONLY valid JSON. If a field is missing, use null."""
```

## Extraction Pipeline

```text
Document --> Prompt + Schema --> LLM --> Raw JSON --> Pydantic Validate --> Typed Data
                                                          |
                                                     On Error --> Retry with error context
```

## Related

- [Output Formatting](../concepts/output-formatting.md)
- [Document Extraction Pattern](../patterns/document-extraction.md)
- [Multi-Pass Extraction](../patterns/multi-pass-extraction.md)
