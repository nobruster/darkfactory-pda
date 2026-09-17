# Executive Summary

> **Purpose**: Generate high-level repository summaries for stakeholders, combining structure, health, and architecture insights
> **MCP Validated**: 2026-02-17

## When to Use

- Producing a quick overview of a codebase for technical leadership
- Onboarding a new team to an inherited or acquired codebase
- Creating documentation for architecture review meetings
- Assessing a repository before starting a migration or refactoring effort

## Implementation

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutiveSummary:
    """High-level codebase summary for stakeholders."""
    project_name: str
    project_type: str              # monorepo | service | library | cli
    primary_language: str
    languages: dict[str, int]
    total_files: int
    total_lines: int
    entry_points: list[str]
    architecture_style: str        # layered | modular | monolithic | microservices
    key_dependencies: list[str]
    health_grade: str              # A-F
    health_score: float            # 0-100
    risks: list[str]
    recommendations: list[str]


SUMMARY_TEMPLATE = """# {project_name} - Codebase Summary

> Generated: {date} | Health Grade: **{health_grade}** ({health_score}/100)

## Overview

| Attribute | Value |
|-----------|-------|
| **Project Type** | {project_type} |
| **Primary Language** | {primary_language} |
| **Total Files** | {total_files:,} |
| **Total Lines** | {total_lines:,} |
| **Architecture** | {architecture_style} |

## Language Distribution

{language_table}

## Entry Points

{entry_points_list}

## Key Dependencies

{dependencies_list}

## Health Assessment

**Grade: {health_grade}** ({health_score}/100)

{health_details}

## Risks

{risks_list}

## Recommendations

{recommendations_list}
"""


def generate_executive_summary(
    repo_structure,     # from repo-analysis
    dependency_graph,   # from dependency-mapping
    health_report,      # from code-health
) -> str:
    """Combine analysis results into an executive summary document."""
    languages = repo_structure.languages
    primary = max(languages, key=languages.get) if languages else "Unknown"

    top_deps = sorted(
        dependency_graph.external_packages.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    risks = _identify_risks(repo_structure, dependency_graph, health_report)
    recommendations = _generate_recommendations(risks, health_report)

    return SUMMARY_TEMPLATE.format(
        project_name=Path(repo_structure.root).name,
        date="auto-generated",
        project_type=repo_structure.project_type,
        primary_language=primary,
        total_files=repo_structure.total_files,
        total_lines=repo_structure.total_lines,
        architecture_style=_detect_architecture(repo_structure),
        health_grade=health_report.grade,
        health_score=health_report.overall_score,
        language_table=_format_language_table(languages),
        entry_points_list=_format_list(repo_structure.entry_points),
        dependencies_list=_format_list([f"{k} ({v} usages)" for k, v in top_deps]),
        health_details=_format_health_details(health_report),
        risks_list=_format_list(risks),
        recommendations_list=_format_list(recommendations),
    )


def _identify_risks(structure, deps, health) -> list[str]:
    """Flag notable risks from analysis data."""
    risks = []
    if deps.circular:
        risks.append(f"{len(deps.circular)} circular dependency chain(s) detected")
    if health.overall_score < 60:
        risks.append(f"Health score {health.overall_score}/100 is below acceptable threshold")
    if len(health.files_at_risk) > 0:
        risks.append(f"{len(health.files_at_risk)} file(s) exceed complexity thresholds")
    if deps.coupling_score > 5.0:
        risks.append(f"High coupling score ({deps.coupling_score}) indicates tight module interdependency")
    return risks or ["No critical risks identified"]
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_dependencies_listed` | `10` | Number of top external deps to show |
| `risk_threshold_score` | `60` | Health score below which risks are flagged |
| `coupling_threshold` | `5.0` | Coupling score above which is flagged |
| `include_file_tree` | `False` | Whether to embed abbreviated file tree |

## Example Usage

```python
from exploration.concepts.repo_analysis import analyze_repo
from exploration.concepts.dependency_mapping import build_dependency_graph
from exploration.concepts.code_health import assess_health

# Step 1: Run all analysis phases
structure = analyze_repo("/path/to/repo")
deps = build_dependency_graph("/path/to/repo", internal_packages={"myapp"})
health = assess_health("/path/to/repo")

# Step 2: Generate summary
summary = generate_executive_summary(structure, deps, health)

# Step 3: Write output
Path("CODEBASE_SUMMARY.md").write_text(summary)
print(f"Summary generated: Grade {health.grade} ({health.overall_score}/100)")
```

## Output Template (Markdown)

```markdown
# my-project - Codebase Summary

> Generated: 2026-02-17 | Health Grade: **B** (78/100)

## Overview
| Attribute | Value |
|-----------|-------|
| **Project Type** | service |
| **Primary Language** | Python |
| **Total Files** | 142 |
| **Total Lines** | 18,340 |
| **Architecture** | layered |

## Risks
- 2 circular dependency chain(s) detected
- 3 file(s) exceed complexity thresholds

## Recommendations
- Break circular imports between `models` and `services`
- Refactor functions exceeding 60 lines in `core/processor.py`
```

## See Also

- [Repo Analysis](../concepts/repo-analysis.md)
- [Deep Dive](../patterns/deep-dive.md)
- [Code Health](../concepts/code-health.md)
