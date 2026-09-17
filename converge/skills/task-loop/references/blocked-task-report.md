# Blocked Task Report

Emitted by Pass 8 (The Loop) when an issue's own eval stays **RED** — the
`budget_iterations` are exhausted, the failure is a broken eval, or it is an
**upstream gap** the loop must not paper over. A blocked report is a first-class
output: it is what you produce *instead of* a PR. No green eval, no PR — but also
no silent give-up. This report names exactly what failed and who owns the fix.

> The loop owns ONE task deeply and never wanders. When a task cannot go green
> from inside its own `touches_paths`, the honest move is to surface the gap,
> not to widen scope or hand-wave the eval.

---

## Report

- **issue:** `<issue-id>`
- **task-spec:** `<task-id>` (`tasks/<task-id>.md`)
- **branch (intended):** `<branch>`
- **agent:** `<agent>`
- **verdict:** RED (eval did not exit 0)
- **iterations used / budget:** _(n of `budget_iterations`)_

## Failing eval

Which `eval_N()` / Exit Check assertion failed, and what it was asserting.
Name the assertion in the project's own terms — a transform step that did not
complete, an output/contract layer that failed a parity or shape check, a
serving-layer response that did not match the contract, etc.

> Example — a dbt/warehouse project: `eval_2` — bronze row-count parity with a
> source table did not hold; `eval_1` — `dbt build --select <model>` did not
> complete; the serving endpoint (API or MCP tool) did not return the contracted
> payload. Adapt these to whatever build/transform/serve steps your stack uses.

- **failing eval id:** _(e.g. `eval_2`)_
- **what it asserts:** _(one line)_

## Last output

The verbatim tail of the last eval run — the real error, not a paraphrase.
Include the failing command's stderr and any log tail the spec points to
(e.g. a build log the eval writes under `/tmp/`).

```
<paste the last eval output here>
```

## Suspected upstream gap

Why this cannot be settled from inside `<task-id>`'s own `touches_paths`. Name
the concrete missing/wrong thing, not just "it fails":

- [ ] **Precondition unmet** — the state the eval assumes is absent: your
      raw/source tables were never landed (the project's data-prep command has
      not run), or your data store is missing or stale.
- [ ] **A cited ADR is missing or wrong** — the spec references
      `docs/adrs/NNNN-*.md` that does not exist or decides the wrong thing.
- [ ] **A dependency (`depends_on`) is not merged** — an upstream task-spec this
      one builds on has not landed (e.g. the output layer depends on a transform
      step that itself depends on ingest, and that upstream step is not merged).
- [ ] **The runtime contract is missing or stale** — Pass 7 (Bind) has not bound the
      current signed Task-Spec hash to evidence, topology, and enforcement.
- [ ] **The eval itself is broken** — a syntax error / unbound variable in the
      task-spec's bash, not a real assertion failure. Do **not** hack the eval to
      pass; the fix belongs upstream in the task-spec.
- [ ] **Genuinely not settleable in budget** — the task is under-specified or
      larger than one unit and needs re-cutting.

## Which pass owns it

Route the fix to the Converge pass that owns the gap — do not fix it here:

| Suspected gap | Owning pass |
|---|---|
| Precondition / repo terrain wrong (source data not landed, data store stale) | operator / run the project's data-prep command before re-dispatch |
| Missing or wrong cited ADR | **Pass 2** (`tech-req-to-adrs`) |
| Wrong swimlane seam / build order | **Pass 3** (`reqs-to-swimlane-plans`) |
| Eval broken / task under-specified / not atomic | **Pass 5** (`task-spec`) |
| Issue missing / dependency links wrong on the board | **Pass 6 · Register** (`task-specs-to-issues`, opt-in) |
| Missing or stale runtime contract / evidence | **Pass 7 · Bind** (`task-to-runtime-contract`) |
| Dispatch order / dependency not yet merged | **the Manager** — future CI/CD, not a pass and not this loop |

## Next action

State the single next step: which pass to re-open with what change, or the
precondition to satisfy before re-dispatching `--issue <issue-id>`. Then stop.
The loop does not escalate, hop tasks, or open a PR from a red eval.
