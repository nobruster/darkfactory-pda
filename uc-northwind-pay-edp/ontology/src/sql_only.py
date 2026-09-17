"""Without-graph baseline: grep live SQL. Never load the catalog graph."""

from __future__ import annotations

import re
from pathlib import Path

from settings import REPO_ROOT

SQL_ROOT = REPO_ROOT / "legacy" / "postgres"


def answer_from_sql(question: str, sql_root: Path | None = None) -> str:
    """Keyword search over .sql files. Does not read ontology/output."""
    root = sql_root or SQL_ROOT
    if not root.is_dir():
        raise RuntimeError(f"SQL corpus missing: {root}")

    paid_hits = _grep_word(root, "paid")
    apply_hits = _grep_regex(root, r"apply_card_settlement")

    lines = [
        "WITHOUT ontology — SQL/grep only (legacy/postgres).",
        f"Question: {question}",
        "",
        f"Hits for the word 'paid': {len(paid_hits)}",
    ]
    if not paid_hits:
        lines.append(
            "DDL never says 'paid'. Cannot name a reporting table or grain from that word."
        )
    else:
        lines.extend(_format_hits(paid_hits, limit=8))

    lines.append("")
    lines.append("Naive procedure-name guess (apply_card_settlement*):")
    if not apply_hits:
        lines.append("  (none)")
    else:
        lines.extend(_format_hits(apply_hits, limit=8))
        lines.append(
            "That name is a guess from DDL identifiers, not a catalog grain or reporting writer."
        )
    return "\n".join(lines) + "\n"


def _sql_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.sql") if p.is_file())


def _grep_word(root: Path, word: str) -> list[tuple[str, int, str]]:
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    return _scan(root, pattern)


def _grep_regex(root: Path, raw: str) -> list[tuple[str, int, str]]:
    return _scan(root, re.compile(raw, re.IGNORECASE))


def _scan(root: Path, pattern: re.Pattern[str]) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in _sql_files(root):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append((rel, i, line.rstrip()))
    return hits


def _format_hits(hits: list[tuple[str, int, str]], limit: int) -> list[str]:
    out = []
    for rel, lineno, line in hits[:limit]:
        out.append(f"  {rel}:{lineno}: {line.strip()}")
    if len(hits) > limit:
        out.append(f"  … {len(hits) - limit} more")
    return out
