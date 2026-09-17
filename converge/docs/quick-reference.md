# Converge quick reference

```bash
export CVG_TASKSPEC_BIN=/absolute/path/to/taskspec
export CVG_SEAMWISE_BIN=/absolute/path/to/seamwise

cvg init
cvg doctor host
cvg compose prepare --source recipe.yaml
cvg compose review --reviewer owner --reason "Topology accepted"
cvg compose preview
cvg compose materialize
cvg compose status

taskspec gate --stamp cvg/tasks/T-…-leaf.md
cvg bind --task cvg/tasks/T-…-leaf.md
cvg loop --issue T-…-leaf --agent codex
cvg loop --issue T-…-leaf --agent codex --verify
```

`cvg tasks plan|new|validate|gate|dod|metrics|rebuild-state` and
`cvg eval|lint|ready|accept|transition` exec the Task-Spec binary. They are
not a second implementation.

## Tokens

| Step | Positive token |
|---|---|
| Prepare | `COMPOSE=NEEDS_REVIEW` |
| Review / preview | `COMPOSE=PREVIEW_READY` |
| Materialize | `COMPOSE=MATERIALIZED` |
| Bind | `CHECK_RUNTIME_CONTRACT=PASS` |
| Loop | `TASK_LOOP=LOCAL_SETTLED` or `TASK_LOOP=SETTLED` |
| Accept | `ACCEPTED=1` |
| Tier-2 | `CHECK_VERIFY=UPHELD` (only if requested) |

## Rules to remember

- Three products: Seamwise decomposes, Task-Spec authorizes and accepts,
  Converge sequences, binds, and loops.
- A composition receipt never authorizes dispatch.
- `signed_off: false` after materialize is required, not a bug.
- Default loop can settle without `--verify`.
- `--json` and `--dry-run` are global.
- Branch on tokens, not prose.
