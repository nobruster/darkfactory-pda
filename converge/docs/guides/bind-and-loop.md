# Bind and loop

Materialization creates unsigned Task-Spec Markdown. Bind freezes one signed
revision into an execution profile. The loop never chooses its own work.

## Authorize, then bind

```bash
taskspec gate --stamp cvg/tasks/T-20260815-health-status.md
cvg bind --task cvg/tasks/T-20260815-health-status.md
cvg bind --check --task cvg/tasks/T-20260815-health-status.md
```

Bind verifies the signed Task-Spec, selects the intra-task topology, hash-binds
the evidence slice, and emits portable path guards. Expected token:
`CHECK_RUNTIME_CONTRACT=PASS`.

Commit the bound artifacts before looping:

```bash
git add cvg/tasks cvg/execution
git commit -m "authorize and bind composed task"
```

## Run one issue

```bash
cvg loop --issue T-20260815-health-status --agent codex
cvg loop --estimate --issue T-20260815-health-status
cvg loop --gate-only --issue T-20260815-health-status
```

The kernel enforces iteration, wall-clock, token, and path budgets. An engine
error, timeout, exhausted budget, or uncommitted out-of-scope write is not
success.

`--agent` selects a Converge engine adapter (`codex`, `claude`, `kimi`). Those
adapters are not Task-Spec and not Seamwise. They are how the loop talks to a
coding CLI.

## Tier-2 verification

```bash
cvg loop --issue T-20260815-health-status --agent codex --verify
cvg loop --issue T-20260815-health-status --agent codex --judge kimi
cvg verify --task cvg/tasks/T-20260815-health-status.md --judge kimi
```

Naming `--judge` turns verification on. FULL lane turns it on without being
asked twice. `--no-verify` is explicit.

The judge is supposed to see the diff, the stated intent, and `## Holdout`.
Today the worker brief still names the Task-Spec as its instruction source, so
holdout secrecy is a convention, not a filesystem split. Do not claim otherwise.
See [trust](../trust/index.md).

## Acceptance

The loop asks Task-Spec to accept the exact handoff and task revision. You can
also invoke the engine directly:

```bash
cvg tasks accept cvg/tasks/T-20260815-health-status.md
```

That is `exec taskspec accept …`. Converge does not re-implement acceptance.
