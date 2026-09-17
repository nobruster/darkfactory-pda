# Pydantic Knowledge Base

> **Purpose**: Python data validation for LLM output parsing and structured extraction
> **MCP Validated**: 2026-02-17

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/base-model.md](concepts/base-model.md) | BaseModel fundamentals, model methods, serialization |
| [concepts/field-types.md](concepts/field-types.md) | Field types, Optional, Annotated, constraints |
| [concepts/validators.md](concepts/validators.md) | field_validator, model_validator, modes |
| [concepts/nested-models.md](concepts/nested-models.md) | Nested model composition, recursive structures |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/llm-output-validation.md](patterns/llm-output-validation.md) | Validate and parse LLM JSON responses |
| [patterns/extraction-schema.md](patterns/extraction-schema.md) | Build schemas for document data extraction |
| [patterns/error-handling.md](patterns/error-handling.md) | Handle ValidationError, retries, fallbacks |
| [patterns/custom-validators.md](patterns/custom-validators.md) | Reusable custom validation logic |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/invoice-schema.yaml](specs/invoice-schema.yaml) | Invoice extraction Pydantic schema spec |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **BaseModel** | Core class for defining data schemas with automatic validation |
| **Field Types** | Type annotations with Optional, Annotated, and Field constraints |
| **Validators** | Decorators for custom field-level and model-level validation |
| **Nested Models** | Composable hierarchical data structures |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/base-model.md, concepts/field-types.md |
| **Intermediate** | concepts/validators.md, patterns/llm-output-validation.md |
| **Advanced** | patterns/extraction-schema.md, patterns/custom-validators.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| ai-prompt-specialist | patterns/llm-output-validation.md, patterns/extraction-schema.md | Define Pydantic schemas for LLM structured output |
