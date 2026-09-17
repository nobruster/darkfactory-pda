# BaseModel

> **Purpose**: Core building block for defining validated data schemas in Pydantic v2
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

BaseModel is the primary class in Pydantic for defining data models with automatic type validation,
serialization, and JSON Schema generation. In Pydantic v2, it uses a Rust-based core
(pydantic-core) for significantly faster validation. Models validate data on instantiation
and provide methods for dict/JSON serialization and schema introspection.

## The Pattern

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class Invoice(BaseModel):
    """Schema for extracted invoice data."""
    model_config = ConfigDict(
        strict=False,           # allow type coercion
        str_strip_whitespace=True,
        validate_default=True,
    )

    invoice_number: str = Field(..., description="Unique invoice identifier")
    vendor_name: str = Field(..., min_length=1, description="Name of the vendor")
    total_amount: float = Field(..., gt=0, description="Total invoice amount")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    issue_date: datetime = Field(..., description="Date the invoice was issued")
    line_items: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
```

## Quick Reference

| Method | Input | Output | Notes |
|--------|-------|--------|-------|
| `Invoice(**data)` | kwargs | Invoice | Validates on creation |
| `Invoice.model_validate(d)` | dict | Invoice | Parse from dict |
| `Invoice.model_validate_json(s)` | JSON str | Invoice | Parse from JSON |
| `inv.model_dump()` | -- | dict | To dictionary |
| `inv.model_dump_json()` | -- | str | To JSON string |
| `inv.model_dump(exclude_none=True)` | -- | dict | Skip None fields |
| `Invoice.model_json_schema()` | -- | dict | JSON Schema output |
| `inv.model_copy(update={"currency": "EUR"})` | dict | Invoice | Clone with changes |

## Common Mistakes

### Wrong (Pydantic v1 syntax)

```python
class MyModel(BaseModel):
    class Config:
        orm_mode = True

    def dict(self, **kwargs):  # v1 method
        return super().dict(**kwargs)
```

### Correct (Pydantic v2 syntax)

```python
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    def to_dict(self):
        return self.model_dump()
```

## ConfigDict Options

| Option | Default | Purpose |
|--------|---------|---------|
| `strict` | `False` | Disable type coercion when True |
| `str_strip_whitespace` | `False` | Strip whitespace from strings |
| `validate_default` | `False` | Validate default values |
| `from_attributes` | `False` | Allow ORM-style attribute access |
| `populate_by_name` | `False` | Allow population by field name or alias |
| `extra` | `"ignore"` | Handle extra fields: ignore, allow, forbid |

## Serialization for LLM Prompts

```python
import json

# Generate JSON Schema to include in LLM prompts
schema = Invoice.model_json_schema()
prompt_instruction = (
    f"Return valid JSON matching this schema:\n"
    f"{json.dumps(schema, indent=2)}"
)

# Parse LLM response back into validated model
llm_response = '{"invoice_number": "INV-001", ...}'
invoice = Invoice.model_validate_json(llm_response)
```

## Related

- [Field Types](../concepts/field-types.md)
- [Validators](../concepts/validators.md)
- [LLM Output Validation](../patterns/llm-output-validation.md)
