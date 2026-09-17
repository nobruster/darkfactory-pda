# Fixtures

> **Purpose**: pytest fixture patterns, scope control, and dependency injection for test setup
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Fixtures are pytest's dependency injection mechanism. A test function declares its dependencies
by naming fixtures as parameters. pytest resolves them automatically, manages their lifecycle
via scope, and handles teardown. Fixtures replace traditional setUp/tearDown with composable,
reusable components defined in `conftest.py` or test modules.

## The Pattern

```python
import pytest
from myapp.db import Database


@pytest.fixture
def sample_invoice():
    """Function-scoped fixture: fresh data per test."""
    return {
        "invoice_number": "INV-001",
        "vendor_name": "Acme Corp",
        "total_amount": 1500.00,
        "currency": "USD",
    }


@pytest.fixture(scope="session")
def db_connection():
    """Session-scoped: one connection for entire test run."""
    conn = Database.connect("test://localhost/testdb")
    yield conn  # yield = setup/teardown pattern
    conn.close()


@pytest.fixture
def db_with_data(db_connection):
    """Fixture composing another fixture."""
    db_connection.execute("INSERT INTO invoices VALUES (...)")
    yield db_connection
    db_connection.execute("DELETE FROM invoices")
```

## Fixture Scopes

| Scope | Created | Destroyed | Use Case |
|-------|---------|-----------|----------|
| `function` | Per test function | After test ends | Default, isolated state |
| `class` | Per test class | After class ends | Shared across class methods |
| `module` | Per .py file | After module ends | Expensive module-level setup |
| `package` | Per package | After package ends | Package-level resources |
| `session` | Once per run | After all tests | DB connections, shared resources |

## conftest.py

```python
# tests/conftest.py -- fixtures available to ALL tests in this directory
import pytest


@pytest.fixture
def api_client():
    """Shared fixture across all test files."""
    from myapp.client import APIClient
    client = APIClient(base_url="http://localhost:8000")
    yield client
    client.close()


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Autouse: runs for EVERY test automatically."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
```

## Yield Fixtures (Setup + Teardown)

```python
import pytest
import tempfile
import os


@pytest.fixture
def temp_csv():
    """Create temp file, clean up after test."""
    path = tempfile.mktemp(suffix=".csv")
    with open(path, "w") as f:
        f.write("id,name,amount\n1,Acme,100.00\n")
    yield path  # test runs here
    os.unlink(path)  # teardown: always runs
```

## Common Mistakes

### Wrong

```python
# Mutable default shared across tests -- causes flaky tests
@pytest.fixture
def shared_list():
    return []  # Same list object if scope > function

def test_a(shared_list):
    shared_list.append(1)
    assert len(shared_list) == 1

def test_b(shared_list):
    # FLAKY: depends on test_a execution order
    assert len(shared_list) == 0
```

### Correct

```python
# Use function scope (default) for mutable state
@pytest.fixture
def fresh_list():
    return []  # New list for every test

def test_a(fresh_list):
    fresh_list.append(1)
    assert len(fresh_list) == 1

def test_b(fresh_list):
    assert len(fresh_list) == 0  # Always passes
```

## Related

- [Fixture Factories](../patterns/fixture-factories.md)
- [Mocking](../concepts/mocking.md)
- [Integration Tests](../patterns/integration-tests.md)
