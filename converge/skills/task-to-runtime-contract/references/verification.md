# Tier-2 verification — grading work with an engine that didn't do the work

## The problem

The task's eval is authored by the same intelligence that implements against it,
and then that intelligence decides whether it passed. That is a closed loop
grading itself.

Code graders catch mechanical wrongness. They do not catch a lookup table that
satisfies the assertion without implementing the behaviour, or an implementation
that meets the letter of the eval while skirting its intent. The field measures
LLM-generated code carrying vulnerabilities at **9.8–42.1%** across benchmarks,
with surviving AI-introduced defects in production repositories past **110,000**
by early 2026. Self-grading is not enough.

## The defense: train/test separation

Borrowed from machine learning — you do not evaluate on the data you trained on.

| Tier | Grader | Catches | Where |
|---|---|---|---|
| **1** | the task's own sealed bash evals | mechanical wrongness | in the loop |
| **2** | a **different-family** model reading the diff, the intent, and a **holdout** it never saw | gamed evals, stub implementations, spec-skirting | before settlement |
| **3** | a human | judgment the spec never captured | PR review, scaled by blast radius |

Two properties make tier 2 real:

**The judge is independent.** Different model *family* — not merely a different
prompt or a different temperature. A model refutes its own family's blind spots
poorly; this is the same cross-family invariant Pass 4 applies to plans, pointed
at diffs. The judge sees the **diff + stated intent + holdout** and is prompted to
**refute by default**. It never sees the worker's transcript — that would let the
worker's reasoning contaminate its grader.

**The criteria are held out.** The spec's `## Exit Check` is what the worker can
see and optimize against. An optional `## Holdout` section carries assertions the
worker never sees, revealed only at verification. You cannot tune to a target you
cannot read.

```markdown
## Exit Check          ← the worker sees this
```bash
eval_1 && eval_2
```

## Holdout             ← revealed only at verify
- The endpoint must stay under 100ms at p99 with 50 concurrent clients.
- A malformed payload must return 400, never 500.
```

## Running it

```bash
cvg verify --task tasks/T-20260519-add-health.md --judge codex
```

```
judge        codex (independent)
blast radius low · holdout present
  - the handler returns a hardcoded {"status":"ok"} without checking the process
reasoning    The eval asserts the response shape, which a constant satisfies…
CHECK_VERIFY=REFUTED
```

Verdicts: `UPHELD` · `REFUTED` · `UNAVAILABLE` · `ERROR`.

## It fails closed

A verdict that cannot be obtained is **never** a pass. Missing engine, malformed
JSON, non-zero exit, timeout — all resolve to `ERROR` or `UNAVAILABLE`, never to
`UPHELD`. This is the whole point: an optimistic verifier is worse than none,
because it manufactures confidence.

## When there is no second engine

Not everyone has two engines installed. The verdict is never silently skipped —
it is recorded as one of three independence levels, exactly like Bind records
`prevent` / `detect` / `unenforced`:

| Available | `independence` | Behaviour |
|---|---|---|
| a different family (codex vs claude) | `independent` | full strength |
| only a different model, same family | `same-family` | runs, **flagged as weaker** |
| one engine only | `none` | verdict `UNAVAILABLE`, recorded |

Whether `UNAVAILABLE` is *acceptable* depends on blast radius:

- **low** — small effort, ≤5 files, nothing sensitive → permitted and recorded.
- **high** — auth, money, migrations, secrets, public API, or L+ effort →
  **blocked**, with three honest exits: install a second engine, reduce the blast
  radius, or `--accept-unverified` to accept the risk in writing.

```
FAIL: no verifier engine installed and blast radius is HIGH.
  install a second engine (codex|kimi|claude), reduce the blast
  radius, or re-run with --accept-unverified to accept the risk.
CHECK_VERIFY=ERROR
```

Same discipline as the capability envelope: **accepting risk is allowed; hiding
it is not.**

## Blast radius

Computed, not claimed:

- **high** if any touched path matches a sensitive surface (auth · session ·
  token · secret · credential · payment · billing · migration · schema), or
  effort is L/XL/XXL, or the change spans more than five files.
- **low** otherwise.

The same signal drives the lane classifier (`cvg lane`), so routing and
verification agree on what "risky" means instead of each inventing its own rule.

## What this is not

It is **not** a second opinion that overrides the eval. Tier 1 still decides
mechanical correctness; tier 2 only ever *adds* a refutation. A `REFUTED` verdict
sends the work back to the loop with concrete findings — it never silently edits
code, and it never grants a pass that tier 1 withheld.

It is also **not** the human gate. Tier 3 remains a person looking at what
survived, and the honest boundary still holds: **the loop converges to green
evals, not to correct outcomes.** Tier 2 narrows the gap between those two; it
does not close it.
