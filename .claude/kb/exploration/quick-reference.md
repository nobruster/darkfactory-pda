# Codebase Exploration Quick Reference

> Fast lookup tables. For code examples, see linked files.
> **MCP Validated:** 2026-02-17

## Analysis Phases

| Phase | Action | Output |
|-------|--------|--------|
| Discovery | Scan file tree, detect languages | Repo structure map |
| Dependency | Trace imports, map packages | Dependency graph |
| Architecture | Identify layers, modules, patterns | Architecture diagram |
| Health | Measure complexity, duplication | Health score report |
| Synthesis | Combine findings into narrative | Executive summary |

## Key File Patterns

| File/Dir | Significance | Priority |
|----------|-------------|----------|
| `README.md` | Project purpose, setup instructions | Critical |
| `package.json` / `pyproject.toml` | Dependencies, scripts, metadata | Critical |
| `Dockerfile` / `docker-compose.yml` | Deployment topology | High |
| `.github/workflows/` | CI/CD pipeline definitions | High |
| `Makefile` / `justfile` | Build and task automation | Medium |
| `src/` or `lib/` | Core source code directory | Critical |
| `tests/` | Test suite structure | High |
| `.env.example` | Environment configuration shape | Medium |

## Health Metrics Thresholds

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Cyclomatic Complexity (per fn) | < 10 | 10-20 | > 20 |
| File Length (lines) | < 300 | 300-500 | > 500 |
| Function Length (lines) | < 30 | 30-60 | > 60 |
| Import Depth (nesting) | < 3 | 3-5 | > 5 |
| Duplication (% similar) | < 5% | 5-15% | > 15% |
| Test Coverage | > 80% | 50-80% | < 50% |

## Decision Matrix

| Use Case | Choose |
|----------|--------|
| Quick overview for stakeholders | `patterns/executive-summary.md` |
| Deep technical architecture review | `patterns/deep-dive.md` |
| New developer joining the team | `patterns/onboarding-guide.md` |
| Identify tightly coupled modules | `concepts/dependency-mapping.md` |
| Evaluate refactoring candidates | `concepts/code-health.md` |
| Understand repo layout and conventions | `concepts/repo-analysis.md` |

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Analyze only `src/` and ignore config | Include config, CI/CD, and infra files |
| Count lines of code as a quality metric | Use cyclomatic complexity and cohesion |
| Ignore test directory structure | Map test coverage to source modules |
| List every file in a large repo | Focus on entry points and module boundaries |
| Skip `.gitignore` and build artifacts | Filter generated/vendored code from analysis |

## Related Documentation

| Topic | Path |
|-------|------|
| Repository structure analysis | `concepts/repo-analysis.md` |
| Dependency graph analysis | `concepts/dependency-mapping.md` |
| Code health metrics | `concepts/code-health.md` |
| Full Index | `index.md` |
