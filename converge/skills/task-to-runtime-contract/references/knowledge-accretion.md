# Knowledge accretion

Generic technology tutorials and TODO-seeded KB trees are not durable project
knowledge. Reusable knowledge must be earned from execution evidence.

## Flow

```text
execution receipt
  -> proposed candidate
  -> owner/reviewer decision
  -> approved project knowledge
  -> future runtime-contract evidence slice
```

## Candidate requirements

A candidate records:

- originating task and Task-Spec hash;
- receipt path and hash;
- kind: `failure`, `pattern`, or `reference`;
- concise reusable summary;
- exact evidence;
- status `proposed`.

The generator never writes into approved knowledge directories. If a candidate
already exists with different content, it writes a `.proposed.md` sibling
instead of overwriting.

## Promotion

Promotion is a human-controlled review action. Approved material may move to:

- `cvg/knowledge/failures/`
- `cvg/knowledge/patterns/`
- `cvg/knowledge/references/`

`pass-to-lesson` may explain the same receipt to a human, but it does not
authorize or write canonical machine knowledge.
