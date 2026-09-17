# Codebase Exploration Knowledge Base

> **Purpose**: Codebase analysis -- repo structure, architecture mapping, dependency analysis, health reports
> **MCP Validated**: 2026-02-17

## Quick Navigation

### Concepts (< 150 lines each)

| File | Purpose |
|------|---------|
| [concepts/repo-analysis.md](concepts/repo-analysis.md) | Repository structure analysis, file tree mapping, language detection |
| [concepts/dependency-mapping.md](concepts/dependency-mapping.md) | Dependency graph analysis, import tracing, coupling metrics |
| [concepts/code-health.md](concepts/code-health.md) | Code health metrics, complexity scoring, maintainability indicators |

### Patterns (< 200 lines each)

| File | Purpose |
|------|---------|
| [patterns/executive-summary.md](patterns/executive-summary.md) | Generate high-level repo executive summaries for stakeholders |
| [patterns/deep-dive.md](patterns/deep-dive.md) | Deep architecture analysis with module interaction mapping |
| [patterns/onboarding-guide.md](patterns/onboarding-guide.md) | Auto-generate new developer onboarding guides from codebase |

### Specs (Machine-Readable)

| File | Purpose |
|------|---------|
| [specs/analysis-framework.yaml](specs/analysis-framework.yaml) | Analysis framework specification with phases, metrics, thresholds |

---

## Quick Reference

- [quick-reference.md](quick-reference.md) - Fast lookup tables

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Repo Analysis** | Structural decomposition of a repository into layers, modules, and entry points |
| **Dependency Mapping** | Tracing import chains and external package graphs to identify coupling |
| **Code Health** | Quantitative metrics (complexity, duplication, coverage) that signal maintainability |

---

## Learning Path

| Level | Files |
|-------|-------|
| **Beginner** | concepts/repo-analysis.md, quick-reference.md |
| **Intermediate** | concepts/dependency-mapping.md, patterns/executive-summary.md |
| **Advanced** | concepts/code-health.md, patterns/deep-dive.md, patterns/onboarding-guide.md |

---

## Agent Usage

| Agent | Primary Files | Use Case |
|-------|---------------|----------|
| codebase-explorer | patterns/executive-summary.md, patterns/deep-dive.md | Full codebase analysis and architecture reports |
| codebase-explorer | patterns/onboarding-guide.md | Generate onboarding documentation for new team members |
| codebase-explorer | concepts/repo-analysis.md, concepts/dependency-mapping.md | Structural and dependency analysis tasks |
