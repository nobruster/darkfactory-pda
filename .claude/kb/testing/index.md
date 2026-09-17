# Python Testing Knowledge Base

> **Purpose**: Comprehensive pytest-based testing patterns for Python data engineering projects
> **MCP Validated**: 2026-02-17

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/pytest-basics.md](concepts/pytest-basics.md) | pytest conventions, markers, CLI usage |
| [concepts/fixtures.md](concepts/fixtures.md) | Fixture patterns, scope, dependency injection |
| [concepts/mocking.md](concepts/mocking.md) | unittest.mock, monkeypatch, patching strategies |
| [concepts/parametrize.md](concepts/parametrize.md) | Parametrized tests, data-driven testing |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/unit-test-patterns.md](patterns/unit-test-patterns.md) | Unit test structure, AAA pattern, edge cases |
| [patterns/integration-tests.md](patterns/integration-tests.md) | Integration test patterns, service boundaries |
| [patterns/fixture-factories.md](patterns/fixture-factories.md) | Factory functions for reusable test data |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/test-config.yaml](specs/test-config.yaml) | pytest configuration spec and marker registry |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **pytest** | Python testing framework with autodiscovery, fixtures, and rich assertions |
| **Fixtures** | Dependency injection for test setup/teardown with configurable scope |
| **Mocking** | Replace real dependencies with controlled doubles for isolation |
| **Parametrize** | Run the same test logic against multiple input/output combinations |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/pytest-basics.md, concepts/fixtures.md |
| **Intermediate** | concepts/mocking.md, concepts/parametrize.md, patterns/unit-test-patterns.md |
| **Advanced** | patterns/integration-tests.md, patterns/fixture-factories.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| ai-data-engineer | patterns/unit-test-patterns.md, concepts/fixtures.md | Generate pytest tests for Python modules |
