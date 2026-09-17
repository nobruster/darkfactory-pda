# Lesson template — `docs/lessons/lesson-<pass-slug>-<topic>.md`

The section skeleton `pass-to-lesson` Step 3 fills. Order fixed; every section
required (an honestly-empty section says why it is empty). The file is the
durable record; the spoken walkthrough follows the same order in plain prose.

## TL;DR

One breath: what exists now that didn't before, and what it unlocks. If the
owner remembers one sentence, it is this one. ≤ 30 words.

## Why this pass exists

The pass's altitude in the descent, what invariant it protects (its "never
blur" rule), and who consumes its output next. Three to five sentences — the
lesson's map, not its territory.

## The artifact, component by component

Every component the pass emitted, at the granularity the owner meets it
(BRD sections, individual ADRs, plan lanes, task-spec fields, harness agents).
Each gets the four-part treatment:

```markdown
### <component>

- **What it is:** one sentence.
- **Why it is shaped this way:** the rule or constraint that forced the shape.
- **The decision it encodes:** what was settled here (link to the Decisions
  section if it is one of the load-bearing ones).
- **What breaks downstream without it:** the concrete failure in a later pass.
```

Nothing emitted is skipped. A trivial component still gets one line saying
why it is trivial — silence is indistinguishable from an oversight.

## Decisions and roads not taken

The pass's locked decisions, most load-bearing first:

| Decision | Rejected alternative | Why it lost |
|----------|---------------------|-------------|

A decision with no named alternative is a description, not a decision — if
the alternative was never articulated, write "alternative unrecorded —
inferred: X" and flag it under What to watch.

## Vocabulary

Every term of art used above, one plain sentence each, alphabetical.
The owner listens by voice; an undefined term is a stall.

## What to watch

The lesson's honest edges: open questions and their owners, `(guessed)`
numbers awaiting verification, accepted risks, minor gaps riding along.
This section is what the owner scans before the next client call.

## Check yourself

3–5 questions the owner should now be able to answer, each with a pointer to
the section that answers it — not the answer itself. These stand in for the
live quiz when the lesson is read async.

```markdown
1. <question>? (→ see "<component>")
```

---

## Teaching-mode sections (optional — present only when the matching mode is on)

Declare active modes on a `modes:` line under the title blockquote, e.g.
`> modes: adept, review, teachback`. Reshape modes (`--teachback`, `--socratic`,
`--why`, `--mix`) change how the sections above are produced and add nothing
here. The three emitter modes append their section after "Check yourself":

### `## ADEPT explanations`  (`--adept`)

One block per load-bearing component, all five labels in order:

```markdown
### <component>
- **Analogy:** <the intuition, in everyday terms>
- **Diagram:** <a small ASCII or mermaid sketch>
- **Example:** <a concrete instance from the real artifact>
- **Plain-English:** <the idea in one plain sentence>
- **Technical:** <the precise, vocabulary-carrying statement>
```

### `## Review schedule`  (`--review [spaced]`)

A flashcard deck then a dated retrieval schedule (spacing is the point):

```markdown
Q: <question from a load-bearing fact>
A: <the answer>
(≥ 3 pairs)

Schedule:
- day 1 — re-test cards 1–N
- day 3 — re-test the ones missed on day 1
- day 7 — full deck
- day 21 — full deck
```

### `## Concept map`  (`--map`)

Owner assembles first; the answer edges sit below the marker:

```markdown
Nodes (shuffled): <A> · <B> · <C> · …
Assemble the flow, then check:

<!-- answer -->
- <A> --> <B>
- <B> --> <C>
```
