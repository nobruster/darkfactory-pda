# Compose and settlement

Compose is the cross-engine sequence. Settlement is the task-scoped loop plus
independent Task-Spec acceptance. They are not the same decision.

## Compose states

| Token | Meaning |
|---|---|
| `COMPOSE=NEEDS_REVIEW` | Seamwise prepared a delivery plan; no current human acceptance |
| `COMPOSE=PREVIEW_READY` | Review is current; preview or materialize is next |
| `COMPOSE=MATERIALIZED` | Tasks and receipts re-hash successfully |
| `COMPOSE=BLOCKED` | Evidence failed verification, or nothing is prepared |
| `COMPOSE=ENGINE_UNAVAILABLE` | Binary, version, JSON, or capabilities are incompatible |

`cvg compose status` is read-only and returns exactly one `NEXT=` action. It
blocks on a stale review, changed plan, mismatched task set, changed task
bytes, incompatible engine, or stale receipt.

## What each compose verb may call

| Verb | May call | Must not |
|---|---|---|
| `prepare` | Seamwise prepare | Compile a TaskPlan, invoke Task-Spec, record review |
| `review` | Seamwise review `--accept` | Compile or materialize |
| `preview` | Seamwise compile + `taskspec plan` | Write Task-Spec Markdown |
| `materialize` | `taskspec plan` + `taskspec batch` | Set `dispatch_authorized` or `signed_off` |
| `status` | Seamwise status + local receipt verification | Mutate anything |

Seamwise is resolved only when a compose verb needs it. Task-Spec is resolved
when preview, materialize, or a `cvg tasks` verb needs it. A Seamwise-only
prepare does not require Task-Spec to be installed.

## Settlement tokens

After `taskspec gate --stamp` and `cvg bind`, `cvg loop` runs one assigned
task under iteration, time, token, and path limits.

| Token | Meaning |
|---|---|
| `TASK_LOOP=LOCAL_SETTLED` | Loop converged locally; acceptance recorded |
| `TASK_LOOP=SETTLED` | Same, and external publication was allowed |
| `ACCEPTED=1` | Task-Spec independently accepted the exact handoff and revision |
| `CHECK_VERIFY=UPHELD` | Tier-2 judge did not refute (only if `--verify` / FULL lane) |
| `CHECK_VERIFY=REFUTED` | Tier-2 judge refused settlement |

Sign-off requires a settled loop token **and** `ACCEPTED=1`. The composition
receipt is not that evidence.

Default `cvg loop` on NORMAL/FAST can settle on the sealed eval alone. That is
documented, not hidden. See [trust](../trust/index.md).
