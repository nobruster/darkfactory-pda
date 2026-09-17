# Python Testing Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## pytest CLI Commands

| Command | Purpose | Notes |
|---------|---------|-------|
| `pytest` | Run all tests | Auto-discovers test_*.py |
| `pytest tests/test_foo.py` | Run single file | Specific module |
| `pytest -k "name"` | Filter by name | Substring match |
| `pytest -m "marker"` | Filter by marker | Run marked tests only |
| `pytest -x` | Stop on first failure | Fast feedback |
| `pytest -v` | Verbose output | Show each test name |
| `pytest --tb=short` | Short tracebacks | Cleaner output |
| `pytest --co` | Collect only | List tests without running |
| `pytest -n auto` | Parallel execution | Requires pytest-xdist |

## Fixture Scopes

| Scope | Lifecycle | Use Case |
|-------|-----------|----------|
| `function` | Per test (default) | Independent test state |
| `class` | Per test class | Shared class state |
| `module` | Per .py file | Expensive module setup |
| `package` | Per package | Package-level resources |
| `session` | Entire run | DB connections, shared resources |

## Mock Patterns

| Pattern | Syntax | Use Case |
|---------|--------|----------|
| Patch function | `@mock.patch("module.func")` | Replace a function |
| Patch method | `@mock.patch.object(Class, "method")` | Replace a method |
| Return value | `mock_obj.return_value = X` | Control output |
| Side effect | `mock_obj.side_effect = [1, 2, 3]` | Sequential returns |
| Exception | `mock_obj.side_effect = ValueError` | Simulate errors |
| Monkeypatch | `monkeypatch.setattr(obj, "attr", val)` | pytest-native patching |
| Env vars | `monkeypatch.setenv("KEY", "val")` | Override env variables |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Isolate a single function | Unit test + mock dependencies |
| Test API/DB interaction | Integration test + fixtures |
| Same logic, many inputs | `@pytest.mark.parametrize` |
| Reusable test objects | Factory fixtures |
| Test data transformations | Factory fixtures + assertions |
| Slow/external resource | Mock it or mark with `@pytest.mark.slow` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Patch where defined | Patch where imported |
| Share mutable state across tests | Use function-scoped fixtures |
| Assert on mock without `assert_called` | Use `mock.assert_called_once_with(...)` |
| Hard-code test data everywhere | Use factory fixtures or parametrize |
| Skip edge cases (None, empty, huge) | Always test boundary conditions |

## Related Documentation

| Topic | Path |
|-------|------|
| pytest basics | `concepts/pytest-basics.md` |
| Fixture patterns | `concepts/fixtures.md` |
| Mocking deep dive | `concepts/mocking.md` |
| Full Index | `index.md` |
