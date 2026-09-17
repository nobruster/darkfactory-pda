# Onboarding Guide Generator

> **Purpose**: Auto-generate new developer onboarding guides from codebase analysis results
> **MCP Validated**: 2026-02-17

## When to Use

- A new developer is joining a team and needs to understand the codebase quickly
- Creating standardized onboarding documentation that stays in sync with the actual code
- Replacing outdated wikis with auto-generated, always-current documentation
- Preparing a handoff document when transferring project ownership

## Implementation

```python
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date


@dataclass
class OnboardingGuide:
    """Auto-generated onboarding documentation."""
    project_name: str
    generated_date: str
    prerequisites: list[str]
    setup_steps: list[str]
    architecture_overview: str
    key_directories: dict[str, str]     # dir -> purpose
    key_files: dict[str, str]           # file -> purpose
    common_tasks: list[dict[str, str]]  # [{task, command, explanation}]
    gotchas: list[str]
    useful_commands: dict[str, str]     # command -> description


ONBOARDING_TEMPLATE = """# {project_name} - Developer Onboarding Guide
> Auto-generated: {generated_date}

## Prerequisites
{prerequisites}

## Setup
{setup_steps}

## Architecture Overview
{architecture_overview}

## Key Directories
{directory_table}

## Key Files to Read First
{files_table}

## Useful Commands
{commands_table}

## Gotchas and Tips
{gotchas}
"""


def generate_onboarding_guide(
    repo_structure,
    dependency_graph,
    health_report,
) -> str:
    """Generate a complete onboarding guide from analysis results."""
    root = Path(repo_structure.root)
    project_name = root.name

    guide = OnboardingGuide(
        project_name=project_name,
        generated_date=str(date.today()),
        prerequisites=_detect_prerequisites(repo_structure, dependency_graph),
        setup_steps=_detect_setup_steps(root),
        architecture_overview=_summarize_architecture(repo_structure),
        key_directories=_identify_key_directories(repo_structure),
        key_files=_identify_key_files(root),
        common_tasks=_detect_common_tasks(root),
        gotchas=_identify_gotchas(repo_structure, health_report),
        useful_commands=_detect_useful_commands(root),
    )

    return _render_guide(guide)


def _detect_prerequisites(structure, deps) -> list[str]:
    """Infer prerequisites from detected languages and dependencies."""
    prereqs = []
    lang_prereqs = {
        "Python": "Python 3.10+ installed (`python --version`)",
        "TypeScript": "Node.js 18+ and npm installed (`node --version`)",
        "Go": "Go 1.21+ installed (`go version`)",
        "Rust": "Rust toolchain via rustup (`rustc --version`)",
        "Java": "JDK 17+ installed (`java --version`)",
    }
    for lang in structure.languages:
        if lang in lang_prereqs:
            prereqs.append(lang_prereqs[lang])

    tool_prereqs = {
        "docker-compose.yml": "Docker Desktop installed and running",
        "Makefile": "GNU Make installed (`make --version`)",
        "terraform": "Terraform CLI installed (`terraform --version`)",
        ".pre-commit-config.yaml": "pre-commit installed (`pip install pre-commit`)",
    }
    for cfg in structure.config_files:
        for pattern, prereq in tool_prereqs.items():
            if pattern in cfg and prereq not in prereqs:
                prereqs.append(prereq)

    return prereqs or ["Check README.md for prerequisites"]


def _detect_setup_steps(root: Path) -> list[str]:
    """Infer setup steps from configuration files present."""
    steps = ["Clone the repository: `git clone <repo-url> && cd <repo>`"]
    install_map = {
        "pyproject.toml": "pip install -e '.[dev]'",
        "requirements.txt": "pip install -r requirements.txt",
        "package.json": "npm install",
        "go.mod": "go mod download",
    }
    for cfg, cmd in install_map.items():
        if (root / cfg).exists():
            if "pip" in cmd:
                steps.append("Create venv: `python -m venv .venv && source .venv/bin/activate`")
            steps.append(f"Install: `{cmd}`")
            break
    if (root / ".env.example").exists():
        steps.append("Config: `cp .env.example .env` and fill in values")
    if (root / "docker-compose.yml").exists():
        steps.append("Services: `docker-compose up -d`")
    return steps
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `include_architecture_diagram` | `True` | Embed Mermaid architecture diagram |
| `max_directories_listed` | `15` | Cap on directory entries in the table |
| `max_commands_listed` | `10` | Cap on useful commands listed |
| `detect_ci_cd` | `True` | Analyze CI/CD pipeline for build/deploy steps |

## Example Usage

```python
# Generate onboarding guide from analysis
structure = analyze_repo("/path/to/repo")
deps = build_dependency_graph("/path/to/repo", {"myapp"})
health = assess_health("/path/to/repo")

guide_markdown = generate_onboarding_guide(structure, deps, health)
Path("ONBOARDING.md").write_text(guide_markdown)
print("Onboarding guide generated successfully")
```

## Output Template (Markdown)

```markdown
# my-service - Developer Onboarding Guide

> Auto-generated: 2026-02-17

## Prerequisites
- Python 3.10+ installed
- Docker Desktop installed and running
- GNU Make installed

## Setup
1. Clone the repository
2. Create virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -e '.[dev]'`
4. Copy config: `cp .env.example .env`
5. Start services: `docker-compose up -d`
6. Run tests: `make test`

## Key Directories
| Directory | Purpose |
|-----------|---------|
| `src/api/` | REST API route handlers |
| `src/services/` | Business logic layer |
| `src/models/` | Data models and schemas |
| `tests/` | Test suite (mirrors src/ structure) |
```

## See Also

- [Executive Summary](../patterns/executive-summary.md)
- [Repo Analysis](../concepts/repo-analysis.md)
- [Deep Dive](../patterns/deep-dive.md)
