# Dependency Mapping

> **Purpose**: Trace import chains, map external packages, and measure coupling between modules
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Dependency mapping builds a directed graph of how modules, packages, and files reference
each other within a codebase. It distinguishes internal imports (module-to-module coupling)
from external dependencies (third-party packages). The resulting graph reveals architectural
layers, circular dependencies, and tightly coupled components that are candidates for
refactoring.

## The Pattern

```python
import ast
import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DependencyNode:
    """A module and its dependencies."""
    module: str
    internal_imports: list[str] = field(default_factory=list)
    external_imports: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """Complete dependency graph for a codebase."""
    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    circular: list[tuple[str, str]] = field(default_factory=list)
    external_packages: dict[str, int] = field(default_factory=dict)  # pkg -> usage count

    @property
    def coupling_score(self) -> float:
        """Ratio of internal edges to nodes (lower = more modular)."""
        if not self.nodes:
            return 0.0
        total_internal = sum(len(n.internal_imports) for n in self.nodes.values())
        return round(total_internal / len(self.nodes), 2)


def extract_python_imports(file_path: Path) -> list[str]:
    """Extract all import statements from a Python file using AST."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


def build_dependency_graph(
    repo_path: str,
    internal_packages: set[str],
) -> DependencyGraph:
    """Build a dependency graph for a Python repository."""
    root = Path(repo_path)
    graph = DependencyGraph()

    for py_file in root.rglob("*.py"):
        if any(p in py_file.parts for p in {".venv", "node_modules", "__pycache__"}):
            continue
        module_name = str(py_file.relative_to(root)).replace("/", ".").removesuffix(".py")
        imports = extract_python_imports(py_file)

        node = DependencyNode(module=module_name)
        for imp in imports:
            if imp in internal_packages:
                node.internal_imports.append(imp)
            else:
                node.external_imports.append(imp)
                graph.external_packages[imp] = graph.external_packages.get(imp, 0) + 1

        graph.nodes[module_name] = node

    graph.circular = _detect_circular(graph)
    return graph
```

## Quick Reference

| Metric | Formula | Healthy Range |
|--------|---------|---------------|
| Coupling Score | internal_edges / nodes | < 3.0 |
| Fan-In (afferent) | count of modules importing X | High = stable core |
| Fan-Out (efferent) | count of modules X imports | High = fragile |
| Instability | fan-out / (fan-in + fan-out) | 0 = stable, 1 = unstable |
| Circular Deps | cycle count in import graph | 0 = ideal |

## Dependency Categories

| Category | Description | Example | Risk |
|----------|-------------|---------|------|
| Internal | Same-repo module imports | `from myapp.utils import helper` | Coupling |
| External | Third-party packages | `import requests` | Version lock |
| Stdlib | Python standard library | `import os` | None |
| Dev-only | Test/build dependencies | `import pytest` | Build bloat |
| Transitive | Indirect dependencies | `requests -> urllib3` | Hidden risk |

## Common Mistakes

### Wrong

```python
# Treating all imports equally
imports = re.findall(r"^import (\w+)", source_code, re.MULTILINE)
# Misses: from X import Y, relative imports, conditional imports
```

### Correct

```python
# Use AST for accurate import extraction
tree = ast.parse(source_code)
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        # Handle both import styles correctly
        pass
```

## Visualization Formats

| Format | Tool | Best For |
|--------|------|----------|
| Adjacency list | Plain text | Quick inspection |
| Mermaid diagram | Mermaid JS | Documentation |
| DOT graph | Graphviz | Complex graphs |
| JSON tree | Custom | Programmatic use |

## Related

- [Repo Analysis](../concepts/repo-analysis.md)
- [Code Health](../concepts/code-health.md)
- [Deep Dive](../patterns/deep-dive.md)
