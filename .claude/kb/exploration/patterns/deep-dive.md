# Deep Dive Architecture Analysis

> **Purpose**: Thorough architecture analysis mapping module interactions, data flow, and design patterns
> **MCP Validated**: 2026-02-17

## When to Use

- Performing an in-depth architectural review before a major refactoring
- Understanding a complex codebase with multiple interacting subsystems
- Evaluating whether a codebase follows intended architectural patterns
- Identifying architectural drift from original design decisions
- Preparing migration plans that require understanding all module boundaries

## Implementation

```python
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class ArchLayer(Enum):
    """Standard architectural layers."""
    PRESENTATION = "presentation"   # API routes, CLI, UI
    APPLICATION = "application"     # Use cases, orchestration
    DOMAIN = "domain"               # Business logic, models
    INFRASTRUCTURE = "infrastructure"  # DB, external APIs, file I/O
    SHARED = "shared"               # Utilities, helpers, constants


@dataclass
class ModuleAnalysis:
    """Deep analysis of a single module/package."""
    name: str
    path: str
    layer: ArchLayer
    public_api: list[str]           # exported functions/classes
    internal_deps: list[str]        # modules it imports internally
    external_deps: list[str]        # third-party packages used
    file_count: int = 0
    line_count: int = 0
    complexity_avg: float = 0.0
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class ArchitectureReport:
    """Complete architecture deep dive report."""
    modules: list[ModuleAnalysis]
    layers: dict[str, list[str]]    # layer -> module names
    data_flow: list[tuple[str, str, str]]  # (source, target, data_type)
    design_patterns: list[str]      # detected patterns
    violations: list[str]           # architectural violations
    boundary_crossings: list[tuple[str, str]]  # illegal layer crossings


# Layer classification heuristics
LAYER_SIGNALS = {
    ArchLayer.PRESENTATION: {
        "dirs": {"api", "routes", "views", "handlers", "cli", "endpoints"},
        "imports": {"fastapi", "flask", "django", "click", "typer"},
    },
    ArchLayer.APPLICATION: {
        "dirs": {"services", "usecases", "use_cases", "controllers", "orchestration"},
        "imports": {"celery", "dramatiq", "rq"},
    },
    ArchLayer.DOMAIN: {
        "dirs": {"models", "domain", "entities", "schemas", "core"},
        "imports": {"pydantic", "dataclasses", "attrs"},
    },
    ArchLayer.INFRASTRUCTURE: {
        "dirs": {"db", "database", "repositories", "adapters", "clients", "external"},
        "imports": {"sqlalchemy", "pymongo", "redis", "boto3", "requests", "httpx"},
    },
    ArchLayer.SHARED: {
        "dirs": {"utils", "helpers", "common", "shared", "lib", "config"},
        "imports": set(),
    },
}


def classify_module_layer(module_path: str, imports: list[str]) -> ArchLayer:
    """Classify a module into an architectural layer based on signals."""
    path_parts = set(Path(module_path).parts)

    for layer, signals in LAYER_SIGNALS.items():
        if path_parts & signals["dirs"]:
            return layer
        if set(imports) & signals["imports"]:
            return layer

    return ArchLayer.SHARED


def detect_violations(modules: list[ModuleAnalysis]) -> list[str]:
    """Detect architectural layer violations."""
    ALLOWED_DEPS = {
        ArchLayer.PRESENTATION: {ArchLayer.APPLICATION, ArchLayer.SHARED},
        ArchLayer.APPLICATION: {ArchLayer.DOMAIN, ArchLayer.INFRASTRUCTURE, ArchLayer.SHARED},
        ArchLayer.DOMAIN: {ArchLayer.SHARED},
        ArchLayer.INFRASTRUCTURE: {ArchLayer.DOMAIN, ArchLayer.SHARED},
        ArchLayer.SHARED: set(),
    }

    violations = []
    module_map = {m.name: m for m in modules}

    for mod in modules:
        allowed = ALLOWED_DEPS.get(mod.layer, set())
        for dep_name in mod.internal_deps:
            dep = module_map.get(dep_name)
            if dep and dep.layer not in allowed and dep.layer != mod.layer:
                violations.append(
                    f"{mod.name} ({mod.layer.value}) -> {dep.name} ({dep.layer.value})"
                )

    return violations
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_depth` | `3` | Directory depth for module discovery |
| `classify_by` | `"both"` | Layer classification: `"path"`, `"imports"`, or `"both"` |
| `detect_patterns` | `True` | Enable design pattern detection |
| `violation_mode` | `"warn"` | `"warn"` logs violations, `"strict"` raises errors |

## Example Usage

```python
# Run deep dive analysis
modules = discover_modules("/path/to/repo", max_depth=3)
for mod in modules:
    mod.layer = classify_module_layer(mod.path, mod.external_deps)

report = ArchitectureReport(
    modules=modules,
    layers=group_by_layer(modules),
    data_flow=trace_data_flow(modules),
    design_patterns=detect_design_patterns(modules),
    violations=detect_violations(modules),
    boundary_crossings=find_boundary_crossings(modules),
)

# Output architecture diagram
print(format_mermaid_diagram(report))
```

## Output Template (Mermaid)

```markdown
## Architecture Diagram

    graph TD
        subgraph Presentation
            API[api/routes]
            CLI[cli/commands]
        end
        subgraph Application
            SVC[services/]
        end
        subgraph Domain
            MOD[models/]
            SCH[schemas/]
        end
        subgraph Infrastructure
            DB[db/repositories]
            EXT[clients/external]
        end
        API --> SVC
        CLI --> SVC
        SVC --> MOD
        SVC --> DB
        DB --> MOD

## Violations Found
- `api/routes` directly imports `db/repositories` (skips application layer)
```

## Design Pattern Detection

| Pattern | Signal | Example |
|---------|--------|---------|
| Repository | Classes with CRUD methods wrapping DB | `UserRepository.get_by_id()` |
| Factory | Functions returning different types | `create_processor(type)` |
| Strategy | Interchangeable algorithms via interface | `Validator` subclasses |
| Observer | Event/callback registration | `on_event()`, `subscribe()` |
| Facade | Simplified interface to subsystem | `APIClient` wrapping multiple endpoints |

## See Also

- [Executive Summary](../patterns/executive-summary.md)
- [Dependency Mapping](../concepts/dependency-mapping.md)
- [Onboarding Guide](../patterns/onboarding-guide.md)
