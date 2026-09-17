# Repository Analysis

> **Purpose**: Systematic decomposition of repository structure, language detection, and entry point identification
> **Confidence**: 0.95
> **MCP Validated**: 2026-02-17

## Overview

Repository analysis is the foundational phase of codebase exploration. It scans the file
tree to detect programming languages, identify project type (monorepo, library, service),
map directory conventions, and locate entry points. This phase produces the structural
map that all subsequent analysis phases build upon.

## The Pattern

```python
import os
from pathlib import Path
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class RepoStructure:
    """Result of repository structure analysis."""
    root: str
    languages: dict[str, int]          # language -> file count
    entry_points: list[str]            # main files, index files
    directories: list[str]             # top-level directory names
    config_files: list[str]            # configuration files found
    total_files: int = 0
    total_lines: int = 0
    project_type: str = "unknown"      # monorepo | library | service | cli


LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
    ".tf": "Terraform", ".hcl": "HCL", ".yaml": "YAML", ".yml": "YAML",
}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "index.ts", "index.js", "main.go",
    "main.rs", "Application.java", "manage.py", "cli.py",
}

CONFIG_PATTERNS = {
    "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
    "go.mod", "Gemfile", "pom.xml", "build.gradle",
    "Dockerfile", "docker-compose.yml", "Makefile",
    ".github", "terraform.tf", "terragrunt.hcl",
}


def analyze_repo(repo_path: str, ignore_dirs: set[str] | None = None) -> RepoStructure:
    """Analyze a repository's structure and produce a structural map."""
    if ignore_dirs is None:
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

    root = Path(repo_path)
    lang_counter: Counter = Counter()
    entry_points, config_files = [], []
    top_dirs = sorted([d.name for d in root.iterdir() if d.is_dir() and d.name not in ignore_dirs])
    total_files, total_lines = 0, 0

    for path in root.rglob("*"):
        if any(part in ignore_dirs for part in path.parts):
            continue
        if not path.is_file():
            continue
        total_files += 1
        ext = path.suffix.lower()
        if ext in LANGUAGE_MAP:
            lang_counter[LANGUAGE_MAP[ext]] += 1
        if path.name in ENTRY_POINT_NAMES:
            entry_points.append(str(path.relative_to(root)))
        if path.name in CONFIG_PATTERNS or path.name.startswith("."):
            config_files.append(str(path.relative_to(root)))

    return RepoStructure(
        root=str(root),
        languages=dict(lang_counter.most_common()),
        entry_points=entry_points,
        directories=top_dirs,
        config_files=config_files,
        total_files=total_files,
        total_lines=total_lines,
        project_type=_detect_project_type(top_dirs, config_files),
    )
```

## Quick Reference

| Signal | Indicates | Example |
|--------|-----------|---------|
| Multiple `*/src/` dirs | Monorepo | `packages/api/src/`, `packages/web/src/` |
| Single `src/` + `setup.py` | Python library | `src/mylib/`, `setup.py` |
| `Dockerfile` + `app.py` | Service/API | `app.py`, `Dockerfile` |
| `bin/` + `cli.py` | CLI tool | `bin/mytool`, `cli.py` |
| `terraform/` + `modules/` | IaC project | `terraform/modules/vpc/` |

## Common Mistakes

### Wrong

```python
# Scanning every file including generated code
all_files = list(Path(repo).rglob("*"))
# Result: node_modules, .git, __pycache__ inflate counts
```

### Correct

```python
# Filter out generated/vendored/cached directories
IGNORE = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
files = [f for f in Path(repo).rglob("*")
         if not any(part in IGNORE for part in f.parts)]
```

## Project Type Detection

| Indicators | Type | Confidence |
|-----------|------|------------|
| `packages/` or `apps/` + workspace config | monorepo | High |
| `setup.py` or `pyproject.toml` + `src/` | library | Medium |
| `Dockerfile` + single entry point | service | High |
| `bin/` or CLI framework in deps | cli | Medium |
| `terraform/` as primary content | iac | High |

## Related

- [Dependency Mapping](../concepts/dependency-mapping.md)
- [Executive Summary](../patterns/executive-summary.md)
- [Deep Dive](../patterns/deep-dive.md)
