"""Shared utilities for skill-creator scripts.

Stdlib-only. parse_frontmatter() replaces the PyYAML dependency with a parser
for exactly the frontmatter shapes this repo's skills use:

- plain and quoted scalars        name: my-skill / version: "1.0"
- inline lists                    allowed-tools: [Bash, Read]
- block scalars (| and >, with    description: |
  -/+ chomping)                     literal or folded lines...
- nested maps, one level deep     metadata:
                                    version: "1.0"

Anything outside these shapes raises FrontmatterError (fail closed) rather
than being silently misparsed. Known limitations vs full YAML: no block
sequences (`- item` lines), no multi-line plain scalars, no nesting deeper
than one level.
"""

import re
from pathlib import Path


class FrontmatterError(ValueError):
    """Raised when SKILL.md frontmatter cannot be parsed."""


_INT_RE = re.compile(r"[-+]?\d+$")
_FLOAT_RE = re.compile(r"[-+]?(\d+\.\d*|\.\d+)$")
_BLOCK_INDICATORS = ("|", ">", "|-", ">-", "|+", ">+")


def _parse_scalar(value: str):
    """Parse a scalar: quoted string, int/float/bool/null, or inline list."""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)
    if value in ("true", "True", "TRUE"):
        return True
    if value in ("false", "False", "FALSE"):
        return False
    if value in ("null", "Null", "NULL", "~"):
        return None
    return value


def _parse_block_scalar(lines: list, style: str) -> str:
    """Join block-scalar content lines per the indicator (e.g. '|', '>-')."""
    literal = style[0] == "|"
    chomp = style[1:] if len(style) > 1 else ""
    content = list(lines)
    if chomp != "+":
        while content and not content[-1].strip():
            content.pop()
    indents = [len(l) - len(l.lstrip()) for l in content if l.strip()]
    if not indents:
        return ""
    margin = min(indents)
    dedented = [l[margin:] if l.strip() else "" for l in content]
    if literal:
        text = "\n".join(dedented)
    else:
        # Folded: wrapped lines join with spaces, blank lines keep paragraphs.
        paragraphs = []
        current: list = []
        for l in dedented:
            if l:
                current.append(l)
            elif current:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        text = "\n".join(paragraphs)
    if chomp == "-":
        return text
    return text + "\n"


def parse_frontmatter(frontmatter_text: str) -> dict:
    """Parse SKILL.md frontmatter body text (between the --- markers).

    Returns a dict of the top-level keys. Raises FrontmatterError on any
    shape outside the supported subset (see module docstring).
    """
    lines = frontmatter_text.split("\n")
    result: dict = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            raise FrontmatterError(f"unexpected indentation: {line.strip()!r}")
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise FrontmatterError(f"expected 'key: value' line, got: {line.strip()!r}")
        key = key.strip()
        value = value.strip()

        if value in _BLOCK_INDICATORS:
            block = []
            while i < n and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i])
                i += 1
            result[key] = _parse_block_scalar(block, value)
        elif value:
            result[key] = _parse_scalar(value)
        else:
            # Empty value: either null, or a nested map one level deep.
            children: dict = {}
            child_indent = None
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if not nxt.startswith((" ", "\t")):
                    break
                indent = len(nxt) - len(nxt.lstrip())
                if child_indent is None:
                    child_indent = indent
                elif indent != child_indent:
                    raise FrontmatterError(
                        f"nested mapping under {key!r} deeper than one level: {nxt.strip()!r}"
                    )
                sub_key, sub_sep, sub_value = nxt.strip().partition(":")
                if not sub_sep or not sub_key.strip():
                    raise FrontmatterError(
                        f"expected nested 'key: value' under {key!r}, got: {nxt.strip()!r}"
                    )
                children[sub_key.strip()] = (
                    _parse_scalar(sub_value.strip()) if sub_value.strip() else None
                )
                i += 1
            result[key] = children if children else None
    return result


def split_frontmatter(content: str) -> str:
    """Return the frontmatter body of a SKILL.md (text between the --- markers)."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("SKILL.md missing frontmatter (no opening ---)")
    for i, line in enumerate(lines[1:], start=1):
        # The closing marker must be unindented so a '---' inside an indented
        # block scalar is not mistaken for it.
        if not line.startswith((" ", "\t")) and line.strip() == "---":
            return "\n".join(lines[1:i])
    raise FrontmatterError("SKILL.md missing frontmatter (no closing ---)")


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text()
    frontmatter = parse_frontmatter(split_frontmatter(content))
    name = frontmatter.get("name") or ""
    description = frontmatter.get("description") or ""
    if not isinstance(name, str):
        name = str(name)
    if not isinstance(description, str):
        description = str(description)
    return name, description, content
