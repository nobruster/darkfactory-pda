# Code Health

> **Purpose**: Quantitative metrics for measuring code complexity, maintainability, and technical debt
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Code health assessment produces quantitative scores that indicate a codebase's maintainability,
readability, and technical debt level. It combines static analysis metrics (cyclomatic complexity,
cognitive complexity, duplication ratio) with structural indicators (file sizes, function lengths,
test coverage) to produce an actionable health report. Metrics are evaluated against industry
thresholds to flag modules that need attention.

## The Pattern

```python
import ast
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class FunctionMetrics:
    """Metrics for a single function or method."""
    name: str
    file: str
    line_start: int
    line_count: int
    cyclomatic_complexity: int
    parameter_count: int

    @property
    def risk_level(self) -> str:
        if self.cyclomatic_complexity > 20 or self.line_count > 60:
            return "critical"
        if self.cyclomatic_complexity > 10 or self.line_count > 30:
            return "warning"
        return "good"


@dataclass
class FileMetrics:
    """Metrics for a single source file."""
    path: str
    total_lines: int
    code_lines: int
    function_count: int
    class_count: int
    max_complexity: int
    avg_complexity: float

    @property
    def risk_level(self) -> str:
        if self.total_lines > 500 or self.max_complexity > 20:
            return "critical"
        if self.total_lines > 300 or self.max_complexity > 10:
            return "warning"
        return "good"


@dataclass
class HealthReport:
    """Aggregated health report for the entire codebase."""
    total_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    files_at_risk: list[FileMetrics] = field(default_factory=list)
    functions_at_risk: list[FunctionMetrics] = field(default_factory=list)
    overall_score: float = 0.0  # 0-100 scale

    @property
    def grade(self) -> str:
        for threshold, g in [(90, "A"), (75, "B"), (60, "C"), (40, "D")]:
            if self.overall_score >= threshold:
                return g
        return "F"


def calculate_cyclomatic_complexity(func_node: ast.FunctionDef) -> int:
    """Count decision points in a function (CC = decisions + 1)."""
    complexity = 1  # base path
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.While, ast.For)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.ExceptHandler):
            complexity += 1
        elif isinstance(node, ast.Assert):
            complexity += 1
    return complexity
```

## Quick Reference

| Metric | What It Measures | Tool |
|--------|-----------------|------|
| Cyclomatic Complexity | Decision branches per function | `ast` analysis |
| Cognitive Complexity | Human comprehension difficulty | Nesting depth + breaks |
| Lines of Code (LOC) | File and function size | Line counting |
| Comment Ratio | Documentation coverage | Comment / total lines |
| Duplication Ratio | Copy-paste code percentage | Token matching |
| Test Coverage | Lines exercised by tests | `coverage.py` |

## Health Score Calculation

| Component | Weight | Scoring |
|-----------|--------|---------|
| Avg Cyclomatic Complexity | 25% | < 5 = 100, 5-10 = 75, 10-15 = 50, > 15 = 25 |
| File Size Distribution | 20% | % files under 300 lines |
| Function Size Distribution | 20% | % functions under 30 lines |
| Duplication Ratio | 15% | < 5% = 100, 5-10% = 75, > 10% = 50 |
| Test Existence | 10% | tests/ directory + test files present |
| Documentation | 10% | README + docstrings + comment ratio |

## Common Mistakes

### Wrong

```python
# Using lines of code as the primary quality metric
quality = "good" if total_lines < 10000 else "bad"
# A 500-line file of spaghetti is worse than a 5000-line well-structured project
```

### Correct

```python
# Use complexity and structure metrics together
is_healthy = (
    avg_complexity < 10
    and pct_files_under_300_lines > 0.80
    and pct_functions_under_30_lines > 0.85
    and duplication_ratio < 0.05
)
```

## Risk Prioritization

| Risk Level | Action | Timeline |
|------------|--------|----------|
| Critical (score < 40) | Immediate refactoring needed | This sprint |
| Warning (score 40-70) | Plan refactoring in backlog | Next 2 sprints |
| Good (score > 70) | Monitor for regression | Ongoing |

## Related
- [Repo Analysis](../concepts/repo-analysis.md)
- [Dependency Mapping](../concepts/dependency-mapping.md)
- [Executive Summary](../patterns/executive-summary.md)
