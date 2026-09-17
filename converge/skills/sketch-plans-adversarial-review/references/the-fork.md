# The Fork — RETIRED (v3.4): Converge is single-path (task-driven)

> **Historical document.** The fork is no longer part of the method — Pass 4 ends
> at **the barrier** (the owner's sign-off), not at a route decision. What survives
> is a *frozen compatibility token* the gate still requires (see the bottom of this
> note). Read this for the rationale; do not read it as a choice to make.
>
> **The fork is collapsed.** Converge no longer chooses between plan-driven (A) and
> task-driven (B). Consensus **always** hands off to task-driven decomposition, because
> `task-spec` is now a six-tier sizing engine (XS/S/M/L leaves + XL/XXL decomposition
> nodes) that scales from a one-liner to a whole backbone — tasks all the way down. The
> old Fork A (wrap the whole system in one plan-driven spec / SDD) is retired: frontier
> models execute well-scoped atoms reliably, and a tree of verified atoms composes back
> up more safely than one monolithic spec. See `../../task-spec/references/concepts/effort-gate.md`.
>
> **What the gate enforces now:** the objection-log's `fork.choice` must be **B**
> (task-driven) with a reason, and every PRD carries a `FORK: B (task-driven)` line. A
> log with `fork.choice: A` is rejected. The rest of this doc is kept as historical
> rationale for *why* the two paths existed and why B won.

---

Converge Pass 4 (Consensus), Step 4. Naming the fork *was* the decision of this pass;
it is now a constant (B). The fork is still declared **at the top of every plan**
(`swimlanes/*.plan`) as `FORK: B (task-driven)` + a one-line reason, and the gate
(`scripts/check-consensus-gate.sh`) fails unless every plan carries it.

## The one question the fork answers

**Where do we draw the boundary we are willing to trust?**

- **Fork A — plan-driven.** Wrap the *whole system* in one trust boundary. Hand
  one coherent, coupled spec to a single autonomous agent. A human holds one big
  end-to-end gate. The unit of trust is the system.
- **Fork B — task-driven.** Draw the boundary around *each unit*. Cut the plans
  into atomic, individually eval-bearing tasks, dispatched per unit. The unit of
  trust is the task; convergence is task-by-task.

Neither is "better" in the abstract. The right fork is the one whose trust
boundary matches how the system actually *verifies*.

## The rubric — decide on verifiability, not size alone

Ask, per system:

| Question | Points to A | Points to B |
|---|---|---|
| Does any single unit verify **in isolation**? | No — only the whole thing proves out | Yes — each unit has a cheap, runnable eval |
| Is the system **small and tightly coupled**? | Yes — the parts don't stand alone | No — clean seams between units |
| Can a human hold **one** end-to-end gate cheaply? | Yes | The gate is naturally per-unit |
| Is the cheapest wrong idea killed by a **whole-run** or a **per-unit** check? | Whole-run | Per-unit |

**Decide on the evals, not the line count.** The deciding test is: *does every
unit — each stage, module, or endpoint — have a cheap, runnable eval?* If yes,
task-by-task convergence beats one big autonomous run → **Fork B**. If nothing
verifies in isolation and the system only makes sense as a whole → **Fork A**.

## Worked example — a data/warehouse project forks

*This is one concrete example, not the required shape.* Consider a project whose
pipeline runs an ingest step into a data store, a multi-stage transform (for
example, a dbt medallion: bronze → silver → gold), then a serving layer (an API,
an MCP tool, or both). Such a system lands on **Fork B**, and both `swimlanes/*.plan`
say so at the top, because:

- The transform is a **deterministic, layered DAG**. Each stage has a known
  input, a known output, and stage-scoped tests that pass or fail **in
  isolation**. One stage + its tests = one atomic, self-checking task.
- The serving layer is a **thin, stateless surface over a frozen contract**: one
  query-core function per published table, one endpoint and one tool per
  question — each independently testable (contract test, endpoint test,
  tool-vs-endpoint parity, read-only isolation check).
- Because every unit has a cheap eval, a whole-spec autonomous run would only
  *blur* the stage boundaries, hide which step regressed, and make the per-stage
  evals unenforceable. Task-driven keeps each defect-handling rule, each output
  table, and each endpoint behind its own green check.

A system that instead had *no* per-unit eval — where the transform and serving
only prove out end-to-end and are too coupled to split — would be **Fork A**:
one coherent spec, one end-to-end eval, one human gate.

## Record the choice AND the why

At the top of every plan, write one of:

```
FORK: B (task-driven) — every layer and endpoint has a cheap runnable eval, so
task-by-task convergence beats one autonomous whole-system run.
```

```
FORK: A (plan-driven) — nothing verifies in isolation; the system is small and
tightly coupled and only proves out as a whole, under one end-to-end gate.
```

The prose form already in this repo's plans is equivalent and also passes the
gate:

```
> **Execution model: FORK B — task-driven.** ...why FORK B fits this build...
```

Both plans must agree on the fork — a split system where lane A is task-driven
and lane B is plan-driven is itself an objection to resolve in Step 3, not a
valid outcome.

## How the hand-off works now

There is only one hand-off, and it is unconditional:

- **→ Pass 5 (`task-spec`).** Cuts the sharpened plans into atomic,
  vendor-portable, self-verifying Task-Specs (`tasks/T-*.md`), each with its own
  runnable eval. From there **Pass 6 Register** (`task-specs-to-issues`, opt-in)
  can put the backlog on a tracker, **Pass 7 Bind**
  (`task-to-runtime-contract`) binds each signed spec to its runtime and emits
  the harness, and **Pass 8** (`task-loop`) drives each issue to a green-eval PR.

> **Historical note — the retired A branch.** Fork A used to hand off to a
> `plans-to-coherent-spec` skill (sometimes called "Pass 5A"), which fused the
> plans into one coupled SDD-style spec under a single end-to-end eval. **That
> skill was deleted** when the fork was removed; a tightly-coupled slice is now
> expressed as a single `L` leaf inside the task tree instead. Do not look for it.

Do not start Pass 5 until the gate is green **and the owner has signed off** —
the barrier is the real exit condition of Pass 4.
