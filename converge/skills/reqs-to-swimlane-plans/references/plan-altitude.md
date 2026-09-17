# Plan altitude — the one guardrail of Pass 3 (no tasks, no code)

Pass 3 produces **plans**, not code and not tasks. A plan describes *what* each
lane contains and *in what order* it is built. This reference draws the altitude
line with worked examples and the rule for pulling a leaked detail back up.

## The one-line test

> Does this line say **what to build and in what order**, or does it say **how to
> build it**? If it's *how* — a query body, a handler body, an atomic task with an
> eval — it has dropped below plan altitude. Push it to Pass 5 (`task-spec`) and
> keep the *responsibility* in prose here.

A plan states responsibilities and sequence. A task states an executable unit with
its own pass/fail check. Code states the implementation. Only the first belongs at
this pass.

## Why the line matters

Pass 3 output is deliberately **un-hardened** — it is *supposed* to have soft spots
that Pass 4's adversary finds and sharpens in place. The moment a plan holds real
code or a task with an eval, it has skipped that review: the code was never
attacked, the seam was never tested, and Pass 5 lost the frozen shape it was meant
to build against. Holding altitude is what keeps the review meaningful.

## Plan altitude vs. below-altitude, side by side

The point is stack-neutral: the left column names a *responsibility and sequence*
in prose; the right column pins an *implementation*. The rows below are drawn from
one worked example — a data-transformation project with a transform pipeline and a
read-only serving layer — but the same split applies to any stack.

| Plan altitude (Pass 3 — keep here) | Below altitude (Pass 5 — move out) |
|---|---|
| A transform stage **dedups duplicate records by business signature and quarantines the rest**. | The literal query that partitions and ranks rows to pick the survivor. |
| The output/contract layer materializes **serving-ready tables shaped to the frozen E4 questions**. | The literal statement that creates a specific published table from a query. |
| The query core exposes **one read-only function per published table**. | A function body that opens a connection and runs a hardcoded read query. |
| Test: **aggregates reconcile to the upstream layer (sum-of-output = sum-of-source)**. | `assert result == 42061.50  # eval` in a `T-*.md` task with a runnable block. |

The left column would read the same to any engineer and leaves the *how* open for
Pass 5. The right column pins an implementation — that is task/code work, and
pinning it here robs Pass 4 of anything to attack.

## Pulling a leaked detail back up

When a draft plan says *"this stage dedups by signature — here's the query:"* split it:

1. **Keep the responsibility.** *"Dedup duplicate records by their non-key business
   signature; keep one canonical survivor, route the rest to quarantine."* That is a
   plan sentence — it says what the layer must do and why.
2. **Move the code.** The concrete query is a Pass 5 atomic task. Delete it from
   the plan; it re-appears as a `tasks/T-*.md` with its own eval (whatever test
   harness the project uses).

Likewise, an atomic task with an eval (`bash_eval:`, an `assert`, a `T-YYYYMMDD-…`
id) does not belong in a plan — the plan names the *test's assertion in prose*
("no NULL measures", "every frozen E4 question maps to an output table"), and Pass 5
writes the runnable eval.

## What the check catches

`scripts/new-plan.sh --check` greps every `swimlanes/*.plan` for head-of-line
altitude leaks and missing structure:

- **Code / query leak** — a line that begins a concrete implementation statement
  rather than describing a responsibility (for example, a line starting with a
  query keyword such as `SELECT` / `INSERT INTO` / `CREATE TABLE|VIEW` /
  `WITH … AS (` / `UPDATE` / `DELETE FROM` / `MERGE INTO`, or an equivalent
  code-body opener in your stack's language).
- **Task / eval leak** — an atomic-task id (`T-######`, a `Task:` bullet) or an
  `eval:` / `acceptance_eval:` / `bash_eval:` block.
- **Missing section** — a plan without Identity / Features / Dependencies / Build
  order / Tests-that-prove / Open-questions is not skimmable or attackable.

A clean `--check` means the plans are at altitude and ready for the Pass 4
adversary. The check is heuristic, not a compiler — a query embedded mid-prose
won't trip it, and judgment still owns the call; the grep just catches the obvious
drops.

## Related boundaries this pass also holds

Altitude is the *primary* guardrail, but two siblings ride with it:

- **Inherit the ADRs; never re-decide them.** A plan cites `docs/adrs/NNNN-*.md`
  (join path, grain, read boundary) — it does not re-settle them. Re-deciding is
  its own failure mode (see the skill's Step 3), distinct from an altitude leak.
- **Don't answer open questions inside the plan.** Anything the ADRs don't cover is
  surfaced in the Open-questions table with an owner and a blocks-build flag — not
  invented into the plan body.
