# Type Hints

> **Purpose**: Type annotations, generics, Self, and Python 3.12+ syntax for clean Python code
> **Confidence**: 0.95
> **MCP Validated:** 2026-02-17

## Overview

Python type hints enable static analysis, IDE support, and documentation without runtime
overhead. Python 3.10+ introduced `X | Y` union syntax, 3.11 added `Self` and
`LiteralString`, and 3.12 introduced the `type` statement and native generic syntax.

## The Pattern

```python
from dataclasses import dataclass
from typing import Self


@dataclass(slots=True)
class TreeNode:
    value: int
    children: list[Self] | None = None

    def add_child(self, value: int) -> Self:
        if self.children is None:
            self.children = []
        child = TreeNode(value=value)
        self.children.append(child)
        return child
```

## Modern Syntax Reference

| Old (pre-3.10) | Modern (3.10+) | Version |
|-----------------|----------------|---------|
| `Optional[str]` | `str \| None` | 3.10+ |
| `Union[int, str]` | `int \| str` | 3.10+ |
| `List[int]` | `list[int]` | 3.9+ |
| `Dict[str, int]` | `dict[str, int]` | 3.9+ |
| `Tuple[int, ...]` | `tuple[int, ...]` | 3.9+ |

## Python 3.11+ Features

```python
from typing import Self, LiteralString, Never

# Self: annotate methods returning their own class
class Builder:
    def set_name(self, name: str) -> Self:
        self.name = name
        return self

# LiteralString: must be a literal, not arbitrary string
def run_query(sql: LiteralString) -> list[dict]: ...

# Never: function that never returns
def fail(msg: str) -> Never:
    raise RuntimeError(msg)
```

## Python 3.12+ Generics

```python
# OLD: verbose TypeVar boilerplate
from typing import TypeVar
T = TypeVar("T")
def first_old(items: list[T]) -> T:
    return items[0]

# NEW: native generic syntax (3.12+)
def first[T](items: list[T]) -> T:
    return items[0]

# NEW: type alias statement (3.12+)
type Vector = list[float]
type Callback[T] = Callable[[T], None]
```

## TypedDict for Structured Dicts

```python
from typing import TypedDict, Required, NotRequired

class APIResponse(TypedDict):
    status: Required[int]
    data: Required[dict]
    error: NotRequired[str]
```

## Common Mistakes

### Wrong (legacy imports)

```python
from typing import Optional, List, Dict, Union
def process(items: Optional[List[Dict[str, Union[int, str]]]]) -> None: ...
```

### Correct (modern syntax)

```python
def process(items: list[dict[str, int | str]] | None) -> None: ...
```

## Protocols (Structural Typing)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...
    def to_json(self) -> str: ...

def save(obj: Serializable) -> None:
    data = obj.to_dict()
    ...
```

## Quick Reference

| Type | Use Case |
|------|----------|
| `str \| None` | Optional value |
| `Self` | Method returns own class |
| `Never` | Function never returns |
| `LiteralString` | SQL injection prevention |
| `Literal["a", "b"]` | Enum-like string constraint |
| `Protocol` | Structural subtyping (duck typing) |
| `Annotated[int, Gt(0)]` | Type with metadata |

## Related

- [Dataclasses](../concepts/dataclasses.md)
- [Clean Architecture](../patterns/clean-architecture.md)
- [Error Handling](../patterns/error-handling.md)
