# Recovery

`cvg compose status` prints one safe next action. Follow `NEXT=`. Do not bypass
a failed contract.

| State | Meaning | One safe next action |
|---|---|---|
| `COMPOSE=BLOCKED` | No prepared plan, or evidence failed verification | Read the status reason; fix the contract; never skip the check |
| `COMPOSE=NEEDS_REVIEW` | Delivery plan exists without current human acceptance | Read `seamwise/delivery-plan.yaml`, then `cvg compose review` |
| `COMPOSE=PREVIEW_READY` | Review is current | Run the exact `NEXT=` from status (`preview` or `materialize`) |
| `COMPOSE=MATERIALIZED` | Tasks and receipts re-hash | `taskspec gate --stamp` on one intended leaf |
| `COMPOSE=ENGINE_UNAVAILABLE` | Binary, version, JSON, or capabilities are incompatible | Install or select the exact supported engine via `CVG_*_BIN` |

## Interrupted materialize

An interrupted materialization may leave the Task-Spec receipt without the
final Converge receipt. Rerun `cvg compose materialize`. Task-Spec proves the
existing bytes are unchanged; Converge writes the composition receipt last.

## Stale review or changed recipe

A changed recipe cannot silently replace a mapped source. Status blocks. Commit
the recipe you intend, then prepare again if the source is allowed to change.

## Loop failures

| Landing | What to do |
|---|---|
| `EXHAUSTED` | Budgets are evidence. Raise them in the signed spec, or split the leaf. |
| `BLOCKED` | Read the handoff. `REFUTED` means fix the work, not the judge. |
| `ERROR` | Engine or coordinator failure. Check `CVG_TASKSPEC_BIN` and the adapter. |
| `CANCELLED` | An external stop arrived. Resume only from the written handoff. |

`--resume` under worktree isolation currently starts a fresh tree at attempt 1.
Do not treat it as a continuation of uncommitted work.

## JSON

```bash
cvg compose status --json
cvg --json compose preview
```

Both emit one `ConvergeCLIResult/v1` document and preserve the exit code.
Branch on `token`, `exit_code`, `changed`, and `dry_run`.
