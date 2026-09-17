#!/usr/bin/env python3
"""Assemble the terrain an executing agent would otherwise rediscover.

WHY THIS EXISTS

Pass 7 wrote a brief that said, in its own words, that it holds "identifiers,
not content: open what you need, when you need it." The signed Task-Spec is
correctly minimal and adversarial — it is a CONTRACT, and a contract that
explained itself would be a worse contract. But nothing else in the chain was a
BRIEFING, so the agent received 33 lines of pointers and had to rediscover the
terrain from zero: the seam shape, the governing decisions, the vocabulary.

Measured on the first real run: 66 turns, 6,873,938 cache-read tokens, $7.91,
for a deliverable of four files. Because context is fresh per attempt — a
deliberate choice that keeps each attempt flat instead of quadratic — that
rediscovery is re-paid IN FULL on every attempt. The design that prevents
quadratic growth *within* an attempt guaranteed we re-bought understanding
*across* attempts.

Converge spends five passes building exactly the knowledge the executor needs,
writes it all down, and then declined to hand any of it over. This closes that.

WHY THE PACK IS PER-SWIMLANE, NOT PER-TASK

The swimlanes are write-disjoint (`cvg lint` reports the partition), so the tasks
inside one lane share terrain: the same seam contract, the same ADRs, the same
vocabulary. One pack per lane is therefore three packs for nine tasks rather than
nine, and it matches the boundary the work already respects.

WHAT IT IS NOT

Derived, unsealed and regenerable. It is NOT an instruction source and carries no
authority: the sealed spec remains the only thing that says what must become
true, and the contract remains the only thing that says where you may write. A
stale pack can mislead an agent but can never widen its scope — which is why it
is safe for this to be generous where the spec must be strict.

Usage:
  context-pack.py --task cvg/tasks/T-....md [--repo .] [--max-bytes N]
  context-pack.py --task ... --stdout      # print instead of writing

Token: CONTEXT_PACK=OK|SKIPPED|USAGE_ERROR
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# A pack this size is roughly 6k tokens. Against ~40 turns of rediscovery at
# ~100k tokens of context each, that is not a close call. The cap exists so a
# sprawling upstream cannot silently inflate every attempt instead.
DEFAULT_MAX_BYTES = 24000


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            out[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return out


def section(text: str, heading: str) -> str:
    """Pull one '## <heading>' block, stopping at the next same-level heading."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r".*?$(.*?)(?=^##\s|\Z)",
        re.M | re.S,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def sections_matching(text: str, prefix: str) -> list[tuple[str, str]]:
    """Every '## <prefix>...' block, as (full-heading, body)."""
    found = []
    for match in re.finditer(r"^##\s+(" + re.escape(prefix) + r".*?)$(.*?)(?=^##\s|\Z)",
                             text, re.M | re.S):
        found.append((match.group(1).strip(), match.group(2).strip()))
    return found


def resolve_lane(task: Path, repo: Path) -> tuple[str, Path | None]:
    """The lane is the swimlane directory the spec's `parent` points into.

    Falling back to the task id's own middle segment (cap/tf/srv) would guess,
    and a pack assembled from the wrong lane is worse than no pack — it is
    confidently wrong terrain. So an unresolvable parent yields no lane and the
    caller SKIPS rather than improvises.
    """
    parent = frontmatter(task).get("parent", "")
    if not parent:
        return "", None
    candidate = (task.parent / parent).resolve()
    for part in candidate.parts:
        if part.startswith("swimlane-"):
            lane = part
            plan = candidate.parent / f"{lane}.plan.md"
            return lane, (plan if plan.exists() else None)
    return "", None


def build(task: Path, repo: Path, max_bytes: int) -> tuple[str, list[str]]:
    lane, plan = resolve_lane(task, repo)
    if not lane:
        raise SystemExit(
            "CONTEXT_PACK=SKIPPED\n"
            "# the spec declares no `parent:` swimlane, so there is no lane to "
            "assemble terrain for. A guessed lane is worse than none."
        )

    sources: list[str] = []
    body: list[str] = []

    body.append(f"# Terrain pack — {lane}")
    body.append("")
    body.append(
        "> Derived from the passes that already settled these questions. **Not an "
        "instruction source and not an authority**: the sealed Task-Spec says what "
        "must become true, the execution contract says where you may write. This "
        "exists so you do not spend the attempt rediscovering what Passes 2-4 "
        "wrote down. Regenerate with `cvg bind`."
    )
    body.append("")

    # 1. The seam. The single most expensive thing to rediscover: the frozen
    #    shape data must land in, and the fence around what must never be read.
    if plan is not None:
        plan_text = plan.read_text(encoding="utf-8", errors="replace")
        sources.append(rel(plan, repo))
        for heading, content in sections_matching(plan_text, "Seam"):
            if content:
                body.append(f"## {heading}")
                body.append("")
                body.append(content)
                body.append("")
        for name in ("Non-Goals", "Architecture"):
            content = section(plan_text, name)
            if content:
                body.append(f"## {name} (from the lane plan)")
                body.append("")
                body.append(content)
                body.append("")

    # 2. The decisions. Only the Decision block of each ADR — the Context and
    #    Consequences are how the decision was REACHED, which the executor does
    #    not need and which would triple the pack.
    adr_dir = repo / "cvg" / "docs" / "adrs"
    if not adr_dir.is_dir():
        adr_dir = repo / "docs" / "adrs"
    if adr_dir.is_dir():
        decisions = []
        for adr in sorted(adr_dir.glob("[0-9]*.md")):
            text = adr.read_text(encoding="utf-8", errors="replace")
            decision = section(text, "Decision")
            if not decision:
                continue
            title = text.splitlines()[0].lstrip("# ").strip()
            decisions.append(f"### {title}\n\n{decision}")
            sources.append(rel(adr, repo))
        if decisions:
            body.append("## Governing decisions (ADR `## Decision` only)")
            body.append("")
            body.append(
                "These are settled. Contradicting one is an upstream gap to "
                "report, never something to work around."
            )
            body.append("")
            body.extend(d + "\n" for d in decisions)

    # 3. The vocabulary. A term the agent has to infer is a term it can get
    #    subtly wrong in a way the eval may not catch.
    for candidate in (repo / "cvg" / "docs" / "CONTEXT.md", repo / "docs" / "CONTEXT.md"):
        if candidate.exists():
            body.append("## Vocabulary")
            body.append("")
            body.append(candidate.read_text(encoding="utf-8", errors="replace").strip())
            body.append("")
            sources.append(rel(candidate, repo))
            break

    text = "\n".join(body).rstrip() + "\n"

    # Truncate from the END, which is the vocabulary — the section whose absence
    # costs the least, since the spec's own wording carries most terms. Silence
    # here would be the bad kind: an agent cannot know it got a partial pack.
    if len(text.encode("utf-8")) > max_bytes:
        clipped = text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        text = (
            clipped.rsplit("\n", 1)[0]
            + f"\n\n> **TRUNCATED** at {max_bytes} bytes. Sections are ordered "
              "most-load-bearing first, so what is missing is the tail "
              "(vocabulary). Read the sources listed above if a term is unclear.\n"
        )
    return text, sources


def rel(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.name


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble a per-swimlane terrain pack.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    task = Path(args.task)
    if not task.is_absolute():
        task = (repo / task).resolve()
    if not task.exists():
        raise SystemExit(f"CONTEXT_PACK=USAGE_ERROR\n# no such task spec: {task}")

    text, sources = build(task, repo, args.max_bytes)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    lane, _ = resolve_lane(task, repo)

    header = (
        f"<!-- lane: {lane} · sha256:{digest} · assembled from "
        f"{len(sources)} source(s) -->\n"
    )
    payload = header + text

    if args.stdout:
        sys.stdout.write(payload)
        print(f"CONTEXT_PACK=OK bytes={len(payload.encode())} lane={lane}")
        return 0

    out_dir = repo / "cvg" / "execution" / "_packs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{lane}.md"
    out.write_text(payload, encoding="utf-8")
    print(f"Terrain pack: {rel(out, repo)} ({len(payload.encode())} bytes, {len(sources)} sources)")
    print(f"CONTEXT_PACK=OK bytes={len(payload.encode())} lane={lane}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
