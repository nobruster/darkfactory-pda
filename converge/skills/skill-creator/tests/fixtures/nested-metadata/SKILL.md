---
name: nested-metadata
description: |
  Fixture mirroring the task-spec skill's frontmatter shape: a literal
  block-scalar description spanning several indented lines, followed by a
  nested metadata map with a quoted version string.
metadata:
  version: "3.6.0"
---

# Nested Metadata

Regression guard for the stdlib frontmatter parser in scripts/utils.py:
the description must come back as one multi-line string and metadata as a
real nested dict.
