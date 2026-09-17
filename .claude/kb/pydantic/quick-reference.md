# Pydantic Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Core Model Methods

| Method | Input | Output | Notes |
|--------|-------|--------|-------|
| `Model(**data)` | kwargs | Model instance | Validates on creation |
| `model_validate(obj)` | dict | Model instance | Parse dict into model |
| `model_validate_json(json_str)` | str | Model instance | Parse JSON string |
| `model_dump()` | -- | dict | Serialize to dict |
| `model_dump_json()` | -- | str | Serialize to JSON |
| `model_json_schema()` | -- | dict | Get JSON Schema |
| `model_copy(update={})` | dict | Model instance | Clone with overrides |

## Field Type Patterns

| Pattern | Syntax | Use Case |
|---------|--------|----------|
| Required | `name: str` | Field must be provided |
| Optional | `name: Optional[str] = None` | Field can be missing |
| Default | `name: str = "default"` | Has fallback value |
| Constrained | `name: Annotated[str, Field(min_length=1)]` | With validation |
| List | `items: list[Item]` | Collection of models |
| Literal | `status: Literal["ok", "error"]` | Enum-like choices |

## Validator Modes

| Decorator | Mode | Receives | Use Case |
|-----------|------|----------|----------|
| `@field_validator` | `"before"` | Raw input | Coerce types |
| `@field_validator` | `"after"` | Validated value | Post-validation logic |
| `@field_validator` | `"wrap"` | value + handler | Control validation |
| `@model_validator` | `"before"` | Raw dict | Pre-process all data |
| `@model_validator` | `"after"` | Model instance | Cross-field validation |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Parse LLM JSON output | `model_validate_json()` |
| Define extraction schema | BaseModel + Field descriptions |
| Cross-field validation | `@model_validator(mode="after")` |
| Type coercion before validation | `@field_validator(mode="before")` |
| Reusable constraint | `Annotated[type, AfterValidator(fn)]` |
| Generate prompt instructions | `Model.model_json_schema()` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `name: Optional[str]` (no default) | `name: Optional[str] = None` |
| `@validator` (v1 syntax) | `@field_validator` (v2 syntax) |
| `.dict()` / `.json()` (v1) | `.model_dump()` / `.model_dump_json()` (v2) |
| `Config` inner class (v1) | `model_config = ConfigDict(...)` (v2) |
| Trust raw LLM output | Always validate with `model_validate_json()` |

## Related Documentation

| Topic | Path |
|-------|------|
| BaseModel basics | `concepts/base-model.md` |
| Validators deep dive | `concepts/validators.md` |
| LLM output parsing | `patterns/llm-output-validation.md` |
| Full Index | `index.md` |
