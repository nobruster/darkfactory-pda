# First composed task

This is the complete coordinator lifecycle for one leaf. The recipe must be
committed. Converge asks Seamwise to decompose and Task-Spec to materialize; it
never writes a Task-Spec itself.

```bash
export CVG_TASKSPEC_BIN=/absolute/path/to/task-spec/bin/taskspec
export CVG_SEAMWISE_BIN=/absolute/path/to/seamwise/bin/seamwise

git add recipe.yaml
git commit -m "pin composed delivery recipe"

cvg compose prepare --source recipe.yaml
# COMPOSE=NEEDS_REVIEW

cvg compose review \
  --reviewer "repository-owner" \
  --reason "Ownership, topology, dependencies, and rollback paths are accepted."
# COMPOSE=PREVIEW_READY

cvg compose preview
# COMPOSE=PREVIEW_READY

cvg compose materialize
# COMPOSE=MATERIALIZED

cvg compose status
# COMPOSE=MATERIALIZED
```

Prepare must not emit a TaskPlan. Review records a human decision and does not
compile. Preview asks Seamwise for `seamwise/task-plan.json` plus lineage, then
calls `taskspec plan`. Materialize calls `taskspec batch` and writes
`cvg/receipts/composition/composition-receipt.json` with
`dispatch_authorized: false`.

The leaves are still unsigned:

```bash
grep '^signed_off:' cvg/tasks/T-20260815-health-status.md
# signed_off: false

taskspec gate --stamp cvg/tasks/T-20260815-health-status.md
cvg bind --task cvg/tasks/T-20260815-health-status.md
git add cvg/tasks cvg/execution
git commit -m "authorize and bind health status task"
cvg loop --issue T-20260815-health-status --agent codex
```

Success is both of:

```text
TASK_LOOP=LOCAL_SETTLED
ACCEPTED=1
```

`TASK_LOOP=SETTLED` is also valid when external publication is allowed. Model
narration, a green-looking diff, or the composition receipt alone is not
acceptance.

Default loop settlement can complete on sealed evals without tier-2
verification. Pass `--verify` (or `--judge <engine>`) when you want a
different-family holdout check. See [bind and loop](../guides/bind-and-loop.md)
and [trust](../trust/index.md).
