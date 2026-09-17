# pytest Basics

> **Purpose**: Core pytest conventions, test discovery, markers, and CLI usage
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

pytest is the standard Python testing framework. It discovers tests automatically by scanning
for files matching `test_*.py` or `*_test.py`, classes prefixed with `Test`, and functions
prefixed with `test_`. It provides rich assertion introspection (no need for `assertEqual`),
powerful fixtures, markers for metadata, and a plugin ecosystem.

## The Pattern

```python
import pytest


# Simple test function -- pytest discovers this automatically
def test_addition():
    assert 1 + 1 == 2


# Test with descriptive assertion messages
def test_parse_invoice_number():
    raw = "  inv-001  "
    result = raw.strip().upper()
    assert result == "INV-001", f"Expected 'INV-001', got '{result}'"


# Group related tests in a class (no inheritance needed)
class TestStringProcessor:
    def test_strip_whitespace(self):
        assert "  hello  ".strip() == "hello"

    def test_uppercase(self):
        assert "hello".upper() == "HELLO"

    def test_empty_string(self):
        assert "".strip() == ""
```

## Markers

```python
import pytest

# Built-in markers
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(
    condition=True, reason="Only on Linux"
)
def test_linux_only():
    pass

@pytest.mark.xfail(reason="Known bug #123")
def test_known_failure():
    assert 1 == 2

# Custom markers (register in pyproject.toml)
@pytest.mark.slow
def test_large_dataset_processing():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass
```

## Test Discovery Rules

| Convention | Example | Discovered? |
|------------|---------|-------------|
| File: `test_*.py` | `test_utils.py` | Yes |
| File: `*_test.py` | `utils_test.py` | Yes |
| Function: `test_*` | `def test_parse():` | Yes |
| Class: `Test*` | `class TestParser:` | Yes |
| Method: `test_*` | `def test_valid(self):` | Yes |
| File: `utils.py` | `utils.py` | No |
| Function: `helper_*` | `def helper_parse():` | No |

## Expected Exceptions

```python
import pytest

def test_raises_value_error():
    with pytest.raises(ValueError, match="must be positive"):
        parse_amount(-5)

def test_raises_type_error():
    with pytest.raises(TypeError):
        parse_amount("not a number")
```

## Common Mistakes

### Wrong

```python
# Using unittest assertions in pytest
import unittest

class TestBad(unittest.TestCase):
    def test_value(self):
        self.assertEqual(1 + 1, 2)  # Works but loses pytest features
```

### Correct

```python
# Plain assert with pytest -- better output on failure
def test_value():
    assert 1 + 1 == 2
```

## CLI Quick Reference

| Flag | Purpose |
|------|---------|
| `-v` | Verbose: show each test name |
| `-x` | Exit on first failure |
| `-s` | Show print/stdout output |
| `--lf` | Re-run only last-failed tests |
| `--ff` | Run failures first, then the rest |
| `-k "expr"` | Filter tests by name expression |
| `-m "marker"` | Run only tests with marker |
| `--co` | Collect and list tests, do not run |

## Related

- [Fixtures](../concepts/fixtures.md)
- [Parametrize](../concepts/parametrize.md)
- [Unit Test Patterns](../patterns/unit-test-patterns.md)
