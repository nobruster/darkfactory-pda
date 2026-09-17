# Python Clean Code Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Dataclass Options (3.10+)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `slots=True` | `False` | Generate `__slots__`, faster attribute access, less memory |
| `frozen=True` | `False` | Immutable instances, hashable |
| `kw_only=True` | `False` | All fields require keyword arguments |
| `match_args=True` | `True` | Enable structural pattern matching |
| `order=True` | `False` | Generate comparison methods |
| `eq=True` | `True` | Generate `__eq__` and `__ne__` |

## Type Hint Patterns (3.11+)

| Pattern | Syntax | Version |
|---------|--------|---------|
| Union (modern) | `int \| str` | 3.10+ |
| Optional (modern) | `str \| None` | 3.10+ |
| Self return | `-> Self` | 3.11+ |
| TypeVar (modern) | `def fn[T](x: T) -> T:` | 3.12+ |
| Type alias (modern) | `type Vector = list[float]` | 3.12+ |
| TypedDict | `class Config(TypedDict):` | 3.8+ |
| Literal | `Literal["read", "write"]` | 3.8+ |

## Generator vs List Comprehension

| Use Case | Choose | Why |
|----------|--------|-----|
| Need all items in memory | List comprehension `[x for x in items]` | Random access |
| Large/infinite dataset | Generator expression `(x for x in items)` | Lazy evaluation |
| Transform + filter pipeline | Generator chaining | Memory efficient |
| Need to iterate once | Generator | Lower memory |
| Need `len()` or indexing | List | Generators have no length |

## Context Manager Patterns

| Pattern | Use Case | Module |
|---------|----------|--------|
| `with open(f) as fh:` | File I/O | builtin |
| `@contextmanager` | Simple resource management | `contextlib` |
| `class + __enter__/__exit__` | Complex state machines | builtin |
| `suppress(ExceptionType)` | Ignore specific exceptions | `contextlib` |
| `ExitStack()` | Dynamic number of resources | `contextlib` |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Plain data container | `@dataclass(slots=True)` |
| Immutable config | `@dataclass(frozen=True, slots=True)` |
| Data with validation | Pydantic BaseModel |
| Return type is self | `-> Self` (3.11+) |
| Parse large file line by line | Generator with `yield` |
| Manage resource lifecycle | Context manager |
| Chain transformations | Generator pipeline |
| Catch specific errors only | `except SpecificError` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| `except Exception:` (bare) | `except (ValueError, TypeError) as e:` |
| Mutable default `field=[]` | `field(default_factory=list)` |
| `type(x) == str` | `isinstance(x, str)` |
| `from typing import Optional` | `str \| None` (3.10+) |
| Return `None` implicitly | Use explicit return type `-> None` |
| Nested list comprehensions (3+) | Extract to named generator function |

## Related Documentation

| Topic | Path |
|-------|------|
| Dataclasses deep dive | `concepts/dataclasses.md` |
| Type hints guide | `concepts/type-hints.md` |
| Error handling patterns | `patterns/error-handling.md` |
| Full Index | `index.md` |
